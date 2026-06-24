# Bu fonksiyon, kamera_modulu.py dosyanızın bir parçası olmalı
# veya benzer bir yardımcı modülde yer almalıdır.

from picamera2 import Picamera2
import cv2
import time
import datetime
import os
import uuid # Benzersiz İçerik ID'leri (CID) oluşturmak için

# === Ayarlar (modül seviyesinde sabitler veya fonksiyona argüman olarak geçilebilir) ===
# KAYIT_YOLU'nun yazılabilir olduğundan emin olun.
VARSAYILAN_KAYIT_YOLU = "/home/pi5/Desktop/final/eposta_cekimleri" # Özel bir alt klasör kullanılıyor
VARSAYILAN_DOSYAADI_ONEKI = "eposta_resmi_"

picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")

def _kayit_yolunu_kontrol_et_ve_olustur(yol):
    """Yardımcı fonksiyon: Klasör yoksa oluşturur."""
    if not os.path.exists(yol):
        try:
            os.makedirs(yol)
            print(f"BILGI (EpostaResimCekimi): Kayit dizini olusturuldu: {yol}") # Türkçe karakterler düzeltildi
            return True
        except Exception as e:
            print(f"HATA (EpostaResimCekimi): Kayit dizini ({yol}) olusturulamadi: {e}") # Türkçe karakterler düzeltildi
            return False
    return True

def _eposta_icin_resmi_hazirla_yoldan(resim_dosya_yolu, alt_metin="Yakalanan Resim"):
    """
    Bir resim dosya yolunu alır, bir CID oluşturur ve e-postaya gömmek için
    bir HTML parçacığı ile CID-dosya yolu eşlemesi döndürür.
    """
    if not os.path.exists(resim_dosya_yolu):
        hata_mesaji = f"E-posta hazirligi icin resim dosyasi bulunamadi: {resim_dosya_yolu}" # Türkçe karakterler düzeltildi
        print(f"HATA (EpostaHazirlik): {hata_mesaji}") # Türkçe karakterler düzeltildi
        return f"<p style='color:red;'>{hata_mesaji}</p>", {}

    resim_cid = f"resim_{uuid.uuid4().hex}" # Benzersiz İçerik ID'si
    dosya_adi = os.path.basename(resim_dosya_yolu)
    
    # E-postada resmi görüntülemek için HTML parçacığı
    html_parcacigi = f"""
        <p>{alt_metin} ({dosya_adi}):</p>
        <img src="cid:{resim_cid}" alt="{alt_metin} - {dosya_adi}" style="max-width:600px; height:auto; border:1px solid #ddd; display:block;">
    """
    # CID'yi gerçek dosya yoluna eşle
    cid_dosyayolu_eslesmesi = {resim_cid: resim_dosya_yolu}
    
    return html_parcacigi, cid_dosyayolu_eslesmesi

