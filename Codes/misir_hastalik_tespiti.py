import tkinter as tk
from tkinter import filedialog, Label, Button, Toplevel
from PIL import Image, ImageTk
import tensorflow as tf
import numpy as np

# Modeli yükleme
model = tf.keras.models.load_model("corn_disease_cnn_model.h5")

# Sınıf etiketlerini tanımlama
class_labels = {0: "Yanık", 1: "Paslı Yaprak", 2: "Lekeli Yaprak", 3: "Sağlıklı"}

# Tkinter ana pencere
window = tk.Tk()
window.title("Mısır Yaprağı Hastalık Tespiti")
window.geometry("600x400+400+200")  # Ekranın ortasında konumlandır

# Arka plan resmi
bg_image_path = "mm.jpeg"  # Arka plan resmi yolunu kontrol edin
try:
    bg_image = Image.open(bg_image_path)
    bg_image = bg_image.resize((600, 400))
    bg_photo = ImageTk.PhotoImage(bg_image)
    background_label = Label(window, image=bg_photo)
    background_label.image = bg_photo  # Referansı sakla
    background_label.place(relwidth=1, relheight=1)
except Exception as e:
    print(f"Arka plan yüklenirken hata: {e}")
    window.configure(bg="lightblue")


# Görüntü seçme işlevi
def load_image():
    file_path = filedialog.askopenfilename(
        title="Görüntü Seçin",
        filetypes=[("All Files", "*.*"), ("JPEG Files", "*.jpg;*.jpeg"), ("PNG Files", "*.png")]
    )

    if not file_path:
        return

    # Görüntü ile tahmin yapma
    open_result_window(file_path)

def open_result_window(image_path):
    result_window = Toplevel(window)
    result_window.title("Tahmin Sonucu")
    result_window.geometry("400x400+450+250")  # Ekranın ortasında konumlandır
    result_window.overrideredirect(False)  # Kenarları kaldırmadan standart pencere

    # Farklı bir arka plan resmi veya renk
    new_bg_image_path = "WhatsApp Image 2025-01-14 at 17.47.33.jpeg"  # İkinci pencere için yeni bir arka plan resmi
    try:
        bg_image = Image.open(new_bg_image_path)
        bg_image = bg_image.resize((400, 400))
        bg_photo = ImageTk.PhotoImage(bg_image)
        background_label = Label(result_window, image=bg_photo)
        background_label.image = bg_photo  # Referansı sakla
        background_label.place(relwidth=1, relheight=1)
    except Exception as e:
        print(f"Arka plan yüklenirken hata: {e}")
        result_window.configure(bg="lightyellow")  # Yeni bir arka plan rengi de kullanabilirsiniz

    # Görüntü
    img = Image.open(image_path)
    img_resized = img.resize((300, 300))
    img_tk = ImageTk.PhotoImage(img_resized)
    img_label = Label(result_window, image=img_tk, bg="#ffffff")
    img_label.image = img_tk  # Referansı sakla
    img_label.pack(pady=10)

    # Tahmin yapma
    img_height, img_width = 128, 128  # Modelin giriş boyutları
    image = tf.keras.utils.load_img(image_path, target_size=(img_height, img_width))
    image_array = tf.keras.utils.img_to_array(image) / 255.0  # 0-1 aralığına ölçekleme
    image_array = np.expand_dims(image_array, axis=0)  # Batch boyutu ekleme

    predictions = model.predict(image_array)
    predicted_class = np.argmax(predictions, axis=1)[0]
    predicted_label = class_labels[predicted_class]
    confidence = np.max(predictions) * 100

    # Tahmin sonucu
    result_label = Label(result_window, text=f"Tahmin Sonucu: {predicted_label}", font=("Helvetica", 14, "bold"))
    result_label.pack(pady=10)

    confidence_label = Label(result_window, text=f"Doğruluk Oranı: %{confidence:.2f}", font=("Helvetica", 12))
    confidence_label.pack(pady=5)

    # Kapat butonu
    close_button = Button(result_window, text="Kapat", command=result_window.destroy, bg="#4682B4", fg="white", font=("Arial", 12, "bold"))
    close_button.pack(pady=20)

# Buton
btn_load = Button(window, text="Resim Seç", command=load_image, bg="#5CA4FF", fg="white",padx=10, pady=5, font=("Tahoma", 12, "bold"))
btn_load.place(relx=0.8, rely=0.1, anchor="center")

# Tkinter döngüsü
window.mainloop()
