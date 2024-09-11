from flask import Flask, request, session, redirect, render_template, jsonify, url_for
import csv
import os
import uuid
from functools import wraps
 
app = Flask(__name__)
app.secret_key = '321'  # Change this to a secure key
PASSWORD_FILE = 'password.csv'
CSV_BASE_FILE = 'students_{}.csv'
STAFF_CSV_BASE_FILE = 'staff_{}.csv'

# Initialize the password file if it does not exist
def init_password():
    if not os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'w') as file:
            file.write('initial_password')  # Set an initial password

# Check if a password is correct
def check_password(password):
    with open(PASSWORD_FILE, 'r') as file:
        return file.read().strip() == password

# Set a new password
def set_password(password):
    with open(PASSWORD_FILE, 'w') as file:
        file.write(password)

def get_staff_csv_file():
    password = session.get('current_password')
    if password:
        return STAFF_CSV_BASE_FILE.format(password)
    return None

# Create the CSV file for the given password
def init_csv(file_name):
    if not os.path.exists(file_name):
        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['name', 'roll_number', 'department', 'class_', 'date_of_birth', 'address', 'phone_number', 'mail_id', 'marksheet', 'certificate'])

# Create the CSV file for staff details
def init_staff_csv(file_name):
    if not os.path.exists(file_name):
        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['id', 'name', 'age', 'gender', 'date_of_joining', 'date_of_birth', 'address', 'designation', 'department'])

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            password = request.form['password']
            if check_password(password):
                session['logged_in'] = True
                session['current_password'] = password
                return redirect(url_for('index'))
            else:
                return jsonify({'error': 'Invalid password.'}), 400
        
        elif action == 'set_password':
            new_password = request.form['new_password']
            current_password = session.get('current_password')
            if new_password == current_password:
                return jsonify({'error': 'New password cannot be the same as the current password.'}), 400
            if not check_password(new_password):
                set_password(new_password)
                init_csv(CSV_BASE_FILE.format(new_password))
                init_staff_csv(STAFF_CSV_BASE_FILE.format(new_password))
                session['logged_in'] = True
                session['current_password'] = new_password
                return jsonify({'success': 'Password updated successfully. Please log in.'}), 200
            else:
                return jsonify({'error': 'Password already exists.'}), 400
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    session.pop('current_password', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

def get_csv_file():
    password = session.get('current_password')
    if password:
        return CSV_BASE_FILE.format(password)
    return None

def get_staff_csv_file():
    password = session.get('current_password')
    if password:
        return STAFF_CSV_BASE_FILE.format(password)
    return None

@app.route('/students', methods=['GET', 'POST'])
@login_required
def manage_students():
    csv_file = get_csv_file()
    if not csv_file:
        return jsonify({'error': 'No database file found.'}), 500

    if request.method == 'POST':
        data = request.json
        try:
            with open(csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    data.get('name', ''),
                    data.get('roll_number', ''),
                    data.get('department', ''),
                    data.get('class_', ''),
                    data.get('date_of_birth', ''),
                    data.get('address', ''),
                    data.get('phone_number', ''),
                    data.get('mail_id', ''),
                    data.get('marksheet', ''),
                    data.get('certificate', '')
                ])
            return jsonify({'message': 'Student added successfully'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        students = []
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        students.append(row)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify(students), 200

@app.route('/students/<roll_number>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def student_details(roll_number):
    csv_file = get_csv_file()
    if not csv_file:
        return jsonify({'error': 'No database file found.'}), 500

    if request.method == 'GET':
        try:
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['roll_number'] == roll_number:
                        return jsonify(row), 200
            return jsonify({'error': 'Student not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'PUT':
        updated_data = request.json
        try:
            rows = []
            student_found = False
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['roll_number'] == roll_number:
                        row.update(updated_data)
                        student_found = True
                    rows.append(row)

            if not student_found:
                return jsonify({'error': 'Student not found'}), 404

            with open(csv_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return jsonify({'message': 'Student updated successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            rows = []
            student_found = False
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['roll_number'] != roll_number:
                        rows.append(row)
                    else:
                        student_found = True

            if not student_found:
                return jsonify({'error': 'Student not found'}), 404

            with open(csv_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return jsonify({'message': 'Student deleted successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/staff', methods=['GET', 'POST'])
@login_required
def manage_staff():
    staff_csv_file = get_staff_csv_file()
    if not staff_csv_file:
        return jsonify({'error': 'No staff database file found.'}), 500

    if request.method == 'POST':
        data = request.json
        data['id'] = str(uuid.uuid4())  # Generate a unique ID for each staff member
        try:
            # Check if file exists, if not, create it with headers
            if not os.path.exists(staff_csv_file):
                with open(staff_csv_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['id', 'name', 'age', 'gender', 'date_of_joining', 'date_of_birth', 'address', 'designation', 'department'])

            with open(staff_csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    data['id'],
                    data.get('name', ''),
                    data.get('age', ''),
                    data.get('gender', ''),
                    data.get('date_of_joining', ''),
                    data.get('date_of_birth', ''),
                    data.get('address', ''),
                    data.get('designation', ''),
                    data.get('department', '')
                ])
            return jsonify({'message': 'Staff added successfully', 'id': data['id']}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        staff_list = []
        if os.path.exists(staff_csv_file):
            try:
                with open(staff_csv_file, 'r') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        staff_list.append(row)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify(staff_list), 200

@app.route('/staff/<staff_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def staff_details(staff_id):
    staff_csv_file = get_staff_csv_file()
    if not staff_csv_file:
        return jsonify({'error': 'No staff database file found.'}), 500

    if request.method == 'GET':
        try:
            with open(staff_csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['id'] == staff_id:
                        return jsonify(row), 200
            return jsonify({'error': 'Staff member not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'PUT':
        updated_data = request.json
        try:
            rows = []
            staff_found = False
            with open(staff_csv_file, 'r') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['id'] == staff_id:
                        row.update(updated_data)
                        staff_found = True
                    rows.append(row)

            if not staff_found:
                return jsonify({'error': 'Staff member not found'}), 404

            with open(staff_csv_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return jsonify({'message': 'Staff member updated successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            rows = []
            staff_found = False
            with open(staff_csv_file, 'r') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['id'] != staff_id:
                        rows.append(row)
                    else:
                        staff_found = True

            if not staff_found:
                return jsonify({'error': 'Staff member not found'}), 404

            with open(staff_csv_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return jsonify({'message': 'Staff member deleted successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_password()
    app.run(debug=True)

