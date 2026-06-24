import cv2
import numpy as np
import argparse
import tkinter as tk
from tkinter import filedialog
import sys

# --- YENİ FONKSİYON: Ekran Çözünürlüğünü Alma ---
def get_screen_resolution():
    """Tkinter kullanarak ana ekran çözünürlüğünü (genişlik, yükseklik) döndürür."""
    try:
        root = tk.Tk()
        root.withdraw() # Gizli pencere
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy() # Pencereyi kapat
        return width, height
    except tk.TclError:
        print("Uyarı: Ekran çözünürlüğü alınamadı. Varsayılan boyut kullanılacak.")
        return 1920, 1080 # Makul bir varsayılan değer

#----------------------------------------------------
# load_and_check_image, segment_plant, calculate_metrics fonksiyonları aynı
#----------------------------------------------------
def load_and_check_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Hata: '{image_path}' bulunamadı veya okunamadı.")
    return img

def segment_plant(image, lower_hsv, upper_hsv, morph_kernel_size=5, min_contour_area=100):
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
    total_pixel_count = cv2.countNonZero(final_mask)
    return final_mask, valid_contours, total_pixel_count

def calculate_metrics(contours):
    if contours is None or not contours: return {'pixel_count': 0, 'bounding_box_height': 0, 'bounding_box_width': 0, 'contour_area': 0}
    total_area = sum(cv2.contourArea(cnt) for cnt in contours)
    all_points = np.concatenate(contours)
    x, y, w, h = cv2.boundingRect(all_points)
    return {'pixel_count': int(total_area), 'bounding_box_height': h, 'bounding_box_width': w, 'contour_area': int(total_area)}
#----------------------------------------------------

