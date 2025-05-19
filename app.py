from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_cors import CORS
import sqlite3
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory, abort
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='template')
app.secret_key = 'your_secret_key'  # for flashing messages
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = 'uploads'  # assuming uploads/bills/

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
CORS(app)

# --- Database Initialization ---
def init_db():
    if not os.path.exists('database.db'):
        print("Creating database...")

    conn = sqlite3.connect('database.db')
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            proof_filename TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Cases table with foreign key reference to users(id)
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            case_id TEXT NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            notes TEXT,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            type TEXT,
            FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Record Permission table
    c.execute('''
        CREATE TABLE IF NOT EXISTS record_permission(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            granted_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

     # Notifications table
    c.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
''')


    # Insurance Claims table
    c.execute('''
        CREATE TABLE IF NOT EXISTS insurance_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            insurance_company_id INTEGER NOT NULL,
            policy_number TEXT NOT NULL,
            case_id TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            bills_path TEXT NOT NULL,
            additional_details TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(patient_id) REFERENCES users(id),
            FOREIGN KEY(insurance_company_id) REFERENCES users(id)
        );
    ''')



    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('database.db')  # Always use 'database.db'
    conn.row_factory = sqlite3.Row  # To access rows as dictionaries
    return conn

# Call the init_db function to ensure the database is set up





def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Routes ---
@app.route('/')
def index():
    return render_template('home.html')

def fix_file_paths():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT id, file_path FROM records")
    rows = c.fetchall()


    for row in rows:
        case_id, path = row
        if "\\" in path:
            fixed_path = path.replace("\\", "/")
            c.execute("UPDATE records SET file_path = ? WHERE id = ?", (fixed_path, case_id))
            print(f"Fixed path for case ID {case_id}: {fixed_path}")
    
    c.execute("SELECT id, bills_path FROM insurance_claims")
    rowss = c.fetchall()
    
    for row in rowss:
        id, path = row
        if "\\" in path:
            fixed_path = path.replace("\\", "/")
            c.execute("UPDATE insurance_claims SET bills_path = ? WHERE id = ?", (fixed_path, id))
            print(f"Fixed path for  ID {id}: {fixed_path}")

    conn.commit()
    conn.close()
    print("File path normalization completed.")

