#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 18 04:17:22 2025

@author: mesut
"""
# saatlik_gorev_yoneticisi.py
import threading
import time
import datetime
import os

# E-posta gönderme kütüphaneleri
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Diğer modüllerden ilgili fonksiyonları import et
MODULES_LOADED = False # Başlangıçta False
hastalik_tespiti_modulu = None
kamera_modulu = None
buyume_analizi_modulu = None

try:
    import hastalik_tespiti_modulu
    import kamera_modulu
    import buyume_analizi_modulu
    MODULES_LOADED = True
    print("Yönetici: Alt modüller (hastalık, kamera, büyüme) başarıyla yüklendi.")
except ImportError as e:
    print(f"YÖNETİCİ MODÜLÜ HATA: Gerekli alt modüllerden biri yüklenemedi: {e}")
    # MODULES_LOADED False olarak kalır.

# === E-POSTA AYARLARI (Merkezi) ===
GMAIL_ADRESI = "mesutbulut305@gmail.com"
GMAIL_SIFRESI = "jsyyoryytwdpupgf"
ALICI_EMAIL_ADRESLERI = ["mesut.2000.bulut@gmail.com"]

# === THREAD KONTROL DEĞİŞKENLERİ ===
_master_thread = None
_master_stop_event = threading.Event()
_initial_setup_manager_ok = False # Bu, yönetici modülün kendi kritik kontrolleri için

# === MERKEZİ E-POSTA GÖNDERME FONKSİYONU ===
def _send_combined_email(html_body_parts, recipients):
    if not GMAIL_ADRESI or not GMAIL_SIFRESI:
        print("Yönetici: E-posta göndermek için GMAIL_ADRESI ve GMAIL_SIFRESI ayarlanmalıdır.")
        return False, "E-posta gönderici bilgileri eksik."

    now = datetime.datetime.now()
    email_subject = f"Akıllı Bahçem - Saatlik Toplu Rapor ({now.strftime('%Y-%m-%d %H:%M')})"

    full_html_body = f"""
    <html><head><style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
        .email-container {{ max-width: 750px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #ffffff; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .section {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        .section:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        h2 {{ text-align: center; color: #0056b3; margin-top:0; }}
        h4 {{ color: #0056b3; margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 5px;}}
        pre {{ background-color: #f0f0f0; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }}
        p {{ margin: 5px 0; }}
        ul {{ padding-left: 20px; }}
    </style></head>
    <body><div class="email-container">
        <h2>Akıllı Bahçem - Saatlik Toplu Rapor</h2>
        <p style="text-align:center; font-size:0.9em; color:#777;">Rapor Tarihi: {now.strftime('%d %B %Y, Saat %H:%M:%S')}</p>
        
        <div class="section">
            {html_body_parts.get('kamera_raporu', '<p>Kamera raporu alınamadı.</p>')}
        </div>
        <div class="section">
            {html_body_parts.get('hastalik_raporu', '<p>Hastalık tespit raporu alınamadı.</p>')}
        </div>
        <div class="section">
            {html_body_parts.get('buyume_raporu', '<p>Büyüme analizi raporu alınamadı.</p>')}
        </div>
        
        <hr style="border:none; border-top:1px solid #eee; margin: 20px 0;">
        <p style="font-size: 0.9em; color: #777; text-align:center;">Bu e-posta Akıllı Bahçem sistemi tarafından otomatik olarak gönderilmiştir.</p>
    </div></body></html>
    """
    
    msg = MIMEMultipart('alternative')
    msg["From"] = GMAIL_ADRESI
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = email_subject
    msg.attach(MIMEText(full_html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_ADRESI, GMAIL_SIFRESI)
        server.sendmail(GMAIL_ADRESI, recipients, msg.as_string())
        server.quit()
        return True, "Birleşik e-posta başarıyla gönderildi."
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP Kimlik Doğrulama Hatası (Yönetici): {e}"
    except Exception as e:
        return False, f"Birleşik e-posta gönderilirken hata oluştu (Yönetici): {e}"

# === SAATLİK GÖREV ÇALIŞTIRICI ===
def _periodic_master_runner():
    global _initial_setup_manager_ok # Bu bayrak start_combined_hourly_tasks içinde ayarlanır

    # MODULES_LOADED ve _initial_setup_manager_ok kontrolü thread başladığında da önemli
    if not MODULES_LOADED:
        print("Yönetici (Thread): Gerekli alt modüller yüklenemediği için saatlik görevler çalıştırılamıyor.")
        return
    if not _initial_setup_manager_ok:
        print("Yönetici (Thread): İlk kurulum kontrolleri başarısız olduğu için saatlik görevler çalıştırılamıyor.")
        return

    print("Birleşik saatlik görev yöneticisi başladı. Durdurulana kadar her saat başı çalışacaktır.")
    while not _master_stop_event.is_set():
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Saatlik görevler başlıyor...")
        rapor_parcalari = {}

        # 1. Fotoğraf Çekme
        if hasattr(kamera_modulu, 'capture_photo_for_report'):
            print("--- Kamera Görevi Çalıştırılıyor ---")
            kamera_raporu_html, _ = kamera_modulu.capture_photo_for_report() # yeni_resim_yolu şu an kullanılmıyor
            rapor_parcalari['kamera_raporu'] = kamera_raporu_html
        else:
            rapor_parcalari['kamera_raporu'] = "<p style='color:orange;'>Kamera modülünde 'capture_photo_for_report' fonksiyonu bulunamadı.</p>"

        # 2. Hastalık Tespiti
        if hasattr(hastalik_tespiti_modulu, 'get_disease_detection_report'):
            print("--- Hastalık Tespit Görevi Çalıştırılıyor ---")
            rapor_parcalari['hastalik_raporu'] = hastalik_tespiti_modulu.get_disease_detection_report()
        else:
            rapor_parcalari['hastalik_raporu'] = "<p style='color:orange;'>Hastalık tespit modülünde 'get_disease_detection_report' fonksiyonu bulunamadı.</p>"
        
        # 3. Büyüme Analizi
        if hasattr(buyume_analizi_modulu, 'get_growth_analysis_report'):
            print("--- Büyüme Analizi Görevi Çalıştırılıyor ---")
            rapor_parcalari['buyume_raporu'] = buyume_analizi_modulu.get_growth_analysis_report()
        else:
            rapor_parcalari['buyume_raporu'] = "<p style='color:orange;'>Büyüme analizi modülünde 'get_growth_analysis_report' fonksiyonu bulunamadı.</p>"

        # 4. Birleşik E-posta Gönder
        print("--- Birleşik E-posta Gönderiliyor ---")
        email_gonderildi, email_durum_mesaji = _send_combined_email(rapor_parcalari, ALICI_EMAIL_ADRESLERI)
        if email_gonderildi:
            print(f"Yönetici: {email_durum_mesaji}")
        else:
            print(f"Yönetici (E-POSTA HATASI): {email_durum_mesaji}")
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Saatlik görevler tamamlandı. Bir sonraki çalıştırma bekleniyor...")
        if _master_stop_event.wait(3600): # 1 saat bekle
            break 
    print("Birleşik saatlik görev yöneticisi durduruldu.")


def start_combined_hourly_tasks(parent_window_for_initial_error=None):
    global _master_thread, _master_stop_event, _initial_setup_manager_ok
    from tkinter import messagebox # Sadece ilk hata için import

    if not MODULES_LOADED: # Bu global değişken modülün en başında ayarlanıyor
        msg = "Gerekli alt modüller (hastalık, kamera, büyüme) yüklenemediği için saatlik sistem başlatılamıyor. Lütfen konsolu kontrol edin."
        print(f"Yönetici (Başlatma): {msg}")
        if parent_window_for_initial_error:
            messagebox.showerror("Modül Yükleme Hatası", msg, parent=parent_window_for_initial_error)
        return False

    if _master_thread is not None and _master_thread.is_alive():
        print("Yönetici: Birleşik saatlik sistem zaten çalışıyor.")
        if parent_window_for_initial_error:
            messagebox.showinfo("Bilgi", "Birleşik saatlik sistem zaten çalışıyor.", parent=parent_window_for_initial_error)
        return False

    print("Yönetici: Birleşik saatlik sistem başlatılıyor...")
    _initial_setup_manager_ok = True # Başlangıçta true, kontroller false yapabilir

    # Hastalık modeli için kritik ön kontrol
    if hasattr(hastalik_tespiti_modulu, 'IS_MODEL_LOADED') and not hastalik_tespiti_modulu.IS_MODEL_LOADED:
        msg = (getattr(hastalik_tespiti_modulu, 'MODEL_LOAD_ERROR_MESSAGE', None) or 
               "Hastalık tespit modeli yüklenemedi (detay yok).")
        print(f"Yönetici (Kritik Hata): {msg}")
        if parent_window_for_initial_error:
            messagebox.showerror("Model Hatası (H.T.)", f"{msg}\nBirleşik sistem başlatılamıyor.", parent=parent_window_for_initial_error)
        _initial_setup_manager_ok = False
    
    # Kamera için kritik ön kontrol (örneğin, _check_camera_availability gibi bir fonksiyon varsa)
    # Bu fonksiyonu kamera_modulu.py'ye ekleyip public yapabilirsiniz.
    # Şimdilik bu kontrolü atlıyorum, kamera_modulu.capture_photo_for_report kendi içinde hallediyor.
    # if hasattr(kamera_modulu, 'is_camera_ready') and not kamera_modulu.is_camera_ready():
    #     msg = "Kamera hazır değil veya bulunamadı."
    #     print(f"Yönetici (Kritik Hata): {msg}")
    #     if parent_window_for_initial_error:
    #         messagebox.showerror("Kamera Hatası", f"{msg}\nBirleşik sistem başlatılamıyor.", parent=parent_window_for_initial_error)
    #     _initial_setup_manager_ok = False

    if not _initial_setup_manager_ok:
        print("Yönetici: Kritik ön kontroller başarısız olduğu için birleşik sistem başlatılamadı.")
        return False # Başlatma başarısız

    _master_stop_event.clear()
    _master_thread = threading.Thread(target=_periodic_master_runner, daemon=True)
    _master_thread.start()
    print("Yönetici: Birleşik saatlik sistem başarıyla başlatıldı (arka planda).")
    return True # Başlatma başarılı

def stop_combined_hourly_tasks():
    global _master_thread, _master_stop_event
    if _master_thread is not None and _master_thread.is_alive():
        print("Yönetici: Birleşik saatlik sistem durduruluyor...")
        _master_stop_event.set()
        _master_thread.join(timeout=10)
        if _master_thread.is_alive():
            print("Yönetici (Uyarı): Ana takip thread'i zamanında durmadı.")
        _master_thread = None
        print("Yönetici: Birleşik saatlik sistem durduruldu.")
        return True
    else:
        print("Yönetici: Birleşik saatlik sistem zaten çalışmıyor.")
        return False

if __name__ == '__main__':
    print("saatlik_gorev_yoneticisi.py doğrudan çalıştırıldı (test modu).")
    # if MODULES_LOADED:
    #     print("Alt modüller yüklendi.")
    #     # Basit bir parent simülasyonu (messagebox için)
    #     class DummyParent: pass 
    #     start_combined_hourly_tasks(DummyParent())
    #     # Test için _periodic_master_runner içindeki wait süresini kısaltın
    #     print("Test için 15 saniye bekleniyor...")
    #     time.sleep(15) 
    #     stop_combined_hourly_tasks()
    # else:
    #     print("Alt modüller yüklenemediği için test çalıştırılamıyor.")
    pass

