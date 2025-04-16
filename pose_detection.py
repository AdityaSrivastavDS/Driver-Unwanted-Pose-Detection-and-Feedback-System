import cv2
import numpy as np
from tensorflow.keras.models import load_model

model = load_model('model/cnn_unwanted_pose.h5')
model.summary()

def preprocess_frame(frame):
    # Resize to match the model's expected input (128x128)
    resized = cv2.resize(frame, (128, 128))

    # Normalize pixel values
    norm = resized.astype('float32') / 255.0

    # Add batch dimension: (1, 128, 128, 3)
    return np.expand_dims(norm, axis=0)


def detect_pose(frame):
    img = cv2.resize(frame, (128, 128))           # Resize to match model input
    img = img.astype("float32") / 255.0           # Normalize
    img = np.expand_dims(img, axis=0)             # Add batch dimension
    prediction = model.predict(img)[0]            # Predict

    # Assuming the model outputs probabilities for classes
    unwanted_pose_threshold = 0.5                 # Define a threshold
    return prediction[0] > unwanted_pose_threshold  # Return True if unwanted pose detected
