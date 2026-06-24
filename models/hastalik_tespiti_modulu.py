# hastalik_tespiti_modulu.py
import tkinter as tk
from tkinter import messagebox
# Diğer PIL, numpy, tf, os, glob, datetime, smtplib, email importları aynı kalacak...
import os
import glob
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np
import tensorflow as tf

import threading
import time

# === MODÜL AYARLARI VE SABİTLER ===
# (MODEL_HASTALIK_PATH, HASTALIK_CLASS_LABELS, DISEASE_EXPLANATIONS, IMAGE_FOLDER_PATH, vb. aynı kalacak)
# --- Model ve Hastalık Bilgileri ---
MODEL_HASTALIK_PATH = "best_leaf_model.keras"
HASTALIK_CLASS_LABELS = {0: "Yanık", 1: "Sağlıklı", 2: "Paslı Yaprak", 3: "Lekeli Yaprak"}
DISEASE_EXPLANATIONS = {
    "Yanık": "Düzenli ve yeterli sulama yapın.\nGübre kullanın, toprağın besin ihtiyacı eksik olduğunda yapraklar yanık olur.",
    "Paslı Yaprak": "Bitki stresini azaltın (susuzluk, aşırı sıcak gibi faktörlere dikkat edin).\nDengeli gübreleme yapın.\nEnfekte yaprakları elde toplayıp yakarak veya çöpe atarak uzaklaştırın.",
    "Lekeli Yaprak": "Aşırı sulama yapmayın.\nEkim rotasyonu yapın.\nYağmurlama sulama yerine damla sulama tercih edin.\nHer yıl aynı yere mısır ekmeyin.\nFasulye, buğday gibi farklı bitkilerle dönüşümlü ekim yaparak patojenin toprakta kalmasını engelleyin.",
    "Sağlıklı": "Bitkiniz sağlıklı görünüyor. Düzenli bakım ve gözlem yapmaya devam edin!"
}
# HASTALIK_ARKA_PLAN_RESMI artık doğrudan kullanılmayacak ama _open_hastalik_result_window için kalabilir.

# --- Otomatik Resim Alma Ayarları ---
IMAGE_FOLDER_PATH = "/home/pi5/Desktop/final/Test_Resimleri"
ALLOWED_IMAGE_EXTENSIONS = ('*.jpg', '*.jpeg', '*.png')

# --- E-posta Ayarları ---
GMAIL_ADRESI = "mesutbulut305@gmail.com"
GMAIL_SIFRESI = "jsyyoryytwdpupgf" # Uygulama Şifresi
ALICI_EMAIL_ADRESLERI = ["mesut.2000.bulut@gmail.com"]

# === MODEL YÜKLEME ===
# (_load_hastalik_model fonksiyonu ve ilgili değişkenler aynı kalacak)
model_hastalik_tespiti = None
MODEL_LOAD_ERROR_MESSAGE = None
IS_MODEL_LOADED = False

def _load_hastalik_model():
    global model_hastalik_tespiti, MODEL_LOAD_ERROR_MESSAGE, IS_MODEL_LOADED
    # ... (önceki gibi) ...
    if model_hastalik_tespiti is not None: # Örnek olarak kısa tutuldu, önceki yükleme mantığı geçerli
        IS_MODEL_LOADED = True
        return True
    try:
        if not os.path.exists(MODEL_HASTALIK_PATH):
            module_dir = os.path.dirname(__file__)
            potential_model_path = os.path.join(module_dir, MODEL_HASTALIK_PATH)
            if not os.path.exists(potential_model_path):
                 raise FileNotFoundError(f"Model dosyası bulunamadı: {MODEL_HASTALIK_PATH} veya {potential_model_path}")
            actual_model_path = potential_model_path
        else:
            actual_model_path = MODEL_HASTALIK_PATH

        model_hastalik_tespiti = tf.keras.models.load_model(actual_model_path)
        print(f"'{actual_model_path}' modeli (hastalık tespit) modülden başarıyla yüklendi.")
        IS_MODEL_LOADED = True
        return True
    except FileNotFoundError as e:
        MODEL_LOAD_ERROR_MESSAGE = str(e)
        print(MODEL_LOAD_ERROR_MESSAGE)
        IS_MODEL_LOADED = False
        return False
    except Exception as e:
        MODEL_LOAD_ERROR_MESSAGE = f"Hastalık tespit modeli ('{MODEL_HASTALIK_PATH}') yüklenirken bir hata oluştu: {e}\nBu özellik çalışmayabilir."
        print(MODEL_LOAD_ERROR_MESSAGE)
        IS_MODEL_LOADED = False
        return False

_load_hastalik_model()


# === YARDIMCI FONKSİYONLAR ===
# (_get_latest_images ve _send_email_notification aynı kalacak)
def _get_latest_images(folder_path, count=1):
    # ... (önceki gibi, count=1 default) ...
    if not os.path.isdir(folder_path):
        print(f"Hata: Resim klasörü bulunamadı: {folder_path}")
        return []
    image_files = []
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
    if not image_files:
        print(f"Uyarı: '{folder_path}' klasöründe hiç resim bulunamadı.")
        return []
    try:
        image_files.sort(key=os.path.getmtime, reverse=True)
    except Exception as e:
        print(f"Resimler zaman damgasına göre sıralanırken hata: {e}")
    return image_files[:count]


