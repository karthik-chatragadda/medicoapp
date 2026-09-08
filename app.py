import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from flask_cors import CORS
import jwt
from werkzeug.security import check_password_hash

from models import init_db, UserModel, AppointmentModel, EmailLogModel

app = Flask(__name__)
app.config['SECRET_KEY'] = 'meedicoapp-super-secret-key-2026'
CORS(app)  # Enable Cross-Origin Resource Sharing

# Initialize Database on startup
init_db()

# --- Utility Email Service Mock ---
def send_email_notification(recipient, subject, body):
    """Simulates sending email notifications and stores logs in SQLite."""
    EmailLogModel.log_email(recipient, subject, body)
    print(f"\n--- [EMAIL SENT] ---\nTo: {recipient}\nSubject: {subject}\nBody: {body}\n--------------------\n")

# --- JWT Authentication Middleware ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('jwt_token') or request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token.split(' ')[1]

        if not token:
            return jsonify({'message': 'Authentication token missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired! Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.get('role') != 'admin':
            return jsonify({'message': 'Access forbidden: Admin privilege required!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# --- Web UI Routes ---

@app.route('/')
def home():
    return render_template('index.html')

# --- Authentication APIs ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        user_id = UserModel.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            role=data.get('role', 'patient')
        )
        send_email_notification(
            recipient=data['email'],
            subject="Welcome to Meedicoapp OP-Booking System",
            body=f"Hello {data['username']},\n\nYour account has been successfully created!"
        )
        return jsonify({'message': 'Registration successful!', 'user_id': user_id}), 201
    except Exception as e:
        return jsonify({'error': 'User or Email already exists.'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    user = UserModel.get_by_email(email)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    payload = {
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=4)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

    response = make_response(jsonify({'message': 'Login successful', 'role': user['role'], 'token': token}))
    response.set_cookie('jwt_token', token, httponly=True)
    return response

@app.route('/api/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': 'Logged out successfully'}))
    response.set_cookie('jwt_token', '', expires=0)
    return response

# --- OP-Booking Routes ---

@app.route('/api/booking', methods=['POST'])
@token_required
def create_booking(current_user):
    data = request.get_json()
    appointment_id = AppointmentModel.create_appointment(
        patient_id=current_user['id'],
        doctor_name=data['doctor_name'],
        department=data['department'],
        booking_date=data['booking_date']
    )
    
    send_email_notification(
        recipient=current_user['email'],
        subject="OP Appointment Confirmation - Meedicoapp",
        body=f"Hi {current_user['username']},\n\nYour OP booking is confirmed with {data['doctor_name']} ({data['department']}) on {data['booking_date']}."
    )

    return jsonify({'message': 'Appointment booked successfully', 'id': appointment_id}), 201

@app.route('/api/my-bookings', methods=['GET'])
@token_required
def get_user_bookings(current_user):
    bookings = AppointmentModel.get_user_appointments(current_user['id'])
    return jsonify({'bookings': bookings})

# --- Role-Based Admin Management APIs ---

@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    users = UserModel.get_all_users()
    appointments = AppointmentModel.get_all_appointments()
    
    stats = {
        'total_users': len(users),
        'total_appointments': len(appointments),
        'patients_count': len([u for u in users if u['role'] == 'patient']),
        'admins_count': len([u for u in users if u['role'] == 'admin'])
    }
    return jsonify({
        'stats': stats,
        'users': users,
        'appointments': appointments
    })

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user_by_admin(current_user, user_id):
    data = request.get_json()
    success = UserModel.update_user(
        user_id=user_id,
        username=data['username'],
        email=data['email'],
        role=data['role']
    )
    if success:
        return jsonify({'message': f'User ID {user_id} updated successfully.'})
    return jsonify({'error': 'User update failed.'}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user_by_admin(current_user, user_id):
    if user_id == current_user['id']:
        return jsonify({'error': 'Admin cannot delete their own active account!'}), 400

    success = UserModel.delete_user(user_id)
    if success:
        return jsonify({'message': f'User ID {user_id} deleted successfully.'})
    return jsonify({'error': 'User deletion failed.'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)