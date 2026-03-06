from flask import Flask, redirect, render_template, request, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'resumes')

db = SQLAlchemy(app)


# MODELS ---------------------

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    graduation_year = db.Column(db.Integer)
    resume_file = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    applications = db.relationship('Application', backref='student', lazy=True)


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    hr_contact = db.Column(db.String(120))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='Pending')
    drives = db.relationship('PlacementDrive', backref='company', lazy=True)


class PlacementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    eligibility = db.Column(db.Text)
    package = db.Column(db.String(100))
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Pending')
    deadline = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    applications = db.relationship('Application', backref='drive', lazy=True)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    status = db.Column(db.String(20), default='Applied')
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)


# HELPERS ---------------------

def student_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'student_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return wrapper


def company_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'company_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('company_login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Admin login required.", "warning")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper


def get_company_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != session['company_id']:
        flash("Access denied.", "danger")
        return None
    return drive


# HOME ROUTE

@app.route('/')
def home():
    return render_template('index.html')


# STUDENT ROUTES ----------------------

@app.route('/students')
def student_home():
    return render_template('students/index.html')


@app.route('/students/register', methods=['GET', 'POST'])
def student_register():

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        full_name = request.form['full_name']
        password = request.form['password']
        if Student.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return render_template("students/register.html")
        new_student = Student(username=username, email=email, full_name=full_name, password=generate_password_hash(password))
        db.session.add(new_student)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('student_login'))
    return render_template('students/register.html')


