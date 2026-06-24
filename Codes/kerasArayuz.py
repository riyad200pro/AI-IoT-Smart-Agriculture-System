#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 07:33:30 2025

@author: mesut
"""
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model

# Modeli yükleyin (eğer model bellekte değilse)
model = tf.keras.models.load_model('my_model1.keras')  # veya 'mysaved_model.h5'

# Test edilecek resmin yolunu belirtin
img_path = 'test_resimleri/WhatsApp Image 2025-01-14 at 17.59.35.jpeg'

# Resmi yükleyin ve işleyin
img = image.load_img(img_path, target_size=(224, 224))
img_array = image.img_to_array(img) / 255.0
img_array = np.expand_dims(img_array, axis=0)

# Tahmin yap
prediction = model.predict(img_array)
predicted_class = np.argmax(prediction, axis=1)

# Sınıf isimleri
class_names = ['Blight', 'Common_Rust', 'Gray_Leaf_Spot', 'Healthy']

# Sonucu yazdırın
print(f"Tahmin edilen sınıf: {class_names[predicted_class[0]]}")

# Resmi ve sonucu görselleştirin
plt.imshow(img)
plt.axis('off')
plt.title(f"Tahmin: {class_names[predicted_class[0]]}")
plt.show()
