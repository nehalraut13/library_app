from flask import Flask, render_template, request, redirect, send_file, session, flash, url_for
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=10)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('students.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            fee_paid TEXT,
            mobile_no TEXT,
            plan_type TEXT,
            start_date TEXT,
            end_date TEXT,
            seat_no TEXT,
            aadhaar_photo TEXT
        )
    ''')
    conn.close()

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

@app.route('/dashboard')
def index():
    if not session.get('admin'):
        return redirect('/')
    conn = sqlite3.connect('students.db')
    records = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('index.html', records=records)

@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return redirect('/')

    form = request.form
    name = form.get('name')
    fee_paid = form.get('fee_paid')
    mobile_no = form.get('mobile_no')
    plan_type = form.get('plan_type')
    start_date = form.get('start_date')
    end_date = form.get('end_date')
    seat_no = form.get('seat_no')

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

    conn = sqlite3.connect('students.db')
    conn.execute('''
        INSERT INTO students 
        (name, fee_paid, mobile_no, plan_type, start_date, end_date, seat_no, aadhaar_photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, fee_paid, mobile_no, plan_type, start_date, end_date, seat_no, aadhaar_filename))
    conn.commit()
    conn.close()

    flash("Student added successfully!")
    return redirect('/dashboard')

@app.route('/delete/<int:id>')
def delete(id):
    if not session.get('admin'):
        return redirect('/')
    conn = sqlite3.connect('students.db')
    conn.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully!")
    return redirect('/dashboard')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if not session.get('admin'):
        return redirect('/')
    conn = sqlite3.connect('students.db')
    if request.method == 'POST':
        form = request.form
        name = form.get('name')
        fee_paid = form.get('fee_paid')
        mobile_no = form.get('mobile_no')
        plan_type = form.get('plan_type')
        start_date = form.get('start_date')
        end_date = form.get('end_date')
        seat_no = form.get('seat_no')

        student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
        aadhaar_file = request.files.get('aadhaar_photo')
        aadhaar_filename = student[8]
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

        conn.execute('''
            UPDATE students
            SET name=?, fee_paid=?, mobile_no=?, plan_type=?, start_date=?, end_date=?, seat_no=?, aadhaar_photo=?
            WHERE id=?
        ''', (name, fee_paid, mobile_no, plan_type, start_date, end_date, seat_no, aadhaar_filename, id))
        conn.commit()
        conn.close()
        flash("Student updated successfully!")
        return redirect('/dashboard')
    else:
        student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
        records = conn.execute('SELECT * FROM students').fetchall()
        conn.close()
        return render_template('index.html', student=student, records=records)

@app.route('/export/excel')
def export_excel():
    if not session.get('admin'):
        return redirect('/')
    conn = sqlite3.connect('students.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    file_path = 'students_export.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    if not session.get('admin'):
        return redirect('/')
    conn = sqlite3.connect('students.db')
    records = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    file_path = 'students_export.pdf'
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 40, "Student Records")
    c.setFont("Helvetica", 10)
    y = height - 80
    headers = ["ID", "Name", "Fee Paid", "Mobile No", "Plan", "Start", "End", "Seat", "Aadhaar"]
    for i, header in enumerate(headers):
        c.drawString(50 + i * 55, y, header)
    y -= 20
    for row in records:
        for i, value in enumerate(row):
            if i >= len(headers):
                break
            c.drawString(50 + i * 55, y, str(value))
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