# --- YENİ: visualize_result Fonksiyonu Tamamen Değiştirildi ---
def visualize_result(image, mask, contours, metrics, window_name="Sonuc", max_disp_width=None, max_disp_height=None):
    """
    Segmentasyon sonucunu orijinal resim üzerinde gösterir.
    Görüntüyü, verilen maksimum genişlik ve yüksekliğe orantısal olarak sığdırır.
    """
    result_img = image.copy()
    result_img[mask == 255] = [0, 255, 0] # Yeşil

    display_img = result_img # Başlangıçta orijinal resmi kullan

    img_height, img_width = result_img.shape[:2]

    # Sadece maksimum boyutlar verilmişse ve resim bunlardan büyükse yeniden boyutlandır
    if max_disp_width and max_disp_height and (img_width > max_disp_width or img_height > max_disp_height):
        # Genişliğe göre ölçek faktörü
        scale_w = max_disp_width / img_width
        # Yüksekliğe göre ölçek faktörü
        scale_h = max_disp_height / img_height
        # Her iki boyuta da sığması için daha küçük olan ölçek faktörünü seç
        scale_factor = min(scale_w, scale_h)

        # Yeni boyutları hesapla
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)

        # Genişlik veya yükseklik 0 olmamalı
        if new_width > 0 and new_height > 0:
           dim = (new_width, new_height)
           display_img = cv2.resize(result_img, dim, interpolation=cv2.INTER_AREA)
        else:
            display_img = result_img # Boyutlandırma başarısız olursa orijinali kullan
    else:
         display_img = result_img # Boyutlandırma gerekmiyorsa orijinali kullan

    # Metrikleri ve konturları (varsa) boyutlandırılmış resme çiz (veya istersen orijinaline çizip sonra boyutlandır)
    if contours:
        # Konturları boyutlandırılmış resme göre yeniden ölçekle (VEYA Çizimleri en başta yap)
        # Bu kısım biraz daha karmaşık olabilir, şimdilik metrikleri boyutlandırılmış resme yazalım
        all_points_orig = np.concatenate(contours)
        x_orig, y_orig, w_orig, h_orig = cv2.boundingRect(all_points_orig)

        # Yazı ve kutu koordinatlarını ölçek faktörüne göre ayarla (eğer ölçekleme yapıldıysa)
        current_h, current_w = display_img.shape[:2]
        draw_scale_w = current_w / img_width
        draw_scale_h = current_h / img_height

        x_disp = int(x_orig * draw_scale_w)
        y_disp = int(y_orig * draw_scale_h)
        # w_disp = int(w_orig * draw_scale_w) # Kutuyu çizmek istersen
        # h_disp = int(h_orig * draw_scale_h) # Kutuyu çizmek istersen

        text = f"Alan: {metrics['contour_area']}px, Yuk.: {metrics['bounding_box_height']}px"
        font_scale = 0.5 # Yazı boyutunu biraz küçülttük
        cv2.putText(display_img, text, (x_disp, max(y_disp - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0,0,255), 1) # Yazıyı daha güvenli bir yere koy

        # İstersen konturları ve kutuyu da ölçekleyip çizebilirsin, ama bu daha fazla hesap gerektirir.

    # --- ÖNEMLİ: namedWindow EKLENDİ ---
    # Pencereyi yeniden boyutlandırılabilir olarak oluştur/tanımla
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # --- namedWindow BİTTİ ---

    # Yeniden boyutlandırılmış görüntüyü göster
    cv2.imshow(window_name, display_img)

#----------------------------------------------------
def select_image_file(title="Resim Dosyası Seç"):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=(("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                   ("Tüm Dosyalar", "*.*"))
    )
    if not file_path:
        print("Dosya seçimi iptal edildi. Program sonlandırılıyor.")
        sys.exit()
    return file_path
#----------------------------------------------------

# --- YENİ: main Fonksiyonu Güncellendi (Ekran boyutları alınıp gönderiliyor) ---
def main(img_path1, img_path2, lower_hsv_str, upper_hsv_str, growth_threshold_percent=5.0, show_visualization=True):
    """Ana iş akışını yönetir."""
    try:
        # Ekran boyutlarını al (Sadece görselleştirme yapılacaksa alınabilir)
        screen_w, screen_h = 0, 0
        if show_visualization:
           screen_w, screen_h = get_screen_resolution()
           # Hedef maksimum boyutları belirle (ekranın yarısı)
           target_w = screen_w // 2
           target_h = screen_h // 2
           print(f"Ekran çözünürlüğü: {screen_w}x{screen_h}. Hedef pencere boyutu (max): {target_w}x{target_h}")
        else:
           target_w, target_h = None, None # Görselleştirme yoksa boyut hesaplama

        lower_hsv = np.array([int(x) for x in lower_hsv_str.split(',')])
        upper_hsv = np.array([int(x) for x in upper_hsv_str.split(',')])

        img1 = load_and_check_image(img_path1)
        img2 = load_and_check_image(img_path2)

        mask1, contours1, _ = segment_plant(img1, lower_hsv, upper_hsv)
        mask2, contours2, _ = segment_plant(img2, lower_hsv, upper_hsv)

        metrics1 = calculate_metrics(contours1)
        metrics2 = calculate_metrics(contours2)

        print(f"--- {img_path1} Metrikleri ---")
        print(metrics1)
        print(f"--- {img_path2} Metrikleri ---")
        print(metrics2)

        metric_to_compare = 'contour_area'
        val1 = metrics1.get(metric_to_compare, 0)
        val2 = metrics2.get(metric_to_compare, 0)

        print(f"\n--- Karşılaştırma ({metric_to_compare}) ---")
        print(f"Zaman 1: {val1}")
        print(f"Zaman 2: {val2}")

        if val1 > 0:
            percentage_increase = ((val2 - val1) / val1) * 100
            print(f"Yüzdesel Değişim: {percentage_increase:.2f}%")
            if percentage_increase > growth_threshold_percent:
                print(f"Sonuç: Büyüme tespit edildi (Eşik: >{growth_threshold_percent}%)")
            else:
                print(f"Sonuç: Anlamlı bir büyüme tespit edilmedi veya bitki küçülmüş (Eşik: >{growth_threshold_percent}%)")
        elif val2 > 0:
             print("Sonuç: Büyüme tespit edildi (İlk resimde bitki yoktu).")
        else:
            print("Sonuç: Her iki resimde de bitki bulunamadı.")

        if show_visualization:
            # visualize_result çağrılarına hedef boyutları ekle
            visualize_result(img1, mask1, contours1, metrics1, window_name="Zaman 1 Sonuc", max_disp_width=target_w, max_disp_height=target_h)
            visualize_result(img2, mask2, contours2, metrics2, window_name="Zaman 2 Sonuc", max_disp_width=target_w, max_disp_height=target_h)
            print("\nGörselleştirme pencerelerini kapatmak için bir tuşa basın...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    except FileNotFoundError as e: print(e)
    except ValueError as e: print(f"Hata: HSV değerleri yanlış formatta. Virgülle ayrılmış sayılar olmalı. ({e})")
    except Exception as e: print(f"Beklenmedik bir hata oluştu: {e}")

# --- YENİ: argparse Güncellendi (--scale kaldırıldı) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seçilen iki görüntüdeki bitki büyümesini karşılaştırır.')
    parser.add_argument('--lhsv', default='35,50,50', help='Alt HSV eşik değeri (virgülle ayrılmış, örn: 35,50,50)')
    parser.add_argument('--uhsv', default='85,255,255', help='Üst HSV eşik değeri (virgülle ayrılmış, örn: 85,255,255)')
    parser.add_argument('--threshold', type=float, default=5.0, help='Büyüme olarak kabul edilecek minimum yüzdesel artış (örn: 5.0)')
    # parser.add_argument('--scale', type=int, default=100, help='...') # KALDIRILDI
    parser.add_argument('--novis', action='store_true', help='Görselleştirme pencerelerini gösterme')

    args = parser.parse_args()

    print("Lütfen karşılaştırılacak İLK resmi seçin...")
    image_path1 = select_image_file(title="İlk Resmi Seç (Önceki Zaman)")
    print(f"İlk resim: {image_path1}")

    print("\nLütfen karşılaştırılacak İKİNCİ resmi seçin...")
    image_path2 = select_image_file(title="İkinci Resmi Seç (Sonraki Zaman)")
    print(f"İkinci resim: {image_path2}")

    # Ana fonksiyonu çağır (display_scale artık yok)
    main(image_path1, image_path2, args.lhsv, args.uhsv, args.threshold, not args.novis)