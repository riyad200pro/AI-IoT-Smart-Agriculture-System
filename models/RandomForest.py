import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

model = joblib.load('crop_recommendation_model.pkl')
print(f"Model Doğruluk Skoru: {accuracy * 100:.2f}%")
joblib.dump(model, 'crop_recommendation_model.pkl')
print("Model başarıyla kaydedildi.")

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
top_n = 21  # En yüksek olasılığa sahip kaç sınıf önerilecek
class_indices = probabilities.argsort()[::-1]  # En yüksek olasılıkları sıralama

# Olasılığı %50'nin üzerinde olan sınıfları filtreleme
recommended_crops = [(model.classes_[index], probabilities[index] * 100) 
                     for index in class_indices if probabilities[index] > 0.3]

# Önerileri yazdırma
if recommended_crops:
    print("\nTahmin edilen ekilecek ürün önerileri (%50'den büyük olasılıklar):")
    for i, (crop, prob) in enumerate(recommended_crops, start=1):
        print(f"{i}. {crop} ({prob:.2f}%)")
else:
    print("\nHiçbir ürün %50'nin üzerinde bir olasılıkla tahmin edilmedi.")
