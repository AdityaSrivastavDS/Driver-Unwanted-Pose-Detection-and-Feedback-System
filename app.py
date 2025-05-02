from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
import bcrypt   
import cv2
from playsound import playsound
from threading import Thread, Event
from datetime import datetime
import os
from pose_detection import detect_pose
from flask import abort
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)
camera = cv2.VideoCapture(0)

# Global event for controlling sound
sound_stop_event = Event()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'processed')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

db = SQLAlchemy(app)
app.secret_key = 'secret_key'

# Ensure upload folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


def play_alert_sound():
    try:
        # Reset the event flag
        sound_stop_event.clear()
        while not sound_stop_event.is_set():
            playsound("static/resources/random_alert.mp3")
            # Small delay to prevent CPU overload
            sound_stop_event.wait(0.1)
    except Exception as e:
        print("Sound alert error:", e)

def process_frame(frame, user_email):
    try:
        is_unwanted, class_name, confidence = detect_pose(frame)
        label = f"{class_name}: {confidence * 100:.2f}%"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9,  
                    (0, 0, 255) if is_unwanted else (0, 255, 0), 2)
        return frame, is_unwanted, class_name, confidence
    except Exception as e:
        print(f"Error processing frame: {e}")
        return frame, False, "Error", 0

def gen_frames(user_email):
    # Only record for normal users, not admin
    if user_email.endswith("@poseguard.com"):
        return

    unwanted_pose_count = 0  # Counter for consecutive unwanted pose detections
    threshold = 10  # Increased threshold for unwanted pose detection
    last_alert_time = datetime.now()  # Track last alert time
    cooldown_seconds = 10  # Cooldown period between alerts
    sound_thread = None

    while True:
        try:
            success, frame = camera.read()
            if not success:
                print("Failed to grab frame")
                continue

            # Process frame in a separate thread
            frame_thread = Thread(target=process_frame, args=(frame, user_email))
            frame_thread.start()
            frame_thread.join()

            frame, is_unwanted, class_name, confidence = process_frame(frame, user_email)

            if is_unwanted:
                unwanted_pose_count += 1
            else:
                unwanted_pose_count = 0
                # Stop sound if pose becomes correct
                if sound_thread and sound_thread.is_alive():
                    sound_stop_event.set()

            current_time = datetime.now()
            time_since_last_alert = (current_time - last_alert_time).total_seconds()

            if unwanted_pose_count > threshold and time_since_last_alert >= cooldown_seconds:
                timestamp = current_time.strftime("%Y%m%d_%H%M%S")
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

                # Start new sound alert thread
                if not sound_thread or not sound_thread.is_alive():
                    sound_thread = Thread(target=play_alert_sound)
                    sound_thread.start()
                
                last_alert_time = current_time  # Update last alert time
                unwanted_pose_count = 0  # Reset the counter after triggering the alert

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error in frame processing: {e}")
            continue


@app.route('/video_feed/<filename>')
def video_feed(filename):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    def generate_frames():
        video_path = os.path.join(tempfile.gettempdir(), secure_filename(filename))
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("Error: Unable to open video file.")
            return
            
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            try:
                is_unwanted, class_name, confidence = detect_pose(frame)
                label = f"{class_name}: {confidence * 100:.1f}%"
                color = (0, 0, 255) if is_unwanted else (0, 255, 0)
                cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            except Exception as e:
                print(f"Error processing frame: {e}")

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        cap.release()

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#For live video processing
@app.route('/live_feed')
def live_feed():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    def generate_live_frames():
        while True:
            success, frame = camera.read()
            if not success:
                print("Failed to grab frame")
                break

            try:
                is_unwanted, class_name, confidence = detect_pose(frame)
                label = f"{class_name}: {confidence * 100:.1f}%"
                color = (0, 0, 255) if is_unwanted else (0, 255, 0)
                cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            except Exception as e:
                print(f"Error processing frame: {e}")

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(generate_live_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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


@app.route('/admin')
def admin_portal():
    if 'user' not in session or not session['user'].endswith('@poseguard.com'):
        abort(403)
    
    # Fetch screenshot alerts
    shots = ScreenshotAlert.query.order_by(ScreenshotAlert.timestamp.desc()).all()
    
    return render_template('admin_portal.html', shots=shots)


@app.route('/reports')
def reports():
    if 'user' not in session or not session['user'].endswith('@poseguard.com'):
        abort(403)
    
    # Fetch alerts and screenshots
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    screenshots = ScreenshotAlert.query.order_by(ScreenshotAlert.timestamp.desc()).all()
    
    return render_template('reports.html', alerts=alerts, screenshots=screenshots)

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.route('/video-upload')
def video_upload():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('video_upload.html')

@app.route('/process-video', methods=['POST'])
def process_video():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if 'video' not in request.files:
        return 'No video file uploaded', 400
    
    video_file = request.files['video']
    if video_file.filename == '':
        return 'No selected file', 400
    
    if not allowed_file(video_file.filename):
        return 'Invalid file type', 400

    # Save uploaded file temporarily
    temp_path = os.path.join(tempfile.gettempdir(), secure_filename(video_file.filename))
    video_file.save(temp_path)
    
    return render_template('video_upload.html', 
                         filename=secure_filename(video_file.filename))


if __name__ == '__main__':
    if not os.path.exists('static/screenshots'):
        os.makedirs('static/screenshots')
    app.run(debug=True)