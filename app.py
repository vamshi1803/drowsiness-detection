from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
import subprocess
import json

app = Flask(__name__)
app.secret_key = 'abcdef0123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)

# Twilio setup
account_sid = "AC43c980359c0c2584c5b4808dc856f51e"
auth_token = "23d75fdba1f81837f017e5f495286541"
twilio_phone_number = "+19413940345"
client = Client(account_sid, auth_token)

# Home page
@app.route('/')
def home():
    return render_template('home.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists! Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, phone_number=phone_number)
        db.session.add(new_user)
        db.session.commit()

        # Log in the user right after registration
        session['user_id'] = new_user.id

        flash('Registration successful! You are now logged in.', 'success')
        flash('Please ensure your phone number is added to Twilio for SMS and call alerts.', 'info')

        return redirect(url_for('login'))  # Redirect to the homepage or dashboard

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

# ✅ Renamed logout function
@app.route('/logout')
def user_logout():
    session.pop('user_id', None)
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

# Index route
@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    flash(f"Welcome, {user.username}!", 'info')
    return render_template('index.html', user=user)

@app.route('/detect')
def detect():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch user from DB using session['user_id']
    user = User.query.get(session['user_id'])

    # Get the phone number
    phone_number = user.phone_number

    # Optional: Save user data to a JSON file for use in final.py (if needed)
    with open("current_user.json", "w") as f:
        json.dump({
            "username": user.username,
            "phone_number": phone_number
        }, f)

    # 🧠 Call your actual detection function or start the detection script here
    subprocess.Popen(['python', 'final.py'])  # change to your actual script

    flash("Detection system started. Check your project window!", "success")
    return redirect(url_for('index'))


# Print all routes to debug
print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    print(rule)

# Main
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
