import streamlit as st
import cv2
import numpy as np
from tensorflow.keras.models import load_model
from playsound import playsound
from PIL import Image
import os

# Load the pre-trained model
model = load_model('model/poseguard_model.h5')

# Class labels (update if needed)
class_labels = [
    "Normal Pose",       # class 0
    "Drinking",          # class 1
    "Using Phone",       # class 2
    "Smoking",           # class 3
    "Looking Away",      # class 4
    "No Hands on Wheel", # class 5
    "Sleeping",          # class 6
    "Other Distraction"  # class 7
]


# Function to preprocess the input image
def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert to BGR for OpenCV
    resized = cv2.resize(frame, (128, 128))
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
st.write("Upload an image to detect unwanted driving behavior.")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    frame = np.array(image)

    st.image(frame, caption="Uploaded Image", use_column_width=True)

    pred_class, confidence, prediction = detect_pose(frame)

    if 0 <= pred_class < len(class_labels):
        st.write(f"Prediction: **{class_labels[pred_class]}**")
        st.write(f"Confidence: `{confidence:.2f}`")

        if pred_class != 0:
            st.error("❌ Unwanted pose detected!")
            if os.path.exists("static/resources/alert.mp3"):
                try:
                    playsound("static/resources/alert.mp3")
                except Exception as e:
                    st.warning(f"Sound error: {e}")
        else:
            st.success("✅ No unwanted pose detected.")
    else:
        st.warning(f"⚠️ Prediction index `{pred_class}` is out of bounds!")
        st.text(f"Raw model output: {prediction}")

