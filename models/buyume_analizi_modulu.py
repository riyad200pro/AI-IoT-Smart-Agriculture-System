#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 18 04:00:30 2025

@author: mesut
"""
# buyume_analizi_modulu.py
import cv2
import numpy as np
import os
import glob
import time
import datetime
import threading

# E-posta gönderme kütüphaneleri (hastalik_tespiti_modulu.py'den kopyalanabilir)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# === MODÜL AYARLARI VE SABİTLER ===
IMAGE_FOLDER_PATH = "/home/pi5/Desktop/final/Test_Resimleri" # Diğer modüllerle aynı olmalı
ALLOWED_IMAGE_EXTENSIONS = ('*.jpg', '*.jpeg', '*.png') # Resim arama için

# Gelişim analizi için varsayılan HSV değerleri ve eşik (verdiğiniz koddan)
DEFAULT_LHSV_STR = '35,50,50'
DEFAULT_UHSV_STR = '85,255,255'
DEFAULT_GROWTH_THRESHOLD_PERCENT = 5.0
METRIC_TO_COMPARE = 'contour_area' # Karşılaştırılacak metrik
MORPH_KERNEL_SIZE = 5 # segment_plant için
MIN_CONTOUR_AREA = 100 # segment_plant için

# E-posta Ayarları (diğer modüllerle aynı veya bu modüle özel olabilir)
GMAIL_ADRESI = "mesutbulut305@gmail.com"
GMAIL_SIFRESI = "jsyyoryytwdpupgf" # Uygulama Şifresi
ALICI_EMAIL_ADRESLERI = ["mesut.2000.bulut@gmail.com"]


# === THREAD KONTROL DEĞİŞKENLERİ ===
_growth_analysis_thread = None
_stop_growth_event = threading.Event()
_initial_setup_successful_ga = False # Büyüme analizi için ilk kurulum durumu


# === TEMEL CV FONKSİYONLARI (Verdiğiniz koddan alındı ve düzenlendi) ===
def load_and_check_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        # Hata vermek yerine None döndürüp çağıran yerde kontrol etmek daha iyi olabilir
        print(f"Hata: '{image_path}' bulunamadı veya okunamadı.")
        return None
    return img

def segment_plant(image, lower_hsv, upper_hsv, morph_kernel_size=MORPH_KERNEL_SIZE, min_contour_area=MIN_CONTOUR_AREA):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    if morph_kernel_size > 0:
        kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return np.zeros_like(mask), None, 0
    valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
    if not valid_contours: return np.zeros_like(mask), None, 0
    final_mask = np.zeros_like(mask)
    cv2.drawContours(final_mask, valid_contours, -1, (255), thickness=cv2.FILLED)
    # total_pixel_count = cv2.countNonZero(final_mask) # Bu satır calculate_metrics'te zaten var gibi
    return final_mask, valid_contours # total_pixel_count'ı kaldırdım

def calculate_metrics(contours):
    if contours is None or not contours: return {'pixel_count': 0, 'bounding_box_height': 0, 'bounding_box_width': 0, 'contour_area': 0}
    total_area = sum(cv2.contourArea(cnt) for cnt in contours)
    all_points = np.concatenate(contours)
    x, y, w, h = cv2.boundingRect(all_points)
    return {'pixel_count': int(total_area), 'bounding_box_height': h, 'bounding_box_width': w, 'contour_area': int(total_area)}

# Görselleştirme fonksiyonları (visualize_result, get_screen_resolution) arka plan görevi için kaldırıldı.
# select_image_file fonksiyonu da kaldırıldı, resimler otomatik seçilecek.

# === YARDIMCI FONKSİYONLAR ===
def _get_two_latest_images_for_growth(folder_path):
    if not os.path.isdir(folder_path):
        print(f"Hata: Büyüme analizi için resim klasörü bulunamadı: {folder_path}")
        return None, None
    
    image_files = []
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
    
    if len(image_files) < 2:
        print(f"Uyarı: '{folder_path}' klasöründe büyüme analizi için yeterli resim (en az 2) bulunamadı.")
        return None, None
        
    try:
        image_files.sort(key=os.path.getmtime, reverse=True) # En yeni önce
    except Exception as e:
        print(f"Resimler zaman damgasına göre sıralanırken hata: {e}")
        return None, None # Sıralama hatası durumunda işlem yapma

    return image_files[1], image_files[0] # [eski_resim, yeni_resim]

def _send_growth_email(subject, html_body, recipients):
    # Bu fonksiyon _send_email_notification (hastalik_tespiti_modulu.py) ile aynı olabilir.
    # Şimdilik kopyalıyorum, daha sonra ortak bir utility modülüne taşınabilir.
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
        return False, f"SMTP Kimlik Doğrulama Hatası (Büyüme Analizi): {e}"
    except Exception as e:
        return False, f"E-posta gönderilirken hata oluştu (Büyüme Analizi): {e}"


# === ANA ANALİZ VE E-POSTA GÖNDERME FONKSİYONU ===
# buyume_analizi_modulu.py içinde

# ... (diğer importlar, sabitler, temel CV fonksiyonları (load_and_check_image, segment_plant, calculate_metrics) aynı kalacak) ...
# _send_growth_email fonksiyonunu bu dosyadan kaldırın.

# _perform_growth_analysis_and_email fonksiyonu yerine bu gelecek:
def get_growth_analysis_report():
    """
    En son iki resmi karşılaştırır, büyüme analizi yapar ve sonucu HTML string olarak döndürür.
    """
    if not os.path.isdir(IMAGE_FOLDER_PATH): # IMAGE_FOLDER_PATH global sabiti
        msg = f"Büyüme Analizi: Resim klasörü bulunamadı: {IMAGE_FOLDER_PATH}"
        print(msg)
        return f"<p style='color:red;'>{msg}</p>"

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Büyüme analizi için son iki resim aranıyor...")
    img_path1, img_path2 = _get_two_latest_images_for_growth(IMAGE_FOLDER_PATH) # _get_two_latest_images_for_growth bu modülde tanımlı

    if not img_path1 or not img_path2:
        msg = "Büyüme Analizi: Karşılaştırma için yeterli resim (en az 2) bulunamadı."
        print(msg)
        return f"<p>{msg}</p>"

    report_html = f"<h4>Büyüme Analizi Sonuçları</h4>"
    report_html += f"<p>Karşılaştırılan Resimler:<ul><li>Eski: {os.path.basename(img_path1)}</li><li>Yeni: {os.path.basename(img_path2)}</li></ul></p>"

    try:
        lower_hsv = np.array([int(x) for x in DEFAULT_LHSV_STR.split(',')]) # Sabitler kullanılıyor
        upper_hsv = np.array([int(x) for x in DEFAULT_UHSV_STR.split(',')])

        img1 = load_and_check_image(img_path1)
        img2 = load_and_check_image(img_path2)

        if img1 is None or img2 is None:
            report_html += "<p style='color:red;'>Resimlerden biri veya her ikisi yüklenemedi.</p>"
            raise ValueError("B.A. - Resim yükleme hatası.")

        _, contours1 = segment_plant(img1, lower_hsv, upper_hsv) # segment_plant bu modülde tanımlı
        _, contours2 = segment_plant(img2, lower_hsv, upper_hsv)

        metrics1 = calculate_metrics(contours1) # calculate_metrics bu modülde tanımlı
        metrics2 = calculate_metrics(contours2)

        report_html += f"<div><strong>{os.path.basename(img_path1)} Metrikleri:</strong><pre style='background-color:#f0f0f0;padding:5px;'>{metrics1}</pre></div>"
        report_html += f"<div><strong>{os.path.basename(img_path2)} Metrikleri:</strong><pre style='background-color:#f0f0f0;padding:5px;'>{metrics2}</pre></div>"

        val1 = metrics1.get(METRIC_TO_COMPARE, 0) # METRIC_TO_COMPARE sabiti
        val2 = metrics2.get(METRIC_TO_COMPARE, 0)
        
        comparison_summary = f"<p><strong>Karşılaştırma ({METRIC_TO_COMPARE}):</strong><br>"
        comparison_summary += f"Eski Resim Değeri: {val1}<br>Yeni Resim Değeri: {val2}<br>"

        result_message = ""
        if val1 > 0:
            percentage_increase = ((val2 - val1) / val1) * 100
            comparison_summary += f"Yüzdesel Değişim: {percentage_increase:.2f}%</p>"
            if percentage_increase > DEFAULT_GROWTH_THRESHOLD_PERCENT: # Sabit kullanılıyor
                result_message = f"Büyüme tespit edildi (Eşik: >{DEFAULT_GROWTH_THRESHOLD_PERCENT}%)"
            else:
                result_message = f"Anlamlı bir büyüme tespit edilmedi veya bitki küçülmüş."
        elif val2 > 0:
            result_message = "Büyüme tespit edildi (İlk resimde bitki/alan yoktu)."
        else:
            result_message = "Her iki resimde de karşılaştırılacak bitki/alan bulunamadı."
        
        comparison_summary += f"<p style='font-weight:bold;'>{result_message}</p>"
        report_html += comparison_summary
        print(f"B.A. - Analiz tamamlandı. {result_message}")

    except Exception as e:
        err_msg = f"B.A. - Analiz sırasında hata: {str(e)}"
        print(err_msg)
        report_html += f"<p style='color:red;'><strong>Analiz Hatası:</strong> {err_msg.replace('<','&lt;').replace('>','&gt;')}</p>"
    
    return report_html



if __name__ == '__main__':
    print("buyume_analizi_modulu.py doğrudan test modunda çalıştırıldı.")
    # Test için IMAGE_FOLDER_PATH'in var olduğundan ve içinde en az 2 resim olduğundan emin olun.
    # _perform_growth_analysis_and_email() # Tek seferlik test
    # start_hourly_growth_analysis() # Saatlik test (wait süresini kısaltmayı unutmayın)
    # time.sleep(15)
    # stop_hourly_growth_analysis()
    pass