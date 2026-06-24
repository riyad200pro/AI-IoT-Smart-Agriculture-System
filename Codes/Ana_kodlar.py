# Ana_kodlar.py

import tkinter as tk
from tkinter import ttk, messagebox, Label, Button
from PIL import Image, ImageTk
import sys
import os

startup_errors = [] # Başlangıç hatalarını toplamak için liste

# urun_oneri_modulu importu
try:
    from urun import open_urun_oneri_ui
except ImportError:
    error_msg = "HATA: 'urun_oneri_modulu.py' bulunamadı veya içe aktarılamadı.\n'Toprak Testi' özelliği çalışmayabilir."
    print(error_msg)
    startup_errors.append(("Ürün Öneri Modül Hatası", error_msg))
    open_urun_oneri_ui = None
except Exception as e:
    error_msg = f"HATA: 'urun_oneri_modulu.py' yüklenirken beklenmedik bir sorun: {e}."
    print(error_msg)
    startup_errors.append(("Ürün Öneri Modül Hatası", error_msg))
    open_urun_oneri_ui = None

# === YÖNETİCİ MODÜL İMPORTU ===
saatlik_yonetici_modulu = None # Başlangıçta None olarak ayarla
try:
    import saatlik_gorev_yoneticisi # Modülü 'saatlik_gorev_yoneticisi' adıyla import et
    saatlik_yonetici_modulu = saatlik_gorev_yoneticisi # *** BU SATIR ÇOK ÖNEMLİ ***

    # Şimdi 'saatlik_yonetici_modulu' üzerinden MODULES_LOADED'a erişebiliriz
    if hasattr(saatlik_yonetici_modulu, 'MODULES_LOADED') and not saatlik_yonetici_modulu.MODULES_LOADED:
        startup_errors.append(("Yönetici Alt Modül Hatası", "Saatlik görev yöneticisinin çalışması için gereken bir veya daha fazla alt modül yüklenemedi. Lütfen konsol çıktılarını kontrol edin."))
    elif not hasattr(saatlik_yonetici_modulu, 'MODULES_LOADED'):
        startup_errors.append(("Yönetici Modül Sorunu", "MODULES_LOADED bayrağı yönetici modülünde bulunamadı."))

except ImportError:
    error_msg = "HATA: 'saatlik_gorev_yoneticisi.py' dosyası bulunamadı veya içe aktarılamadı.\nSaatlik görevler çalışmayabilir."
    print(error_msg)
    startup_errors.append(("Yönetici Modül Hatası", error_msg))
    saatlik_yonetici_modulu = None # Hata durumunda None olduğundan emin ol
except Exception as e:
    error_msg = f"HATA: 'saatlik_gorev_yoneticisi.py' yüklenirken beklenmedik bir hata: {e}."
    print(error_msg)
    startup_errors.append(("Yönetici Modül Hatası", error_msg))
    saatlik_yonetici_modulu = None # Hata durumunda None olduğundan emin ol


# === GENEL YARDIMCI FONKSİYONLAR ===
def show_general_message(title, message, parent=None):
    if parent is None:
        parent_candidate = globals().get('window')
        if parent_candidate and isinstance(parent_candidate, tk.Tk) and parent_candidate.winfo_exists():
            parent = parent_candidate
            
    msg_win = tk.Toplevel(parent)
    msg_win.title(title)
    msg_win.geometry("500x300") 
    msg_win.configure(bg="#f0f0f0")

    main_frame = tk.Frame(msg_win, bg="#f0f0f0", padx=15, pady=15)
    main_frame.pack(expand=True, fill="both")

    text_frame = tk.Frame(main_frame, bg="white", bd=1, relief="sunken")
    text_frame.pack(expand=True, fill="both", pady=(0,10))
    
    msg_text_widget = tk.Text(text_frame, wrap="word", font=("Arial", 10), relief="flat", borderwidth=0, bg="white", spacing1=5, spacing3=5)
    msg_text_widget.insert(tk.END, message)
    msg_text_widget.config(state="disabled")
    
    scrollbar = tk.Scrollbar(text_frame, command=msg_text_widget.yview, orient=tk.VERTICAL)
    msg_text_widget['yscrollcommand'] = scrollbar.set
    
    msg_text_widget.pack(side="left", expand=True, fill="both", padx=(5,0), pady=5)
    scrollbar.pack(side="right", fill="y", padx=(0,5), pady=5)

    tk.Button(main_frame, text="Tamam", command=msg_win.destroy, bg="#007bff", fg="white", font=("Arial", 10, "bold"), width=10).pack(pady=(5,0))
    
    if parent and parent.winfo_exists():
        msg_win.transient(parent)
    msg_win.grab_set()
    msg_win.wait_window()

def show_startup_errors_if_any():
    """Başlangıçta biriken hataları gösterir."""
    if startup_errors:
        full_error_message = "Uygulama başlarken aşağıdaki sorunlar tespit edildi:\n\n"
        for title, msg_content in startup_errors:
            if isinstance(msg_content, str):
                cleaned_msg = msg_content.replace('BİLİNMİYOR', '').strip()
            else:
                cleaned_msg = str(msg_content).strip()
            full_error_message += f"- {title}:\n  {cleaned_msg}\n\n"
        
        parent_window = None
        if 'window' in globals() and isinstance(window, tk.Tk) and window.winfo_exists():
            parent_window = window
        show_general_message("Başlangıç Uyarıları", full_error_message.strip(), parent=parent_window)


