# 📋 Placement Portal

A web-based college placement management system built with Flask. The system provides separate portals for Students, Companies, and Admins — each with their own login, dashboard, and functionality.

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask |
| Database ORM | Flask-SQLAlchemy |
| Database | PostgreSQL (production) / SQLite (dev) |
| Frontend | HTML5 + Bootstrap 5 |
| Templating | Jinja2 |
| Auth | Werkzeug (password hashing) |
| Config | python-dotenv |

---

## ⚙️ Setup and Installation

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd placement_portal
```

**2. Install dependencies**
```bash
pip install flask flask-sqlalchemy werkzeug python-dotenv
```

**3. Create a `.env` file in the root folder**
```
SECRET_KEY=your_secret_key_here
DATABASE_URI=your_database_url_here
```

For local development with SQLite:
```
DATABASE_URI=sqlite:///placement.db
```

**4. Run the application**
```bash
python app.py
```

**5. Open in browser**
```
http://127.0.0.1:5001
```

---

## 🔑 Default Admin Login

| Field | Value |
|-------|-------|
| Username | admin |
| Password | admin123 |

> Change this after first login.

---

## 👥 User Roles

### 🎓 Student
- Register and login at `/student/signin`
- Update profile (department, CGPA, graduation year, resume)
- Browse approved placement drives
- Apply to drives and track application status

### 🏢 Company
- Register at `/company/signup` — requires admin approval before login
- Post placement drives (requires admin approval before visible to students)
- View and manage applicants per drive
- Update applicant status: Applied → Shortlisted → Selected / Rejected

### 🛠️ Admin
- Login at `/admin/signin`
- Approve / Reject / Blacklist companies
- Approve / Reject / Delete drives
- Blacklist / Activate / Delete students
- View all applications across the system

---

## 📁 Project Structure

```
placement_portal/
├── app.py                  Main application
├── .env                    Environment variables (not committed)
├── .gitignore
├── static/
│   ├── style.css           Custom styles
│   └── resumes/            Uploaded student resumes
└── templates/
    ├── base.html           Base template with Bootstrap
    ├── index.html          Landing page
    ├── students/
    │   ├── index.html
    │   ├── login.html
    │   ├── register.html
    │   ├── dashboard.html
    │   ├── drives.html
    │   ├── profile.html
    │   └── history.html
    ├── company/
    │   ├── index.html
    │   ├── login.html
    │   ├── register.html
    │   ├── dashboard.html
    │   ├── profile.html
    │   ├── create_drive.html
    │   ├── edit_drive.html
    │   └── applications.html
    └── admin/
        ├── index.html
        ├── login.html
        ├── dashboard.html
        ├── companies.html
        ├── drives.html
        ├── students.html
        └── applications.html
```

---

## 🔒 Security

- Passwords hashed using Werkzeug's `generate_password_hash`
- Session-based authentication with role-specific keys (`sid`, `cid`, `aid`)
- Route protection via `student_required`, `company_required`, `admin_required` decorators
- Company ownership verified before any drive edit/delete operation
- Secret key and DB URL stored in `.env` — never hardcoded

---

## 📌 Key Routes

| Portal | Route | Description |
|--------|-------|-------------|
| Home | `/` | Landing page |
| Student | `/student/signin` | Student login |
| Student | `/student/home` | Student dashboard |
| Student | `/student/openings` | Browse drives |
| Company | `/company/signin` | Company login |
| Company | `/company/home` | Company dashboard |
| Company | `/company/drive/new` | Post a new drive |
| Admin | `/admin/signin` | Admin login |
| Admin | `/admin/home` | Admin dashboard |
| Admin | `/admin/companies` | Manage companies |
| Admin | `/admin/drives` | Manage drives |
| Admin | `/admin/students` | Manage students |