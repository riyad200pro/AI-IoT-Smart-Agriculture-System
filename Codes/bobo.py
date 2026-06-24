import tkinter as tk
from tkinter import ttk, messagebox, Label, Button, Toplevel, Text, Scrollbar, VERTICAL, RIGHT, Y, END, StringVar
from PIL import Image, ImageTk
import pandas as pd
import joblib
import os # Artık sadece path işlemleri için (eğer model yolu vs. için kullanılıyorsa)
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

# === ÜRÜN ÖNERİ SİSTEMİ İÇİN SABİTLER VE MODEL ===
SABIT_N = 90.0
SABIT_P = 42.0
SABIT_K = 43.0
SABIT_PH = 6.5

MODEL_URUN_ONERI_PATH = 'crop_recommendation_model.pkl'
model_urun_onerisi = None
try:
    model_urun_onerisi = joblib.load(MODEL_URUN_ONERI_PATH)
    print(f"'{MODEL_URUN_ONERI_PATH}' modeli (ürün öneri) başarıyla yüklendi.")
    # ... (model sınıf bilgileri yazdırma kısmı aynı kalabilir)
except FileNotFoundError:
    print(f"HATA: Ürün öneri modeli ('{MODEL_URUN_ONERI_PATH}') bulunamadı.")
except Exception as e:
    print(f"Ürün öneri modeli yüklenirken bir hata oluştu: {e}")

NEM_DOSYA = "Nem_sehir_ortalamalari.xlsx"
SICAKLIK_DOSYA = "Sicaklik_sehir_ortalamalari.xlsx"
YAGIS_DOSYA = "Yagis_sehir_ortalamalari.xlsx"

GMAIL_ADRESI_URUN = "mesutbulut305@gmail.com"
GMAIL_SIFRESI_URUN = "jsyyoryytwdpupgf"
ALICILAR_URUN = ["read.alshawe537@gmail.com"]

BG_IMAGE_PATH_SOIL = "arka_plan.jpg"

# === SENSÖR AYARLARI VE GLOBAL DEĞİŞKENLER ===
SENSOR_SERIAL_PORT = '/dev/ttyUSB0'
SENSOR_BAUDRATE = 115200
SENSOR_READ_INTERVAL = 3 # Saniye

sensor_thread = None
stop_sensor_event = threading.Event()
nan_value_detected_from_sensor = False
ser_port_sensor = None
sensor_status_message_var = None

# Sensör verilerini saklamak için global değişkenler
guncel_sensor_degeri = None
son_sensor_okuma_zamani = None


