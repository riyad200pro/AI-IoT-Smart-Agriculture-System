# Ana_kodlar.py (Eski, daha basit hali)

import tkinter as tk
from tkinter import ttk, messagebox, Label, Button # ttk burada kullanılmıyor gibi ama import kalabilir
from PIL import Image, ImageTk
import sys # Kullanılmıyor gibi ama kalabilir
import os # Kullanılmıyor gibi ama kalabilir

startup_errors = [] # Başlangıç hatalarını toplamak için liste

# urun_oneri_modulu importu
try:
    from urun_oneri_modulu import open_urun_oneri_ui
except ImportError:
    error_msg = "HATA: 'urun_oneri_modulu.py' bulunamadı veya içe aktarılamadı.\n'Toprak Testi' özelliği çalışmayabilir."
    print(error_msg)
    startup_errors.append(("Ürün Öneri Modül Hatası", error_msg))
    open_urun_oneri_ui = None # Fonksiyonu None olarak ayarla ki buton hata versin
except Exception as e:
    error_msg = f"HATA: 'urun_oneri_modulu.py' yüklenirken beklenmedik bir sorun: {e}."
    print(error_msg)
    startup_errors.append(("Ürün Öneri Modül Hatası", error_msg))
    open_urun_oneri_ui = None

# === YÖNETİCİ MODÜL İMPORTU ===
saatlik_yonetici_modulu = None # Başlangıçta None olarak ayarla
try:
    import saatlik_gorev_yoneticisi # Modülü 'saatlik_gorev_yoneticisi' adıyla import et
    # Eğer saatlik_gorev_yoneticisi içindeki fonksiyonları doğrudan kullanacaksanız,
    # saatlik_yonetici_modulu = saatlik_gorev_yoneticisi ataması gereksiz olabilir,
    # doğrudan saatlik_gorev_yoneticisi.fonksiyon_adi() şeklinde çağırabilirsiniz.
    # Ancak mevcut yapınızda bu şekilde bir atama var, koruyorum.
    saatlik_yonetici_modulu = saatlik_gorev_yoneticisi

    # Bu MODULES_LOADED kontrolü, saatlik_gorev_yoneticisi.py dosyasında tanımlı olmalı
    if hasattr(saatlik_yonetici_modulu, 'CORE_REPORT_MODULES_LOADED'): # Bayrak adını kontrol edin, belki MODULES_LOADED idi
        if not saatlik_yonetici_modulu.CORE_REPORT_MODULES_LOADED:
            startup_errors.append(("Yönetici Alt Modül Hatası", "Saatlik görev yöneticisinin raporlama için gereken alt modülleri (hastalık, kamera, büyüme) yüklenemedi. Lütfen konsol çıktılarını kontrol edin."))
    elif hasattr(saatlik_yonetici_modulu, 'MODULES_LOADED'): # Eski bayrak adı için de kontrol
         if not saatlik_yonetici_modulu.MODULES_LOADED:
            startup_errors.append(("Yönetici Alt Modül Hatası", "Saatlik görev yöneticisinin raporlama için gereken alt modülleri (hastalık, kamera, büyüme) yüklenemedi. Lütfen konsol çıktılarını kontrol edin."))
    else:
        # Eğer bayrak hiç yoksa, bu da bir bilgilendirme olabilir.
        # startup_errors.append(("Yönetici Modül Sorunu", "MODULES_LOADED/CORE_REPORT_MODULES_LOADED bayrağı yönetici modülünde bulunamadı."))
        print("UYARI: saatlik_gorev_yoneticisi modülünde CORE_REPORT_MODULES_LOADED bayrağı bulunamadı.")


except ImportError:
    error_msg = "HATA: 'saatlik_gorev_yoneticisi.py' dosyası bulunamadı veya içe aktarılamadı.\nSaatlik görevler çalışmayabilir."
    print(error_msg)
    startup_errors.append(("Yönetici Modül Hatası", error_msg))
    saatlik_yonetici_modulu = None