def eposta_icin_resim_cek_ve_hazirla(kayit_yolu=VARSAYILAN_KAYIT_YOLU, dosyaadi_oneki=VARSAYILAN_DOSYAADI_ONEKI):
    """
    Picamera2 kullanarak bir resim çeker, kaydeder ve e-postaya gömmek için
    bir HTML parçacığı ile CID eşlemesi döndürür.
    Sağlamlık için kendi Picamera2 yaşam döngüsünü yönetir.
    """
    picam2_yerel = None # Bu fonksiyon çağrısı için yerel Picamera2 nesnesi
    kaydedilen_dosya_yolu = None
    donecek_html = ""
    donecek_cid_eslesmesi = {}

    if not _kayit_yolunu_kontrol_et_ve_olustur(kayit_yolu):
        donecek_html = "<p style='color:red;'>Resim kayit dizininin varligi saglanamadi.</p>" # Türkçe karakterler düzeltildi
        return donecek_html, donecek_cid_eslesmesi

    try:
        print("BILGI (EpostaResimCekimi): Cekim icin Picamera2 baslatiliyor...") # Türkçe karakterler düzeltildi
        picam2_yerel = Picamera2()
        
        # Fotoğraf çekimi için yapılandırma
        # Yaygın bir boyut kullanılıyor, gerektiği gibi ayarlayın. RGB888 cv2 için iyidir.
        foto_config = picam2_yerel.create_still_configuration(main={"format": "RGB888", "size": (1280, 720)})
        picam2_yerel.configure(foto_config)
        
        picam2_yerel.start()
        print("BILGI (EpostaResimCekimi): Kamera baslatildi, sensorun oturmasi icin 1.5sn bekleniyor...") # Türkçe karakterler düzeltildi
        

        print("BILGI (EpostaResimCekimi): Resim dizisi yakalaniyor...") # Türkçe karakterler düzeltildi
        frame_rgb = picam2_yerel.capture_array("main") # still_config'in 'main' akışından yakala
        
        # Picamera2'nin RGB888'i bir RGB numpy dizisidir. cv2.imwrite BGR bekler.
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        print("BILGI (EpostaResimCekimi): Resim dizisi yakalandi ve BGR'ye donusturuldu.") # Türkçe karakterler düzeltildi

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya_adi = f"{dosyaadi_oneki}{timestamp}.jpg"
        kaydedilen_dosya_yolu = os.path.join(kayit_yolu, dosya_adi)
        
        cv2.imwrite(kaydedilen_dosya_yolu, frame_bgr)
        print(f"BILGI (EpostaResimCekimi): Fotograf basariyla kaydedildi: {kaydedilen_dosya_yolu}") # Türkçe karakterler düzeltildi

        # Resim kaydedildiğine göre, e-posta için hazırla
        donecek_html, donecek_cid_eslesmesi = _eposta_icin_resmi_hazirla_yoldan(
            kaydedilen_dosya_yolu, 
            f"Otomatik Bahce Cekimi {timestamp}" # Türkçe karakterler düzeltildi
        )

    except Exception as e:
        hata_mesaji = f"E-posta icin resim cekme/isleme sirasinda hata: {e}" # Türkçe karakterler düzeltildi
        print(f"HATA (EpostaResimCekimi): {hata_mesaji}") # Türkçe karakterler düzeltildi
        donecek_html = f"<p style='color:red;'>{hata_mesaji}</p>"
        # CID eşlemesi oluşturulmadan önce kaydetme başarısız olduysa filepath'in None olduğundan emin ol
        if kaydedilen_dosya_yolu and not os.path.exists(kaydedilen_dosya_yolu): 
            kaydedilen_dosya_yolu = None 
        donecek_cid_eslesmesi = {} # Hata durumunda eşlenecek resim yok
    finally:
        if picam2_yerel:
            try:
                if picam2_yerel.started:
                    picam2_yerel.stop()
                    print("BILGI (EpostaResimCekimi): Kamera durduruldu.") # Türkçe karakterler düzeltildi
                picam2_yerel.close()
                print("BILGI (EpostaResimCekimi): Kamera kapatildi ve kaynaklar serbest birakildi.") # Türkçe karakterler düzeltildi
            except Exception as e_kapat:
                print(f"UYARI (EpostaResimCekimi): Kamera kapatilirken hata: {e_kapat}") # Türkçe karakterler düzeltildi

    return donecek_html, donecek_cid_eslesmesi

# This is the example of how to use this function (e.g., in saatlik_gorev_yoneticisi.py)
if __name__ == '__main__':
    print("'eposta_icin_resim_cek_ve_hazirla' function is being tested...")
    
    # This test runs the function as if it were called from another module.
    # It does not rely on any pre-existing global picam2 instance from this file.
    
    eposta_icin_html_parcacigi, eposta_icin_cid_eslesmesi = eposta_icin_resim_cek_ve_hazirla()
    
    print("\n--- HTML Snippet for Email ---")
    print(eposta_icin_html_parcacigi)
    
    print("\n--- CID Map for Email Attachments ---")
    print(eposta_icin_cid_eslesmesi)

    if eposta_icin_cid_eslesmesi:
        for cid_degeri, dosya_konumu in eposta_icin_cid_eslesmesi.items():
            if os.path.exists(dosya_konumu):
                print(f"VERIFICATION: Image file '{dosya_konumu}' for CID '{cid_degeri}' exists.")
            else:
                print(f"VERIFICATION FAILED: Image file '{dosya_konumu}' for CID '{cid_degeri}' DOES NOT exist.")
    else:
        print("VERIFICATION: No image was processed or an error occurred.")
        
    print("\nTest completed.")