import cv2
import numpy as np
from tensorflow.keras.models import load_model

# Load model only once when module is imported
model = load_model('model/poseguard_model.h5')

# Class labels for your model's output
class_labels = ['Drinking', 'Phone Call (Left)', 'Phone Call (Right)', 'Smoking',
                'Safe Driving', 'Texting (Left)', 'Texting (Right)', 'Hair and Makeup']

# Define unwanted classes
unwanted_classes = ['Drinking', 'Phone Call (Left)', 'Phone Call (Right)', 
                    'Smoking', 'Texting (Left)', 'Texting (Right)', 'Hair and Makeup']

def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    resized = cv2.resize(frame, (128, 128))
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