def _send_email_notification(subject, html_body, recipients):
    # ... (önceki gibi) ...
    if not GMAIL_ADRESI or not GMAIL_SIFRESI:
        print("E-posta göndermek için GMAIL_ADRESI ve GMAIL_SIFRESI ayarlanmalıdır.")
        return False, "E-posta gönderici bilgileri eksik."
    msg = MIMEMultipart('alternative')
    msg["From"] = GMAIL_ADRESI
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo(); server.starttls(); server.ehlo()
        server.login(GMAIL_ADRESI, GMAIL_SIFRESI)
        server.sendmail(GMAIL_ADRESI, recipients, msg.as_string())
        server.quit()
        return True, "E-posta başarıyla gönderildi."
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP Kimlik Doğrulama Hatası: {e}"
    except Exception as e:
        return False, f"E-posta gönderilirken bir hata oluştu: {e}"


# GUI sonuç penceresi fonksiyonu (_open_hastalik_result_window) artık çağrılmayacak.
# İsteğe bağlı olarak silinebilir veya referans için bırakılabilir.

# === SAATLİK OTOMATİK TESPİT İÇİN YENİ FONKSİYONLAR ===
_monitoring_thread = None
_stop_event = threading.Event()
_initial_setup_successful_for_monitoring = False

# hastalik_tespiti_modulu.py içinde

# ... (diğer importlar, sabitler, _load_hastalik_model, _get_latest_images aynı kalacak) ...
# _send_email_notification fonksiyonunu bu dosyadan kaldırın.

# _perform_detection_and_email fonksiyonu yerine bu gelecek:
def get_disease_detection_report():
    """
    En son tek resmi işler ve sonucu bir HTML string parçası olarak döndürür.
    """
    if not IS_MODEL_LOADED: # IS_MODEL_LOADED global değişkeni kontrol ediliyor
        print("Hastalık Tespiti: Model yüklenemedi.")
        return "<p style='color:red;'>Hastalık Tespiti: Model yüklenemedi.</p>"
    
    if not os.path.isdir(IMAGE_FOLDER_PATH): # IMAGE_FOLDER_PATH global değişkeni
        print(f"Hastalık Tespiti: Resim klasörü bulunamadı: {IMAGE_FOLDER_PATH}")
        return f"<p style='color:red;'>Hastalık Tespiti: Resim klasörü bulunamadı ({IMAGE_FOLDER_PATH}).</p>"

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Hastalık tespiti için son resim aranıyor...")
    latest_images = _get_latest_images(IMAGE_FOLDER_PATH, count=1)

    if not latest_images:
        msg = f"Hastalık Tespiti: '{IMAGE_FOLDER_PATH}' klasöründe işlenecek uygun resim bulunamadı."
        print(msg)
        return f"<p>{msg}</p>"

    image_path = latest_images[0]
    image_filename = os.path.basename(image_path)
    report_html = f"<h4>Hastalık Tespiti Sonucu (Resim: {image_filename})</h4>"

    try:
        img_height, img_width = 128, 128
        image_tf = tf.keras.utils.load_img(image_path, target_size=(img_height, img_width))
        image_array_tf = tf.keras.utils.img_to_array(image_tf) / 255.0
        image_array_tf = np.expand_dims(image_array_tf, axis=0)

        predictions = model_hastalik_tespiti.predict(image_array_tf, verbose=0)
        predicted_class_idx = np.argmax(predictions, axis=1)[0]
        predicted_label_str = HASTALIK_CLASS_LABELS.get(predicted_class_idx, "Bilinmeyen")
        confidence_val = np.max(predictions) * 100
        explanation_str = DISEASE_EXPLANATIONS.get(predicted_label_str, "Açıklama bulunamadı.")
        
        print(f"H.T - '{image_filename}': {predicted_label_str} ({confidence_val:.2f}%)")
        
        processed_explanation_for_html = explanation_str.replace("\n", "<br>")
        report_html += f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                <p><strong>Tahmin Edilen Durum:</strong> {predicted_label_str}</p>
                <p><strong>Doğruluk Oranı:</strong> {confidence_val:.2f}%</p>
                <p><strong>Öneriler ve Açıklama:</strong><br>{processed_explanation_for_html}</p>
            </div>"""
    except Exception as e:
        error_details = f"H.T - '{image_filename}' işlenirken hata: {str(e)}"
        print(error_details)
        report_html += f"<p style='color:red;'>{error_details.replace('<','&lt;').replace('>','&gt;')}</p>"
    
    return report_html


if __name__ == '__main__':
    # Modül doğrudan çalıştırıldığında test için kullanılabilir.
    print("hastalik_tespiti_modulu.py doğrudan test modunda çalıştırıldı.")
    
    # Test 1: Sadece bir kerelik çalıştırma (GUI'siz)
    # print("\n--- Tek Seferlik Test ---")
    # _perform_detection_and_email()
    
    # Test 2: Saatlik başlatma ve durdurma testi (konsoldan)
    print("\n--- Saatlik Test (10 saniyede bir çalışacak şekilde ayarlandı, normalde 3600sn) ---")
    # Gerçek kullanımda _hourly_task_runner içindeki _stop_event.wait(3600) olmalı.
    # Test için kısa bir süre (örn: 10 saniye) kullanılabilir.
    # Bunun için _hourly_task_runner içindeki wait süresini geçici olarak değiştirmeniz gerekir.
    # VEYA:
    # class DummyParent: pass # messagebox için
    # start_hourly_monitoring(DummyParent())
    # print("15 saniye boyunca çalışacak, sonra durdurulacak...")
    # time.sleep(15)
    # stop_hourly_monitoring()
    # print("Test tamamlandı.")
    pass