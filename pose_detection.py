import cv2
import numpy as np
from tensorflow.keras.models import load_model
import os

# Ensure model path is correct using absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'model', 'poseguard_model.h5')

# Load model only once when module is imported
try:
    model = load_model(model_path)
except Exception as e:
    print(f"Error loading model: {e}")
    raise

# Standardized class labels
class_labels = [
    "Normal Pose",       # class 0 sahi
    "",      # class 1
    "Using Phone",       # class 2 sahi
    "",           # class 3
    "Drinking",      # class 4 sahi
    "No Hands on Wheel", # class 5 sahi
    "Makeup",          # class 6 sahi
    "Looking Away"  # class 7 sahi
]


# Define unwanted classes (all except Normal Pose)
unwanted_classes = [label for label in class_labels if label != "Normal Pose"]

def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    resized = cv2.resize(frame, (224, 224))
    norm = resized.astype('float32') / 255.0
    return np.expand_dims(norm, axis=0)

def detect_pose(frame):
    img = preprocess_frame(frame)
    prediction = model.predict(img)[0]
    pred_class = np.argmax(prediction)
    class_name = class_labels[pred_class]
    confidence = prediction[pred_class]

    is_unwanted = class_name in unwanted_classes and confidence > 0.7
    return is_unwanted, class_name, confidence
