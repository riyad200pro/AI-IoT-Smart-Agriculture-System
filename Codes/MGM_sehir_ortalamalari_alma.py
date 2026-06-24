# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 15:29:22 2025

@author: mesutbulut
"""

import pandas as pd

# Veriyi oku (örneğin 'veri.xlsx' dosyasından)
# Eğer veriniz .txt ise, pd.read_csv('dosya.txt', sep='\t', header=None) kullanabilirsiniz.
df = pd.read_excel('Yagis_Output_Data.xlsx', header=None)  # Başlık yoksa header=None ekleyin

# Sütun isimlerini belirle (örneğin: Şehir, Sütun1, Sütun2, ..., Sütun12)
df.columns = ['Şehir'] + [f'Sütun_{i}' for i in range(1, 13)]

# Şehirlere göre grupla ve her sütunun ortalamasını al
ortalama_df = df.groupby('Şehir').mean().reset_index()

# Yeni bir Excel dosyasına kaydet
ortalama_df.to_excel('Yagis_sehir_ortalamalari.xlsx', index=False)

print("Ortalamalar başarıyla 'sehir_ortalamalari.xlsx' dosyasına kaydedildi!")