except Exception as e:
    error_msg = f"HATA: 'saatlik_gorev_yoneticisi.py' yüklenirken beklenmedik bir hata: {e}."
    print(error_msg)
    startup_errors.append(("Yönetici Modül Hatası", error_msg))
    saatlik_yonetici_modulu = None


# === GENEL YARDIMCI FONKSİYONLAR ===
def show_general_message(title, message, parent=None):
    # Bu fonksiyon, bir önceki verdiğiniz Ana_kodlar.py'den alınmıştır.
    # Parent pencereyi bulma mantığı iyileştirilmiş.
    active_window = parent
    if active_window is None:
        # Aktif bir Toplevel veya Tk penceresi bulmaya çalış
        if 'window' in globals() and isinstance(window, tk.Tk) and window.winfo_exists():
            active_window = window
        # Veya messagebox'ın kendi parent bulma mekanizmasına güvenebiliriz.
        # Ancak Toplevel için parent belirtmek daha iyi.

    # Eğer hala parent bulunamadıysa ve bir ana pencere varsa, onu kullan
    if active_window is None and 'window' in globals() and isinstance(window, tk.Tk):
        active_window = window
        
    msg_win = tk.Toplevel(active_window) # active_window None ise, ana pencereyi parent alır veya yeni bir root oluşturur.
    msg_win.title(title)
    msg_win.geometry("500x300+400+250") # Konumu biraz ayarlandı
    msg_win.configure(bg="#f0f0f0")
    msg_win.resizable(False, False)

    main_frame = tk.Frame(msg_win, bg="#f0f0f0", padx=15, pady=15)
    main_frame.pack(expand=True, fill="both")

    text_frame = tk.Frame(main_frame, bg="white", bd=1, relief="sunken")
    text_frame.pack(expand=True, fill="both", pady=(0,10))
    
    msg_text_widget = tk.Text(text_frame, wrap="word", font=("Arial", 10), relief="flat", borderwidth=0, bg="white", spacing1=5, spacing3=5, padx=5, pady=5)
    msg_text_widget.insert(tk.END, message)
    msg_text_widget.config(state="disabled")
    
    scrollbar = tk.Scrollbar(text_frame, command=msg_text_widget.yview, orient=tk.VERTICAL)
    msg_text_widget['yscrollcommand'] = scrollbar.set
    
    scrollbar.pack(side="right", fill="y") # padx, pady kaldırıldı, Text widget'ına eklendi
    msg_text_widget.pack(side="left", expand=True, fill="both")

    tk.Button(main_frame, text="Tamam", command=msg_win.destroy, bg="#007bff", fg="white", font=("Arial", 10, "bold"), width=10, relief="raised", bd=1).pack(pady=(5,0))
    
    if active_window and active_window.winfo_exists(): # Parent varsa transient yap
        msg_win.transient(active_window)
    msg_win.grab_set()
    # msg_win.wait_window() # Bu, ana thread'i bloklar. Startup hataları için belki sorun değil.


def show_startup_errors_if_any():
    """Başlangıçta biriken hataları gösterir."""
    if startup_errors:
        full_error_message = "Uygulama başlarken aşağıdaki sorunlar tespit edildi:\n\n"
        for title, msg_content in startup_errors:
            # msg_content'in string olup olmadığını kontrol etmeye gerek yok, str() her türlü çevirir.
            cleaned_msg = str(msg_content).replace('BİLİNMİYOR', '').strip() # BİLİNMİYOR temizliği kalabilir
            full_error_message += f"- {title}:\n  {cleaned_msg}\n\n"
        
        # Parent pencereyi bulmaya çalış
        parent_for_startup_error = None
        if 'window' in globals() and isinstance(window, tk.Tk) and window.winfo_exists():
            parent_for_startup_error = window
        
        # show_general_message yerine doğrudan messagebox.showerror kullanmak daha standart olabilir
        # ama mevcut show_general_message fonksiyonunuzu kullanıyorum.
        show_general_message("Başlangıç Uyarıları", full_error_message.strip(), parent=parent_for_startup_error)


