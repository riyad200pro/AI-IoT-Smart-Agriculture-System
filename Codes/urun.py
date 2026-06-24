import tkinter as tk
from tkinter import ttk, messagebox, Label, Button, Toplevel, Text, Scrollbar, VERTICAL, RIGHT, Y, END, StringVar
from PIL import Image, ImageTk
import pandas as pd
import joblib
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import time
import serial
import threading

# === ÜRÜN İSİMLERİ İÇİN ÇEVİRİ SÖZLÜĞÜ ===
CROP_TRANSLATIONS_TR = {
    'rice': 'Pirinç', 'maize': 'Mısır', 'chickpea': 'Nohut', 'kidneybeans': 'Barbunya',
    'pigeonpeas': 'Bezelye', 'mothbeans': 'Mat Fasulyesi', 'mungbean': 'Maş',
    'blackgram': 'Siyah Mercimek', 'lentil': 'Mercimek', 'pomegranate': 'Nar',
    'banana': 'Muz', 'mango': 'Mango', 'grapes': 'Üzüm', 'watermelon': 'Karpuz',
    'muskmelon': 'Kavun', 'apple': 'Elma', 'orange': 'Portakal', 'papaya': 'Papaya',
    'coconut': 'Hindistan Cevizi', 'cotton': 'Pamuk', 'jute': 'Jüt', 'coffee': 'Kahve',
}

# === SENSÖR VERİ İNDEKS TANIMLARI ===
# Sensörden gelen 8 değerin varsayılan sıralaması:
# 0: N, 1: P, 2: K, 3: Kart Üzeri Sıcaklık, 4: Toprak Nemi, 5: Asıl pH, 6: Kullanılmayan, 7: Hava Sıcaklığı
SENSOR_VALUE_INDICES = {
    'N': 0,
    'P': 1,
    'K': 2,
    'TEMP_ON_SENSOR': 3, # Sensör kartı üzerindeki sıcaklık
    'SOIL_MOISTURE': 4,  # Toprak Nemi
    'ACTUAL_PH': 7,      # Asıl pH değeri (model için kullanılacak)
    'UNUSED_6': 6,       # Kullanılmayan 6. değer (varsa)
    'AIR_TEMP': 5        # Hava Sıcaklığı (sensörden gelen son değer)
}
# Modelin doğru çalışması için geçerli sayısal değere sahip olması gereken sensör anahtarları
CRITICAL_SENSOR_KEYS_FOR_MODEL = ['N', 'P', 'K', 'ACTUAL_PH']


# === MODEL YÜKLEME ===
MODEL_URUN_ONERI_PATH = 'crop_recommendation_model.pkl'
model_urun_onerisi = None
try:
    model_urun_onerisi = joblib.load(MODEL_URUN_ONERI_PATH)
    print(f"'{MODEL_URUN_ONERI_PATH}' modeli (ürün öneri) başarıyla yüklendi.")
    if model_urun_onerisi and hasattr(model_urun_onerisi, 'classes_'):
        print("Modelin bildiği ürün sınıfları (İngilizce):")
        for crop_name_en in model_urun_onerisi.classes_:
            turkish_name = CROP_TRANSLATIONS_TR.get(crop_name_en.lower(), f"ÇEVİRİ YOK ({crop_name_en})")
            print(f" - {crop_name_en} -> {turkish_name}")
except FileNotFoundError:
    print(f"HATA: Ürün öneri modeli ('{MODEL_URUN_ONERI_PATH}') bulunamadı.")
    model_urun_onerisi = None
except Exception as e:
    print(f"Ürün öneri modeli yüklenirken bir hata oluştu: {e}")
    model_urun_onerisi = None

# === DIŞ VERİ DOSYALARI VE AYARLAR ===
NEM_DOSYA = "Nem.xlsx"
SICAKLIK_DOSYA = "Sicaklik.xlsx"
YAGIS_DOSYA = "Yagis.xlsx"

GMAIL_ADRESI_URUN = "mesutbulut305@gmail.com"
GMAIL_SIFRESI_URUN = "jsyyoryytwdpupgf"
ALICILAR_URUN = ["read.alshawe537@gmail.com"]

BG_IMAGE_PATH_SOIL = "arka_plan.jpg"

# === SENSÖR AYARLARI VE GLOBAL DEĞİŞKENLER ===
SENSOR_SERIAL_PORT = '/dev/ttyUSB0'
SENSOR_BAUDRATE = 115200
SENSOR_READ_INTERVAL = 3
EXPECTED_SENSOR_VALUE_COUNT = 8 # N,P,K,KartSic,Nem,AsilPH,Kullanilmayan,HavaSic (Toplam 8 değer)

sensor_thread = None
stop_sensor_event = threading.Event()
nan_value_detected_from_sensor = True # Kritik bir sensör verisi (N,P,K,ACTUAL_PH) NaN veya geçersizse True olur
ser_port_sensor = None
son_okuma_detay_mesaji = "Sensör verisi bekleniyor..."

