 # otomatik_sulama_kontrolu.py (KENDİ SENSÖR OKUMASINI YAPAN VERSİYON)

import threading
import time
import serial  # Bu modül kendi seri port okumasını yapacağı için GEREKLİ
import gpiod   # GPIO kontrolü için

# === MODÜL AYARLARI ===
# --- Sensör ve Seri Port Ayarları (Bu modül için özel) ---
SENSOR_SERIAL_PORT_SULAMA = '/dev/ttyUSB0'  # Bu modülün kullanacağı seri port
SENSOR_BAUDRATE_SULAMA = 115200
EXPECTED_SENSOR_VALUE_COUNT_SULAMA = 8  # Sensörden beklenen toplam değer sayısı (boşlukla ayrılmış)
# Sensör okuma ve motor kontrol döngüsünün ne sıklıkta çalışacağı (saniye)
SENSOR_OKUMA_VE_KONTROL_ARALIGI_SANIYE = 5 

# --- Sulama Nemi İndeksi ---
# !!! KULLANICI DOĞRULAMALI !!!
# Bu modülün okuyacağı 8 değerden hangisi SULAMA için kullanılacak TOPRAK NEMİ?
SULAMA_NEM_INDEKSI = 6  # Örnek: 8 parçalı veride 7. değer (indeks 6)

# --- Motor ve GPIO Ayarları ---
MOTOR_PIN_SULAMA = 27  # Motorunuzun bağlı olduğu GPIO pini
GPIO_CHIP_NAME_SULAMA = 'gpiochip4'  # Kullandığınız GPIO chip adı

# --- Sulama Eşik Değeri ---
NEM_SULAMA_ESIGI = 300.0  # Nem bu değerin ALTINA düşerse motor ÇALIŞIR, eşit veya üzerindeyse DURUR.

# === GLOBAL DEĞİŞKENLER (MODÜL İÇİ) ===
g_sulama_ve_sensor_thread = None  # Thread nesnesini tutmak için
g_stop_sulama_event = threading.Event()  # Thread'i durdurmak için event

# GPIO nesneleri
g_gpio_chip_sulama_motor = None
g_motor_line_gpio_pin = None
g_gpio_sulama_motor_kurulum_basarili = False

# Seri port nesnesi (bu modüle özel)
g_serial_port_sulama_obj = None
g_serial_port_sulama_acik_basarili = False


def _gpio_kurulumu_sulama_motor():
    """Sulama motoru için GPIO pinlerini ayarlar."""
    global g_gpio_chip_sulama_motor, g_motor_line_gpio_pin, g_gpio_sulama_motor_kurulum_basarili
    if g_gpio_sulama_motor_kurulum_basarili: return True
    try:
        g_gpio_chip_sulama_motor = gpiod.Chip(GPIO_CHIP_NAME_SULAMA)
        g_motor_line_gpio_pin = g_gpio_chip_sulama_motor.get_line(MOTOR_PIN_SULAMA)
        g_motor_line_gpio_pin.request(consumer="otomatik_sulama_motor_gpio_v3", type=gpiod.LINE_REQ_DIR_OUT)
        g_motor_line_gpio_pin.set_value(0)  # Başlangıçta motor kapalı
        g_gpio_sulama_motor_kurulum_basarili = True
        print(f"SULAMA (BağımsızSensör): GPIO Pini {MOTOR_PIN_SULAMA} motor için ayarlandı. Motor KAPALI.")
        return True
    except Exception as e:
        print(f"HATA (Sulama GPIO Kurulumu - BağımsızSensör): {e}")
        g_gpio_sulama_motor_kurulum_basarili = False
        return False

def _gpio_serbest_birak_sulama_motor():
    """Kullanılan GPIO kaynaklarını serbest bırakır."""
    global g_gpio_chip_sulama_motor, g_motor_line_gpio_pin, g_gpio_sulama_motor_kurulum_basarili
    if g_gpio_sulama_motor_kurulum_basarili and g_motor_line_gpio_pin:
        try:
            g_motor_line_gpio_pin.set_value(0)
            g_motor_line_gpio_pin.release()
        except Exception as e: print(f"HATA (Sulama GPIO Serbest Bırakma - BağımsızSensör): {e}")
    if g_gpio_chip_sulama_motor:
        try: g_gpio_chip_sulama_motor.close()
        except Exception as e: print(f"HATA (Sulama GPIO Chip Kapatma - BağımsızSensör): {e}")
    g_gpio_sulama_motor_kurulum_basarili = False
    print("SULAMA (BağımsızSensör): GPIO kaynakları temizlendi.")

