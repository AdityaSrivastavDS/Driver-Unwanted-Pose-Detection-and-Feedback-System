from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import bcrypt   
from flask import Response
from pose_detection import detect_pose
import cv2
from playsound import playsound
from threading import Thread
from datetime import datetime


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

with app.app_context():
    db.create_all()


def gen_frames(user_email):
    while True:
        success, frame = camera.read()
        if not success:
            break

        is_unwanted, class_name, confidence = detect_pose(frame)

        if is_unwanted:
            with app.app_context():  # 👈 FIX
                new_alert = Alert(alert_type=f"Unwanted Pose Detected ({class_name})", user_email=user_email)
                db.session.add(new_alert)
                db.session.commit()

            try:
                playsound("static/resources/alert.mp3")
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
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/information')
def information():
    return render_template('information.html')

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    return render_template('reports.html', alerts=alerts)


if __name__ == '__main__':
    app.run(debug=True)
