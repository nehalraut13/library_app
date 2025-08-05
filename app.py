import os
from flask import Flask, render_template, request, redirect, send_file, session, flash, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=10)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE_URL = os.getenv("DATABASE_URL")


# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('admin'):
        return redirect('/dashboard')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            session.permanent = True
            return redirect('/dashboard')
        else:
            return render_template('dashboard.html', error="Invalid username or password")
    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def index():
    if not session.get('admin'):
        return redirect('/')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    records = cur.fetchall()
    conn.close()
    return render_template('index.html', records=records)


# ---------- ADD STUDENT ----------
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return redirect('/')

    form = request.form
    name = form.get('name')
    seat_no = form.get('seat_no')
    mobile_no = form.get('mobile_no')
    fee_paid = form.get('fee_paid')
    plan_type = form.get('plan_type')
    start_date = form.get('start_date')
    end_date = form.get('end_date')

    aadhaar_file = request.files.get('aadhaar_photo')
    aadhaar_filename = ''
    if aadhaar_file and aadhaar_file.filename != '':
        aadhaar_filename = secure_filename(aadhaar_file.filename)
        aadhaar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename))

    if not all([name, mobile_no, plan_type, start_date, end_date, seat_no]):
        return "Missing required fields", 400
    if not re.fullmatch(r'[A-Za-z ]+', name):
        return "Name must contain only letters and spaces", 400
    if not re.fullmatch(r'\d{10}', mobile_no):
        return "Mobile number must be 10 digits", 400
    if fee_paid and not fee_paid.isdigit():
        return "Fee paid must be numeric", 400
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if start_dt > end_dt:
            return "Start date must be before or equal to end date", 400
    except ValueError:
        return "Invalid date format", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO students 
        (name, seat_no, mobile_no, fee_paid, plan_type, start_date, end_date, aadhaar_photo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (name, seat_no, mobile_no, fee_paid, plan_type, start_date, end_date, aadhaar_filename))
    conn.commit()
    conn.close()

    flash("Student added successfully!")
    return redirect('/dashboard')


# ---------- DELETE STUDENT ----------
@app.route('/delete/<int:id>')
def delete(id):
    if not session.get('admin'):
        return redirect('/')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM students WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully!")
    return redirect('/dashboard')


# ---------- UPDATE STUDENT ----------
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if not session.get('admin'):
        return redirect('/')
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        form = request.form
        name = form.get('name')
        seat_no = form.get('seat_no')
        mobile_no = form.get('mobile_no')
        fee_paid = form.get('fee_paid')
        plan_type = form.get('plan_type')
        start_date = form.get('start_date')
        end_date = form.get('end_date')

        cur.execute("SELECT * FROM students WHERE id = %s", (id,))
        student = cur.fetchone()

        aadhaar_file = request.files.get('aadhaar_photo')
        aadhaar_filename = student['aadhaar_photo']
        if aadhaar_file and aadhaar_file.filename != '':
            aadhaar_filename = secure_filename(aadhaar_file.filename)
            aadhaar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename))

        if not all([name, mobile_no, plan_type, start_date, end_date, seat_no]):
            return "Missing required fields", 400
        if not re.fullmatch(r'[A-Za-z ]+', name):
            return "Name must contain only letters and spaces", 400
        if not re.fullmatch(r'\d{10}', mobile_no):
            return "Mobile number must be 10 digits", 400
        if fee_paid and not fee_paid.isdigit():
            return "Fee paid must be numeric", 400
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if start_dt > end_dt:
                return "Start date must be before or equal to end date", 400
        except ValueError:
            return "Invalid date format", 400

        cur.execute('''
            UPDATE students
            SET name=%s, seat_no=%s, mobile_no=%s, fee_paid=%s, plan_type=%s, start_date=%s, end_date=%s, aadhaar_photo=%s
            WHERE id=%s
        ''', (name, seat_no, mobile_no, fee_paid, plan_type, start_date, end_date, aadhaar_filename, id))
        conn.commit()
        conn.close()
        flash("Student updated successfully!")
        return redirect('/dashboard')
    else:
        cur.execute("SELECT * FROM students WHERE id = %s", (id,))
        student = cur.fetchone()
        cur.execute("SELECT * FROM students")
        records = cur.fetchall()
        conn.close()
        return render_template('index.html', student=student, records=records)


# ---------- EXPORT EXCEL ----------
@app.route('/export/excel')
def export_excel():
    if not session.get('admin'):
        return redirect('/')
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    file_path = 'students_export.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)


# ---------- EXPORT PDF ----------
@app.route('/export/pdf')
def export_pdf():
    if not session.get('admin'):
        return redirect('/')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    records = cur.fetchall()
    conn.close()
    file_path = 'students_export.pdf'
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 40, "Student Records")
    c.setFont("Helvetica", 10)
    y = height - 80
    headers = ["ID", "Name", "Seat No", "Mobile No", "Fee Paid", "Plan", "Start", "End", "Aadhaar"]
    for i, header in enumerate(headers):
        c.drawString(50 + i * 55, y, header)
    y -= 20
    for row in records:
        reordered = [row['id'], row['name'], row['seat_no'], row['mobile_no'], row['fee_paid'],
                     row['plan_type'], row['start_date'], row['end_date'], row['aadhaar_photo']]
        for i, value in enumerate(reordered):
            c.drawString(50 + i * 55, y, str(value))
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    return send_file(file_path, as_attachment=True)


# ---------- RUN FLASK APP ----------
if __name__ == '__main__':
    # Do NOT call init_db here for PostgreSQL on Render
    app.run(debug=True)
