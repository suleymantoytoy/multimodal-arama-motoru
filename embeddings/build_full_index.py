# ============================================================
# Bu script, data/raw_images klasorundeki TUM gorselleri (5.000
# tane) CLIP'ten gecirip embedding'lerini cikarir ve diske kaydeder.
#
# ONCEKI VERSIYONDAN FARKI: Artik gorselleri TEK TEK degil, encode_
# images_batch() fonksiyonuyla GRUPLAR HALINDE (batch_size=32)
# isliyoruz - bu, ozellikle GPU'da ama CPU'da da belirgin bir hiz
# kazanci saglar. Ayrica islemin TOPLAM SURESINI de olcup ekrana
# yazdiriyoruz - bu sayi, Faz 6'daki README'de "5.000 gorsel icin
# embedding cikarma X dakika surdu" seklinde somut bir veri olarak
# kullanilacak.
# ============================================================

import os
import json
import time
import numpy as np

from clip_encoder import encode_images_batch

GORSEL_KLASORU = "data/raw_images"

EMBEDDING_DOSYASI = "data/full_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/full_image_paths.json"

# Her seferde kac gorselin AYNI ANDA islenecegi. 32, CPU/GPU
# bellek kullanimi ile hiz arasinda dengeli bir tercih - cok
# buyutursen (orn. 256) bellek yetersiz kalabilir, cok kucultursen
# (orn. 4) batch'in hiz avantaji azalir.
BATCH_SIZE = 32


def calistir():
    # os.listdir(): klasordeki TUM dosya/klasor isimlerini bir liste
    # olarak doner. endswith(".jpg") ile sadece .jpg uzantili
    # dosyalari filtreliyoruz (baska dosya turu varsa almiyoruz).
    tum_dosyalar = [f for f in os.listdir(GORSEL_KLASORU) if f.endswith(".jpg")]

    # Sadece dosya isimlerini degil, TAM YOLLARI (klasor + dosya adi)
    # olusturuyoruz - encode_images_batch() fonksiyonu tam yol bekliyor.
    tum_yollar = [os.path.join(GORSEL_KLASORU, f) for f in tum_dosyalar]

    print(f"{len(tum_yollar)} gorsel islenecek (batch_size={BATCH_SIZE})...")

    # time.time(): programin o anki calisma zamanini (saniye cinsinden,
    # bir referans noktasina gore) verir. Islem oncesi ve sonrasi bu
    # degeri alip farkini hesaplayarak, islemin ne kadar surdugunu
    # olcebiliyoruz.
    baslangic_zamani = time.time()

    # ISTE ANA ISLEM: tum gorselleri batch batch isleyip, hem
    # embedding matrisini hem de basariyla islenen dosyalarin
    # yollarini geri aliyoruz.
    embedding_matrisi, basarili_yollar = encode_images_batch(
        tum_yollar, batch_size=BATCH_SIZE
    )

    gecen_sure_saniye = time.time() - baslangic_zamani

    # Diske kaydediyoruz - onceki versiyonla ayni mantik.
    np.save(EMBEDDING_DOSYASI, embedding_matrisi)
    with open(YOL_LISTESI_DOSYASI, "w") as f:
        json.dump(basarili_yollar, f)

    # ------------------------------------------------------------
    # SURE RAPORU: Bu kisim yeni. Toplam sureyi hem saniye hem
    # dakika cinsinden, hem de "gorsel basina ortalama sure" olarak
    # yazdiriyoruz - Faz 6'daki README'de kullanmak icin.
    # ------------------------------------------------------------
    dakika = gecen_sure_saniye / 60
    gorsel_basina_ms = (gecen_sure_saniye / len(basarili_yollar)) * 1000

    print(f"\nBitti! {embedding_matrisi.shape} boyutunda bir matris kaydedildi.")
    print(f"Kaydedilen dosyalar: {EMBEDDING_DOSYASI}, {YOL_LISTESI_DOSYASI}")
    print(f"\n--- SURE RAPORU ---")
    print(f"Toplam sure: {gecen_sure_saniye:.1f} saniye ({dakika:.2f} dakika)")
    print(f"Gorsel basina ortalama: {gorsel_basina_ms:.2f} ms")
    print(f"Islenen gorsel sayisi: {len(basarili_yollar)} / {len(tum_yollar)}")


if __name__ == "__main__":
    calistir()