# === ANA UYGULAMA PENCERESİ ===
window = tk.Tk()
window.title("Akıllı Bahçem Ana Menü")
window.geometry("600x450+300+150") # Pencere boyutu ve konumu
window.resizable(False, False) # Yeniden boyutlandırmayı engelle

MAIN_APP_BG_IMAGE_PATH = "mm.jpeg" # Arka plan resminizin yolu
try:
    main_bg_pil = Image.open(MAIN_APP_BG_IMAGE_PATH)
    main_bg_pil = main_bg_pil.resize((600, 450), Image.LANCZOS) # Pillow 9.0.0+ için Image.LANCZOS
    window.main_bg_tk_ref = ImageTk.PhotoImage(main_bg_pil) # Referansı sakla
    main_background_label = tk.Label(window, image=window.main_bg_tk_ref)
    main_background_label.place(x=0, y=0, relwidth=1, relheight=1)
    main_background_label.lower() # Diğer widget'ların arkasında kalması için
except FileNotFoundError:
    error_msg_bg = f"Ana pencere arka plan resmi '{MAIN_APP_BG_IMAGE_PATH}' bulunamadı."
    print(f"UYARI: {error_msg_bg}")
    window.configure(bg="#ADD8E6") # Açık mavi bir arka plan
    startup_errors.append(("Arka Plan Hatası", error_msg_bg))
except Exception as e_bg:
    error_msg_bg_general = f"Ana pencere arka plan resmi yüklenirken bir hata oluştu: {e_bg}"
    print(f"HATA: {error_msg_bg_general}")
    window.configure(bg="#ADD8E6")
    startup_errors.append(("Arka Plan Hatası", error_msg_bg_general))

# === BUTON KOMUTLARI ===
def urun_oneri_command():
    if open_urun_oneri_ui is None: # Modül yüklenememişse
        messagebox.showerror("Modül Hatası", 
                             "'urun_oneri_modulu.py' yüklenemedi veya içinde 'open_urun_oneri_ui' fonksiyonu bulunamadı.\n"
                             "'Toprak Testi' özelliği kullanılamıyor.", 
                             parent=window)
        return
    try:
        open_urun_oneri_ui(window) # open_urun_oneri_ui fonksiyonunu çağır
    except Exception as e_urun_oneri:
        messagebox.showerror("Arayüz Hatası", f"Ürün Öneri arayüzü açılırken bir hata oluştu:\n{e_urun_oneri}", parent=window)
        print(f"HATA (urun_oneri_command): {e_urun_oneri}")


def tum_saatlik_sistemleri_baslat_command():
    if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'start_combined_hourly_tasks'):
        # Saatlik görev yöneticisindeki CORE_REPORT_MODULES_LOADED bayrağını kontrol et (varsa)
        # Bu bayrak sadece raporlama modüllerinin (hastalık, kamera, büyüme) durumunu gösterir.
        # Sensör ve sulama gibi yeni eklenen servislerin kendi yüklenme durumları ayrı ele alınmalı.
        perform_start = True
        if hasattr(saatlik_yonetici_modulu, 'CORE_REPORT_MODULES_LOADED') and not saatlik_yonetici_modulu.CORE_REPORT_MODULES_LOADED:
             # Kullanıcıya bilgi verilebilir ama başlatmayı engellemeyebiliriz, çünkü sensör/sulama çalışabilir.
             proceed = messagebox.askyesno("Modül Uyarısı (Raporlama)",
                                           "Saatlik raporlama için gerekli alt modüller (hastalık, kamera, büyüme) yüklenemedi.\n"
                                           "Diğer sistemler (sensör, sulama vb.) yine de başlatılsın mı?",
                                           parent=window)
             if not proceed:
                 perform_start = False
        
        if perform_start:
            # parent_window_for_initial_error parametresini gönderiyoruz.
            if saatlik_yonetici_modulu.start_combined_hourly_tasks(parent_window_for_initial_error=window):
                btn_saatlik_baslat.config(state="disabled")
                btn_saatlik_durdur.config(state="normal")
                messagebox.showinfo("Sistem Başlatıldı", "Tüm saatlik görevler ve servisler için yönetici başarıyla başlatıldı (arka planda).", parent=window)
            # else: start_combined_hourly_tasks fonksiyonu kendi içinde hata mesajı (messagebox) verebilir.
    else:
        messagebox.showerror("Modül Hatası", 
                             "'saatlik_gorev_yoneticisi.py' yüklenemedi veya içinde 'start_combined_hourly_tasks' fonksiyonu bulunamadı.", 
                             parent=window)