@app.route('/register', methods=['GET', 'POST'])
def register():
    print(os.path.exists('database.db'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')
        file = request.files['fileUpload']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('register'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace("\\", "/")
            file.save(file_path)
        else:
            flash("Invalid file format.")
            return redirect(url_for('register'))

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()

            # Insert into users table
            c.execute(''' 
                INSERT INTO users (name, email, role, proof_filename, password) 
                VALUES (?, ?, ?, ?, ?)''', 
                (name, email, role, filename, password))

            # If the role is 'insurance_company', also insert into the insurance_companies table
            if role == 'Insurance Companies':
                c.execute(''' 
                    INSERT INTO insurance_companies (name) 
                    VALUES (?)''', 
                    (name,))

            conn.commit()
            conn.close()
            flash("Registration successful!")
            return redirect(url_for('index1'))  # Redirect to login page or dashboard
        except sqlite3.IntegrityError:
            flash("Email already exists.")
            return redirect(url_for('register'))

    return render_template('index2.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id, name, role, password FROM users WHERE email = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user is None:
            flash("User has not registered.")
            return redirect(url_for('login'))
        elif user[3] != password:
            flash("Invalid password.")
            return redirect(url_for('login'))
        else:
            session['role'] = user[2]  # role
            session['email'] = username  # email
            session['user_id'] = user[0]
            return redirect(url_for('dashboard_redirect'))

    return render_template('index1.html')

@app.template_filter('basename')
def basename_filter(value):
    return os.path.basename(value)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

    user_role = session.get('role')
    user_email = session.get('email')

    if user_role != 'Hospital Administrator' and user_role != 'Law Enforcement Officials':
        flash("Access denied: Only Hospital Administrators and Law Enforcement Officials can upload records.")
        return redirect(url_for('dashboard_redirect', role=user_role))

    # Connect to DB and get user ID
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (user_email,))
    user_row = c.fetchone()
    if not user_row:
        flash("User not found.")
        return redirect(url_for('dashboard_redirect', role=user_role))
    user_id = user_row[0]

    # Get form data
    patient_name = request.form['patientName']
    case_id = request.form['caseId']
    date = request.form['date']
    category = request.form['category']
    notes = request.form['notes']
    file = request.files['file']

    # Determine type
    if user_role == 'Hospital Administrator':
        record_type = 'Medical'
    elif user_role == 'Law Enforcement Officials':
        record_type = 'Legal'
    else:
        flash("Invalid role for record type.")
        return redirect(url_for('upload'))

    # Check for existing record of same case_id and type
    c.execute("SELECT * FROM records WHERE case_id = ? AND type = ?", (case_id, record_type))
    existing_record = c.fetchone()
    if existing_record:
        flash("Record already exists.")
        conn.close()
        return redirect(url_for('upload'))

    # Save file
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_path = filename

        # Insert record
        c.execute('''
            INSERT INTO records (patient_name, case_id, date, category, notes, file_path, uploaded_by, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_name, case_id, date, category, notes, file_path, user_id, record_type))

        conn.commit()
        conn.close()

        flash("Case uploaded successfully.")
        return redirect(url_for('dashboard_redirect', role=user_role))
    else:
        flash("Invalid file format.")
        conn.close()
        return redirect(url_for('upload'))

@app.route('/patient/approved-records')
def view_approved_records():
    user_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    approved_records = conn.execute('''
        SELECT r.id as record_id, r.case_id, r.file_path
        FROM record_permission rp
        JOIN records r ON rp.case_id = r.case_id
        WHERE rp.user_id = ? AND rp.status = 'Approved' AND r.type = 'Medical'
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('approved_records.html', records=approved_records)

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row  # This is the key fix
c = conn.cursor()

@app.route('/download/<int:record_id>')
def download_record(record_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # <-- This line is crucial!
    record = conn.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
    conn.close()

    if record:
        return send_from_directory(app.config['UPLOAD_FOLDER'], record['file_path'], as_attachment=True)
    else:
        flash("Record not found.")
        return redirect(url_for('view_approved_records'))



@app.route('/index1')
def index1():
    return render_template('index1.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard_redirect():
    user_email = session.get('email')
    user_role = session.get('role')

    if not user_email or not user_role:
        flash("Unauthorized access. Please log in.")
        return redirect(url_for('login'))

    # Redirect based on role
    if user_role == 'Hospital Administrator' or user_role == 'Healthcare Providers':
        pass  # Fall through to dashboard.html below
    elif user_role == 'Law Enforcement Officials':
        return redirect(url_for('law_dashboard'))
    elif user_role == 'Legal Professionals':
        return redirect(url_for('legal_professionals'))
    elif user_role == 'Patients & Family Members':
        return redirect(url_for('patient_dashboard'))
    elif user_role == 'Insurance Companies':
        return redirect(url_for('insurance_company'))
    else:
        flash("Access denied.")
        return redirect(url_for('home'))

    # Default hospital / healthcare dashboard
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE email = ?", (user_email,))
    row = c.fetchone()
    conn.close()

    user_name = row[0] if row else "User"
    return render_template('dashboard.html', user_name=user_name, user_role=user_role)



from flask import send_from_directory
conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row  # This is the key fix
c = conn.cursor()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/search', methods=['GET', 'POST'])
def search():
    user_role = session.get('role')
    user_email = session.get('email')

    if not user_email or user_role not in ['Hospital Administrator', 'Healthcare Providers','Law Enforcement Officials']:
        flash("Access denied: Only Hospital Administrators and Healthcare Providers can access this page.")
        return redirect(url_for('dashboard_redirect'))

    results = []
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').lower()
        doc_type = request.form.get('document_type', '')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        query = '''
            SELECT patient_name, case_id, date, category, file_path
            FROM records
            WHERE LOWER(patient_name) LIKE ?
               OR LOWER(case_id) LIKE ?
        '''
        params = [f'%{keyword}%', f'%{keyword}%']

        if doc_type:
            query += ' AND LOWER(category) = ?'
            params.append(doc_type.lower())

        c.execute(query, params)
        results = c.fetchall()
        conn.close()

    return render_template('search.html', results=results, user_role=user_role)

# @app.route('/search', methods=['GET', 'POST'])
# def search():
#     user_role = session.get('role')
#     user_email = session.get('email')

#     if not user_email or user_role not in ['Hospital Administrator', 'Healthcare Providers', 'Law Enforcement Officials']:
#         flash("Access denied: Only authorized users can access this page.")
#         return redirect(url_for('dashboard_redirect'))

#     results = []
#     if request.method == 'POST':
#         keyword = request.form.get('keyword', '').lower()
#         doc_type = request.form.get('document_type', '')  # 'Medical' or 'Legal'

#         conn = sqlite3.connect('database.db')
#         conn.row_factory = sqlite3.Row
#         c = conn.cursor()

#         query = '''
#             SELECT patient_name, case_id, date, category, file_path, type
#             FROM records
#             WHERE (LOWER(patient_name) LIKE ? OR LOWER(case_id) LIKE ?)
#         '''
#         params = [f'%{keyword}%', f'%{keyword}%']

#         if doc_type:
#             query += ' AND type = ?'
#             params.append(doc_type)

#         c.execute(query, params)
#         results = c.fetchall()
#         conn.close()

#     return render_template('search.html', results=results)

@app.route('/lawenforcement/my-uploads')
def my_uploaded_records():
    user_role = session.get('role')
    user_email = session.get('email')

    if not user_email or user_role != 'Law Enforcement Officials':
        flash("Access denied: Only Hospital Administrators and Healthcare Providers can access this page.")
        return redirect(url_for('dashboard_redirect'))

    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT patient_name, case_id, date, category, notes, file_path
        FROM records
        WHERE uploaded_by = ?
    ''', (user_id,))
    
    records = c.fetchall()
    conn.close()

    return render_template('my_uploaded_records.html', records=records)

@app.route('/admin/permissions', methods=['GET', 'POST'])
def manage_permissions():
    if 'user_id' not in session or session.get('role') != 'Hospital Administrator':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        permission_id = request.form['permission_id']
        action = request.form['action']
        if action in ['Approved', 'Rejected']:
            # Update both status and granted_by
            c.execute('''
                UPDATE record_permission 
                SET status = ?, granted_by = ? 
                WHERE id = ?
            ''', (action, admin_id, permission_id))
            conn.commit()

    # Pending requests — all visible to admin
    c.execute('''
        SELECT rp.id AS permission_id, rp.status, rp.case_id, u.name, u.role, u.email
        FROM record_permission rp
        JOIN users u ON rp.user_id = u.id
        WHERE rp.status = 'Pending'
    ''')
    pending_requests = c.fetchall()

    # Past requests — only those granted by this admin
    c.execute('''
        SELECT rp.id AS permission_id, rp.status, rp.case_id, u.name, u.role, u.email
        FROM record_permission rp
        JOIN users u ON rp.user_id = u.id
        WHERE rp.status != 'Pending' AND rp.granted_by = ?
        ORDER BY rp.id DESC
    ''', (admin_id,))
    past_requests = c.fetchall()

    conn.close()
    return render_template('manage_permissions.html',
                           pending_requests=pending_requests,
                           past_requests=past_requests)

@app.route('/law-enforcement/request-access')
def request_access():
    if 'user_id' not in session or session.get('role') != 'Law Enforcement Officials':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all records (excluding file_path)
    c.execute('''
        SELECT r.case_id, r.patient_name, r.date, r.category, r.notes,
               IFNULL(rp.status, 'Not Requested') as permission_status,
               r.id as record_id
        FROM records r
        LEFT JOIN (
            SELECT * FROM record_permission WHERE user_id = ?
        ) rp ON r.case_id = rp.case_id
    ''', (user_id,))
    records = c.fetchall()

    conn.close()
    return render_template('request_access.html', records=records)

@app.route('/law-enforcement/request-access/submit', methods=['POST'])
def submit_access_request():
    if 'user_id' not in session or session.get('role') != 'Law Enforcement Officials':
        return redirect(url_for('login'))

    user_id = session['user_id']
    case_id = request.form['case_id']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if already requested
    c.execute('SELECT * FROM record_permission WHERE user_id = ? AND case_id = ?', (user_id, case_id))
    if not c.fetchone():
        c.execute('INSERT INTO record_permission (case_id, user_id, status) VALUES (?, ?, "Pending")', (case_id, user_id))
        conn.commit()

    conn.close()
    return redirect(url_for('request_access'))

@app.route('/legal-professionals/request-records')
def request_records():
    if 'user_id' not in session or session.get('role') != 'Legal Professionals':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT r.case_id, r.patient_name, r.date, r.category, r.notes,
               IFNULL(rp.status, 'Not Requested') as permission_status
        FROM records r
        LEFT JOIN (
            SELECT * FROM record_permission WHERE user_id = ?
        ) rp ON r.case_id = rp.case_id
    ''', (user_id,))
    records = c.fetchall()
    conn.close()
    return render_template('legal_request_records.html', records=records)

@app.route('/legal-professionals/request-records/submit', methods=['POST'])
def legal_submit_request():
    if 'user_id' not in session or session.get('role') != 'Legal Professionals':
        return redirect(url_for('login'))

    case_id = request.form['case_id']
    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('SELECT * FROM record_permission WHERE case_id = ? AND user_id = ?', (case_id, user_id))
    if not c.fetchone():
        c.execute('INSERT INTO record_permission (case_id, user_id, status) VALUES (?, ?, "Pending")', (case_id, user_id))
        conn.commit()

    conn.close()
    return redirect(url_for('request_records'))

@app.route('/legal-professionals/accessible-records/<category>')
def accessible_records_by_category(category):
    if 'user_id' not in session or session.get('role') != 'Legal Professionals':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT r.*, u.name as uploaded_by_name
        FROM records r
        JOIN record_permission rp ON r.case_id = rp.case_id
        JOIN users u ON r.uploaded_by = u.id
        WHERE rp.user_id = ? AND rp.status = 'Approved' AND LOWER(r.type) = LOWER(?)
    ''', (user_id, category))
    records = c.fetchall()
    conn.close()

    return render_template('legal_accessible_records.html', records=records, category=category)

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session.get('role') != 'Patients & Family Members':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE id = ?", (session['user_id'],))
    row = c.fetchone()
    conn.close()

    user_name = row['name'] if row else "Patient"
    return render_template('patient_dashboard.html', user_name=user_name, user_role='Patients & Family Members')


@app.route('/patients/request-records', methods=['GET', 'POST'])
def patient_request_records():
    if 'user_id' not in session or session.get('role') != 'Patients & Family Members':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    search_case_id = request.args.get('case_id', '').strip()

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Records searched by case_id
    records = []
    no_records = False

    if search_case_id:
        c.execute('''
            SELECT r.case_id, r.patient_name, r.date, r.category, r.notes,
                   IFNULL(rp.status, 'Not Requested') AS permission_status
            FROM records r
            LEFT JOIN (
                SELECT * FROM record_permission WHERE user_id = ?
            ) rp ON r.case_id = rp.case_id
            WHERE r.case_id = ? AND r.type='Medical'
        ''', (user_id, search_case_id))
        records = c.fetchall()
        if not records:
            no_records = True

    # Fetch previously requested records
    c.execute('''
        SELECT r.case_id, r.patient_name, r.date, r.category, rp.status
        FROM record_permission rp
        JOIN records r ON rp.case_id = r.case_id
        WHERE rp.user_id = ? AND r.type = 'Medical'
    ''', (user_id,))
    previous_requests = c.fetchall()

    conn.close()
    return render_template(
        'patient_request_records.html',
        records=records,
        no_records=no_records,
        previous_requests=previous_requests
    )




@app.route('/patients/submit-request', methods=['POST'])
def patient_submit_request():
    if 'user_id' not in session or session.get('role') != 'Patients & Family Members':
        return redirect(url_for('login'))

    user_id = session['user_id']
    case_id = request.form.get('case_id')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO record_permission (user_id, case_id, status)
        VALUES (?, ?, 'Pending')
    ''', (user_id, case_id))
    conn.commit()
    conn.close()

    flash("Access request submitted successfully.")
    return redirect(url_for('patient_request_records', case_id=case_id))

@app.route('/insurance/dashboard')
def insurance_company():
    return render_template('insurance_dashboard.html')


@app.route('/insurance/request-record', methods=['GET', 'POST'])
def insurance_request_record():
    if 'user_id' not in session or session.get('role') != 'Insurance Companies':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    message = None
    user_id = session.get('user_id')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Process form submission
    if request.method == 'POST':
        case_id = request.form['case_id'].strip()

        # Check if the case ID exists
        c.execute("SELECT * FROM records WHERE case_id = ?", (case_id,))
        record = c.fetchone()

        if record:
            # Check if a request has already been made
            c.execute('''
                SELECT * FROM record_permission
                WHERE user_id = ? AND case_id = ? AND role = 'Insurance' 
            ''', (user_id, case_id))
            existing_request = c.fetchone()

            if existing_request:
                message = f"A request for Case ID '{case_id}' has already been submitted."
            else:
                conn.execute('''
                    INSERT INTO record_permission (user_id, case_id, status, role)
                    VALUES (?, ?, 'Pending', 'Insurance')
                ''', (user_id, case_id))
                conn.commit()
                message = f"Request for Case ID '{case_id}' submitted to Hospital Administrator."
        else:
            message = f"No records found for Case ID '{case_id}'."

    # Fetch all submitted requests with joined record data
    c.execute('''
        SELECT r.case_id, r.patient_name, r.date, r.category, r.notes, r.file_path,
               rp.status
        FROM record_permission rp
        JOIN records r ON rp.case_id = r.case_id
        WHERE rp.user_id = ? AND rp.role = 'Insurance'
        ORDER BY r.date DESC
    ''', (user_id,))
    requested_records = c.fetchall()

    conn.close()

    
    return render_template('insurance_request_record.html', message=message, requested_records=requested_records)



@app.route('/insurance/approved-records')
def insurance_approved_records():
    user_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    approved_medical = c.execute('''
        SELECT r.id as record_id, r.case_id, r.file_path
        FROM record_permission rp
        JOIN records r ON rp.case_id = r.case_id
        WHERE rp.user_id = ? AND rp.status = 'Approved' AND r.type='Medical'
    ''', (user_id,)).fetchall()

    approved_legal = c.execute('''
        SELECT r.id as record_id, r.case_id, r.file_path
        FROM record_permission rp
        JOIN records r ON rp.case_id = r.case_id
        WHERE rp.user_id = ? AND rp.status = 'Approved' AND r.type='Legal'
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('insurance_approved_records.html', 
                           records_medical=approved_medical, 
                           records_legal=approved_legal)


@app.route('/insurance/download/<int:record_id>')
def insurance_download(record_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # <-- This line is crucial!
    record = conn.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
    conn.close()

    if record:
        return send_from_directory(app.config['UPLOAD_FOLDER'], record['file_path'], as_attachment=True)
    else:
        flash("Record not found.")
        return redirect(url_for('insurance_approved_records'))



def get_db():
    conn = sqlite3.connect('database.db')  # Use 'database.db' instead of 'your_database.db'
    conn.row_factory = sqlite3.Row  # To access rows as dictionaries
    return conn

# In your route, replace 'db.execute' with a connection
@app.route('/apply-insurance', methods=['GET', 'POST'])
def apply_insurance():
   user_email = session.get('email')
   conn = get_db()
   
   cursor = conn.cursor()

    # Load all registered insurance companies
   cursor.execute("SELECT id, name FROM users WHERE role = 'Insurance Companies'")

   companies = cursor.fetchall()

    # Fetch approved claims for this user
   cursor.execute('''
        SELECT ic.id AS claim_id, ic.case_id, ins.name AS company_name, ic.status
        FROM insurance_claims ic
        JOIN users ins ON ic.insurance_company_id = ins.id

        WHERE ic.patient_id = (SELECT id FROM users WHERE email = ?) AND ic.status IN ('Approved', 'Rejected')

    ''', (user_email,))
   approved_claims = cursor.fetchall()

   conn.close()

   return render_template('apply_insurance.html', companies=companies, approved_claims=approved_claims)


@app.route('/claim-insurance/<int:company_id>', methods=['GET', 'POST'])
def claim_insurance(company_id):
    if request.method == 'POST':
        policy_number = request.form['policy_number']
        case_id = request.form['case_id']
        patient_name = request.form['patient_name']
        gender = request.form['gender']
        age = request.form['age']
        additional_details = request.form.get('additional_info', '')
        bills = request.files.get('bills')

        if not bills or bills.filename == '':
            flash("No bill file uploaded.")
            return redirect(request.url)

        filename = secure_filename(bills.filename)
        bills_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'bills')
        os.makedirs(bills_folder, exist_ok=True)
        bills_path = os.path.join(bills_folder, filename)
        bills.save(bills_path)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO insurance_claims (
                patient_id, insurance_company_id, policy_number, case_id,
                patient_name, gender, age, bills_path, additional_details, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        ''', (
            session['user_id'], company_id, policy_number, case_id,
            patient_name, gender, age, bills_path, additional_details
        ))
        conn.commit()
        conn.close()

        flash("Insurance claim submitted.")
        return redirect(url_for('patient_dashboard'))

    return render_template('claim_insurance.html')

@app.route('/insurance/claims')
def view_claims():
    company_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    claims = cursor.execute('''
        SELECT ic.*, u.name AS patient_name
        FROM insurance_claims ic
        JOIN users u ON ic.patient_id = u.id
        WHERE ic.insurance_company_id = ?
    ''', (company_id,)).fetchall()
    conn.close()
    return render_template('insurance_claims.html', claims=claims)

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row  # This is the key fix
c = conn.cursor()

@app.route('/bills/<filename>')
def serve_bill_file(filename):
      return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'bills'), filename)

@app.route('/insurance/claim/<int:claim_id>/<action>')
def update_claim_status(claim_id, action):
    if action not in ['approve', 'reject']:
        flash("Invalid action.")
        return redirect(url_for('view_claims'))

    status = 'Approved' if action == 'approve' else 'Rejected'
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE insurance_claims SET status = ? WHERE id = ?", (status, claim_id))
    conn.commit()
    conn.close()
    flash(f"Claim {status}.")
    return redirect(url_for('view_claims'))



@app.route('/verify_claims')
def verify_claims():
    return render_template('verify_claims.html')

@app.route('/policyholder_records')
def policyholder_records():
    return render_template('policyholder_records.html')

@app.route('/claim_approvals')
def claim_approvals():
    return render_template('claim_approvals.html')

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, message, created_at, is_read FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    notifications = cursor.fetchall()
    conn.close()
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/notifications/unread-count')
def unread_count():
    user_id = session.get('user_id')
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)).fetchone()[0]
    conn.close()
    return {'count': count}

