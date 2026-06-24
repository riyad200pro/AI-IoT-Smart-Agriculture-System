#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 18 18:16:20 2024

@author: mesut
"""

import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score

# Veri setini yükleme
data = pd.read_csv('Crop_recommendation.csv')  # CSV dosyasını yükleyin

# Özellikler ve etiketler
X = data[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
y = data['label']

# Veriyi eğitim ve test setlerine ayırma
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# Decision Tree modelini optimize etmek için GridSearchCV ayarları
param_grid = {
    'criterion': ['gini', 'entropy'],  # Bölünme kriteri
    'max_depth': [None, 5, 10, 15, 20],  # Maksimum derinlik
    'min_samples_split': [2, 5, 10],  # Bir düğümün bölünmesi için minimum örnek sayısı
    'min_samples_leaf': [1, 2, 4],  # Bir yaprak düğümünde bulunması gereken minimum örnek sayısı
}

# Model ve GridSearchCV
dt = DecisionTreeClassifier(random_state=42)
grid_search = GridSearchCV(dt, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid_search.fit(X_train, y_train)

# En iyi parametreler ve model performansı
print("En iyi parametreler:", grid_search.best_params_)
print("Eğitim setindeki en iyi doğruluk skoru: {:.2f}%".format(grid_search.best_score_ * 100))

# Test seti performansı
best_dt = grid_search.best_estimator_
y_pred = best_dt.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Test setindeki doğruluk skoru: {accuracy * 100:.2f}%")

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
probabilities = best_dt.predict_proba(input_data)[0]
class_indices = probabilities.argsort()[::-1]  # En yüksek olasılıkları sıralama

# %30 üzerindeki ürünleri sıralama
recommended_crops = [(best_dt.classes_[index], probabilities[index] * 100)
                     for index in class_indices if probabilities[index] > 0.3]  # %30 üzerindekileri al

# Sonuçları yazdırma
if recommended_crops:
    print("\nTahmin edilen ekilecek ürün önerileri (%30 üzerindeki olasılıklara göre sıralanmış):")
    for i, (crop, prob) in enumerate(recommended_crops, start=1):
        print(f"{i}. {crop}: {prob:.2f}%")
else:
    print("\nTahmin edilecek uygun bir ürün bulunamadı.")