def _seri_port_ac_sulama_bu_modulde():
    """Bu modül için özel seri portu açar."""
    global g_serial_port_sulama_obj, g_serial_port_sulama_acik_basarili
    if g_serial_port_sulama_acik_basarili and g_serial_port_sulama_obj and g_serial_port_sulama_obj.is_open:
        return True # Zaten açıksa tekrar açma
    try:
        g_serial_port_sulama_obj = serial.Serial(SENSOR_SERIAL_PORT_SULAMA, SENSOR_BAUDRATE_SULAMA, timeout=1)
        g_serial_port_sulama_acik_basarili = True
        print(f"SULAMA (BağımsızSensör): Seri port {SENSOR_SERIAL_PORT_SULAMA} açıldı.")
        time.sleep(0.5) # Portun oturması için kısa bir bekleme
        if g_serial_port_sulama_obj.in_waiting > 0:
            g_serial_port_sulama_obj.read(g_serial_port_sulama_obj.in_waiting) # Olası başlangıç buffer'ını temizle
        return True
    except serial.SerialException as e:
        print(f"HATA (Sulama Seri Port Açma - BağımsızSensör): {SENSOR_SERIAL_PORT_SULAMA} - {e}")
        g_serial_port_sulama_acik_basarili = False
        return False

def _seri_port_kapat_sulama_bu_modulde():
    """Bu modül için özel seri portu kapatır."""
    global g_serial_port_sulama_obj, g_serial_port_sulama_acik_basarili
    if g_serial_port_sulama_obj and g_serial_port_sulama_obj.is_open:
        try:
            g_serial_port_sulama_obj.close()
        except Exception as e:
            print(f"HATA (Sulama Seri Port Kapatma - BağımsızSensör): {e}")
    g_serial_port_sulama_acik_basarili = False
    print(f"SULAMA (BağımsızSensör): Seri port {SENSOR_SERIAL_PORT_SULAMA} kapatıldı.")


