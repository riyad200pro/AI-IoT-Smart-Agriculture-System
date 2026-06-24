# saatlik_gorev_yoneticisi.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 18 04:17:22 2025 # Bu tarih muhtemelen sizin oluşturma tarihiniz

@author: mesut
"""
import threading
import time
import datetime
import os
import sys # sys.executable için eklendi

# E-posta gönderme kütüphaneleri
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage # <<< RESİMLERİ EKLEMEK İÇİN YENİ IMPORT

# --- Diğer Modüllerin Import Edilmesi ---
# (Bu kısım bir önceki cevaptaki gibi, modüllerin import edilmesini ve
# None olarak ayarlanmasını içerir, burada tekrar yazmıyorum, aynı kalacak.)
print("SAATLİK GÖREV YÖNETİCİSİ: Modüller yükleniyor...")
# Örnek importlar (kendi kodunuzdaki gibi olmalı)
try:
    import merkezi_sensor_servisi # Eğer kullanıyorsanız
    print("SAATLİK GÖREV YÖNETİCİSİ: 'merkezi_sensor_servisi' yüklendi.")
except ImportError: merkezi_sensor_servisi = None; print("UYARI: 'merkezi_sensor_servisi' bulunamadı.")

try:
    import otomatik_sulama_modulu # Eğer kullanıyorsanız
    print("SAATLİK GÖREV YÖNETİCİSİ: 'otomatik_sulama_kontrolu' yüklendi.")
except ImportError: otomatik_sulama_modulu = None; print("UYARI: 'otomatik_sulama_kontrolu' bulunamadı.")

hastalik_tespiti_modulu = None
kamera_modulu = None
buyume_analizi_modulu = None
CORE_REPORT_MODULES_LOADED = False

try:
    import hastalik_tespiti_modulu
    print("SAATLİK GÖREV YÖNETİCİSİ: 'hastalik_tespiti_modulu' yüklendi.")
except ImportError: print("UYARI (SAATLİK GÖREV YÖN.): 'hastalik_tespiti_modulu' bulunamadı.");
except Exception as e: print(f"HATA (SAATLİK GÖREV YÖN.): 'hastalik_tespiti_modulu' yüklenirken: {e}");

try:
    import kamera_modulu
    print("SAATLİK GÖREV YÖNETİCİSİ: 'kamera_modulu' yüklendi.")
except ImportError: print("UYARI (SAATLİK GÖREV YÖN.): 'kamera_modulu' bulunamadı.");
except Exception as e: print(f"HATA (SAATLİK GÖREV YÖN.): 'kamera_modulu' yüklenirken: {e}");

try:
    import buyume_analizi_modulu
    print("SAATLİK GÖREV YÖNETİCİSİ: 'buyume_analizi_modulu' yüklendi.")
except ImportError: print("UYARI (SAATLİK GÖREV YÖN.): 'buyume_analizi_modulu' bulunamadı.");
except Exception as e: print(f"HATA (SAATLİK GÖREV YÖN.): 'buyume_analizi_modulu' yüklenirken: {e}");

if hastalik_tespiti_modulu and kamera_modulu and buyume_analizi_modulu:
    CORE_REPORT_MODULES_LOADED = True
    print("SAATLİK GÖREV YÖNETİCİSİ: Çekirdek raporlama modülleri (hastalık, kamera, büyüme) tam olarak yüklendi.")
else:
    print("UYARI (SAATLİK GÖREV YÖN.): Çekirdek raporlama modüllerinden bir veya daha fazlası yüklenemedi.")


# === E-POSTA AYARLARI (Merkezi) ===
GMAIL_ADRESI = "mesutbulut305@gmail.com"
GMAIL_SIFRESI = "jsyyoryytwdpupgf" # Uygulama şifresi kullanmanız önerilir
ALICI_EMAIL_ADRESLERI = ["read.alshawe537@gmail.com"] # Alıcı listesi

# === THREAD KONTROL DEĞİŞKENLERİ (Saatlik Raporlama için) ===
_hourly_reporter_thread = None
_stop_hourly_reporter_event = threading.Event()
_initial_hourly_reporter_setup_ok = False


# === MERKEZİ E-POSTA GÖNDERME FONKSİYONU (Güncellenmiş) ===
def _send_combined_email(html_body_parts, recipients, image_cid_map=None):
    """
    Tüm raporları içeren ve resimleri gömülü bir HTML e-postası gönderir.
    image_cid_map: {'cid_etiketi': 'dosya/yolu/resim.jpg'} formatında bir sözlük olmalı.
                   HTML içindeki <img> etiketleri src="cid:cid_etiketi" şeklinde olmalı.
    """
    if not GMAIL_ADRESI or not GMAIL_SIFRESI:
        print("HATA (E-POSTA): Gönderici e-posta bilgileri (GMAIL_ADRESI, GMAIL_SIFRESI) ayarlanmalıdır.")
        return False, "E-posta gönderici bilgileri eksik."
    if not recipients:
        print("UYARI (E-POSTA): Alıcı e-posta adresi tanımlanmamış.")
        return False, "Alıcı e-posta adresi eksik."

    now = datetime.datetime.now()
    email_subject = f"Akıllı Bahçem - Saatlik Toplu Rapor ({now.strftime('%Y-%m-%d %H:%M')})"

    # Ana mesajı 'related' olarak oluştur, bu HTML ve gömülü resimleri destekler
    msg = MIMEMultipart('related')
    msg["From"] = GMAIL_ADRESI
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = email_subject

    # HTML İçeriğini Oluştur (CSS Stilleri dahil)
    # Bu kısım sizin sağladığınızla aynı, sadece resimlerin CID ile referanslandığından emin olunmalı
    full_html_body = f"""
    <html><head><style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f9f9f9; }}
        .email-container {{ max-width: 800px; margin: 20px auto; padding: 25px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #ffffff; box-shadow: 0 2px 15px rgba(0,0,0,0.08); }}
        .section {{ margin-bottom: 25px; padding-bottom: 25px; border-bottom: 1px dashed #e0e0e0; }}
        .section:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        h2 {{ text-align: center; color: #2c3e50; margin-top:0; padding-bottom:10px; border-bottom: 2px solid #3498db; }}
        h4 {{ color: #3498db; margin-top: 0; margin-bottom: 10px; font-size: 1.1em; }}
        pre {{ background-color: #ecf0f1; padding: 12px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', Courier, monospace; font-size: 0.95em; border: 1px solid #bdc3c7; }}
        p {{ margin: 8px 0; font-size: 1em; }}
        ul {{ padding-left: 20px; }}
        img {{ max-width: 100%; height: auto; border-radius: 4px; margin-top: 10px; }} /* Resimler için genel stil */
        .footer {{ font-size: 0.85em; color: #7f8c8d; text-align:center; margin-top: 20px; padding-top:20px; border-top: 1px solid #e0e0e0; }}
    </style></head>
    <body><div class="email-container">
        <h2>Akıllı Bahçem - Saatlik Toplu Rapor</h2>
        <p style="text-align:center; font-size:0.95em; color:#555;">Rapor Tarihi: {now.strftime('%d %B %Y, Saat %H:%M:%S')}</p>
        
        <div class="section">
            <h4><span style="font-size:1.2em; margin-right: 8px;">📷</span>Kamera Görüntüsü ve Raporu</h4>
            {html_body_parts.get('kamera_raporu', '<p><i>Kamera raporu bu saat için oluşturulamadı veya mevcut değil.</i></p>')}
        </div>
        <div class="section">
            <h4><span style="font-size:1.2em; margin-right: 8px;">🌿</span>Hastalık Tespit Raporu</h4>
            {html_body_parts.get('hastalik_raporu', '<p><i>Hastalık tespit raporu bu saat için oluşturulamadı veya mevcut değil.</i></p>')}
        </div>
        <div class="section">
            <h4><span style="font-size:1.2em; margin-right: 8px;">📈</span>Büyüme Analizi Raporu</h4>
            {html_body_parts.get('buyume_raporu', '<p><i>Büyüme analizi raporu bu saat için oluşturulamadı veya mevcut değil.</i></p>')}
        </div>
        
        <div class="footer">
            Bu e-posta Akıllı Bahçem sistemi tarafından otomatik olarak oluşturulmuştur.
        </div>
    </div></body></html>
    """
    html_part = MIMEText(full_html_body, "html", "utf-8")
    msg.attach(html_part)

    # Resimleri E-postaya Gömme
    if image_cid_map: # {'cid_etiketi1': 'dosya/yolu1.jpg', 'cid_etiketi2': 'dosya/yolu2.png'}
        for cid, image_path in image_cid_map.items():
            try:
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as fp:
                        mime_image = MIMEImage(fp.read())
                    # Content-ID başlığını ayarla (HTML'deki cid ile eşleşmeli)
                    # CID'ler genellikle '<' ve '>' arasına alınır.
                    mime_image.add_header('Content-ID', f'<{cid}>')
                    # Resmin e-posta içinde nasıl gösterileceği (isteğe bağlı ama önerilir)
                    mime_image.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                    msg.attach(mime_image)
                    print(f"E-POSTA: Resim eklendi: '{image_path}' (CID: {cid})")
                else:
                    print(f"HATA (E-POSTA RESİM): Resim dosyası bulunamadı: {image_path}")
            except Exception as e_img:
                print(f"HATA (E-POSTA RESİM): '{image_path}' eklenirken sorun: {e_img}")
    
    # E-postayı Gönderme
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo() # SMTP sunucusuna merhaba deyin (isteğe bağlı ama iyi pratik)
        server.starttls() # TLS şifrelemesini başlat
        server.ehlo() # TLS sonrası tekrar merhaba
        server.login(GMAIL_ADRESI, GMAIL_SIFRESI)
        server.sendmail(GMAIL_ADRESI, recipients, msg.as_string())
        server.quit()
        return True, "Birleştirilmiş e-posta (gömülü resimlerle) başarıyla gönderildi."
    except smtplib.SMTPAuthenticationError as e_auth:
        error_detail = f"SMTP Kimlik Doğrulama Hatası (E-posta): {e_auth}."
        print(f"HATA: {error_detail}")
        return False, error_detail
    except Exception as e_general:
        error_detail = f"E-posta gönderilirken genel bir hata oluştu: {e_general}"
        print(f"HATA: {error_detail}")
        return False, error_detail

# === SAATLİK RAPORLAMA GÖREV ÇALIŞTIRICI (Güncellenmiş) ===
def _hourly_report_runner_thread_target():
    global _initial_hourly_reporter_setup_ok

    if not CORE_REPORT_MODULES_LOADED:
        print("SAATLİK RAPORLAMA (Thread): Çekirdek raporlama modülleri yüklenemediği için çalıştırılamıyor.")
        return
    if not _initial_hourly_reporter_setup_ok:
        print("SAATLİK RAPORLAMA (Thread): Raporlama için ilk kurulum kontrolleri başarısız.")
        return

    print("SAATLİK RAPORLAMA (Thread): Raporlama sistemi başlatıldı.")
    while not _stop_hourly_reporter_event.is_set():
        current_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{current_time_str}] SAATLİK RAPORLAMA: Görevler başlıyor...")
        
        html_report_parts = {}  # HTML parçalarını saklamak için
        image_cid_to_path_map = {} # Tüm resimlerin CID ve yollarını toplamak için

        # 1. Fotoğraf Çekme (kamera_modulu)
        if kamera_modulu and hasattr(kamera_modulu, 'capture_photo_for_report'):
            print("SAATLİK RAPORLAMA: Kamera görevi çalıştırılıyor...")
            try:
                # kamera_modulu.capture_photo_for_report() fonksiyonunun
                # (html_str, {'cid1':'path1', 'cid2':'path2'}) formatında dönmesi beklenir.
                kamera_html, kamera_images_map = kamera_modulu.capture_photo_for_report()
                html_report_parts['kamera_raporu'] = kamera_html
                if kamera_images_map: # Eğer resim bilgisi döndüyse
                    image_cid_to_path_map.update(kamera_images_map)
            except Exception as e_cam:
                error_msg = f"<p style='color:red;'>Kamera raporu oluşturulurken hata: {e_cam}</p>"
                html_report_parts['kamera_raporu'] = error_msg
                print(f"HATA (SAATLİK RAPORLAMA - Kamera): {e_cam}")
        else:
            html_report_parts['kamera_raporu'] = "<p style='color:orange;'>Kamera modülü veya 'capture_photo_for_report' fonksiyonu bulunamadı.</p>"

        # 2. Hastalık Tespiti (hastalik_tespiti_modulu)
        # Eğer bu modül de resim içeriyorsa, kamera_modulu gibi CID map döndürmeli
        if hastalik_tespiti_modulu and hasattr(hastalik_tespiti_modulu, 'get_disease_detection_report'):
            print("SAATLİK RAPORLAMA: Hastalık tespit görevi çalıştırılıyor...")
            try:
                # Varsayım: Bu fonksiyon da (html_str, {'cid':'path'}) veya sadece html_str dönebilir.
                # Eğer resim varsa, yukarıdaki gibi map'i de alıp image_cid_to_path_map'e ekleyin.
                # Şimdilik sadece HTML döndürdüğünü varsayıyorum:
                hastalik_html = hastalik_tespiti_modulu.get_disease_detection_report() 
                html_report_parts['hastalik_raporu'] = hastalik_html
                # Eğer hastalık_tespiti_modulu da resim döndürüyorsa:
                # hastalik_html, hastalik_images_map = hastalik_tespiti_modulu.get_disease_detection_report()
                # html_report_parts['hastalik_raporu'] = hastalik_html
                # if hastalik_images_map: image_cid_to_path_map.update(hastalik_images_map)
            except Exception as e_disease:
                error_msg = f"<p style='color:red;'>Hastalık tespit raporu oluşturulurken hata: {e_disease}</p>"
                html_report_parts['hastalik_raporu'] = error_msg
                print(f"HATA (SAATLİK RAPORLAMA - Hastalık Tespiti): {e_disease}")
        else:
            html_report_parts['hastalik_raporu'] = "<p style='color:orange;'>Hastalık tespit modülü veya 'get_disease_detection_report' fonksiyonu bulunamadı.</p>"
        
        # 3. Büyüme Analizi (buyume_analizi_modulu)
        # Eğer bu modül de resim içeriyorsa, kamera_modulu gibi CID map döndürmeli
        if buyume_analizi_modulu and hasattr(buyume_analizi_modulu, 'get_growth_analysis_report'):
            print("SAATLİK RAPORLAMA: Büyüme analizi görevi çalıştırılıyor...")
            try:
                # Varsayım: Sadece HTML döndürüyor. Resim varsa yukarıdaki gibi yapın.
                buyume_html = buyume_analizi_modulu.get_growth_analysis_report()
                html_report_parts['buyume_raporu'] = buyume_html
            except Exception as e_growth:
                error_msg = f"<p style='color:red;'>Büyüme analizi raporu oluşturulurken hata: {e_growth}</p>"
                html_report_parts['buyume_raporu'] = error_msg
                print(f"HATA (SAATLİK RAPORLAMA - Büyüme Analizi): {e_growth}")
        else:
            html_report_parts['buyume_raporu'] = "<p style='color:orange;'>Büyüme analizi modülü veya 'get_growth_analysis_report' fonksiyonu bulunamadı.</p>"

        # 4. Birleştirilmiş E-posta Gönder (Resimlerle birlikte)
        print("SAATLİK RAPORLAMA: Birleştirilmiş e-posta (resimlerle) gönderiliyor...")
        email_sent, email_status_message = _send_combined_email(html_report_parts, ALICI_EMAIL_ADRESLERI, image_cid_to_path_map)
        if email_sent:
            print(f"SAATLİK RAPORLAMA (E-posta): {email_status_message}")
        else:
            print(f"HATA (SAATLİK RAPORLAMA E-POSTA): {email_status_message}")
        
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SAATLİK RAPORLAMA: Görevler tamamlandı. Bir sonraki çalıştırma bekleniyor...")
        
        if _stop_hourly_reporter_event.wait(3600): # 1 saat bekle
            break 
            
    print("SAATLİK RAPORLAMA (Thread): Raporlama sistemi durduruldu.")


# === DIŞARIDAN ÇAĞRILACAK ANA KONTROL FONKSİYONLARI (Güncellenmiş) ===
def start_combined_hourly_tasks(parent_window_for_initial_error=None):
    """Tüm arka plan servislerini (sensör, sulama, saatlik raporlama) başlatır."""
    global _hourly_reporter_thread, _stop_hourly_reporter_event, _initial_hourly_reporter_setup_ok
    
    tk_messagebox = None
    if parent_window_for_initial_error: # Sadece GUI'den çağrıldığında messagebox kullan
        try:
            from tkinter import messagebox as tk_mb
            tk_messagebox = tk_mb
        except ImportError:
            print("UYARI (SAATLİK GÖREV YÖN.): tkinter.messagebox yüklenemedi.")

    print("SAATLİK GÖREV YÖNETİCİSİ: Tüm sistemleri başlatma komutu alındı.")
    any_critical_service_started_successfully = False

    # 1. Merkezi Sensör Servisini Başlat (Eğer varsa)
    if merkezi_sensor_servisi:
        print("SAATLİK GÖREV YÖNETİCİSİ: Merkezi sensör servisi başlatılıyor...")
        if merkezi_sensor_servisi.start_sensor_servisi():
            print("SAATLİK GÖREV YÖNETİCİSİ: Merkezi sensör servisi başarıyla başlatıldı.")
            any_critical_service_started_successfully = True
        else:
            msg_sens_fail = "Merkezi sensör servisi başlatılamadı."
            print(f"HATA (SAATLİK GÖREV YÖN.): {msg_sens_fail}")
            if tk_messagebox: tk_messagebox.showerror("Servis Hatası", msg_sens_fail, parent=parent_window_for_initial_error)
    else:
        print("UYARI (SAATLİK GÖREV YÖN.): Merkezi sensör servisi modülü yüklenemedi.")

    # 2. Otomatik Sulama Kontrol Sistemini Başlat (Eğer varsa ve sensör servisi başladıysa)
    if otomatik_sulama_modulu:
        print("SAATLİK GÖREV YÖNETİCİSİ: Otomatik sulama sistemi başlatılıyor...")
        # Sulama, sensör servisine bağımlı olabilir veya kendi sensörünü okuyabilir.
        # Eğer merkezi servise bağımlıysa 'any_critical_service_started_successfully' kontrolü önemli.
        # Eğer kendi sensörünü okuyorsa bu kontrol gereksiz.
        # Şimdilik bağımsız olduğunu varsayarak veya sensör servisi olmasa da denemesine izin vererek:
        if otomatik_sulama_modulu.start_otomatik_sulama_sistemi():
            print("SAATLİK GÖREV YÖNETİCİSİ: Otomatik sulama sistemi başarıyla başlatıldı.")
            any_critical_service_started_successfully = True # Sulama da kritikse
        else:
            msg_sulama_fail = "Otomatik sulama sistemi başlatılamadı."
            print(f"HATA (SAATLİK GÖREV YÖN.): {msg_sulama_fail}")
            if tk_messagebox: tk_messagebox.showerror("Sulama Hatası", msg_sulama_fail, parent=parent_window_for_initial_error)
    else:
        print("UYARI (SAATLİK GÖREV YÖN.): Otomatik sulama kontrol modülü yüklenemedi.")

    # 3. Mevcut Saatlik Raporlama Görevleri
    print("SAATLİK GÖREV YÖNETİCİSİ: Saatlik raporlama sistemi (kamera, hastalık, büyüme) kontrol ediliyor...")
    if not CORE_REPORT_MODULES_LOADED: # Sadece hastalık, kamera, büyüme için
        msg_report_deps = "Çekirdek raporlama modülleri yüklenemediği için saatlik raporlama sistemi başlatılamıyor."
        print(f"UYARI (SAATLİK GÖREV YÖN.): {msg_report_deps}")
        if tk_messagebox: tk_messagebox.showwarning("Modül Eksikliği (Raporlama)", msg_report_deps, parent=parent_window_for_initial_error)
    else:
        if _hourly_reporter_thread and _hourly_reporter_thread.is_alive():
            print("SAATLİK GÖREV YÖNETİCİSİ: Saatlik raporlama sistemi zaten çalışıyor.")
        else:
            _initial_hourly_reporter_setup_ok = True
            if hastalik_tespiti_modulu and hasattr(hastalik_tespiti_modulu, 'IS_MODEL_LOADED') and not hastalik_tespiti_modulu.IS_MODEL_LOADED:
                # ... (hastalık modeli yüklenemedi hata yönetimi - önceki gibi) ...
                _initial_hourly_reporter_setup_ok = False
            
            if _initial_hourly_reporter_setup_ok:
                _stop_hourly_reporter_event.clear()
                _hourly_reporter_thread = threading.Thread(target=_hourly_report_runner_thread_target, daemon=True)
                _hourly_reporter_thread.start()
                print("SAATLİK GÖREV YÖNETİCİSİ: Saatlik raporlama sistemi başarıyla başlatıldı.")
            else:
                print("UYARI (SAATLİK GÖREV YÖN.): Raporlama sistemi ön kontrolleri başarısız, başlatılmadı.")
    
    return any_critical_service_started_successfully # Ana GUI buton durumu için


def stop_combined_hourly_tasks():
    """Tüm arka plan servislerini durdurur."""
    global _hourly_reporter_thread, _stop_hourly_reporter_event
    print("SAATLİK GÖREV YÖNETİCİSİ: Tüm sistemleri durdurma komutu alındı.")

    # 1. Otomatik Sulama Kontrol Sistemini Durdur
    if otomatik_sulama_modulu:
        print("SAATLİK GÖREV YÖNETİCİSİ: Otomatik sulama sistemi durduruluyor...")
        otomatik_sulama_modulu.stop_otomatik_sulama_sistemi()
    
    # 2. Merkezi Sensör Servisini Durdur
    if merkezi_sensor_servisi:
        print("SAATLİK GÖREV YÖNETİCİSİ: Merkezi sensör servisi durduruluyor...")
        merkezi_sensor_servisi.stop_sensor_servisi()

    # 3. Saatlik Raporlama Görevleri
    if _hourly_reporter_thread and _hourly_reporter_thread.is_alive():
        print("SAATLİK GÖREV YÖNETİCİSİ: Saatlik raporlama sistemi durduruluyor...")
        _stop_hourly_reporter_event.set()
        _hourly_reporter_thread.join(timeout=10)
        if _hourly_reporter_thread.is_alive(): print("UYARI (SAATLİK GÖREV YÖN.): Raporlama thread'i zamanında durmadı.")
        _hourly_reporter_thread = None
    print("SAATLİK GÖREV YÖNETİCİSİ: Saatlik raporlama sistemi durduruldu (veya zaten çalışmıyordu).")
    
    print("SAATLİK GÖREV YÖNETİCİSİ: Tüm sistemlerin durdurulma işlemleri tamamlandı.")
    return True

# Bu dosya doğrudan çalıştırılırsa (test amaçlı)
if __name__ == '__main__':
    # ... (Bir önceki cevaptaki test kodu buraya eklenebilir,
    #      ancak diğer modüllerin varlığına ve çalışmasına bağlı olacaktır.) ...
    print("SAATLİK GÖREV YÖNETİCİSİ (Test Modu): Bu modül doğrudan çalıştırıldı.")
    print("   Modül yüklenme durumları:")
    print(f"   - Merkezi Sensör Servisi: {'Yüklendi' if merkezi_sensor_servisi else 'Yüklenemedi'}")
    print(f"   - Otomatik Sulama Kontrolü: {'Yüklendi' if otomatik_sulama_modulu else 'Yüklenemedi'}")
    print(f"   - Çekirdek Raporlama Modülleri (H,K,B): {'Tamam' if CORE_REPORT_MODULES_LOADED else 'Eksik'}")
    print("\n   Not: Tam işlevsellik için Ana_kodlar.py üzerinden çalıştırılmalıdır.")
