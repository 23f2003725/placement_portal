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


# ─── MODELS

class Admin(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Student(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(100), unique=True, nullable=False)
    password        = db.Column(db.String(200), nullable=False)
    email           = db.Column(db.String(100), unique=True, nullable=False)
    full_name       = db.Column(db.String(100), nullable=False)
    phone           = db.Column(db.String(20))
    department      = db.Column(db.String(100))
    cgpa            = db.Column(db.Float)
    graduation_year = db.Column(db.Integer)
    resume_file     = db.Column(db.String(200))
    is_active       = db.Column(db.Boolean, default=True)
    applications    = db.relationship('Application', backref='student', lazy=True)


class Company(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(100), unique=True, nullable=False)
    password        = db.Column(db.String(200), nullable=False)
    company_name    = db.Column(db.String(200), nullable=False)
    email           = db.Column(db.String(120), nullable=False)
    hr_contact      = db.Column(db.String(120))
    website         = db.Column(db.String(200))
    description     = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='Pending')
    drives          = db.relationship('PlacementDrive', backref='company', lazy=True)


class PlacementDrive(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    company_id   = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title    = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text)
    eligibility  = db.Column(db.Text)
    package      = db.Column(db.String(100))
    location     = db.Column(db.String(100))
    status       = db.Column(db.String(20), default='Pending')
    deadline     = db.Column(db.String(100), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    applications = db.relationship('Application', backref='drive', lazy=True)


class Application(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id     = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    status       = db.Column(db.String(20), default='Applied')
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)


# ─── DECORATORS

def student_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'sid' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login_student'))
        return f(*args, **kwargs)
    return wrapper


def company_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'cid' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login_company'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'aid' not in session:
            flash("Admin login required.", "warning")
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return wrapper


# ─── HELPER

def fetch_drive(drive_id):
    record = PlacementDrive.query.get_or_404(drive_id)
    if record.company_id != session['cid']:
        flash("Access denied.", "danger")
        return None
    return record


# ─── HOME

@app.route('/')
def home():
    return render_template('index.html')


# ─── STUDENT

@app.route('/student')
def students_portal():
    return render_template('students/index.html')


@app.route('/student/signup', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        username  = request.form['username']
        email     = request.form['email']
        full_name = request.form['full_name']
        password  = request.form['password']
        if Student.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template('students/register.html')
        s           = Student()
        s.username  = username
        s.email     = email
        s.full_name = full_name
        s.password  = generate_password_hash(password)
        db.session.add(s)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login_student'))
    return render_template('students/register.html')


@app.route('/student/signin', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        s = Student.query.filter_by(username=username).first()
        if s and check_password_hash(s.password, password):
            if not s.is_active:
                flash("Your account is disabled. Contact admin.", "danger")
                return render_template('students/login.html')
            session['sid']   = s.id
            session['sname'] = s.full_name
            return redirect(url_for('dashboard_student'))
        flash("Invalid credentials.", "danger")
    return render_template('students/login.html')


@app.route('/student/signout')
def logout_student():
    session.clear()
    return redirect(url_for('login_student'))


@app.route('/student/home')
@student_required
def dashboard_student():
    s           = db.session.get(Student, session['sid'])
    apps        = Application.query.filter_by(student_id=s.id).all()
    open_drives = PlacementDrive.query.filter_by(status='Approved').all()
    applied_ids = {a.drive_id for a in apps}
    return render_template('students/dashboard.html', student=s, applications=apps, drives=open_drives, applied_drive_ids=applied_ids)


@app.route('/student/openings')
@student_required
def browse_drives():
    open_drives = PlacementDrive.query.filter_by(status='Approved').all()
    s           = db.session.get(Student, session['sid'])
    applied_ids = {a.drive_id for a in s.applications}
    return render_template('students/drives.html', drives=open_drives, applied_ids=applied_ids)


@app.route('/student/submit/<int:drive_id>', methods=['POST'])
@student_required
def apply_to_drive(drive_id):
    sid   = session['sid']
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.status != 'Approved':
        flash("This drive is not open.", "danger")
        return redirect(url_for('browse_drives'))
    if Application.query.filter_by(student_id=sid, drive_id=drive_id).first():
        flash("Already applied.", "warning")
        return redirect(url_for('browse_drives'))
    db.session.add(Application(student_id=sid, drive_id=drive_id))
    db.session.commit()
    flash("Application submitted!", "success")
    return redirect(url_for('dashboard_student'))


@app.route('/student/account', methods=['GET', 'POST'])
@student_required
def profile_student():
    s = db.session.get(Student, session['sid'])
    if request.method == 'POST':
        s.full_name       = request.form.get('full_name', s.full_name)
        s.email           = request.form.get('email', s.email)
        s.phone           = request.form.get('phone')
        s.department      = request.form.get('department')
        cgpa              = request.form.get('cgpa')
        s.cgpa            = float(cgpa) if cgpa else s.cgpa
        gy                = request.form.get('graduation_year')
        s.graduation_year = int(gy) if gy else s.graduation_year
        resume = request.files.get('resume')
        if resume and resume.filename:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename      = f"student_{s.id}_{resume.filename}"
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            s.resume_file = filename
        db.session.commit()
        session['sname'] = s.full_name
        flash("Profile updated!", "success")
    return render_template('students/profile.html', student=s)


@app.route('/student/records')
@student_required
def application_history():
    apps = Application.query.filter_by(student_id=session['sid']).all()
    return render_template('students/history.html', applications=apps)


# ─── COMPANY

@app.route('/company')
def company_portal():
    return render_template('company/index.html')


@app.route('/company/signup', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        username     = request.form['username']
        password     = request.form['password']
        company_name = request.form['company_name']
        email        = request.form['email']
        if Company.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template('company/register.html')
        c              = Company()
        c.username     = username
        c.password     = generate_password_hash(password)
        c.company_name = company_name
        c.email        = email
        c.hr_contact   = request.form.get('hr_contact', '')
        c.website      = request.form.get('website', '')
        db.session.add(c)
        db.session.commit()
        flash("Registration successful! Await admin approval.", "success")
        return redirect(url_for('login_company'))
    return render_template('company/register.html')


@app.route('/company/signin', methods=['GET', 'POST'])
def login_company():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        c = Company.query.filter_by(username=username).first()
        if c and check_password_hash(c.password, password):
            if c.approval_status == 'Pending':
                flash("Your account is pending admin approval.", "warning")
                return render_template('company/login.html')
            if c.approval_status in ('Rejected', 'Blacklisted'):
                flash(f"Account {c.approval_status.lower()}. Contact admin.", "danger")
                return render_template('company/login.html')
            session['cid']   = c.id
            session['cname'] = c.company_name
            return redirect(url_for('dashboard_company'))
        flash("Invalid credentials.", "danger")
    return render_template('company/login.html')


@app.route('/company/signout')
def logout_company():
    session.clear()
    return redirect(url_for('login_company'))


@app.route('/company/home')
@company_required
def dashboard_company():
    c      = db.session.get(Company, session['cid'])
    drives = PlacementDrive.query.filter_by(company_id=c.id).all()
    return render_template('company/dashboard.html', company=c, drives=drives)


@app.route('/company/account', methods=['GET', 'POST'])
@company_required
def profile_company():
    c = db.session.get(Company, session['cid'])
    if request.method == 'POST':
        c.company_name = request.form.get('company_name', c.company_name)
        c.email        = request.form.get('email', c.email)
        c.hr_contact   = request.form.get('hr_contact', c.hr_contact)
        c.website      = request.form.get('website', c.website)
        c.description  = request.form.get('description', c.description)
        db.session.commit()
        session['cname'] = c.company_name
        flash("Profile updated!", "success")
    return render_template('company/profile.html', company=c)


@app.route('/company/drive/new', methods=['GET', 'POST'])
@company_required
def post_drive():
    if request.method == 'POST':
        d             = PlacementDrive()
        d.company_id  = session['cid']
        d.job_title   = request.form['job_title']
        d.description = request.form.get('description', '')
        d.eligibility = request.form.get('eligibility', '')
        d.package     = request.form.get('package', '')
        d.location    = request.form.get('location', '')
        d.deadline    = request.form.get('deadline', '')
        db.session.add(d)
        db.session.commit()
        flash("Drive submitted for admin approval.", "success")
        return redirect(url_for('dashboard_company'))
    return render_template('company/create_drive.html')


@app.route('/company/drive/update/<int:drive_id>', methods=['GET', 'POST'])
@company_required
def modify_drive(drive_id):
    d = fetch_drive(drive_id)
    if not d:
        return redirect(url_for('dashboard_company'))
    if request.method == 'POST':
        d.job_title   = request.form['job_title']
        d.description = request.form.get('description', '')
        d.eligibility = request.form.get('eligibility', '')
        d.package     = request.form.get('package', '')
        d.location    = request.form.get('location', '')
        d.deadline    = request.form.get('deadline', '')
        d.status      = 'Pending'
        db.session.commit()
        flash("Drive updated and re-submitted for approval.", "success")
        return redirect(url_for('dashboard_company'))
    return render_template('company/edit_drive.html', drive=d)


@app.route('/company/drive/remove/<int:drive_id>', methods=['POST'])
@company_required
def remove_drive(drive_id):
    d = fetch_drive(drive_id)
    if not d:
        return redirect(url_for('dashboard_company'))
    Application.query.filter_by(drive_id=d.id).delete()
    db.session.delete(d)
    db.session.commit()
    flash("Drive deleted.", "success")
    return redirect(url_for('dashboard_company'))


@app.route('/company/drive/close/<int:drive_id>', methods=['POST'])
@company_required
def close_drive(drive_id):
    d = fetch_drive(drive_id)
    if not d:
        return redirect(url_for('dashboard_company'))
    d.status = 'Closed'
    db.session.commit()
    flash("Drive closed.", "success")
    return redirect(url_for('dashboard_company'))


@app.route('/company/drive/applicants/<int:drive_id>')
@company_required
def drive_applicants(drive_id):
    d    = fetch_drive(drive_id)
    if not d:
        return redirect(url_for('dashboard_company'))
    apps = Application.query.filter_by(drive_id=d.id).all()
    return render_template('company/applications.html', drive=d, applications=apps)


@app.route('/company/applicant/update/<int:app_id>', methods=['POST'])
@company_required
def update_applicant_status(app_id):
    app_record = Application.query.get_or_404(app_id)
    d          = fetch_drive(app_record.drive_id)
    if not d:
        return redirect(url_for('dashboard_company'))
    new_status = request.form.get('status')
    if new_status in ('Applied', 'Shortlisted', 'Selected', 'Rejected'):
        app_record.status = new_status
        db.session.commit()
        flash("Status updated.", "success")
    else:
        flash("Invalid status.", "danger")
    return redirect(url_for('drive_applicants', drive_id=d.id))


# ─── ADMIN

@app.route('/admin')
def admin_portal():
    return render_template('admin/index.html')


@app.route('/admin/signin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['aid'] = admin.id
            return redirect(url_for('dashboard_admin'))
        flash("Invalid credentials.", "danger")
    return render_template('admin/login.html')


@app.route('/admin/signout')
def logout_admin():
    session.clear()
    return redirect(url_for('login_admin'))


@app.route('/admin/home')
@admin_required
def dashboard_admin():
    return render_template('admin/dashboard.html',
        total_students    = Student.query.count(),
        total_companies   = Company.query.count(),
        total_drives      = PlacementDrive.query.count(),
        total_apps        = Application.query.count(),
        pending_companies = Company.query.filter_by(approval_status='Pending').all(),
        pending_drives    = PlacementDrive.query.filter_by(status='Pending').all()
    )


@app.route('/admin/companies')
@admin_required
def manage_companies():
    search = request.args.get('search', '')
    q      = Company.query
    if search:
        q = q.filter(Company.company_name.ilike(f'%{search}%') | Company.username.ilike(f'%{search}%'))
    return render_template('admin/companies.html', companies=q.all(), search=search)


@app.route('/admin/company/approve/<int:company_id>', methods=['POST'])
@admin_required
def approve_company(company_id):
    comp                 = Company.query.get_or_404(company_id)
    comp.approval_status = 'Approved'
    db.session.commit()
    flash(f'{comp.company_name} approved.', 'success')
    return redirect(url_for('manage_companies'))


@app.route('/admin/company/reject/<int:company_id>', methods=['POST'])
@admin_required
def reject_company(company_id):
    comp                 = Company.query.get_or_404(company_id)
    comp.approval_status = 'Rejected'
    db.session.commit()
    flash(f'{comp.company_name} rejected.', 'warning')
    return redirect(url_for('manage_companies'))


@app.route('/admin/company/blacklist/<int:company_id>', methods=['POST'])
@admin_required
def blacklist_company(company_id):
    comp                 = Company.query.get_or_404(company_id)
    comp.approval_status = 'Blacklisted'
    db.session.commit()
    flash(f'{comp.company_name} blacklisted.', 'danger')
    return redirect(url_for('manage_companies'))


@app.route('/admin/company/delete/<int:company_id>', methods=['POST'])
@admin_required
def delete_company(company_id):
    comp = Company.query.get_or_404(company_id)
    for drv in comp.drives:
        Application.query.filter_by(drive_id=drv.id).delete()
        db.session.delete(drv)
    db.session.delete(comp)
    db.session.commit()
    flash("Company deleted.", "success")
    return redirect(url_for('manage_companies'))


@app.route('/admin/drives')
@admin_required
def manage_drives():
    return render_template('admin/drives.html', drives=PlacementDrive.query.all())


@app.route('/admin/drive/approve/<int:drive_id>', methods=['POST'])
@admin_required
def approve_drive(drive_id):
    drv        = PlacementDrive.query.get_or_404(drive_id)
    drv.status = 'Approved'
    db.session.commit()
    flash("Drive approved.", "success")
    return redirect(url_for('manage_drives'))


@app.route('/admin/drive/reject/<int:drive_id>', methods=['POST'])
@admin_required
def reject_drive(drive_id):
    drv        = PlacementDrive.query.get_or_404(drive_id)
    drv.status = 'Rejected'
    db.session.commit()
    flash("Drive rejected.", "warning")
    return redirect(url_for('manage_drives'))


@app.route('/admin/drive/delete/<int:drive_id>', methods=['POST'])
@admin_required
def delete_drive(drive_id):
    drv = PlacementDrive.query.get_or_404(drive_id)
    Application.query.filter_by(drive_id=drive_id).delete()
    db.session.delete(drv)
    db.session.commit()
    flash("Drive deleted.", "success")
    return redirect(url_for('manage_drives'))


@app.route('/admin/students')
@admin_required
def manage_students():
    search = request.args.get('search', '')
    q      = Student.query
    if search:
        from sqlalchemy import or_
        filters = [
            Student.full_name.ilike(f'%{search}%'),
            Student.username.ilike(f'%{search}%'),
            Student.email.ilike(f'%{search}%')
        ]
        if search.isdigit():
            filters.append(Student.id == int(search))
        q = q.filter(or_(*filters))
    return render_template('admin/students.html', students=q.all(), search=search)


@app.route('/admin/student/blacklist/<int:student_id>', methods=['POST'])
@admin_required
def blacklist_student(student_id):
    stu           = Student.query.get_or_404(student_id)
    stu.is_active = False
    db.session.commit()
    flash(f'{stu.full_name} blacklisted.', 'danger')
    return redirect(url_for('manage_students'))


@app.route('/admin/student/activate/<int:student_id>', methods=['POST'])
@admin_required
def activate_student(student_id):
    stu           = Student.query.get_or_404(student_id)
    stu.is_active = True
    db.session.commit()
    flash(f'{stu.full_name} re-activated.', 'success')
    return redirect(url_for('manage_students'))


@app.route('/admin/student/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    stu = Student.query.get_or_404(student_id)
    Application.query.filter_by(student_id=student_id).delete()
    db.session.delete(stu)
    db.session.commit()
    flash("Student deleted.", "success")
    return redirect(url_for('manage_students'))


@app.route('/admin/applications')
@admin_required
def manage_applications():
    return render_template('admin/applications.html', applications=Application.query.all())


# ─── INIT

def init_db():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        default_admin          = Admin()
        default_admin.username = 'admin'
        default_admin.password = generate_password_hash('admin123')
        db.session.add(default_admin)
        db.session.commit()

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5001)