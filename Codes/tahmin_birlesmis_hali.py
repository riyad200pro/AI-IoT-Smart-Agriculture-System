#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 18:20:52 2025

@author: mesut
"""

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

model = joblib.load('crop_recommendation_model.pkl')
# === 2. KULLANICIDAN GİRDİLERİ AL ===
print("\nToprağa ait bilgileri giriniz:")
N = float(input("Azot (N): "))
P = float(input("Fosfor (P): "))
K = float(input("Potasyum (K): "))
ph = float(input("pH: "))
sehir = input("Şehir (büyük harflerle): ").strip()
ay = int(input("Ay (1-12): "))

# === 3. EXCEL DOSYALARINDAN VERİ ÇEK ===
def veri_al(dosya_yolu, sheet, sehir, ay):
    df = pd.read_excel(dosya_yolu, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]  # Temizlik
    satir = df[df['Şehir'].str.upper() == sehir.upper()]
    if satir.empty:
        raise ValueError(f"{sehir} bulunamadı.")
    return float(satir.iloc[0, ay])  # 1-12 = Ocak-Aralık

# 🔽 BURAYA DOSYA YOLLARINI GİRECEKSİN
nem_dosya = "Nem_sehir_ortalamalari.xlsx"
sicaklik_dosya = "Sicaklik_sehir_ortalamalari.xlsx"
yagis_dosya = "Yagis_sehir_ortalamalari.xlsx"

try:
    nem = veri_al(nem_dosya, 'Sheet1', sehir, ay)
    sicaklik = veri_al(sicaklik_dosya, 'Sheet1', sehir, ay)
    yagis = veri_al(yagis_dosya, 'Sheet1', sehir, ay)
    print(nem,yagis,sicaklik)
except Exception as e:
    print("Veri çekilirken hata oluştu:", e)
    exit()

# === 4. TAHMİN YAP ===
input_data = pd.DataFrame([[N, P, K, sicaklik, nem, ph, yagis]],
                          columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])

# Tahmin ve olasılık
probabilities = model.predict_proba(input_data)[0]
class_indices = probabilities.argsort()[::-1]
recommended_crops = [(model.classes_[index], probabilities[index] * 100) 
                     for index in class_indices if probabilities[index] > 0.1]

print("\nTahmin edilen ürünler (%30'dan büyük olasılıklar):")
if recommended_crops:
    for i, (crop, prob) in enumerate(recommended_crops, 1):
        print(f"{i}. {crop} ({prob:.2f}%)")
else:
    print("Hiçbir ürün %30'un üzerinde olasılıkla tahmin edilmedi.")
