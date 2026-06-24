import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
# CSV dosyasını yükleme
data = pd.read_csv('Crop_recommendation.csv')

# İlk birkaç satırı görüntüleme
print(data.head())

# Veri setinin boyutunu öğrenme
print(data.shape)

# Kolon isimlerini görüntüleme
print(data.columns)

# Eksik verileri kontrol et
print(data.isnull().sum())

# Veri türlerini incele
print(data.info())

# Sayısal kolonlar için temel istatistikler
print(data.describe())


import seaborn as sns
import matplotlib.pyplot as plt

# Sadece sayısal sütunları seç
numeric_data = data.select_dtypes(include=['float64', 'int64'])

# Korelasyon matrisi çizme
plt.figure(figsize=(10, 8))
sns.heatmap(numeric_data.corr(), annot=True, cmap='coolwarm')
plt.show()



# Özellikler (features) ve etiket (labels) ayırma
X = data[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
y = data['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

print("Eğitim Seti (X_train):", X_train.shape)
print("Eğitim Etiketleri (y_train):", y_train.shape)
print("Test Seti (X_test):", X_test.shape)
print("Test Etiketleri (y_test):", y_test.shape)

print("Eğitim setindeki etiket dağılımı:")
print(y_train.value_counts())

print("Test setindeki etiket dağılımı:")
print(y_test.value_counts())


# Modeli oluşturma ve eğitme
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Test seti üzerinde tahmin yapma
y_pred = model.predict(X_test)

# Doğruluk skorunu hesaplama
accuracy = accuracy_score(y_test, y_pred)
print("Doğruluk Skoru:", accuracy)
