import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Gönderici e-posta bilgileri
GMAIL_ADRESI = "mesutbulut305@gmail.com"
GMAIL_SIFRESI = "jsyyoryytwdpupgf"  # Normal şifre değil, özel uygulama şifresi kullanılmalı!

# Alıcı e-posta adresi
alicilar = ["mesut.2000.bulut@gmail.com"]

# SMTP sunucusuna bağlan
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(GMAIL_ADRESI, GMAIL_SIFRESI)

# E-posta içeriğini hazırla
msg = MIMEMultipart()
msg["From"] = GMAIL_ADRESI
msg["To"] = ", ".join(alicilar)
msg["Subject"] = "Python ile Mail Gönderme"
body = "Merhaba, bu e-posta Python ile gönderildi!"
msg.attach(MIMEText(body, "plain"))

# E-postayı gönder
server.sendmail(GMAIL_ADRESI, alicilar, msg.as_string())

# Sunucudan çıkış yap
server.quit()

print("E-posta başarıyla gönderildi!")
