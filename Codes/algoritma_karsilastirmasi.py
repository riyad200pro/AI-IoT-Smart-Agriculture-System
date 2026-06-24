import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
import matplotlib.pyplot as plt
import seaborn as sns

# Veri setini yükleme
data = pd.read_csv('Crop_recommendation.csv')

# Özellikler ve etiketler
X = data[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
y = data['label']

# Veriyi eğitim ve test setlerine ayırma
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# Algoritmaları tanımlama
models = {
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(random_state=42),
    "SVM": SVC(probability=True, random_state=42),
    "KNN": KNeighborsClassifier()
}

# Performans sonuçlarını saklama
results = []
confusion_matrices = {}

for name, model in models.items():
    # Modeli eğitme
    model.fit(X_train, y_train)
    
    # Tahmin yapma
    y_pred = model.predict(X_test)
    
    # Performans metriklerini hesaplama
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Confusion Matrix'i hesaplama
    cm = confusion_matrix(y_test, y_pred)
    confusion_matrices[name] = cm
    
    # Sonuçları saklama
    results.append({
        "Model": name,
        "Accuracy": accuracy * 100,
        "F1 Score": f1 * 100
    })

# Sonuçları bir DataFrame'e dönüştürme
results_df = pd.DataFrame(results)

# Tabloyu yazdırma
print(results_df)

# Performansı görselleştirme
plt.figure(figsize=(10, 6))
for metric in ["Accuracy", "F1 Score"]:
    plt.plot(results_df["Model"], results_df[metric], marker='o', label=metric)

plt.title("Algoritma Performans Karşılaştırması")
plt.xlabel("Model")
plt.ylabel("Performans (%)")
plt.legend()
plt.grid()
plt.show()

# Confusion Matrix'leri görselleştirme
for name, cm in confusion_matrices.items():
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=model.classes_, yticklabels=model.classes_)
    plt.title(f'{name} - Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.show()