# === ANA UYGULAMA PENCERESİ ===
window = tk.Tk()
window.title("Akıllı Bahçem Ana Menü")
window.geometry("600x450+300+150")
window.resizable(False, False)

MAIN_APP_BG_IMAGE_PATH = "mm.jpeg"
try:
    main_bg_pil = Image.open(MAIN_APP_BG_IMAGE_PATH)
    main_bg_pil = main_bg_pil.resize((600, 450), Image.LANCZOS)
    window.main_bg_tk_ref = ImageTk.PhotoImage(main_bg_pil)
    main_background_label = tk.Label(window, image=window.main_bg_tk_ref)
    main_background_label.place(x=0, y=0, relwidth=1, relheight=1)
    main_background_label.lower()
except FileNotFoundError:
    print(f"Uyarı: Ana pencere arka plan resmi '{MAIN_APP_BG_IMAGE_PATH}' bulunamadı.")
    window.configure(bg="#ADD8E6")
    startup_errors.append(("Arka Plan Hatası", f"Ana pencere arka plan resmi '{MAIN_APP_BG_IMAGE_PATH}' bulunamadı."))
except Exception as e:
    print(f"Ana pencere arka plan resmi yüklenirken hata: {e}")
    window.configure(bg="#ADD8E6")
    startup_errors.append(("Arka Plan Hatası", f"Ana pencere arka plan resmi yüklenirken hata: {e}"))

# === BUTON KOMUTLARI ===
def urun_oneri_command():
    if open_urun_oneri_ui is None:
        messagebox.showerror("Modül Hatası", "'urun_oneri_modulu.py' yüklenemedi.\n'Toprak Testi' özelliği kullanılamıyor.", parent=window)
        return
    open_urun_oneri_ui(window)

def tum_saatlik_sistemleri_baslat_command():
    if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'start_combined_hourly_tasks'):
        # MODULES_LOADED kontrolü, yönetici modülünün içindeki alt modüllerin durumunu gösterir.
        if hasattr(saatlik_yonetici_modulu, 'MODULES_LOADED') and saatlik_yonetici_modulu.MODULES_LOADED is False:
            messagebox.showerror("Modül Hatası", "Saatlik görev yöneticisi için gerekli alt modüller yüklenemedi. Lütfen konsolu kontrol edin.", parent=window)
            return

        if saatlik_yonetici_modulu.start_combined_hourly_tasks(parent_window_for_initial_error=window):
            btn_saatlik_baslat.config(state="disabled")
            btn_saatlik_durdur.config(state="normal")
            messagebox.showinfo("Sistem Başlatıldı", "Tüm saatlik görevler için yönetici başarıyla başlatıldı (arka planda).", parent=window)
        # else: start_combined_hourly_tasks zaten kendi içinde hata mesajı (popup/print) veriyor.
    else:
        messagebox.showerror("Modül Hatası", "Saatlik görev yöneticisi modülü veya 'start_combined_hourly_tasks' fonksiyonu bulunamadı.", parent=window)


def tum_saatlik_sistemleri_durdur_command():
    if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'stop_combined_hourly_tasks'):
        if saatlik_yonetici_modulu.stop_combined_hourly_tasks():
            btn_saatlik_baslat.config(state="normal")
            btn_saatlik_durdur.config(state="disabled")
            messagebox.showinfo("Sistem Durduruldu", "Tüm saatlik görev yöneticisi başarıyla durduruldu.", parent=window)
    else:
        messagebox.showerror("Modül Hatası", "Saatlik görev yöneticisi modülü veya 'stop_combined_hourly_tasks' fonksiyonu bulunamadı.", parent=window)


# === BUTONLAR ===
btn_urun_oneri = tk.Button(window, text="Toprak Testi",
                        command=urun_oneri_command,
                        bg="#5CA4FF", fg="white", padx=10, pady=5, font=("Tahoma", 12, "bold"), relief="raised", bd=2)
btn_urun_oneri.place(relx=0.75, rely=0.10, anchor="center", width=240, height=50)

btn_saatlik_baslat = tk.Button(window, text="Sistemi Başlat",
                            command=tum_saatlik_sistemleri_baslat_command,
                            bg="#5CA4FF", fg="white", padx=10, pady=5, font=("Tahoma", 11, "bold"), relief="raised", bd=2)
btn_saatlik_baslat.place(relx=0.75, rely=0.23, anchor="center", width=240, height=50)

btn_saatlik_durdur = tk.Button(window, text="Sistemi Durdur",
                            command=tum_saatlik_sistemleri_durdur_command,
                            bg="#5CA4FF", fg="white", padx=10, pady=5, font=("Tahoma", 11, "bold"), relief="raised", bd=2)
btn_saatlik_durdur.place(relx=0.75, rely=0.36, anchor="center", width=240, height=50)


# === ÇIKIŞ İŞLEMLERİ ===
def on_main_window_closing():
    if messagebox.askokcancel("Çıkış", "Akıllı Bahçe uygulamasından çıkmak istediğinize emin misiniz?", parent=window):
        print("Uygulama kapatılıyor, tüm saatlik görev yöneticisi durduruluyor...")
        if saatlik_yonetici_modulu and hasattr(saatlik_yonetici_modulu, 'stop_combined_hourly_tasks'):
            saatlik_yonetici_modulu.stop_combined_hourly_tasks()
        print("Ana uygulama kapatılıyor.")
        window.destroy()

window.protocol("WM_DELETE_WINDOW", on_main_window_closing)


if __name__ == '__main__':
    window.after(100, show_startup_errors_if_any)
    window.mainloop()