# Bu global değişkenler arayüzde gösterilen ve modelde kullanılan ana değerlerdir.
guncel_n_okunan, guncel_p_okunan, guncel_k_okunan, guncel_ph_okunan, guncel_nem_okunan, guncel_hava_sicakligi_okunan = None, None, None, None, None, None
# Diğer sensör değerleri (TEMP_ON_SENSOR) `sensor_values_this_cycle` içinde tutulur.
n_display_var, p_display_var, k_display_var, ph_display_var, nem_display_var, hava_sicakligi_display_var = None, None, None, None, None, None


# === YARDIMCI FONKSİYONLAR ===
def veri_al_urun_oneri(dosya_yolu, sheet, sehir, ay):
    try:
        df = pd.read_excel(dosya_yolu, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        df['Şehir'] = df['Şehir'].str.strip().str.upper()
        satir = df[df['Şehir'] == sehir.strip().upper()]
        if satir.empty:
            raise ValueError(f"'{sehir}' şehri '{os.path.basename(dosya_yolu)}' dosyasında bulunamadı.")
        ay_sutun_adi = str(ay)
        if ay_sutun_adi not in df.columns:
            raise ValueError(f"Geçersiz ay ({ay}). '{os.path.basename(dosya_yolu)}' dosyasında '{ay_sutun_adi}' adlı sütun bulunamadı.")
        return float(satir.iloc[0][ay_sutun_adi])
    except FileNotFoundError:
        raise FileNotFoundError(f"HATA: '{dosya_yolu}' dosyası bulunamadı.")
    except ValueError as ve:
        raise ve
    except KeyError as ke:
        raise ValueError(f"Geçersiz ay ({ay}). '{os.path.basename(dosya_yolu)}' dosyasında '{str(ke)}' adlı sütun bulunamadı.")
    except Exception as e:
        raise Exception(f"'{os.path.basename(dosya_yolu)}' dosyasından veri çekilirken beklenmeyen bir hata oluştu: {e}")

def send_email_urun_oneri(subject_prefix, body_content, to_emails=None):
    if to_emails is None:
        to_emails = ALICILAR_URUN
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_ADRESI_URUN, GMAIL_SIFRESI_URUN)
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADRESI_URUN
        msg["To"] = ", ".join(to_emails)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg["Subject"] = f"{subject_prefix} - {now}"
        msg.attach(MIMEText(body_content, "plain", "utf-8"))
        server.sendmail(GMAIL_ADRESI_URUN, to_emails, msg.as_string())
        server.quit()
        print(f"DEBUG: E-posta başarıyla gönderildi: {subject_prefix}")
        return True, "E-posta başarıyla gönderildi!"
    except smtplib.SMTPAuthenticationError:
        error_msg = "E-posta gönderilemedi: Kimlik doğrulama hatası."
        print(f"HATA: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"E-posta gönderirken beklenmeyen bir hata oluştu: {e}"
        print(f"HATA: {error_msg}")
        return False, error_msg

# === SENSÖR OKUMA THREAD FONKSİYONU ===
def continuous_sensor_reader(parent_window_ref):
    global nan_value_detected_from_sensor, ser_port_sensor
    global guncel_n_okunan, guncel_p_okunan, guncel_k_okunan, guncel_ph_okunan, guncel_nem_okunan, guncel_hava_sicakligi_okunan
    global n_display_var, p_display_var, k_display_var, ph_display_var, nem_display_var, hava_sicakligi_display_var
    global son_okuma_detay_mesaji

    ser_port_sensor = None
    alert_messagebox_active = False
    last_error_summary_for_email_and_alert = "" 

    def _update_display_var(var, prefix, value, precision=2, suffix=""):
        if var: 
            val_to_set = f"{prefix}N/A" # Varsayılan
            if isinstance(value, (int, float)):
                try:
                    val_to_set = f"{prefix}{value:.{precision}f}{suffix}"
                except TypeError: # Eğer value None ise formatlama hatası almamak için
                    print(f"DEBUG: _update_display_var içinde TypeError - value: {value}, prefix: {prefix}")
                    val_to_set = f"{prefix}N/A"
            elif value is not None: # Sayı değil ama None da değilse (örn: "Hata" gibi bir string olabilir)
                val_to_set = f"{prefix}{str(value)}"
            
            if parent_window_ref.winfo_exists():
                parent_window_ref.after(0, var.set, val_to_set)


    def show_alert_messagebox_once(title, message_body):
        nonlocal alert_messagebox_active, last_error_summary_for_email_and_alert
        current_alert_key = title + message_body 
        if not alert_messagebox_active and last_error_summary_for_email_and_alert != current_alert_key:
            alert_messagebox_active = True
            last_error_summary_for_email_and_alert = current_alert_key 
            if parent_window_ref.winfo_exists():
                messagebox.showwarning(title, message_body, parent=parent_window_ref)
            alert_messagebox_active = False
        elif alert_messagebox_active:
            print("DEBUG: Mevcut bir uyarı penceresi zaten aktif.")

    try:
        ser_port_sensor = serial.Serial(SENSOR_SERIAL_PORT, SENSOR_BAUDRATE, timeout=1)
        print(f"Seri port {SENSOR_SERIAL_PORT} açıldı.")
        nan_value_detected_from_sensor = True 
        son_okuma_detay_mesaji = f"Sensör ({SENSOR_SERIAL_PORT}) bağlandı. Veri bekleniyor..."
        
        if parent_window_ref.winfo_exists():
            _update_display_var(n_display_var, "N: ", None)
            _update_display_var(p_display_var, "P: ", None)
            _update_display_var(k_display_var, "K: ", None)
            _update_display_var(ph_display_var, "pH: ", None, precision=1)
            _update_display_var(nem_display_var, "Nem: ", None, precision=1, suffix="%")
            _update_display_var(hava_sicakligi_display_var, "Hava Sic.: ", None, precision=1, suffix="°C")


        while not stop_sensor_event.is_set():
            current_read_has_critical_error = False
            problematic_sensor_details_for_this_read = []
            sensor_values_this_cycle = {key: None for key in SENSOR_VALUE_INDICES.keys()}
            raw_data_from_sensor = ""
            current_date_for_log = datetime.now()

            try:
                if not (ser_port_sensor and ser_port_sensor.is_open):
                    son_okuma_detay_mesaji = "HATA: Seri port kapalı/erişilemiyor."
                    current_read_has_critical_error = True
                    problematic_sensor_details_for_this_read.append(son_okuma_detay_mesaji)
                    print(son_okuma_detay_mesaji)
                    break 

                if ser_port_sensor.in_waiting > 0:
                    readtxt_bytes = ser_port_sensor.readline()
                    raw_data_from_sensor = readtxt_bytes.decode('utf-8', errors='replace').strip()

                    if not raw_data_from_sensor:
                        time.sleep(0.05)
                        continue

                    print(f"DEBUG: Ham sensör verisi ({current_date_for_log.strftime('%H:%M:%S')}): '{raw_data_from_sensor}'")
                    parts = raw_data_from_sensor.split(' ')
                    print(f"DEBUG: Ayrıştırılan parçalar ({len(parts)} adet): {parts}")
                    
                    if len(parts) == EXPECTED_SENSOR_VALUE_COUNT:
                        for key, index in SENSOR_VALUE_INDICES.items():
                            if index < len(parts): 
                                val_str = parts[index].strip()
                                print(f"DEBUG: İşleniyor: key='{key}', index={index}, val_str='{val_str}'")
                                if val_str.lower() == 'nan':
                                    sensor_values_this_cycle[key] = None
                                    if key in CRITICAL_SENSOR_KEYS_FOR_MODEL:
                                        current_read_has_critical_error = True
                                        problematic_sensor_details_for_this_read.append(f"{key}: NaN")
                                    print(f"DEBUG: '{key}' için 'nan' algılandı.")
                                else:
                                    try:
                                        float_val = float(val_str)
                                        sensor_values_this_cycle[key] = float_val
                                        print(f"DEBUG: '{key}' için float değer: {float_val}")
                                    except ValueError:
                                        sensor_values_this_cycle[key] = None 
                                        if key in CRITICAL_SENSOR_KEYS_FOR_MODEL:
                                            current_read_has_critical_error = True
                                            problematic_sensor_details_for_this_read.append(f"{key}: Geçersiz ({val_str})")
                                        print(f"DEBUG: '{key}' için ValueError: '{val_str}' float'a çevrilemedi")
                            else: 
                                sensor_values_this_cycle[key] = None
                                if key in CRITICAL_SENSOR_KEYS_FOR_MODEL:
                                    current_read_has_critical_error = True
                                    problematic_sensor_details_for_this_read.append(f"{key}: Veri Eksik (Index {index})")
                                print(f"DEBUG: '{key}' için veri eksik (index {index} parts listesinin dışında)")
                        
                        guncel_n_okunan = sensor_values_this_cycle.get('N')
                        guncel_p_okunan = sensor_values_this_cycle.get('P')
                        guncel_k_okunan = sensor_values_this_cycle.get('K')
                        guncel_ph_okunan = sensor_values_this_cycle.get('ACTUAL_PH')
                        guncel_nem_okunan = sensor_values_this_cycle.get('SOIL_MOISTURE')
                        guncel_hava_sicakligi_okunan = sensor_values_this_cycle.get('AIR_TEMP')


                        print(f"DEBUG: Global değerler güncellendi: N={guncel_n_okunan}, P={guncel_p_okunan}, K={guncel_k_okunan}, pH(Asıl)={guncel_ph_okunan}, Nem={guncel_nem_okunan}, HavaSic={guncel_hava_sicakligi_okunan}")
                        print(f"DEBUG: Diğer okunanlar: KartSic={sensor_values_this_cycle.get('TEMP_ON_SENSOR')}")


                        if parent_window_ref.winfo_exists():
                            _update_display_var(n_display_var, "N: ", guncel_n_okunan, 2)
                            _update_display_var(p_display_var, "P: ", guncel_p_okunan, 2)
                            _update_display_var(k_display_var, "K: ", guncel_k_okunan, 2)
                            _update_display_var(ph_display_var, "pH: ", guncel_ph_okunan, 1)
                            _update_display_var(nem_display_var, "Nem: ", guncel_nem_okunan, 1, "%")
                            _update_display_var(hava_sicakligi_display_var, "Hava Sic.: ", guncel_hava_sicakligi_okunan, 1, "°C")
                    else: 
                        son_okuma_detay_mesaji = f"Format Hatası! Beklenen {EXPECTED_SENSOR_VALUE_COUNT}, Gelen {len(parts)} parça."
                        print(f"HATA: {son_okuma_detay_mesaji} Veri: '{raw_data_from_sensor}'")
                        current_read_has_critical_error = True
                        problematic_sensor_details_for_this_read.append("Veri Formatı Hatalı")
                        guncel_n_okunan,guncel_p_okunan,guncel_k_okunan,guncel_ph_okunan,guncel_nem_okunan,guncel_hava_sicakligi_okunan = None,None,None,None,None,None
                        if parent_window_ref.winfo_exists(): 
                            _update_display_var(n_display_var, "N: ", None)
                            _update_display_var(p_display_var, "P: ", None)
                            _update_display_var(k_display_var, "K: ", None)
                            _update_display_var(ph_display_var, "pH: ", None, precision=1)
                            _update_display_var(nem_display_var, "Nem: ", None, precision=1, suffix="%")
                            _update_display_var(hava_sicakligi_display_var, "Hava Sic.: ", None, precision=1, suffix="°C")
                    
                    nan_value_detected_from_sensor = current_read_has_critical_error
                    
                    if nan_value_detected_from_sensor:
                        current_error_summary = f"Sensör Hatası: {', '.join(problematic_sensor_details_for_this_read)}"
                        son_okuma_detay_mesaji = f"{current_error_summary} ({current_date_for_log.strftime('%H:%M:%S')})"
                        print(f"UYARI ALGILANDI: {son_okuma_detay_mesaji}")
                        if last_error_summary_for_email_and_alert != current_error_summary:
                            if parent_window_ref.winfo_exists():
                                alert_body = f"{son_okuma_detay_mesaji}\nBu durumdayken ürün önerisi yapılamayacaktır.\nLütfen sensörleri kontrol edin!"
                                parent_window_ref.after(0, lambda: show_alert_messagebox_once("Sensör Veri Uyarısı", alert_body))
                            
                            email_subject_detail = ', '.join(problematic_sensor_details_for_this_read)
                            email_subject = f"ACİL: Sensör Veri Sorunu ({email_subject_detail})"
                            email_body_text = (
                                f"Merhaba,\n\nSensör sisteminden {current_date_for_log.strftime('%Y-%m-%d %H:%M:%S')} tarihinde sorunlu veri alınmıştır:\n"
                                f"Detaylar: {', '.join(problematic_sensor_details_for_this_read)}\n"
                                f"Lütfen en kısa sürede sensör sistemini kontrol ediniz.\nSaygılarımızla,\nQuantum Farmers Otomatik İzleme Sistemi"
                            )
                            send_email_urun_oneri(email_subject, email_body_text)
                            last_error_summary_for_email_and_alert = current_error_summary
                    else: 
                        son_okuma_detay_mesaji = f"Tüm sensörler normal ({current_date_for_log.strftime('%H:%M:%S')})"
                        if last_error_summary_for_email_and_alert != "": 
                            last_error_summary_for_email_and_alert = "" 
                            print(f"BİLGİ: Sensör durumu normale döndü. {son_okuma_detay_mesaji}")
                else: 
                    time.sleep(0.1) 
                time.sleep(max(0, SENSOR_READ_INTERVAL - 0.1)) 
            except serial.SerialException as e:
                son_okuma_detay_mesaji = f"Seri Port Okuma Hatası: {e}"
                print(f"HATA (iç döngü): {son_okuma_detay_mesaji}")
                nan_value_detected_from_sensor = True
                guncel_n_okunan,guncel_p_okunan,guncel_k_okunan,guncel_ph_okunan,guncel_nem_okunan,guncel_hava_sicakligi_okunan = None,None,None,None,None,None
                stop_sensor_event.set(); break 
            except UnicodeDecodeError as ude:
                son_okuma_detay_mesaji = f"Veri Decode Hatası: {ude}. Okunan: {readtxt_bytes[:50]}..."
                print(f"HATA (iç döngü): {son_okuma_detay_mesaji}")
                nan_value_detected_from_sensor = True 
                guncel_n_okunan,guncel_p_okunan,guncel_k_okunan,guncel_ph_okunan,guncel_nem_okunan,guncel_hava_sicakligi_okunan = None,None,None,None,None,None
            except Exception as e:
                son_okuma_detay_mesaji = f"Genel Sensör Okuma Hatası: {type(e).__name__} - {e}"
                print(f"HATA (iç döngü): {son_okuma_detay_mesaji}")
                nan_value_detected_from_sensor = True
                guncel_n_okunan,guncel_p_okunan,guncel_k_okunan,guncel_ph_okunan,guncel_nem_okunan,guncel_hava_sicakligi_okunan = None,None,None,None,None,None
                time.sleep(SENSOR_READ_INTERVAL) 
    except serial.SerialException as se: 
        son_okuma_detay_mesaji = f"Sensör Bağlantı Hatası: {se}"
        print(f"HATA (dış try): {son_okuma_detay_mesaji}")
        nan_value_detected_from_sensor = True
        if parent_window_ref.winfo_exists(): 
            _update_display_var(n_display_var, "N: ", None)
            _update_display_var(p_display_var, "P: ", None)
            _update_display_var(k_display_var, "K: ", None)
            _update_display_var(ph_display_var, "pH: ", None, precision=1)
            _update_display_var(nem_display_var, "Nem: ", None, precision=1, suffix="%")
            _update_display_var(hava_sicakligi_display_var, "Hava Sic.: ", None, precision=1, suffix="°C")
    finally:
        final_exit_msg = son_okuma_detay_mesaji
        if ser_port_sensor and ser_port_sensor.is_open:
            ser_port_sensor.close()
            print("Seri port kapatıldı.")
        elif ser_port_sensor is None and not stop_sensor_event.is_set(): 
             final_exit_msg = "Sensör: Başlatılamadı (Port Açılamadı)!"
        print(f"Sensör okuma thread'i sonlandırıldı. Son mesaj: {final_exit_msg}")


# === KULLANICI ARAYÜZÜ (GUI) FONKSİYONLARI ===
def open_urun_oneri_ui(parent_window):
    global sensor_thread, stop_sensor_event, nan_value_detected_from_sensor
    global n_display_var, p_display_var, k_display_var, ph_display_var, nem_display_var, hava_sicakligi_display_var
    global guncel_n_okunan, guncel_p_okunan, guncel_k_okunan, guncel_ph_okunan, guncel_nem_okunan, guncel_hava_sicakligi_okunan
    global son_okuma_detay_mesaji

    soil_test_window = tk.Toplevel(parent_window)
    soil_test_window.title("Ürün Öneri Sistemi ve Canlı Sensör Verileri")
    soil_test_window.geometry("700x820") # Yükseklik biraz arttırıldı
    
    n_display_var = StringVar(value="N: Bekleniyor...")
    p_display_var = StringVar(value="P: Bekleniyor...")
    k_display_var = StringVar(value="K: Bekleniyor...")
    ph_display_var = StringVar(value="pH: Bekleniyor...")
    nem_display_var = StringVar(value="Nem: Bekleniyor...")
    hava_sicakligi_display_var = StringVar(value="Hava Sic.: Bekleniyor...")


    try: 
        bg_image_pil_soil = Image.open(BG_IMAGE_PATH_SOIL)
        bg_image_pil_soil = bg_image_pil_soil.resize((700, 820), Image.LANCZOS)
        soil_test_window.bg_image_tk_soil_ref = ImageTk.PhotoImage(bg_image_pil_soil) 
        bg_label_soil = tk.Label(soil_test_window, image=soil_test_window.bg_image_tk_soil_ref)
        bg_label_soil.place(x=0, y=0, relwidth=1, relheight=1)
    except Exception as e_img_soil:
        print(f"Arka plan resmi yüklenemedi ({BG_IMAGE_PATH_SOIL}): {e_img_soil}")
        soil_test_window.configure(bg="#e0f0e0") 

    style = ttk.Style(soil_test_window) 
    style.theme_use('clam')
    style.configure("TLabel", font=("Helvetica", 11), padding=5) 
    style.configure("TButton", font=("Helvetica", 11, "bold"), padding=10, foreground="white", background="#4CAF50")
    style.map("TButton", background=[('active', '#388E3C')])
    style.configure("TEntry", font=("Helvetica", 11), padding=5)
    style.configure("TLabelframe", labelanchor="n", font=("Helvetica", 13, "bold"), padding=10) 
    style.configure("TLabelframe.Label", font=("Helvetica", 13, "bold"), background="#c8e6c9", foreground="#1B5E20", padding=5)
    style.configure("LiveData.TLabel", font=("Consolas", 12, "bold"), foreground="#005000", padding=3)

    main_frame_soil = ttk.Frame(soil_test_window, padding="15 15 15 15", style="TFrame")
    main_frame_soil.pack(expand=True, fill="both", padx=20, pady=20)
    
    title_label_soil = ttk.Label(main_frame_soil, text="Ürün Öneri Sistemi ve Canlı Sensör Verileri",
                                 font=("Helvetica", 16, "bold"),
                                 foreground="#004D40", background="#A5D6A7", anchor="center")
    title_label_soil.pack(pady=(0, 15), fill="x", ipady=5)

    live_sensor_data_frame = ttk.LabelFrame(main_frame_soil, text="Canlı Sensör Verileri")
    live_sensor_data_frame.pack(pady=5, fill="x", padx=5)
    ttk.Label(live_sensor_data_frame, textvariable=n_display_var, style="LiveData.TLabel").grid(row=0, column=0, padx=10, pady=3, sticky="w")
    ttk.Label(live_sensor_data_frame, textvariable=p_display_var, style="LiveData.TLabel").grid(row=0, column=1, padx=10, pady=3, sticky="w")
    ttk.Label(live_sensor_data_frame, textvariable=k_display_var, style="LiveData.TLabel").grid(row=1, column=0, padx=10, pady=3, sticky="w")
    ttk.Label(live_sensor_data_frame, textvariable=ph_display_var, style="LiveData.TLabel").grid(row=1, column=1, padx=10, pady=3, sticky="w") 
    ttk.Label(live_sensor_data_frame, textvariable=nem_display_var, style="LiveData.TLabel").grid(row=2, column=0, padx=10, pady=3, sticky="w") 
    ttk.Label(live_sensor_data_frame, textvariable=hava_sicakligi_display_var, style="LiveData.TLabel").grid(row=2, column=1, padx=10, pady=3, sticky="w")
    live_sensor_data_frame.columnconfigure((0,1), weight=1)

    input_frame_soil = ttk.LabelFrame(main_frame_soil, text="Konum ve Zaman Bilgileri")
    input_frame_soil.pack(pady=(10,5), fill="x", padx=5)
    ttk.Label(input_frame_soil, text="Şehir Adı:").grid(row=0, column=0, padx=5, pady=4, sticky="w")
    entry_sehir_urun = ttk.Entry(input_frame_soil, width=30); entry_sehir_urun.grid(row=0, column=1, padx=5, pady=4, sticky="ew"); entry_sehir_urun.insert(0, "MALATYA")
    ttk.Label(input_frame_soil, text="Ay (1-12):").grid(row=1, column=0, padx=5, pady=4, sticky="w")
    entry_ay_urun = ttk.Entry(input_frame_soil, width=10); entry_ay_urun.grid(row=1, column=1, padx=5, pady=4, sticky="w"); entry_ay_urun.insert(0, str(datetime.now().month))
    input_frame_soil.columnconfigure(1, weight=1)
    
    predict_button_soil = ttk.Button(main_frame_soil, text="ÜRÜN ÖNERİSİ AL",
                                     command=lambda: tahmin_yap_urun_oneri(soil_test_window, entry_sehir_urun, entry_ay_urun, result_text_urun))
    predict_button_soil.pack(pady=10, ipady=3)

    output_frame_soil = ttk.LabelFrame(main_frame_soil, text="Analiz Sonuçları ve Öneriler")
    output_frame_soil.pack(pady=(10,0), fill="both", expand=True)
    scrollbar_soil = ttk.Scrollbar(output_frame_soil, orient=tk.VERTICAL)
    result_text_urun = tk.Text(output_frame_soil, wrap=tk.WORD, state=tk.DISABLED, width=70, height=12, font=("Consolas", 10), bg="#FFFFFF", fg="#333333", relief=tk.SUNKEN, borderwidth=1, yscrollcommand=scrollbar_soil.set)
    scrollbar_soil.config(command=result_text_urun.yview); scrollbar_soil.pack(side=tk.RIGHT, fill=tk.Y); result_text_urun.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    stop_sensor_event.clear()
    nan_value_detected_from_sensor = True 
    guncel_n_okunan,guncel_p_okunan,guncel_k_okunan,guncel_ph_okunan,guncel_nem_okunan,guncel_hava_sicakligi_okunan = None,None,None,None,None,None
    son_okuma_detay_mesaji = "Sensör başlatılıyor..."
    
    sensor_thread = threading.Thread(target=continuous_sensor_reader, args=(soil_test_window,), daemon=True)
    sensor_thread.start()

    soil_test_window.transient(parent_window)
    soil_test_window.grab_set()
    soil_test_window.protocol("WM_DELETE_WINDOW", lambda: on_toplevel_close_urun_oneri(soil_test_window))

def on_toplevel_close_urun_oneri(toplevel_window):
    global sensor_thread, stop_sensor_event
    print(f"'{toplevel_window.title()}' penceresi kapatılıyor.")
    if sensor_thread and sensor_thread.is_alive():
        print("Sensör okuma thread'i durduruluyor...")
        stop_sensor_event.set()
        sensor_thread.join(timeout=max(1, SENSOR_READ_INTERVAL + 1)) 
        if sensor_thread.is_alive(): print("UYARI: Sensör thread'i sonlandırılamadı.")
    else: print("Sensör thread'i zaten çalışmıyor veya None.")
    toplevel_window.destroy()
    print(f"'{toplevel_window.title()}' penceresi kapatıldı.")

# === TAHMİN FONKSİYONU ===
def tahmin_yap_urun_oneri(parent_window, entry_sehir_urun, entry_ay_urun, result_text_urun):
    global nan_value_detected_from_sensor, son_okuma_detay_mesaji
    global guncel_n_okunan, guncel_p_okunan, guncel_k_okunan, guncel_ph_okunan, guncel_nem_okunan, guncel_hava_sicakligi_okunan

    if model_urun_onerisi is None:
        messagebox.showerror("Model Hatası", "Ürün öneri modeli yüklenemedi.", parent=parent_window); return

    kritik_sensorler_ok = (isinstance(guncel_n_okunan, float) and 
                           isinstance(guncel_p_okunan, float) and
                           isinstance(guncel_k_okunan, float) and
                           isinstance(guncel_ph_okunan, float)) 

    if nan_value_detected_from_sensor or not kritik_sensorler_ok: 
        error_msg_to_show = son_okuma_detay_mesaji
        if not kritik_sensorler_ok and not nan_value_detected_from_sensor: 
            error_msg_to_show = "Sensörlerden henüz tüm kritik veriler (N,P,K,pH) alınamadı veya geçersiz."
        
        messagebox.showerror("Sensör Veri Sorunu",
                             f"Gerekli sensör verileri (N, P, K, pH) alınamadı veya hatalı.\nDurum: {error_msg_to_show}\nÜrün önerisi yapılamaz.",
                             parent=parent_window)
        result_text_urun.config(state=tk.NORMAL); result_text_urun.delete(1.0, tk.END)
        result_text_urun.insert(tk.END, f"HATA: Öneri yapılamıyor.\n{error_msg_to_show}"); result_text_urun.config(state=tk.DISABLED)
        return

    n_val_model = int(guncel_n_okunan)
    p_val_model = int(guncel_p_okunan)
    k_val_model = int(guncel_k_okunan)
    ph_val_model = guncel_ph_okunan 

    result_text_urun.config(state=tk.NORMAL); result_text_urun.delete(1.0, tk.END)
    result_text_urun.insert(tk.END, "Analiz başlatılıyor...\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
    email_body_string = "Quantum Farmers - Ürün Öneri Analizi Sonuçları:\n\n"
    try:
        sehir = entry_sehir_urun.get().strip().upper()
        ay_str = entry_ay_urun.get().strip()
        if not sehir or not ay_str:
            messagebox.showwarning("Eksik Girdi", "Şehir ve Ay alanları doldurulmalı.", parent=parent_window); return
        try:
            ay = int(ay_str)
            if not 1 <= ay <= 12:
                messagebox.showwarning("Geçersiz Girdi", "Ay 1-12 arası olmalı.", parent=parent_window); return
        except ValueError:
            messagebox.showwarning("Geçersiz Girdi", "Ay sayısal olmalı.", parent=parent_window); return

        result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, f"\n{sehir.capitalize()}, {ay}. ay için iklim verileri alınıyor...\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
        try:
            nem_excel = veri_al_urun_oneri(NEM_DOSYA, 'Sheet1', sehir, ay) 
            sicaklik = veri_al_urun_oneri(SICAKLIK_DOSYA, 'Sheet1', sehir, ay) 
            yagis = veri_al_urun_oneri(YAGIS_DOSYA, 'Sheet1', sehir, ay)
            result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, "İklim verileri (Excel) alındı.\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
            
            girilen_ve_cekilen_veriler_str = "ANALİZ VERİLERİ:\n-----------------\n"
            girilen_ve_cekilen_veriler_str += f"Sensör N: {guncel_n_okunan:.2f} (Model için: {n_val_model})\n"
            girilen_ve_cekilen_veriler_str += f"Sensör P: {guncel_p_okunan:.2f} (Model için: {p_val_model})\n"
            girilen_ve_cekilen_veriler_str += f"Sensör K: {guncel_k_okunan:.2f} (Model için: {k_val_model})\n"
            girilen_ve_cekilen_veriler_str += f"Sensör pH: {guncel_ph_okunan:.1f} (Model için: {ph_val_model:.1f})\n" 
            if guncel_nem_okunan is not None: girilen_ve_cekilen_veriler_str += f"Sensör Toprak Nemi: {guncel_nem_okunan:.1f}%\n"
            if guncel_hava_sicakligi_okunan is not None: girilen_ve_cekilen_veriler_str += f"Sensör Hava Sıcaklığı: {guncel_hava_sicakligi_okunan:.1f}°C\n"
            
            girilen_ve_cekilen_veriler_str += f"Şehir: {sehir.capitalize()}, Ay: {ay}\n"
            girilen_ve_cekilen_veriler_str += f"Ort. Hava Sıcaklığı (Excel): {sicaklik:.2f}°C\nOrt. Hava Nemi (Excel): {nem_excel:.2f}%\nOrt. Yağış (Excel): {yagis:.2f} mm\n"
            
            email_body_string += girilen_ve_cekilen_veriler_str
            result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, girilen_ve_cekilen_veriler_str + "Model hesaplıyor...\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
        except (FileNotFoundError, ValueError, Exception) as file_error:
            messagebox.showerror("Excel Veri Hatası", str(file_error), parent=parent_window)
            result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, f"\nExcel Hata:\n{str(file_error)}"); result_text_urun.config(state=tk.DISABLED); return

        input_data = pd.DataFrame([[n_val_model, p_val_model, k_val_model, sicaklik, nem_excel, ph_val_model, yagis]],
                                  columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])
        
        probabilities = model_urun_onerisi.predict_proba(input_data)[0]
        class_indices = probabilities.argsort()[::-1] 
        english_classes = model_urun_onerisi.classes_
        recommended_crops_turkish = []
        for index in class_indices:
            prob_val = probabilities[index]
            english_crop_name = english_classes[index]
            turkish_crop_name = CROP_TRANSLATIONS_TR.get(english_crop_name.lower(), english_crop_name) 
            if prob_val > 0.05 or len(recommended_crops_turkish) < 3: recommended_crops_turkish.append((turkish_crop_name, prob_val * 100))
            if len(recommended_crops_turkish) >= 5: break
        
        result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, "\nÖNERİLEN ÜRÜNLER:\n------------------\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
        onerilen_urunler_str = ""
        if recommended_crops_turkish:
            for i, (crop_tr, prob_val) in enumerate(recommended_crops_turkish, 1): onerilen_urunler_str += f"{i}. {crop_tr} (Uygunluk: {prob_val:.2f}%)\n"
        else: onerilen_urunler_str += "Uygun ürün önerisi bulunamadı.\n"
        
        email_body_string += "------------------\nÖNERİLEN ÜRÜNLER:\n------------------\n" + onerilen_urunler_str
        email_body_string += "\nBereketli bir sezon dileriz!\n\nSaygılarımızla,\nQuantum Farmers Ekibi"
        
        result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, onerilen_urunler_str + "\nAnaliz tamamlandı!\n"); result_text_urun.config(state=tk.DISABLED); parent_window.update_idletasks()
        
        email_success, email_message = send_email_urun_oneri("QUANTUM FARMERS - Ürün Öneri Sonuçları", email_body_string)
        if email_success: messagebox.showinfo("E-posta Bilgisi", email_message, parent=parent_window)
        else: messagebox.showwarning("E-posta Hatası", email_message, parent=parent_window)

    except Exception as e:
        error_msg_final = f"Tahmin hatası: {e}"
        print(f"TAHMİN HATASI: {error_msg_final}")
        messagebox.showerror("Genel Hata", error_msg_final, parent=parent_window)
        result_text_urun.config(state=tk.NORMAL); result_text_urun.insert(tk.END, f"\n\nHata: {error_msg_final}"); result_text_urun.config(state=tk.DISABLED)
    finally:
        if result_text_urun.winfo_exists(): result_text_urun.config(state=tk.DISABLED)


# === ANA PROGRAM ===
if __name__ == '__main__':
    test_root = tk.Tk()
    test_root.title("Ürün Öneri Modülü Ana Pencere")
    test_root.geometry("400x200")
    if model_urun_onerisi is None: Label(test_root, text=f"Model YÜKLENEMEDİ!\n'{MODEL_URUN_ONERI_PATH}'", fg="red", font=("Arial", 10, "bold")).pack(pady=20)
    else: Label(test_root, text="Ürün Öneri Modülü Hazır.").pack(pady=10)
    
    Button(test_root, text="Ürün Öneri ve Sensör İzleme Arayüzünü Aç", command=lambda: open_urun_oneri_ui(test_root)).pack(pady=20, padx=20, ipady=10)
    
    def on_main_close():
        global sensor_thread, stop_sensor_event
        print("Ana uygulama kapatılıyor...")
        if sensor_thread and sensor_thread.is_alive():
            print("Sensör thread'i durduruluyor...")
            stop_sensor_event.set()
            sensor_thread.join(timeout=max(1, SENSOR_READ_INTERVAL + 1)) 
        test_root.destroy()

    test_root.protocol("WM_DELETE_WINDOW", on_main_close)
    test_root.mainloop()

