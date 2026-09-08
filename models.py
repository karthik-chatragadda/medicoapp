import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE_NAME = 'meedicoapp.db'

def get_db_connection():
    """Establishes a connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enables column access by key
    return conn

def init_db():
    """Initializes schema and seeds default Admin user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            department TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Create Email Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Seed Default Admin if not exists
    cursor.execute('SELECT * FROM users WHERE role = ?', ('admin',))
    admin_exists = cursor.fetchone()

    if not admin_exists:
        hashed_pw = generate_password_hash('admin123')
        cursor.execute(
            'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
            ('admin', 'admin@meedicoapp.com', hashed_pw, 'admin')
        )
        conn.commit()

    conn.close()

# --- Database Helper Model Operations using SQL Cursors ---

class UserModel:
    @staticmethod
    def create_user(username, email, password, role='patient'):
        conn = get_db_connection()
        cursor = conn.cursor()
        hashed_pw = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
            (username, email, hashed_pw, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def get_all_users():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, created_at FROM users')
        users = cursor.fetchall()
        conn.close()
        return [dict(user) for user in users]

    @staticmethod
    def update_user(user_id, username, email, role):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?',
            (username, email, role, user_id)
        )
        conn.commit()
        updated = cursor.rowcount
        conn.close()
        return updated > 0

    @staticmethod
    def delete_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted > 0

class AppointmentModel:
    @staticmethod
    def create_appointment(patient_id, doctor_name, department, booking_date):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO appointments (patient_id, doctor_name, department, booking_date) VALUES (?, ?, ?, ?)',
            (patient_id, doctor_name, department, booking_date)
        )
        conn.commit()
        appointment_id = cursor.lastrowid
        conn.close()
        return appointment_id

    @staticmethod
    def get_user_appointments(patient_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments WHERE patient_id = ? ORDER BY booking_date DESC', (patient_id,))
        appointments = cursor.fetchall()
        conn.close()
        return [dict(app) for app in appointments]

    @staticmethod
    def get_all_appointments():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, u.username, u.email 
            FROM appointments a 
            JOIN users u ON a.patient_id = u.id 
            ORDER BY a.created_at DESC
        ''')
        appointments = cursor.fetchall()
        conn.close()
        return [dict(app) for app in appointments]

class EmailLogModel:
    @staticmethod
    def log_email(recipient, subject, body):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO email_logs (recipient, subject, body) VALUES (?, ?, ?)',
            (recipient, subject, body)
        )
        conn.commit()
        conn.close()