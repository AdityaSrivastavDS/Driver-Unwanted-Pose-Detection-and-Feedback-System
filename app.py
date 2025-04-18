from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
import bcrypt   
import cv2
from playsound import playsound
from threading import Thread
from datetime import datetime
import os
from pose_detection import detect_pose
from flask import abort

app = Flask(__name__)
camera = cv2.VideoCapture(0)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __init__(self, name, username, email, password):
        self.name = name
        self.username = username
        self.email = email
        self.password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
    def check_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, alert_type, user_email):
        self.alert_type = alert_type
        self.user_email = user_email

class ScreenshotAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(200), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    alert_type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def gen_frames(user_email):
    # Only record for normal users, not admin
    if user_email.endswith("@poseguard.com"):
        return

    while True:
        success, frame = camera.read()
        if not success:
            break

        is_unwanted, class_name, confidence = detect_pose(frame)

        if is_unwanted:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user_email}_{timestamp}.jpg"
            image_path = f"static/screenshots/{filename}"
            cv2.imwrite(image_path, frame)

            with app.app_context():
                new_alert = Alert(alert_type=f"Unwanted Pose Detected ({class_name})", user_email=user_email)
                db.session.add(new_alert)

                screenshot_alert = ScreenshotAlert(
                    image_path=image_path,
                    user_email=user_email,
                    alert_type=f"Unwanted Pose Detected ({class_name})"
                )
                db.session.add(screenshot_alert)
                db.session.commit()

            try:
                playsound("static/resources/random_alert.mp3")
            except Exception as e:
                print("Sound alert error:", e)

        label = f"{class_name}: {confidence * 100:.2f}%"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 0, 255) if is_unwanted else (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session.get('user')
    
    # ❌ Prevent admin from running video feed
    if user_email.endswith('@poseguard.com'):
        return "Admins do not have access to live video feed."

    return Response(gen_frames(user_email), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            return render_template('signup.html', error="Username or Email already exists!")

        new_user = User(name, username, email, password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['username']
        password = request.form['password']
        user = User.query.filter((User.username == email_or_username) | (User.email == email_or_username)).first()

        if user and user.check_password(password):
            session['user'] = user.email
            if user.email.endswith("@poseguard.com"):
                session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

# In app.py
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session.get('user')
    is_admin = user_email.endswith('@poseguard.com')
    return render_template('dashboard.html', is_admin=is_admin)


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/information')
def information():
    return render_template('information.html')

@app.route('/alerts')
def alerts():
    return redirect(url_for('login'))

@app.route('/admin')
def admin_portal():
    if 'user' not in session or not session['user'].endswith('@poseguard.com'):
        abort(403)
    
    # Fetch screenshot alerts
    all_screenshots = ScreenshotAlert.query.order_by(ScreenshotAlert.timestamp.desc()).all()
    
    return render_template('admin_portal.html', screenshots=all_screenshots)


@app.route('/reports')
def reports():
    if 'user' not in session or not session['user'].endswith('@poseguard.com'):
        abort(403)
    # your report logic
    return render_template('reports.html')

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


if __name__ == '__main__':
    app.run(debug=True)
