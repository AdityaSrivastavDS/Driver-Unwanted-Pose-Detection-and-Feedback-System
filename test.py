import streamlit as st
import cv2
import numpy as np
from tensorflow.keras.models import load_model
from playsound import playsound
from PIL import Image
import os

# Ensure model path is correct using absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'model', 'poseguard_model.h5')

# Load the pre-trained model
try:
    model = load_model(model_path)
except Exception as e:
    st.error(f"Error loading model: {e}")
    raise

# Standardized class labels
class_labels = [
    "Normal Pose",       # class 0
    "Smoking",      # class 1
    "Using Phone",       # class 2 sahi
    "Other Distraction",           # class 3
    "Drinking",      # class 4 sahi
    "No Hands on Wheel", # class 5 sahi
    "Makeup",          # class 6 sahi
    "Looking Away"  # class 7 sahi
]

# Function to preprocess the input image
def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert to BGR for OpenCV
    resized = cv2.resize(frame, (224, 224))
    norm = resized.astype('float32') / 255.0
    return np.expand_dims(norm, axis=0)

# Function to detect unwanted pose
def detect_pose(frame):
    img = preprocess_frame(frame)
    prediction = model.predict(img)[0]
    pred_class = np.argmax(prediction)
    confidence = prediction[pred_class]
    return pred_class, confidence, prediction

# Streamlit app
st.set_page_config(page_title="Unwanted Pose Detection", layout="centered")
st.title("🚨 Unwanted Pose Detection")
st.write("Upload a video to detect unwanted driving behavior.")

uploaded_file = st.file_uploader("Choose a video...", type=["mp4", "avi", "mov"])

if uploaded_file is not None:
    video_path = os.path.join(current_dir, "uploaded_video.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_file.read())

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        st.error("Error: Unable to open the video file.")
    else:
        unwanted_pose_detected = False
        frame_placeholder = st.empty()  # Placeholder for displaying video frames

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Convert frame to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame_rgb, channels="RGB")

            pred_class, confidence, prediction = detect_pose(frame)

            if 0 <= pred_class < len(class_labels):
                if pred_class != 0 and not unwanted_pose_detected:  # Unwanted pose detected
                    unwanted_pose_detected = True
                    st.error(f"❌ Unwanted pose detected: {class_labels[pred_class]} (Confidence: {confidence:.2f})")

                    if os.path.exists("static/resources/random_alert.mp3"):
                        try:
                            playsound("static/resources/random_alert.mp3")
                        except Exception as e:
                            st.warning(f"Sound error: {e}")

            # Add a small delay to simulate real-time processing
            cv2.waitKey(1)

        cap.release()

        if not unwanted_pose_detected:
            st.success("✅ No unwanted pose detected in the video.")

