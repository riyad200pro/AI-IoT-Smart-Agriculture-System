import os
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report

# Verilerinizi hazırlama (%80 Eğitim, %20 Test)
data_dir = 'data'
train_dir = 'data/train'
test_dir = 'data/test'

class_names = ['Blight', 'Common_Rust', 'Gray_Leaf_Spot', 'Healthy']

# 1. ResNet50 Modeli ve Transfer Öğrenme
base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
predictions = Dense(len(class_names), activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

for layer in base_model.layers:
    layer.trainable = False

model.compile(optimizer=Adam(), loss='categorical_crossentropy', metrics=['accuracy'])

# 2. Veri Augmentasyonu
train_datagen = ImageDataGenerator(rescale=1./255, shear_range=0.2, zoom_range=0.2, horizontal_flip=True)
val_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    train_dir, target_size=(224, 224), batch_size=32, class_mode='categorical')

validation_generator = val_datagen.flow_from_directory(
    test_dir, target_size=(224, 224), batch_size=32, class_mode='categorical', shuffle=False)

# 3. Modeli Eğitme
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

history = model.fit(
    train_generator,
    steps_per_epoch=train_generator.samples // train_generator.batch_size,
    epochs=40,  # Maksimum epoch sayısı
    validation_data=validation_generator,
    validation_steps=validation_generator.samples // validation_generator.batch_size,
    callbacks=[early_stopping]
)
# Modeli kaydetme - Yeni Keras formatı
model.save('my_model1.keras')
# 4. Confusion Matrix ve Performans Metrikleri
# Gerçek etiketler
y_true = validation_generator.classes

# Tahmin edilen etiketler
y_pred = model.predict(validation_generator, steps=validation_generator.samples // validation_generator.batch_size + 1)
y_pred_classes = np.argmax(y_pred, axis=1)

# Confusion matrisi
cm = confusion_matrix(y_true, y_pred_classes)

# Görselleştirme
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
disp.plot(cmap=plt.cm.Blues)
plt.title("Confusion Matrix")
plt.show()

# Performans raporu ve sınıf bazında metrikler
report = classification_report(y_true, y_pred_classes, target_names=class_names, output_dict=True)
print(classification_report(y_true, y_pred_classes, target_names=class_names))

# DataFrame oluştur
metrics_df = pd.DataFrame(report).transpose()
metrics_df = metrics_df.loc[class_names]  # Sadece sınıfları al

# Precision, Recall ve F1 Score Grafiklerini Çizme
plt.figure(figsize=(12, 6))

# Precision
plt.subplot(1, 3, 1)
plt.plot(metrics_df.index, metrics_df['precision'], marker='o', color='blue', label='Precision')
plt.title('Precision per Class')
plt.xlabel('Classes')
plt.ylabel('Precision')
plt.xticks(rotation=45)

# Recall
plt.subplot(1, 3, 2)
plt.plot(metrics_df.index, metrics_df['recall'], marker='o', color='orange', label='Recall')
plt.title('Recall per Class')
plt.xlabel('Classes')
plt.ylabel('Recall')
plt.xticks(rotation=45)

# F1 Score
plt.subplot(1, 3, 3)
plt.plot(metrics_df.index, metrics_df['f1-score'], marker='o', color='green', label='F1 Score')
plt.title('F1 Score per Class')
plt.xlabel('Classes')
plt.ylabel('F1 Score')
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()

# 5. Eğitim Sürecinin Görselleştirilmesi
plt.figure(figsize=(12, 6))

# Loss
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()

# Accuracy
plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Accuracy Over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend()

plt.tight_layout()
plt.show()