def _sulama_ve_bagimsiz_sensor_dongusu():
    """Sensör verisini okur, nemi ayrıştırır ve motoru kontrol eder."""
    global g_stop_sulama_event, g_gpio_sulama_motor_kurulum_basarili, g_motor_line_gpio_pin
    global g_serial_port_sulama_acik_basarili, g_serial_port_sulama_obj

    if not g_gpio_sulama_motor_kurulum_basarili:
        print("SULAMA (Döngü - BağımsızSensör): GPIO ayarlanmadığı için başlatılamıyor.")
        return
    
    if not _seri_port_ac_sulama_bu_modulde(): # Thread başladığında portu açmayı dene
        print("SULAMA (Döngü - BağımsızSensör): Seri port açılamadığı için başlatılamıyor.")
        return

    print("SULAMA (Döngü - BağımsızSensör): Bağımsız sensör okuma ve sulama mantığı başlatıldı.")
    print(f"SULAMA (Döngü - BağımsızSensör): Nem (indeks {SULAMA_NEM_INDEKSI}) < {NEM_SULAMA_ESIGI}% ise MOTOR AÇIK, değilse MOTOR KAPALI.")

    while not g_stop_sulama_event.is_set():
        sulama_nemi_degeri = None
        raw_data_line = ""

        if not g_serial_port_sulama_acik_basarili: # Port bir şekilde kapanmışsa
            print("SULAMA (Döngü - BağımsızSensör): Seri port kapalı, yeniden açılmaya çalışılıyor...")
            if not _seri_port_ac_sulama_bu_modulde():
                g_stop_sulama_event.wait(5) # Açılamazsa 5 saniye bekle ve döngüye devam et (tekrar deneyecek)
                continue
        
        try:
            if g_serial_port_sulama_obj and g_serial_port_sulama_obj.is_open and g_serial_port_sulama_obj.in_waiting > 0:
                read_bytes = g_serial_port_sulama_obj.readline()
                raw_data_line = read_bytes.decode('utf-8', errors='replace').strip()

                if raw_data_line:
                    # print(f"DEBUG (SulamaBağımsızSensör): Ham Veri: '{raw_data_line}'") # Gerekirse açın
                    parts = raw_data_line.split(' ')
                    if len(parts) == EXPECTED_SENSOR_VALUE_COUNT_SULAMA:
                        if 0 <= SULAMA_NEM_INDEKSI < len(parts):
                            try:
                                nem_str = parts[SULAMA_NEM_INDEKSI]
                                sulama_nemi_degeri = float(nem_str)
                                print(f"DEBUG (SulamaBağımsızSensör): Ayrıştırılan Nem: {sulama_nemi_degeri}%")
                            except ValueError:
                                print(f"HATA (SulamaBağımsızSensör): Nem değeri (indeks {SULAMA_NEM_INDEKSI}, değer: '{nem_str}') float'a çevrilemedi.")
                        else:
                            print(f"HATA (SulamaBağımsızSensör): Tanımlı SULAMA_NEM_INDEKSI ({SULAMA_NEM_INDEKSI}) gelen {len(parts)} parça için geçersiz.")
                    # else: Parça sayısı uyuşmuyorsa bu döngüde nem None kalır
                # else: Boş satır geldi
            # else: Portta okunacak veri yok
            
            # Motor kontrolü
            if sulama_nemi_degeri is not None:
                current_motor_state = g_motor_line_gpio_pin.get_value() # GPIO pin durumunu oku
                if sulama_nemi_degeri < NEM_SULAMA_ESIGI:
                    if current_motor_state == 0: # Motor kapalıysa ve açılması gerekiyorsa
                        print(f"SULAMA (BağımsızSensör): MOTOR AÇILIYOR (Nem: {sulama_nemi_degeri:.2f}%, Eşik: <{NEM_SULAMA_ESIGI}%)")
                        g_motor_line_gpio_pin.set_value(1)
                else: # Nem eşiğe eşit veya üzerindeyse
                    if current_motor_state == 1: # Motor açıksa ve kapatılması gerekiyorsa
                        print(f"SULAMA (BağımsızSensör): MOTOR KAPATILIYOR (Nem: {sulama_nemi_degeri:.2f}%, Eşik: >={NEM_SULAMA_ESIGI}%)")
                        g_motor_line_gpio_pin.set_value(0)
            else: # sulama_nemi_degeri None ise (okuma hatası, parse hatası vb.)
                # Güvenlik için motoru kapatabilirsiniz veya son durumunu koruyabilirsiniz. Kapatmak daha güvenli.
                if g_gpio_sulama_motor_kurulum_basarili and g_motor_line_gpio_pin.get_value() == 1: # Eğer motor açıksa
                    print(f"UYARI (SulamaBağımsızSensör): Geçerli nem verisi alınamadı. Güvenlik için motor kapatılıyor.")
                    g_motor_line_gpio_pin.set_value(0)

        except serial.SerialException as se_loop:
            print(f"HATA (Sulama Döngüsü Seri Port - BağımsızSensör): {se_loop}. Port kapatılıyor.")
            _seri_port_kapat_sulama_bu_modulde() # Hata durumunda portu kapat
        except Exception as e_loop:
            print(f"HATA (Sulama Döngüsü Genel - BağımsızSensör): {type(e_loop).__name__} - {e_loop}")
            # Genel bir hatada da portu kapatmak ve motoru güvenli duruma getirmek iyi bir fikir olabilir.
            _seri_port_kapat_sulama_bu_modulde()
            if g_gpio_sulama_motor_kurulum_basarili and g_motor_line_gpio_pin:
                 try: g_motor_line_gpio_pin.set_value(0)
                 except: pass


        g_stop_sulama_event.wait(timeout=SENSOR_OKUMA_VE_KONTROL_ARALIGI_SANIYE)

    _seri_port_kapat_sulama_bu_modulde() # Thread bittiğinde seri portu kapat
    print("SULAMA (Döngü - BağımsızSensör): Bağımsız sensör okuma ve sulama mantığı sonlandırılıyor.")


