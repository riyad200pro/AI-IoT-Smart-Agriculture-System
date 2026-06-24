import tensorflow as tf
from sklearn.metrics import precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
import os

# Veri seti yolu
data_path = "data"

# Veriyi yükleme
images = []
labels = []

for subfolder in os.listdir(data_path):
    subfolder_path = os.path.join(data_path, subfolder)
    if not os.path.isdir(subfolder_path):
        continue

    for image_filename in os.listdir(subfolder_path):
        image_path = os.path.join(subfolder_path, image_filename)
        images.append(image_path)
        labels.append(subfolder)

data = pd.DataFrame({'image': images, 'label': labels})

# Veri setini bölme
strat = data['label']
train_df, dummy_df = train_test_split(data, train_size=0.81, shuffle=True, random_state=123, stratify=strat)

strat = dummy_df['label']
valid_df, test_df = train_test_split(dummy_df, train_size=0.5, shuffle=True, random_state=123, stratify=strat)

# Parametreler
img_height, img_width = 128, 128  # Girdi boyutları
batch_size = 32
num_classes = len(data['label'].unique())  # Sınıf sayısı

# Veri artırma ve ön işleme
train_datagen = ImageDataGenerator(rescale=1./255,
                                    rotation_range=20,
                                    width_shift_range=0.2,
                                    height_shift_range=0.2,
                                    shear_range=0.2,
                                    zoom_range=0.2,
                                    horizontal_flip=True)
val_test_datagen = ImageDataGenerator(rescale=1./255)

def dataframe_to_generator(df, datagen, target_size, batch_size):
    return datagen.flow_from_dataframe(
        dataframe=df,
        directory=None,
        x_col="image",
        y_col="label",
        target_size=target_size,
        batch_size=batch_size,
        class_mode="categorical"
    )

train_data = dataframe_to_generator(train_df, train_datagen, (img_height, img_width), batch_size)
val_data = dataframe_to_generator(valid_df, val_test_datagen, (img_height, img_width), batch_size)
test_data = dataframe_to_generator(test_df, val_test_datagen, (img_height, img_width), batch_size)

# Kendi callback fonksiyonumuzu tanımlayalım
class MetricsHistory(tf.keras.callbacks.Callback):
    def __init__(self):
        super().__init__()
        self.precisions = []
        self.recalls = []
        self.f1_scores = []

    def on_epoch_end(self, epoch, logs=None):
        # Her epoch sonunda doğrulama verisi üzerinde tahmin yapalım
        val_data = self.validation_data[0]
        val_labels = self.validation_data[1]
        val_predictions = np.argmax(self.model.predict(val_data), axis=1)

        # Precision, Recall ve F1-Score hesapla
        precision = precision_score(val_labels, val_predictions, average='weighted', zero_division=1)
        recall = recall_score(val_labels, val_predictions, average='weighted', zero_division=1)
        f1 = f1_score(val_labels, val_predictions, average='weighted', zero_division=1)

        # Metrikleri kaydet
        self.precisions.append(precision)
        self.recalls.append(recall)
        self.f1_scores.append(f1)

# Model
model = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(img_height, img_width, 3)),
    MaxPooling2D((2, 2)),
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D((2, 2)),
    Conv2D(128, (3, 3), activation='relu'),
    MaxPooling2D((2, 2)),
    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.5),
    Dense(num_classes, activation='softmax')
])

# Modeli derleme
model.compile(optimizer='adam',
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# Early stopping
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# Callback'i başlat
metrics_history = MetricsHistory()

# Modeli eğitirken callback'i dahil et
history = model.fit(train_data,
                    validation_data=val_data,
                    epochs=3,
                    callbacks=[early_stopping, metrics_history])

# Precision, Recall ve F1-Score Grafikleri
def plot_metrics(metrics_history):
    # Precision grafiği
    plt.figure(figsize=(12, 6))
    plt.plot(metrics_history.precisions, label="Precision", color='blue')
    plt.title('Precision over Epochs')
    plt.xlabel('Epochs')
    plt.ylabel('Precision')
    plt.legend()
    plt.show()

    # Recall grafiği
    plt.figure(figsize=(12, 6))
    plt.plot(metrics_history.recalls, label="Recall", color='green')
    plt.title('Recall over Epochs')
    plt.xlabel('Epochs')
    plt.ylabel('Recall')
    plt.legend()
    plt.show()

    # F1-Score grafiği
    plt.figure(figsize=(12, 6))
    plt.plot(metrics_history.f1_scores, label="F1-Score", color='red')
    plt.title('F1-Score over Epochs')
    plt.xlabel('Epochs')
    plt.ylabel('F1-Score')
    plt.legend()
    plt.show()

# Metrikleri çizme
plot_metrics(metrics_history)

# Modeli değerlendirme
test_loss, test_accuracy = model.evaluate(test_data)
print(f"Test Accuracy: {test_accuracy * 100:.2f}%")

# Modeli kaydetme
model.save("corn_disease_cnn_model.h5")
