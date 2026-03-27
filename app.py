import os
import random
import string
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

from models import db, User, AttendanceSession, AttendanceRecord, Notice

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-super-secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Create an Admin
    if not User.query.filter_by(username='admin123').first():
        admin = User(
            username='admin123',
            password=generate_password_hash('admin123'),
            role='admin',
            name='System Administrator',
            avatar='default.png'
        )
        db.session.add(admin)
        
    # Create a dummy teacher
    if not User.query.filter_by(username='teacher1').first():
        teacher = User(
            username='teacher1',
            password=generate_password_hash('password'),
            role='teacher',
            name='Dr. Smith',
            course='Computer Science'
        )
        db.session.add(teacher)
    
    # Create a dummy student
    if not User.query.filter_by(username='student1').first():
        student = User(
            username='student1',
            password=generate_password_hash('password'),
            role='student',
            name='Alice Johnson',
            course='Computer Science',
            year='2nd Year'
        )
        db.session.add(student)
    db.session.commit()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- CLI Commands -----------------
@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    print("Dropped and created the database tables.")

# ----------------- Routes -----------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        if current_user.role == 'student':
            current_user.course = request.form.get('course')
            current_user.year = request.form.get('year')
        
        dob = request.form.get('dob')
        if dob:
            current_user.dob = datetime.strptime(dob, '%Y-%m-%d').date()
            
        current_user.gender = request.form.get('gender')
        
        # Handle avatar upload
        file = request.files.get('avatar')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"{current_user.username}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.avatar = filename
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html')

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role not in ['teacher', 'admin']:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        course = request.form.get('course')
        year = request.form.get('year')
        
        if User.query.filter_by(username=username).first():
            flash('Username/ID already exists.', 'danger')
        else:
            student = User(
                username=username,
                password=generate_password_hash(password),
                role='student',
                name=name,
                course=course,
                year=year
            )
            db.session.add(student)
            db.session.commit()
            flash(f'Student {name} added successfully!', 'success')
            return redirect(url_for('teacher_dashboard') if current_user.role == 'teacher' else url_for('admin_dashboard'))
            
    return render_template('add_student.html')

@app.route('/student_directory')
@login_required
def student_directory():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
        
    students = User.query.filter_by(role='student').all()
    # Simple overall stat for context
    total_sessions = AttendanceSession.query.count()
    
    # We can calculate percentage directly in template or here
    return render_template('student_directory.html', students=students, total_sessions=total_sessions)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    teachers = User.query.filter_by(role='teacher').all()
    students = User.query.filter_by(role='student').all()
    
    return render_template('admin_dashboard.html', teachers=teachers, students=students)

@app.route('/add_teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(username=username).first():
            flash('Teacher ID already exists.', 'danger')
        else:
            teacher = User(
                username=username,
                password=generate_password_hash(password),
                role='teacher',
                name=name
            )
            db.session.add(teacher)
            db.session.commit()
            flash(f'Teacher {name} added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
    return render_template('add_teacher.html')

@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    # Analytics
    sessions = AttendanceSession.query.filter_by(teacher_id=current_user.id).order_by(AttendanceSession.date.desc()).all()
    # Basic stat: total sessions
    total_sessions = len(sessions)
    
    return render_template('teacher_dashboard.html', sessions=sessions, total_sessions=total_sessions)

@app.route('/create_session', methods=['GET', 'POST'])
@login_required
def create_session():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        subject = request.form.get('subject')
        # Generate a random 6-character alphanumeric code
        session_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        new_session = AttendanceSession(
            teacher_id=current_user.id,
            session_code=session_code,
            subject=subject,
            is_active=True
        )
        db.session.add(new_session)
        db.session.commit()
        flash(f'Session created successfully! Code: {session_code}', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('create_session.html')

@app.route('/view_attendance/<int:session_id>')
@login_required
def view_attendance(session_id):
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
        
    session_obj = AttendanceSession.query.get_or_404(session_id)
    if session_obj.teacher_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('teacher_dashboard'))
        
    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    return render_template('view_attendance.html', session=session_obj, records=records)

@app.route('/end_session/<int:session_id>')
@login_required
def end_session(session_id):
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
        
    session_obj = AttendanceSession.query.get_or_404(session_id)
    if session_obj.teacher_id == current_user.id:
        session_obj.is_active = False
        db.session.commit()
        flash('Session ended.', 'info')
    return redirect(url_for('teacher_dashboard'))

@app.route('/post_notice', methods=['GET', 'POST'])
@login_required
def post_notice():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        notice = Notice(teacher_id=current_user.id, title=title, content=content)
        db.session.add(notice)
        db.session.commit()
        flash('Notice posted successfully.', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('post_notice.html')

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    records = AttendanceRecord.query.filter_by(student_id=current_user.id).order_by(AttendanceRecord.timestamp.desc()).all()
    total_attended = len(records)
    
    # Subject-wise attendance
    subjects_stats = {}
    
    # Monthly attendance
    monthly_stats = {}
    
    # Pre-fetch total sessions per subject to prevent N+1 queries in the loop
    all_sessions = AttendanceSession.query.all()
    total_subj_sessions = {}
    for s in all_sessions:
        total_subj_sessions[s.subject] = total_subj_sessions.get(s.subject, 0) + 1
        
    for r in records:
        subj = r.session.subject
        if subj not in subjects_stats:
            subjects_stats[subj] = {
                'attended': 0,
                'total': total_subj_sessions.get(subj, 0)
            }
        subjects_stats[subj]['attended'] += 1
        
        month_str = r.timestamp.strftime('%B %Y')
        if month_str not in monthly_stats:
            monthly_stats[month_str] = 0
        monthly_stats[month_str] += 1
    
    # Get latest notices
    notices = Notice.query.order_by(Notice.timestamp.desc()).limit(5).all()
    
    return render_template('student_dashboard.html', 
                           records=records, 
                           total_attended=total_attended, 
                           notices=notices,
                           subjects_stats=subjects_stats,
                           monthly_stats=monthly_stats)

@app.route('/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        code = request.form.get('session_code')
        
        # Verify session
        session_obj = AttendanceSession.query.filter_by(session_code=code, is_active=True).first()
        if not session_obj:
            flash('Invalid or expired session code.', 'danger')
            return redirect(url_for('mark_attendance'))
            
        # Check if already marked
        existing = AttendanceRecord.query.filter_by(session_id=session_obj.id, student_id=current_user.id).first()
        if existing:
            flash('Attendance already marked for this session.', 'info')
            return redirect(url_for('student_dashboard'))
            
        # Record attendance
        record = AttendanceRecord(session_id=session_obj.id, student_id=current_user.id)
        db.session.add(record)
        db.session.commit()
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('student_dashboard'))
        
    return render_template('mark_attendance.html')

if __name__ == '__main__':
    app.run(debug=True)