@app.route('/notifications/list')
def list_notifications():
    user_id = session.get('user_id')
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    notifications = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return render_template('notifications.html', notifications=notifications)


@app.route('/notifications/mark-read')
def mark_all_read():
    user_id = session.get('user_id')
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_notifications'))


@app.route('/settings')
def settings():
    user_email = session.get('email')
    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM users WHERE email = ?", (user_email,)).fetchone()
    conn.close()
    return render_template('settings.html', user=user)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    name = request.form['name']
    email = request.form['email']
    proof_file = request.files.get('proof')
    user_id = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()

    if proof_file and proof_file.filename != '':
        filename = secure_filename(proof_file.filename)
        proof_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        proof_file.save(proof_path)

        cursor.execute("""
            UPDATE users SET name = ?, email = ?, proof_document = ?
            WHERE id = ?
        """, (name, email, proof_path, user_id))
    else:
        cursor.execute("""
            UPDATE users SET name = ?, email = ?
            WHERE id = ?
        """, (name, email, user_id))

    conn.commit()
    conn.close()

    flash("Settings updated successfully.")
    return redirect(url_for('settings'))

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row  # This is the key fix
c = conn.cursor()

@app.route('/proofs/<filename>')
def serve_proof_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/healthcare')
def healthcare():
    return render_template('home.html')



