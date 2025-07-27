from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Initialize database
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
            end_date TEXT
        )
    ''')
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('students.db')
    records = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('index.html', records=records)

@app.route('/add', methods=['POST'])
def add():
    form = request.form
    name = form.get('name')
    fee_paid = form.get('fee_paid')
    mobile_no = form.get('mobile_no')
    plan_type = form.get('plan_type')
    start_date = form.get('start_date')
    end_date = form.get('end_date')

    if not all([name, mobile_no]):
        return "Missing required fields", 400

    conn = sqlite3.connect('students.db')
    conn.execute('''
        INSERT INTO students 
        (name, fee_paid, mobile_no, plan_type, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, fee_paid, mobile_no, plan_type, start_date, end_date))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect('students.db')
    conn.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    conn = sqlite3.connect('students.db')
    if request.method == 'POST':
        form = request.form
        values = (
            form.get('name'), form.get('fee_paid'), form.get('mobile_no'),
            form.get('plan_type'), form.get('start_date'), form.get('end_date'), id
        )
        conn.execute('''
            UPDATE students
            SET name=?, fee_paid=?, mobile_no=?, plan_type=?, start_date=?, end_date=?
            WHERE id=?
        ''', values)
        conn.commit()
        conn.close()
        return redirect('/')
    else:
        student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
        records = conn.execute('SELECT * FROM students').fetchall()
        conn.close()
        return render_template('index.html', student=student, records=records)

# ---------------------
# Export to Excel
@app.route('/export/excel')
def export_excel():
    conn = sqlite3.connect('students.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    file_path = 'students_export.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

# Export to PDF
@app.route('/export/pdf')
def export_pdf():
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
    headers = ["ID", "Name", "Fee Paid", "Mobile No", "Plan", "Start", "End"]

    for i, header in enumerate(headers):
        c.drawString(50 + i * 75, y, header)

    y -= 20
    for row in records:
        for i, value in enumerate(row):
            if i >= len(headers):
                break
            c.drawString(50 + i * 75, y, str(value))
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
