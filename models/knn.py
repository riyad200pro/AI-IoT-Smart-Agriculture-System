#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 18 18:14:58 2024

@author: mesut
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

# Örnek veri seti (CSV dosyasından alınabilir)
data = pd.read_csv('Crop_recommendation.csv')  # CSV dosyasını yükleyin

# Özellikler ve etiketler
X = data[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
y = data['label']

# Veriyi eğitim ve test setlerine ayırma
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# KNN modeli oluşturma ve eğitme
model = KNeighborsClassifier(n_neighbors=5)  # K değeri 5 olarak ayarlandı
model.fit(X_train, y_train)

# Modelin doğruluk skorunu test etme
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Doğruluk Skoru: {accuracy * 100:.2f}%")

# Kullanıcıdan sensör verilerini alma
print("\nToprağa ait bilgileri giriniz:")
N = float(input("Azot (N) değeri: "))
P = float(input("Fosfor (P) değeri: "))
K = float(input("Potasyum (K) değeri: "))
temperature = float(input("Sıcaklık (°C): "))
humidity = float(input("Nem (%): "))
ph = float(input("pH değeri: "))
rainfall = float(input("Yağış (mm): "))

# Kullanıcıdan alınan verileri bir DataFrame'e dönüştürme
input_data = pd.DataFrame([[N, P, K, temperature, humidity, ph, rainfall]],
                          columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])

# Tahmin olasılıklarını hesaplama
probabilities = model.predict_proba(input_data)[0]
class_indices = probabilities.argsort()[::-1]  # En yüksek olasılıkları sıralama

# Olasılığı %50'nin üzerinde olan sınıfları filtreleme
recommended_crops = [(model.classes_[index], probabilities[index] * 100) 
                     for index in class_indices if probabilities[index] > 0.5]

# Önerileri yazdırma
if recommended_crops:
    print("\nTahmin edilen ekilecek ürün önerileri (%50'den büyük olasılıklar):")
    for i, (crop, prob) in enumerate(recommended_crops, start=1):
        print(f"{i}. {crop} ({prob:.2f}%)")
else:
    print("\nHiçbir ürün %50'nin üzerinde bir olasılıkla tahmin edilmedi.")