@app.route('/law_enforcement')
def law_enforcement():
    return render_template('law_enforcement.html')

@app.route('/investigation_reports')
def investigation_reports():
    return render_template('investigation_reports.html')



@app.route('/legal_professionals')
def legal_professionals():
    return render_template('legal_dashboard.html')



@app.route('/submit_documents')
def submit_documents():
    return render_template('submit_documents.html')

@app.route('/parents_family')
def parents_family():
    return render_template('parents_family.html')

@app.route('/law_dashboard')
def law_dashboard():
    return render_template('law_dashboard.html')

@app.route('/suspect_medical')
def suspect_medical():
    user_role = session.get('role')
    user_email = session.get('email')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # This makes fetched rows act like dicts
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE email = ?", (user_email,))
    user_row = c.fetchone()
    if not user_row:
        flash("User not found.")
        return redirect(url_for('dashboard_redirect', role=user_role))
    user_id = user_row[0]

    c.execute('''
        SELECT r.*
        FROM records r
        JOIN record_permission rp ON r.case_id = rp.case_id
        WHERE rp.user_id = ? and r.type = 'Medical'
    ''', (user_id,))

    records = c.fetchall()
    conn.close()

    return render_template('suspect_medical.html', records=records)

# --- Run the app and initialize the DB ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
