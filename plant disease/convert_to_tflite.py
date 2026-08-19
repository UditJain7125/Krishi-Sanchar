"""
Run this ONCE, locally, on the machine where you trained the model and
still have full TensorFlow installed (e.g. wherever you ran
plant_disease_detection.ipynb). This is NOT deployed to Render — it just
produces a .tflite file that you commit to git instead of the .h5 file.

Usage:
    python convert_to_tflite.py

Requires: pip install tensorflow  (the full package, only needed locally)
"""

import tensorflow as tf

MODEL_PATH = "plant_disease_prediction_model.h5"
OUTPUT_PATH = "plant_disease_prediction_model.tflite"

print(f"Loading Keras model from {MODEL_PATH} ...")
model = tf.keras.models.load_model(MODEL_PATH)

print("Converting to TFLite ...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# DEFAULT optimization applies post-training quantization, which shrinks
# the model file and speeds up inference with a negligible accuracy hit
# for most image classifiers. Remove this line if you'd rather keep full
# float32 precision (bigger file, marginally more accurate).
converter.optimizations = [tf.lite.Optimize.DEFAULT]

tflite_model = converter.convert()

with open(OUTPUT_PATH, "wb") as f:
    f.write(tflite_model)

size_mb = len(tflite_model) / (1024 * 1024)
print(f"Saved {OUTPUT_PATH} ({size_mb:.2f} MB)")
print("Commit this .tflite file to git instead of the .h5 file.")