# === DIŞARIDAN ÇAĞRILACAK ANA FONKSİYONLAR ===
def start_otomatik_sulama_sistemi():
    """Otomatik sulama sistemini (bağımsız sensör okumalı) başlatır."""
    global g_sulama_ve_sensor_thread, g_stop_sulama_event
    
    print("SULAMA (Sistem - BağımsızSensör): Başlatma komutu alındı.")
    if g_sulama_ve_sensor_thread and g_sulama_ve_sensor_thread.is_alive():
        print("SULAMA (Sistem - BağımsızSensör): Sistem zaten çalışıyor.")
        return True

    g_stop_sulama_event.clear()
    if not _gpio_kurulumu_sulama_motor(): # Önce GPIO'yu kur
        print("HATA (SULAMA Sistem - BağımsızSensör): GPIO kurulumu BAŞARISIZ. Sistem başlatılamıyor.")
        return False
    
    # Seri port açma işlemi thread içinde yapılacak.
    g_sulama_ve_sensor_thread = threading.Thread(target=_sulama_ve_bagimsiz_sensor_dongusu, daemon=True)
    g_sulama_ve_sensor_thread.start()
    # Thread'in portu açması için kısa bir bekleme ve kontrol (isteğe bağlı)
    time.sleep(1) 
    if g_serial_port_sulama_acik_basarili:
        print("SULAMA (Sistem - BağımsızSensör): Sistem başarıyla başlatıldı (arka planda).")
        return True
    else:
        print("UYARI (SULAMA Sistem - BağımsızSensör): Sistem başlatıldı ancak seri port hemen açılamamış olabilir. Thread içinde denenecek.")
        # Hata olarak işaretlemek yerine, thread'in kendi kendine toparlanmasına izin verebiliriz.
        # Eğer ilk açılış kesin başarılı olmalıysa, burada stop_otomatik_sulama_sistemi() çağrılıp False dönülebilir.
        return True # Şimdilik thread'in denemesine izin veriyoruz


def stop_otomatik_sulama_sistemi():
    """Otomatik sulama sistemini (bağımsız sensör okumalı) durdurur."""
    global g_sulama_ve_sensor_thread, g_stop_sulama_event
    
    print("SULAMA (Sistem - BağımsızSensör): Durdurma komutu alındı.")
    if g_sulama_ve_sensor_thread and g_sulama_ve_sensor_thread.is_alive():
        g_stop_sulama_event.set() # Thread'e durma sinyali gönder
        g_sulama_ve_sensor_thread.join(timeout=SENSOR_OKUMA_VE_KONTROL_ARALIGI_SANIYE + 3) # Thread'in bitmesini bekle
        if g_sulama_ve_sensor_thread.is_alive():
             print("UYARI (Sulama Sistem - BağımsızSensör): Sulama thread'i zamanında sonlandırılamadı.")
    else:
        print("SULAMA (Sistem - BağımsızSensör): Sistem zaten çalışmıyor veya hiç başlatılmamış.")
    
    _gpio_serbest_birak_sulama_motor() # Her durumda GPIO kaynaklarını temizle
    _seri_port_kapat_sulama_bu_modulde() # Seri portu da kapat (thread kendi içinde de yapar ama garanti)
    g_sulama_ve_sensor_thread = None # Thread referansını temizle
    print("SULAMA (Sistem - BağımsızSensör): Sistem durduruldu ve kaynaklar temizlendi.")
    return True

# Bu script doğrudan çalıştırılırsa basit bir test için
if __name__ == '__main__':
    print("OTOMATİK SULAMA KONTROL MODÜLÜ (Bağımsız Sensörlü Test Modu)")
    # Bu test için "/dev/ttyUSB0" portunda bir sensörün veri göndermesi beklenir.
    # GPIO pinlerinin de doğru ayarlanmış olması gerekir.
    if start_otomatik_sulama_sistemi():
        print("Sulama sistemi (bağımsız sensörlü) test için başlatıldı. Çıkmak için Ctrl+C.")
        try:
            while True:
                time.sleep(10) # Ana thread'in çalışmasını ve logları görmek için bekle
                print("...(Test ana döngüsü çalışıyor)...")
        except KeyboardInterrupt:
            print("\nTest kullanıcı tarafından sonlandırılıyor.")
        finally:
            stop_otomatik_sulama_sistemi()
    else:
        print("Sulama sistemi (bağımsız sensörlü) test için başlatılamadı.")
    print("OTOMATİK SULAMA KONTROL MODÜLÜ (Bağımsız Sensörlü Test Modu) Bitti.")