# === YARDIMCI FONKSİYONLAR === (veri_al_urun_oneri, send_email_urun_oneri aynı kalır)
def veri_al_urun_oneri(dosya_yolu, sheet, sehir, ay):
    try:
        df = pd.read_excel(dosya_yolu, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        df['Şehir'] = df['Şehir'].str.strip().str.upper()
        satir = df[df['Şehir'] == sehir.strip().upper()]
        if satir.empty:
            raise ValueError(f"'{sehir}' şehri '{os.path.basename(dosya_yolu)}' dosyasında bulunamadı.")
        sutun_indeksi = ay
        if sutun_indeksi < 1 or sutun_indeksi >= len(df.columns):
            raise ValueError(f"Geçersiz ay ({ay}). '{os.path.basename(dosya_yolu)}' dosyasında {ay}. ay için veri sütunu bulunamadı.")
        return float(satir.iloc[0, sutun_indeksi])
    except FileNotFoundError:
        raise FileNotFoundError(f"HATA: '{dosya_yolu}' dosyası bulunamadı.")
    except ValueError as ve:
        raise ve
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
        print(f"E-posta başarıyla gönderildi: {subject_prefix}")
        return True, "E-posta başarıyla gönderildi!"
    except smtplib.SMTPAuthenticationError:
        error_msg = "E-posta gönderilemedi: Kimlik doğrulama hatası. Gmail adresinizi veya uygulama şifrenizi kontrol edin."
        print(f"HATA: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"E-posta gönderirken beklenmeyen bir hata oluştu: {e}"
        print(f"HATA: {error_msg}")
        return False, error_msg

# === SENSÖR OKUMA THREAD FONKSİYONU ===
# === SENSÖR OKUMA THREAD FONKSİYONU ===
def continuous_sensor_reader(parent_window_ref):
    global nan_value_detected_from_sensor, ser_port_sensor, sensor_status_message_var
    global guncel_sensor_degeri, son_sensor_okuma_zamani

    # Bu dış try...finally bloğu seri portun açılması ve kapanmasını yönetir
    try:
        ser_port_sensor = serial.Serial(SENSOR_SERIAL_PORT, SENSOR_BAUDRATE, timeout=1)
        if parent_window_ref.winfo_exists() and sensor_status_message_var:
            parent_window_ref.after(0, lambda: sensor_status_message_var.set(f"Sensör ({SENSOR_SERIAL_PORT}) bağlandı."))
        print(f"Seri port {SENSOR_SERIAL_PORT} açıldı.")

        print("Sensör okuma thread'i başlatıldı.")
        while not stop_sensor_event.is_set():
            # Bu iç try...except bloğu her bir okuma denemesini yönetir
            try:
                if ser_port_sensor.in_waiting > 0:
                    readtxt_bytes = ser_port_sensor.readline()
                    readtxt = readtxt_bytes.decode('utf-8', errors='ignore').strip()
                    current_date = datetime.now()
                    son_sensor_okuma_zamani = current_date

                    if not readtxt:
                        time.sleep(0.1)
                        continue

                    if readtxt.lower() == "nan":
                        nan_value_detected_from_sensor = True
                        guncel_sensor_degeri = "NaN"
                        if parent_window_ref.winfo_exists() and sensor_status_message_var:
                            parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: NaN Değeri Algılandı!"))
                        
                        if parent_window_ref.winfo_exists():
                            parent_window_ref.after(0, lambda: messagebox.showwarning(
                                "Sensör Uyarısı",
                                f"Sensörden 'NaN' değeri okundu ({current_date.strftime('%Y-%m-%d %H:%M:%S')}).\n"
                                "Bu durumdayken ürün önerisi yapılamayacaktır.\n"
                                "Lütfen sensörü kontrol edin!",
                                parent=parent_window_ref
                            ))
                        
                        email_subject = "ACİL: Sensör Arızası Tespit Edildi"
                        email_body = (
                            f"Merhaba,\n\n"
                            f"Toprak nemi sensöründen {current_date.strftime('%Y-%m-%d %H:%M:%S')} tarihinde 'NaN' değeri alınmıştır.\n"
                            f"Bu, sensörde bir sorun olabileceğini göstermektedir.\n"
                            f"Lütfen en kısa sürede sensör sistemini kontrol ediniz.\n\n"
                            f"Saygılarımızla,\nQuantum Farmers Otomatik İzleme Sistemi"
                        )
                        send_email_urun_oneri(email_subject, email_body)
                        print(f"NaN değeri algılandı: {current_date}, Değer: {guncel_sensor_degeri}")

                    else: 
                        nan_value_detected_from_sensor = False
                        guncel_sensor_degeri = readtxt
                        try:
                            if parent_window_ref.winfo_exists() and sensor_status_message_var:
                                 parent_window_ref.after(0, lambda val=readtxt: sensor_status_message_var.set(f"Sensör: {val}%"))
                            print(f"Sensör Verisi: {guncel_sensor_degeri}%, Zaman: {current_date}")
                        except ValueError: # Bu artık gereksiz olabilir çünkü readtxt'i doğrudan kullanıyoruz
                            guncel_sensor_degeri = f"HATALI_VERI ({readtxt})"
                            if parent_window_ref.winfo_exists() and sensor_status_message_var:
                                parent_window_ref.after(0, lambda val=readtxt: sensor_status_message_var.set(f"Sensör: Hatalı Veri ({val})"))
                            print(f"Hatalı sensör verisi (NaN değil): {readtxt}, Zaman: {current_date}")
                    
                time.sleep(SENSOR_READ_INTERVAL)

            except serial.SerialException as e: # Bu except, içteki try'a ait
                error_msg = f"Seri port hatası (okuma sırasında): {e}"
                print(f"HATA: {error_msg}")
                if parent_window_ref.winfo_exists():
                    parent_window_ref.after(0, lambda: messagebox.showerror("Sensör Okuma Hatası", error_msg, parent=parent_window_ref))
                    if sensor_status_message_var:
                        parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: Okuma Hatası!"))
                nan_value_detected_from_sensor = True
                guncel_sensor_degeri = "Okuma Hatası"
                son_sensor_okuma_zamani = datetime.now()
                stop_sensor_event.set() # Thread'i durdurmak için olayı ayarla
                break # While döngüsünden çık
            except UnicodeDecodeError as ude: # Bu except, içteki try'a ait
                print(f"Unicode decode hatası: {ude}. Veri: {readtxt_bytes}")
                guncel_sensor_degeri = f"DECODE_ERROR ({readtxt_bytes})"
                son_sensor_okuma_zamani = datetime.now()
            except Exception as e: # Bu except, içteki try'a ait
                error_msg = f"Sensör okuma thread'inde genel hata: {e}"
                print(f"HATA: {error_msg}")
                guncel_sensor_degeri = "Genel Hata"
                son_sensor_okuma_zamani = datetime.now()
                if parent_window_ref.winfo_exists() and sensor_status_message_var:
                     parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: Genel Hata!"))
                time.sleep(SENSOR_READ_INTERVAL) # Hata sonrası kısa bekleme, döngü devam eder

    except serial.SerialException as se: # Bu except, dıştaki try'a ait (port açma hatası)
        error_msg = f"Seri port ({SENSOR_SERIAL_PORT}) açılamadı: {se}\nLütfen bağlantıyı ve port adını kontrol edin."
        print(f"HATA: {error_msg}")
        if parent_window_ref.winfo_exists():
            parent_window_ref.after(0, lambda: messagebox.showerror("Sensör Bağlantı Hatası", error_msg, parent=parent_window_ref))
            if sensor_status_message_var:
                 parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: Bağlantı Hatası!"))
        nan_value_detected_from_sensor = True
        guncel_sensor_degeri = "Bağlantı Hatası"
        son_sensor_okuma_zamani = datetime.now()
        # return zaten fonksiyonun sonu olacak, ekstra return'e gerek yok
    finally: # Bu finally, dıştaki try'a ait
        if ser_port_sensor and ser_port_sensor.is_open:
            ser_port_sensor.close()
            print("Seri port kapatıldı.")
        print("Sensör okuma thread'i sonlandırıldı (veya başlatılamadı ve sonlandırılıyor).")
        if parent_window_ref.winfo_exists() and sensor_status_message_var:
            # Thread sonlandığında veya başlatılamadığında durumu güncelle
            if not stop_sensor_event.is_set(): # Eğer stop_sensor_event ayarlanmadıysa, bir hata yüzünden kapanmıştır.
                 parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: Durduruldu (Hata veya Başlatılamadı)"))
            else: # Normal kapatma
                 parent_window_ref.after(0, lambda: sensor_status_message_var.set("Sensör: Durduruldu."))

# === TAHMİN FONKSİYONU === (tahmin_yap_urun_oneri aynı kalır, nan_value_detected_from_sensor kontrolü devam eder)
def tahmin_yap_urun_oneri(parent_window, entry_sehir_urun, entry_ay_urun, result_text_urun):
    global nan_value_detected_from_sensor

    if model_urun_onerisi is None:
        messagebox.showerror("Model Hatası", f"Ürün öneri modeli ('{MODEL_URUN_ONERI_PATH}') yüklenemediği için bu işlem gerçekleştirilemiyor.", parent=parent_window)
        return

    if nan_value_detected_from_sensor:
        messagebox.showerror("Sensör Hatası",
                             "Sensörden 'NaN' veya hatalı bir değer okunuyor.\n"
                             "Bu koşullarda doğru bir ürün önerisi yapılamaz.\n"
                             f"Son okunan sensör değeri: {guncel_sensor_degeri} ({son_sensor_okuma_zamani.strftime('%Y-%m-%d %H:%M:%S') if son_sensor_okuma_zamani else 'N/A'})\n"
                             "Lütfen sensör bağlantılarınızı ve durumunu kontrol edin.",
                             parent=parent_window)
        result_text_urun.config(state=tk.NORMAL)
        result_text_urun.delete(1.0, tk.END)
        result_text_urun.insert(tk.END, "HATA: Sensör 'NaN' veya hatalı veri bildiriyor. Öneri yapılamıyor.\nLütfen sensörü kontrol edin.")
        result_text_urun.config(state=tk.DISABLED)
        return

    # ... (tahmin_yap_urun_oneri fonksiyonunun geri kalanı aynı)
    result_text_urun.config(state=tk.NORMAL)
    result_text_urun.delete(1.0, tk.END)
    result_text_urun.insert(tk.END, "Quantum Farmers ürün öneri sistemine hoş geldiniz!\nSizin için en uygun ürünleri bulmaya başlıyoruz...\nLütfen bekleyiniz.\n")
    result_text_urun.config(state=tk.DISABLED)
    parent_window.update_idletasks()

    email_body_string = "Quantum Farmers - Ürün Öneri Analizi Sonuçları:\n\n"

    try:
        sehir = entry_sehir_urun.get().strip().upper()
        ay_str = entry_ay_urun.get().strip()

        if not sehir or not ay_str:
            messagebox.showwarning("Eksik Girdi", "Lütfen Şehir ve Ay alanlarını doldurun.", parent=parent_window)
            result_text_urun.config(state=tk.NORMAL)
            result_text_urun.delete(1.0, tk.END)
            result_text_urun.insert(tk.END, "Hata: Şehir ve Ay alanları boş bırakılamaz.\nLütfen bilgileri girip tekrar deneyin.")
            result_text_urun.config(state=tk.DISABLED)
            return
        try:
            ay = int(ay_str)
            if not 1 <= ay <= 12:
                messagebox.showwarning("Geçersiz Girdi", "Ay için 1 ile 12 arasında bir tam sayı girin.", parent=parent_window)
                result_text_urun.config(state=tk.NORMAL)
                result_text_urun.delete(1.0, tk.END)
                result_text_urun.insert(tk.END, "Hata: Ay için 1 ile 12 arasında bir tam sayı girilmelidir.\nLütfen düzeltip tekrar deneyin.")
                result_text_urun.config(state=tk.DISABLED)
                return
        except ValueError:
            messagebox.showwarning("Geçersiz Girdi", "Ay için geçerli bir tam sayı girin.", parent=parent_window)
            result_text_urun.config(state=tk.NORMAL)
            result_text_urun.delete(1.0, tk.END)
            result_text_urun.insert(tk.END, "Hata: Ay için sayısal bir değer girilmelidir.\nLütfen düzeltip tekrar deneyin.")
            result_text_urun.config(state=tk.DISABLED)
            return

        result_text_urun.config(state=tk.NORMAL)
        result_text_urun.insert(tk.END, f"\nHarika! {sehir.capitalize()} şehri için {ay}. ayda analiz yapılıyor...\nBölgenizin iklim verilerini kontrol ediyoruz...\n")
        result_text_urun.config(state=tk.DISABLED)
        parent_window.update_idletasks()

        try:
            nem = veri_al_urun_oneri(NEM_DOSYA, 'Sheet1', sehir, ay)
            sicaklik = veri_al_urun_oneri(SICAKLIK_DOSYA, 'Sheet1', sehir, ay)
            yagis = veri_al_urun_oneri(YAGIS_DOSYA, 'Sheet1', sehir, ay)
            
            result_text_urun.config(state=tk.NORMAL)
            result_text_urun.insert(tk.END, "\nİklim verileri başarıyla alındı.\n")
            result_text_urun.config(state=tk.DISABLED)
            parent_window.update_idletasks()

            girilen_ve_cekilen_veriler_str = "---------------------------\n"
            girilen_ve_cekilen_veriler_str += "GİRİLEN VE ÇEKİLEN VERİLER:\n"
            girilen_ve_cekilen_veriler_str += "---------------------------\n"
            girilen_ve_cekilen_veriler_str += f"Azot (N): {SABIT_N}\n"
            girilen_ve_cekilen_veriler_str += f"Fosfor (P): {SABIT_P}\n"
            girilen_ve_cekilen_veriler_str += f"Potasyum (K): {SABIT_K}\n"
            girilen_ve_cekilen_veriler_str += f"pH: {SABIT_PH}\n"
            girilen_ve_cekilen_veriler_str += f"Girilen Şehir: {sehir.capitalize()}\n"
            girilen_ve_cekilen_veriler_str += f"Girilen Ay: {ay}\n"
            girilen_ve_cekilen_veriler_str += f"Ortalama Sıcaklık (°C): {sicaklik:.2f}\n"
            girilen_ve_cekilen_veriler_str += f"Ortalama Nem (%): {nem:.2f}\n"
            girilen_ve_cekilen_veriler_str += f"Ortalama Yağış (mm): {yagis:.2f}\n"
            
            email_body_string += girilen_ve_cekilen_veriler_str

            result_text_urun.config(state=tk.NORMAL)
            result_text_urun.insert(tk.END, girilen_ve_cekilen_veriler_str)
            result_text_urun.insert(tk.END, "İklim verileri tamam! Şimdi akıllı modelimiz sizin için en iyi ürünleri hesaplıyor...\nLütfen bekleyiniz.\n")
            result_text_urun.config(state=tk.DISABLED)
            parent_window.update_idletasks()

        except (FileNotFoundError, ValueError, Exception) as file_error:
            messagebox.showerror("Veri Çekme Hatası", str(file_error), parent=parent_window)
            result_text_urun.config(state=tk.NORMAL)
            result_text_urun.insert(tk.END, f"\n\nHata: Veri çekilirken sorun oluştu.\n{str(file_error)}\nLütfen Excel dosyalarının doğru yerde olduğundan ve şehir/ay bilgisinin doğru olduğundan emin olun.")
            result_text_urun.config(state=tk.DISABLED)
            return

        input_data = pd.DataFrame([[SABIT_N, SABIT_P, SABIT_K, sicaklik, nem, SABIT_PH, yagis]],
                                    columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])

        probabilities = model_urun_onerisi.predict_proba(input_data)[0]
        class_indices = probabilities.argsort()[::-1] 
        english_classes = model_urun_onerisi.classes_

        recommended_crops_turkish = []
        for index in class_indices:
            prob = probabilities[index]
            english_crop_name = english_classes[index]
            turkish_crop_name = CROP_TRANSLATIONS_TR.get(english_crop_name.lower(), english_crop_name) 
            
            if prob > 0.05 or len(recommended_crops_turkish) < 3: 
                recommended_crops_turkish.append((turkish_crop_name, prob * 100))
            if len(recommended_crops_turkish) >= 5: 
                break
        
        result_text_urun.config(state=tk.NORMAL)
        result_text_urun.insert(tk.END, "\nİşte size özel ürün önerilerimiz!\n")
        result_text_urun.config(state=tk.DISABLED)
        parent_window.update_idletasks()

        onerilen_urunler_str = "------------------\n"
        onerilen_urunler_str += "ÖNERİLEN ÜRÜNLER:\n"
        onerilen_urunler_str += "------------------\n"
        if recommended_crops_turkish:
            for i, (crop_tr, prob) in enumerate(recommended_crops_turkish, 1):
                onerilen_urunler_str += f"{i}. {crop_tr} (Uygunluk: {prob:.2f}%)\n"
        else:
            onerilen_urunler_str += "Belirtilen koşullar için uygun bir ürün önerisi bulunamadı.\n"
        
        email_body_string += onerilen_urunler_str
        email_body_string += "\nUmarız bu önerilerle bereketli bir sezon geçirirsiniz!\n\nSaygılarımızla,\nQuantum Farmers Ekibi"

        result_text_urun.config(state=tk.NORMAL)
        result_text_urun.insert(tk.END, f"\n{onerilen_urunler_str}")
        result_text_urun.insert(tk.END, "\nAnaliz başarıyla tamamlandı. Umarız bu önerilerle bereketli bir sezon geçirirsiniz!\nSonuçlar e-posta ile de gönderilecektir.\nİyi günler dileriz.")
        result_text_urun.config(state=tk.DISABLED)
        parent_window.update_idletasks()

        email_success, email_message = send_email_urun_oneri("QUANTUM FARMERS - Ürün Öneri Sonuçları", email_body_string)
        if email_success:
            messagebox.showinfo("E-posta Bilgisi", email_message, parent=parent_window)
        else:
            messagebox.showwarning("E-posta Hatası", email_message, parent=parent_window)

    except Exception as e:
        error_msg_final = f"Tahmin yapılırken beklenmeyen bir genel hata oluştu: {e}"
        messagebox.showerror("Genel Hata", error_msg_final, parent=parent_window)
        result_text_urun.config(state=tk.NORMAL)
        result_text_urun.insert(tk.END, f"\n\nHata: {error_msg_final}\nLütfen girdilerinizi kontrol edin veya daha sonra tekrar deneyin.")
        result_text_urun.config(state=tk.DISABLED)
    finally:
        if result_text_urun.winfo_exists():
            result_text_urun.config(state=tk.DISABLED)

# === GUI FONKSİYONLARI === (on_toplevel_close_urun_oneri, open_urun_oneri_ui aynı kalır)
def on_toplevel_close_urun_oneri(toplevel_window):
    global sensor_thread, stop_sensor_event
    print(f"'{toplevel_window.title()}' penceresi kapatılıyor.")
    
    if sensor_thread and sensor_thread.is_alive():
        print("Sensör okuma thread'i durduruluyor...")
        stop_sensor_event.set()
        sensor_thread.join(timeout=SENSOR_READ_INTERVAL + 2)
        if sensor_thread.is_alive():
            print("UYARI: Sensör thread'i zaman aşımına uğradı ve sonlandırılamadı.")
    
    toplevel_window.destroy()
    print(f"'{toplevel_window.title()}' penceresi kapatıldı.")

def open_urun_oneri_ui(parent_window):
    global sensor_thread, stop_sensor_event, nan_value_detected_from_sensor 
    global sensor_status_message_var, guncel_sensor_degeri, son_sensor_okuma_zamani

    soil_test_window = tk.Toplevel(parent_window)
    soil_test_window.title("Ürün Öneri Sistemi ve Sensör İzleme")
    soil_test_window.geometry("700x800")

    sensor_status_message_var = StringVar()
    sensor_status_message_var.set("Sensör: Başlatılıyor...")
    guncel_sensor_degeri = None # Başlangıç değeri
    son_sensor_okuma_zamani = None # Başlangıç değeri


    try:
        bg_image_pil_soil = Image.open(BG_IMAGE_PATH_SOIL)
        bg_image_pil_soil = bg_image_pil_soil.resize((700, 800), Image.LANCZOS)
        soil_test_window.bg_image_tk_soil_ref = ImageTk.PhotoImage(bg_image_pil_soil) 
        bg_label_soil = tk.Label(soil_test_window, image=soil_test_window.bg_image_tk_soil_ref)
        bg_label_soil.place(x=0, y=0, relwidth=1, relheight=1)
    except Exception as e_img_soil:
        print(f"Ürün öneri arayüzü arka plan resmi yüklenemedi ({BG_IMAGE_PATH_SOIL}): {e_img_soil}")
        soil_test_window.configure(bg="#e0f0e0") 

    style = ttk.Style(soil_test_window) 
    style.theme_use('clam')
    style.configure("TLabel", font=("Helvetica", 11), padding=5) 
    style.configure("TButton", font=("Helvetica", 11, "bold"), padding=10, foreground="white", background="#4CAF50")
    style.map("TButton", background=[('active', '#388E3C')])
    style.configure("TEntry", font=("Helvetica", 11), padding=5)
    style.configure("TLabelframe", labelanchor="n", font=("Helvetica", 13, "bold"), padding=10) 
    style.configure("TLabelframe.Label", font=("Helvetica", 13, "bold"), background="#c8e6c9", foreground="#1B5E20", padding=5)
    style.configure("SensorStatus.TLabel", font=("Consolas", 10), foreground="blue", padding=5, background="#e0f0e0")


    main_frame_soil = ttk.Frame(soil_test_window, padding="15 15 15 15", style="TFrame") 
    main_frame_soil.pack(expand=True, fill="both", padx=20, pady=20)
    
    title_label_soil = ttk.Label(main_frame_soil, text="Ürün Öneri Sistemi ve Sensör İzleme", 
                                font=("Helvetica", 16, "bold"), 
                                foreground="#004D40", background="#A5D6A7", anchor="center")
    title_label_soil.pack(pady=(0, 10), fill="x", ipady=5)

    sensor_status_label = ttk.Label(main_frame_soil, textvariable=sensor_status_message_var, style="SensorStatus.TLabel")
    sensor_status_label.pack(pady=(0,10), fill="x")

    sabit_degerler_frame_soil = ttk.LabelFrame(main_frame_soil, text="Sabit Toprak Verileri (Model İçin)")
    sabit_degerler_frame_soil.pack(pady=5, fill="x") 
    ttk.Label(sabit_degerler_frame_soil, text=f"Azot (N): {SABIT_N}").grid(row=0, column=0, padx=5, pady=2, sticky="w") 
    ttk.Label(sabit_degerler_frame_soil, text=f"Fosfor (P): {SABIT_P}").grid(row=0, column=1, padx=10, pady=2, sticky="w") 
    ttk.Label(sabit_degerler_frame_soil, text=f"Potasyum (K): {SABIT_K}").grid(row=1, column=0, padx=5, pady=2, sticky="w") 
    ttk.Label(sabit_degerler_frame_soil, text=f"pH Değeri: {SABIT_PH}").grid(row=1, column=1, padx=10, pady=2, sticky="w") 
    sabit_degerler_frame_soil.columnconfigure((0,1), weight=1)

    input_frame_soil = ttk.LabelFrame(main_frame_soil, text="Konum ve Zaman Bilgileri")
    input_frame_soil.pack(pady=5, fill="x") 
    ttk.Label(input_frame_soil, text="Şehir Adı:").grid(row=0, column=0, padx=5, pady=4, sticky="w") 
    entry_sehir_urun = ttk.Entry(input_frame_soil, width=30)
    entry_sehir_urun.grid(row=0, column=1, padx=5, pady=4, sticky="ew") 
    entry_sehir_urun.insert(0, "MALATYA") 
    ttk.Label(input_frame_soil, text="Ay (1-12):").grid(row=1, column=0, padx=5, pady=4, sticky="w") 
    entry_ay_urun = ttk.Entry(input_frame_soil, width=10)
    entry_ay_urun.grid(row=1, column=1, padx=5, pady=4, sticky="w") 
    entry_ay_urun.insert(0, str(datetime.now().month)) 
    input_frame_soil.columnconfigure(1, weight=1)
    
    predict_button_soil = ttk.Button(main_frame_soil, text="ÜRÜN ÖNERİSİ AL", 
                                        command=lambda: tahmin_yap_urun_oneri(soil_test_window, entry_sehir_urun, entry_ay_urun, result_text_urun))
    predict_button_soil.pack(pady=10, ipady=3)

    output_frame_soil = ttk.LabelFrame(main_frame_soil, text="Analiz Sonuçları ve Öneriler")
    output_frame_soil.pack(pady=(10,0), fill="both", expand=True) 
    
    scrollbar_soil = ttk.Scrollbar(output_frame_soil, orient=tk.VERTICAL)
    result_text_urun = tk.Text(output_frame_soil, wrap=tk.WORD, state=tk.DISABLED, 
                                width=70, height=15,
                                font=("Consolas", 10), bg="#FFFFFF", fg="#333333", 
                                relief=tk.SUNKEN, borderwidth=1, yscrollcommand=scrollbar_soil.set)
    scrollbar_soil.config(command=result_text_urun.yview)
    scrollbar_soil.pack(side=tk.RIGHT, fill=tk.Y)
    result_text_urun.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    stop_sensor_event.clear()
    nan_value_detected_from_sensor = False
    sensor_thread = threading.Thread(target=continuous_sensor_reader, args=(soil_test_window,), daemon=True)
    sensor_thread.start()

    soil_test_window.transient(parent_window)
    soil_test_window.grab_set()
    soil_test_window.protocol("WM_DELETE_WINDOW", lambda: on_toplevel_close_urun_oneri(soil_test_window))

# === ANA PROGRAM ===
if __name__ == '__main__':
    test_root = tk.Tk()
    test_root.title("Ürün Öneri Modülü Test Ana Penceresi")
    test_root.geometry("400x250")
    
    if model_urun_onerisi is None:
        Label(test_root, text=f"Model '{MODEL_URUN_ONERI_PATH}' YÜKLENEMEDİ!\nLütfen dosya yolunu ve bağımlılıkları kontrol edin.", 
              fg="red", font=("Arial", 10, "bold")).pack(pady=20)
    else:
        Label(test_root, text="Ürün Öneri Modülü Hazır.").pack(pady=10)

    def open_main_app():
        open_urun_oneri_ui(test_root)

    Button(test_root, text="Ürün Öneri ve Sensör İzleme Arayüzünü Aç", command=open_main_app).pack(pady=20, padx=20, ipady=10)
    
    def on_main_close():
        global sensor_thread, stop_sensor_event
        print("Ana uygulama kapatılıyor...")
        if sensor_thread and sensor_thread.is_alive():
             print("Sensör thread'i ana pencere kapanışından durduruluyor...")
             stop_sensor_event.set()
             sensor_thread.join(timeout=5)
        test_root.destroy()

    test_root.protocol("WM_DELETE_WINDOW", on_main_close)
    test_root.mainloop()