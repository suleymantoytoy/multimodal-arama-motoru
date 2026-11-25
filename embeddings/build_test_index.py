# ============================================================
# Bu script, data/raw_images klasorundeki BIRDEN FAZLA gorseli
# tek tek CLIP'ten gecirip, hepsinin vektorunu tek bir buyuk
# tabloda (numpy array) toplar ve diske kaydeder.
#
# Neden diske kaydediyoruz? Cunku CLIP ile embedding cikarmak
# yavas bir islem - her arama yaptigimizda TUM gorselleri yeniden
# islemek yerine, bir kere isleyip sonucu saklayacagiz, arama
# yaparken sadece bu kayitli dosyayi okuyacagiz.
# ============================================================

import os
import json
import numpy as np
from tqdm import tqdm  # ilerleme cubugu gostermek icin (kac gorsel islendi gibi)

# Az once yazdigimiz clip_encoder.py dosyasindaki fonksiyonu buraya cagiriyoruz.
from clip_encoder import encode_image

GORSEL_KLASORU = "data/raw_images"
# Test asamasinda TUM veri setini degil, ilk 300 gorseli kullanacagiz.
# Boylece islem hizli biter, mekanizmayi dogruladiktan sonra Faz 2'de
# TUM veri setine (5.000+) genisletecegiz.
MAKS_GORSEL_SAYISI = 300

# Kayit edecegimiz dosyalarin isimleri
EMBEDDING_DOSYASI = "data/test_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/test_image_paths.json"


def calistir():
    # Klasordeki tum .jpg dosyalarini bul, ilk MAKS_GORSEL_SAYISI kadarini al.
    tum_dosyalar = [f for f in os.listdir(GORSEL_KLASORU) if f.endswith(".jpg")]
    secilen_dosyalar = tum_dosyalar[:MAKS_GORSEL_SAYISI]

    print(f"{len(secilen_dosyalar)} gorsel islenecek...")

    # Her gorselin embedding'ini bu listede toplayacagiz.
    tum_embeddingler = []
    # Her embedding'in HANGI dosyaya ait oldugunu unutmamak icin
    # dosya yollarini da ayni sirada bir listede tutuyoruz.
    tum_yollar = []

    # tqdm(), for dongusunu bir ilerleme cubugu ile sarmalar -
    # terminalde "kac tanesi bitti" gorebilmemizi saglar.
    for dosya_adi in tqdm(secilen_dosyalar):
        tam_yol = os.path.join(GORSEL_KLASORU, dosya_adi)
        try:
            vektor = encode_image(tam_yol)
            tum_embeddingler.append(vektor)
            tum_yollar.append(tam_yol)
        except Exception as hata:
            # Bazi gorseller bozuk/okunamaz olabilir - programi durdurmak
            # yerine o gorseli atlayip devam ediyoruz, hangi dosyada
            # sorun oldugunu ekrana yazdiriyoruz.
            print(f"HATA ({dosya_adi}): {hata}")

    # Liste halindeki embeddingleri tek bir numpy array'e ceviriyoruz.
    # Sonuc: (300, 512) boyutunda bir tablo - 300 satir (gorsel),
    # her satirda 512 sayi (o gorselin vektoru).
    embedding_matrisi = np.array(tum_embeddingler)

    # Diske kaydediyoruz.
    np.save(EMBEDDING_DOSYASI, embedding_matrisi)
    with open(YOL_LISTESI_DOSYASI, "w") as f:
        json.dump(tum_yollar, f)

    print(f"Bitti! {embedding_matrisi.shape} boyutunda bir matris kaydedildi.")
    print(f"Kaydedilen dosyalar: {EMBEDDING_DOSYASI}, {YOL_LISTESI_DOSYASI}")


# Bu dosya dogrudan calistirildiginda calistir() fonksiyonunu cagir.
if __name__ == "__main__":
    calistir()