@app.route('/students/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Student.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("your account is disabled", "danger")
                return render_template("students/login.html")
            session['student_id'] = user.id
            session['full_name'] = user.full_name
            return redirect(url_for('student_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('students/login.html')


@app.route('/students/logout')
def student_logout():
    session.clear()
    return redirect(url_for('student_login'))


@app.route('/students/dashboard')
@student_required
def student_dashboard():
    student = Student.query.get(session['student_id'])
    applications = Application.query.filter_by(student_id=student.id).all()
    approved_drives = PlacementDrive.query.filter_by(status="Approved").all()
    applied_ids = {a.drive_id for a in applications}

    return render_template('students/dashboard.html', student=student, applications=applications, drives=approved_drives, applied_drive_ids=applied_ids)

@app.route('/students/drives')
@student_required
def view_drives():
    drives = PlacementDrive.query.filter_by(status='Approved').all()
    student = Student.query.get(session['student_id'])
    applied_ids = {a.drive_id for a in student.applications}
    return render_template('students/drives.html', drives=drives, applied_ids=applied_ids)

@app.route('/students/apply/<int:drive_id>', methods=['POST'])
@student_required
def student_apply(drive_id):
    student_id = session['student_id']
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.status != 'Approved':
        flash('This drive is not open.', 'danger')
        return redirect(url_for('view_drives'))
    if Application.query.filter_by(student_id=student_id, drive_id=drive_id).first():
        flash('Already applied.', 'warning')
        return redirect(url_for('view_drives'))
    db.session.add(Application(student_id=student_id, drive_id=drive_id))
    db.session.commit()
    flash('Application submitted!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/students/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    student = Student.query.get(session['student_id'])
    if request.method == 'POST':
        student.full_name       = request.form.get('full_name', student.full_name)
        student.email           = request.form.get('email', student.email)
        student.phone           = request.form.get('phone')
        student.department      = request.form.get('department')
        cgpa = request.form.get('cgpa')
        student.cgpa = float(cgpa) if cgpa else student.cgpa
        gy = request.form.get('graduation_year')
        student.graduation_year = int(gy) if gy else student.graduation_year
        resume = request.files.get('resume')
        if resume and resume.filename:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = f"student_{student.id}_{resume.filename}"
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            student.resume_file = filename
        db.session.commit()
        session['full_name'] = student.full_name
        flash('Profile updated!', 'success')
    return render_template('students/profile.html', student=student)

@app.route('/students/history')
@student_required
def student_history():
    apps = Application.query.filter_by(student_id=session['student_id']).all()
    return render_template('students/history.html', applications=apps)



# COMPANY ROUTES ----------------------

@app.route('/company')
def company_home():
    return render_template('company/index.html')


@app.route('/company/register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        company_name = request.form['company_name']
        email = request.form['email']
        if Company.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return render_template("company/register.html")
        company = Company(username=username, password=generate_password_hash(password), company_name=company_name, email=email)
        db.session.add(company)
        db.session.commit()
        flash("Registration successful", "success")
        return redirect(url_for('company_login'))
    return render_template('company/register.html')


@app.route('/company/login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        company = Company.query.filter_by(username=username).first()
        if company and check_password_hash(company.password, password):
            if company.approval_status == 'Pending':
                flash('Pending admin approval.', 'warning')
                return render_template('company/login.html')
            if company.approval_status in ('Rejected', 'Blacklisted'):
                flash(f'Account {company.approval_status.lower()}. Contact admin.', 'danger')
                return render_template('company/login.html')
            session['company_id'] = company.id
            session['company_name'] = company.company_name
            return redirect(url_for('company_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('company/login.html')


@app.route('/company/dashboard')
@company_required
def company_dashboard():
    company = Company.query.get(session['company_id'])
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return render_template('company/dashboard.html', company=company, drives=drives)

@app.route('/company/logout')
def company_logout():
    session.clear()
    return redirect(url_for('company_login'))

@app.route('/company/profile', methods=['GET', 'POST'])
@company_required
def company_profile():
    company = Company.query.get(session['company_id'])
    if request.method == 'POST':
        company.company_name = request.form['company_name']
        company.email = request.form['email']
        company.hr_contact = request.form.get('hr_contact')
        company.website = request.form.get('website')
        company.description = request.form.get('description')
        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for('company_profile'))
    return render_template("company/profile.html", company=company)

@app.route('/company/drives/create', methods=['GET', 'POST'])
@company_required
def company_create_drive():
    if request.method == 'POST':
        drive = PlacementDrive(
            company_id=session['company_id'],
            job_title=request.form['job_title'],
            description=request.form.get('description'),
            eligibility=request.form.get('eligibility'),
            package=request.form.get('package'),
            location=request.form.get('location'),
            deadline=request.form.get('deadline')
        )
        db.session.add(drive)
        db.session.commit()
        flash("Drive created successfully", "success")
        return redirect(url_for('company_dashboard'))
    return render_template("company/create_drive.html")

@app.route('/company/drives/edit/<int:drive_id>', methods=['GET', 'POST'])
@company_required
def company_edit_drive(drive_id):
    drive = get_company_drive(drive_id)
    if not drive:
        return redirect(url_for('company_dashboard'))
    if request.method == 'POST':
        drive.job_title = request.form['job_title']
        drive.description = request.form.get('description')
        drive.eligibility = request.form.get('eligibility')
        drive.package = request.form.get('package')
        drive.location = request.form.get('location')
        drive.deadline = request.form.get('deadline')
        drive.status = 'Pending'
        db.session.commit()
        flash("Drive updated successfully", "success")
        return redirect(url_for('company_dashboard'))
    return render_template("company/edit_drive.html", drive=drive)

@app.route('/company/drives/delete/<int:drive_id>', methods=['POST'])
@company_required
def company_delete_drive(drive_id):
    drive = get_company_drive(drive_id)
    if not drive:
        return redirect(url_for('company_dashboard'))
    Application.query.filter_by(drive_id=drive.id).delete()
    db.session.delete(drive)
    db.session.commit()
    flash("Drive deleted successfully", "success")
    return redirect(url_for('company_dashboard'))

@app.route('/company/drives/close/<int:drive_id>', methods=['POST'])
@company_required
def company_close_drive(drive_id):
    drive = get_company_drive(drive_id)
    if not drive:
        return redirect(url_for('company_dashboard'))
    drive.status = "Closed"
    db.session.commit()
    flash("Drive closed successfully", "success")
    return redirect(url_for('company_dashboard'))

@app.route('/company/drives/applications/<int:drive_id>')
@company_required
def company_view_applications(drive_id):
    drive = get_company_drive(drive_id)
    if not drive:
        return redirect(url_for('company_dashboard'))
    applications = Application.query.filter_by(drive_id=drive.id).all()
    return render_template("company/applications.html", drive=drive, applications=applications)

@app.route('/company/drives/applications/update/<int:application_id>', methods=['POST'])
@company_required
def company_update_application(application_id):
    application = Application.query.get_or_404(application_id)
    drive = get_company_drive(application.drive_id)
    if not drive:
        return redirect(url_for('company_dashboard'))
    new_status = request.form['status']
    if new_status not in ['Applied', 'Shortlisted', 'Selected', 'Rejected']:
        flash("Invalid status", "danger")
        return redirect(url_for('company_view_applications', drive_id=drive.id))
    application.status = new_status
    db.session.commit()
    flash("Application status updated", "success")
    return redirect(url_for('company_view_applications', drive_id=drive.id))



# ADMIN ROUTES -------------------


@app.route('/admin')
def admin_home():
    return render_template('admin/index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html',
        total_students  = Student.query.count(),
        total_companies = Company.query.count(),
        total_drives    = PlacementDrive.query.count(),
        total_apps      = Application.query.count(),
        pending_companies = Company.query.filter_by(approval_status='Pending').all(),
        pending_drives    = PlacementDrive.query.filter_by(status='Pending').all()
    )

@app.route('/admin/companies')
@admin_required
def admin_companies():
    search = request.args.get('search', '')
    q = Company.query
    if search:
        q = q.filter(Company.company_name.ilike(f'%{search}%') | Company.username.ilike(f'%{search}%'))
    return render_template('admin/companies.html', companies=q.all(), search=search)

@app.route('/admin/companies/approve/<int:company_id>', methods=['POST'])
@admin_required
def approved_companies(company_id):
    c = Company.query.get_or_404(company_id)
    c.approval_status = 'Approved'
    db.session.commit()
    flash(f'{c.company_name} approved.', 'success')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/reject/<int:company_id>', methods=['POST'])
@admin_required
def rejected_companies(company_id):
    c = Company.query.get_or_404(company_id)
    c.approval_status = 'Rejected'
    db.session.commit()
    flash(f'{c.company_name} rejected.', 'warning')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/blacklist/<int:company_id>', methods=['POST'])
@admin_required
def blacklisted_companies(company_id):
    c = Company.query.get_or_404(company_id)
    c.approval_status = 'Blacklisted'
    db.session.commit()
    flash(f'{c.company_name} blacklisted.', 'danger')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/delete/<int:company_id>', methods=['POST'])
@admin_required
def deleted_companies(company_id):
    c = Company.query.get_or_404(company_id)
    for d in c.drives:
        Application.query.filter_by(drive_id=d.id).delete()
        db.session.delete(d)
    db.session.delete(c)
    db.session.commit()
    flash('Company deleted.', 'success')
    return redirect(url_for('admin_companies'))

@app.route('/admin/drives')
@admin_required
def admin_drives():
    return render_template('admin/drives.html', drives=PlacementDrive.query.all())

@app.route('/admin/drives/approve/<int:drive_id>', methods=['POST'])
@admin_required
def approved_drives(drive_id):
    d = PlacementDrive.query.get_or_404(drive_id)
    d.status = 'Approved'
    db.session.commit()
    flash('Drive approved', 'success')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drives/reject/<int:drive_id>', methods=['POST'])
@admin_required
def rejected_drives(drive_id):
    d = PlacementDrive.query.get_or_404(drive_id)
    d.status = 'Rejected'
    db.session.commit()
    flash('Drive rejected.', 'warning')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drives/delete/<int:drive_id>', methods=['POST'])
@admin_required
def deleted_drives(drive_id):
    d = PlacementDrive.query.get_or_404(drive_id)
    Application.query.filter_by(drive_id=drive_id).delete()
    db.session.delete(d)
    db.session.commit()
    flash('Drive deleted.', 'success')
    return redirect(url_for('admin_drives'))

@app.route('/admin/students')
@admin_required
def admin_students():
    search = request.args.get('search', '')
    q = Student.query
    if search:
        filters = [Student.full_name.ilike(f'%{search}%'), Student.username.ilike(f'%{search}%'), Student.email.ilike(f'%{search}%')]
        if search.isdigit():
            filters.append(Student.id == int(search))
        from sqlalchemy import or_
        q = q.filter(or_(*filters))
    return render_template('admin/students.html', students=q.all(), search=search)

@app.route('/admin/students/blacklist/<int:student_id>', methods=['POST'])
@admin_required
def blacklisted_students(student_id):
    s = Student.query.get_or_404(student_id)
    s.is_active = False
    db.session.commit()
    flash(f'{s.full_name} blacklisted.', 'danger')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/activate/<int:student_id>', methods=['POST'])
@admin_required
def activated_students(student_id):
    s = Student.query.get_or_404(student_id)
    s.is_active = True
    db.session.commit()
    flash(f'{s.full_name} re-activated.', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/delete/<int:student_id>', methods=['POST'])
@admin_required
def deleted_students(student_id):
    s = Student.query.get_or_404(student_id)
    Application.query.filter_by(student_id=student_id).delete()
    db.session.delete(s)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/applications')
@admin_required
def admin_applications():
    return render_template('admin/applications.html', applications=Application.query.all())

# init ----------------

with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        db.session.add(Admin(username='admin', password=generate_password_hash('admin123')))
        db.session.commit()

if __name__ == '__main__':
    port = 5001
    app.run(debug=True, port=port)