def tum_saatlik_sistemleri_durdur_command():
    if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'stop_combined_hourly_tasks'):
        if saatlik_yonetici_modulu.stop_combined_hourly_tasks(): # Bu fonksiyonun True/False dönmesi iyi olur.
            btn_saatlik_baslat.config(state="normal")
            btn_saatlik_durdur.config(state="disabled")
            messagebox.showinfo("Sistem Durduruldu", "Tüm saatlik görevler ve servisler için yönetici başarıyla durduruldu.", parent=window)
        # else: Hata durumunda stop_combined_hourly_tasks kendi mesajını verebilir.
    else:
        messagebox.showerror("Modül Hatası", 
                             "'saatlik_gorev_yoneticisi.py' yüklenemedi veya içinde 'stop_combined_hourly_tasks' fonksiyonu bulunamadı.", 
                             parent=window)


# === BUTONLAR ===
# Butonların stil ve yerleşimleri daha önce sağladığınız koddaki gibi.
btn_urun_oneri = tk.Button(window, text="Toprak Testi",
                           command=urun_oneri_command,
                           bg="#5CA4FF", fg="white", padx=10, pady=5, font=("Tahoma", 12, "bold"), relief="raised", bd=2)
btn_urun_oneri.place(relx=0.75, rely=0.30, anchor="center", width=240, height=50)

btn_saatlik_baslat = tk.Button(window, text="Tüm Saatlik Sistemleri Başlat",
                               command=tum_saatlik_sistemleri_baslat_command,
                               bg="#28a745", fg="white", padx=10, pady=5, font=("Tahoma", 11, "bold"), relief="raised", bd=2)
btn_saatlik_baslat.place(relx=0.75, rely=0.47, anchor="center", width=240, height=50)

btn_saatlik_durdur = tk.Button(window, text="Tüm Saatlik Sistemleri Durdur",
                               command=tum_saatlik_sistemleri_durdur_command,
                               bg="#dc3545", fg="white", padx=10, pady=5, font=("Tahoma", 11, "bold"), relief="raised", bd=2,
                               state="disabled") # Başlangıçta durdur butonu pasif
btn_saatlik_durdur.place(relx=0.75, rely=0.64, anchor="center", width=240, height=50)


# === ÇIKIŞ İŞLEMLERİ ===
def on_main_window_closing():
    if messagebox.askokcancel("Çıkış", "Akıllı Bahçe uygulamasından çıkmak istediğinize emin misiniz?", parent=window):
        print("Ana uygulama kapatılıyor, tüm arka plan görevleri durduruluyor...")
        if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'stop_combined_hourly_tasks'):
            saatlik_yonetici_modulu.stop_combined_hourly_tasks() # Tüm servisleri durdur
        
        # Eğer urun_oneri_modulu'nün kendi UI thread'i varsa ve o da ayrıca kapatılmalıysa,
        # burada ona özel bir kapatma fonksiyonu da çağrılabilir.
        # Ancak şu anki yapıda on_toplevel_close_urun_oneri bunu hallediyor.
        # Ana pencere kapatılırken açık bir ürün öneri penceresi varsa, o da kapatılmalı.

        print("Ana uygulama penceresi yok ediliyor.")
        window.destroy()

window.protocol("WM_DELETE_WINDOW", on_main_window_closing)


if __name__ == '__main__':
    # Başlangıç hatalarını göstermek için ana döngü başladıktan kısa bir süre sonra çağır
    window.after(100, show_startup_errors_if_any) 
    window.mainloop()
