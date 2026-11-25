# ============================================================
# Bu script, az once diske kaydettigimiz embedding'leri okuyup,
# bir metin sorgusu alip, o sorguya en "yakin" (en benzer) gorselleri
# bulan bir arama fonksiyonu icerir.
#
# Henuz FAISS kullanmiyoruz - sadece numpy ile matematiksel olarak
# "hangi gorsel vektoru, sorgu vektorune en yakin" hesabini yapiyoruz.
# ============================================================

import json
import numpy as np
from clip_encoder import encode_text

EMBEDDING_DOSYASI = "data/test_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/test_image_paths.json"


def sorgu_ara(sorgu_metni, k=5):
    """
    sorgu_metni: aranacak metin (orn. "a red car")
    k: kac tane sonuc dondurulecek (varsayilan 5)
    """
    # Daha once kaydettigimiz embedding matrisini ve dosya yollarini geri yukluyoruz.
    embedding_matrisi = np.load(EMBEDDING_DOSYASI)  # (300, 512) boyutunda
    with open(YOL_LISTESI_DOSYASI, "r") as f:
        image_paths = json.load(f)

    # Sorgu metnini de ayni 512 boyutlu vektor uzayina ceviriyoruz.
    sorgu_vektoru = encode_text(sorgu_metni)  # (512,) boyutunda

    # ============================================================
    # ISTE ISIN KALBI: Cosine Similarity Hesabi
    #
    # embedding_matrisi: (300, 512)  -> 300 gorsel, her biri 512 sayidan olusuyor
    # sorgu_vektoru:      (512,)     -> 1 sorgu, 512 sayidan olusuyor
    #
    # embedding_matrisi @ sorgu_vektoru -> matris carpimi.
    # Bu islem, HER gorsel vektoru ile sorgu vektoru arasinda "ic carpim"
    # (dot product) hesaplar ve sonucta (300,) boyutunda bir liste doner -
    # yani her gorsel icin TEK BIR benzerlik skoru.
    #
    # Neden bu bir "cosine similarity" oluyor? Cunku clip_encoder.py'de
    # her iki vektoru de L2 normalize etmistik (uzunluklarini 1 yapmistik).
    # Uzunlugu 1 olan iki vektorun ic carpimi = aralarindaki acinin kosinusu
    # = cosine similarity. Normalize etmeseydik bu formul GECERSIZ olurdu.
    #
    # Skor -1 ile 1 arasinda olur: 1'e yakinsa "cok benzer",
    # 0'a yakinsa "alakasiz", -1'e yakinsa "zit anlamli" (CLIP'te nadir gorulur).
    # ============================================================
    benzerlik_skorlari = embedding_matrisi @ sorgu_vektoru

    # np.argsort(): skorlari KUCUKTEN BUYUGE siralar, ama biz index (sira
    # numarasi) istiyoruz, deger degil. [::-1] ile ters ceviriyoruz ki
    # BUYUKTEN KUCUGE olsun (en benzer en basta olsun).
    # [:k] ile sadece ilk k taneyi aliyoruz.
    en_iyi_indeksler = np.argsort(benzerlik_skorlari)[::-1][:k]

    print(f"\n'{sorgu_metni}' icin en iyi {k} sonuc:\n")
    for sira, indeks in enumerate(en_iyi_indeksler, start=1):
        dosya_yolu = image_paths[indeks]
        skor = benzerlik_skorlari[indeks]
        print(f"{sira}. {dosya_yolu}  (benzerlik skoru: {skor:.3f})")


# Bu dosya dogrudan calistirildiginda birkac ornek sorgu ile test ediyoruz.
if __name__ == "__main__":
    # matplotlib: Python'da grafik/gorsel gostermek icin kullanilan kutuphane.
    # Burada sonuc olarak gelen gorselleri ekranda gostermek icin kullanacagiz.
    import matplotlib.pyplot as plt
    from PIL import Image

    def sorgu_ara_ve_goster(sorgu_metni, k=5):
        # Once, az once yazdigimiz sorgu_ara fonksiyonunun ic mantigini
        # tekrar kullanmak yerine, onu biraz degistirip sonuc listesini
        # DONDUREN bir versiyonunu burada tekrar yaziyoruz (kucuk bir tekrar,
        # ama gorsellestirme icin pratik).
        embedding_matrisi = np.load(EMBEDDING_DOSYASI)
        with open(YOL_LISTESI_DOSYASI, "r") as f:
            image_paths = json.load(f)

        sorgu_vektoru = encode_text(sorgu_metni)
        benzerlik_skorlari = embedding_matrisi @ sorgu_vektoru
        en_iyi_indeksler = np.argsort(benzerlik_skorlari)[::-1][:k]

        # plt.subplots(1, k): yan yana k tane kucuk resim kutusu (panel) olustur.
        # figsize: pencerenin genisligini/yuksekligini ayarlar (inc cinsinden).
        fig, eksenler = plt.subplots(1, k, figsize=(4 * k, 4))
        fig.suptitle(f"Sorgu: '{sorgu_metni}'", fontsize=16)

        for sira, indeks in enumerate(en_iyi_indeksler):
            dosya_yolu = image_paths[indeks]
            skor = benzerlik_skorlari[indeks]

            # Gorseli ac ve o panelin icine yerlestir.
            gorsel = Image.open(dosya_yolu)
            eksenler[sira].imshow(gorsel)
            eksenler[sira].set_title(f"#{sira+1}\nskor: {skor:.3f}", fontsize=10)
            eksenler[sira].axis("off")  # eksen cizgilerini/sayilarini gizle, sadece resim gorunsun

        plt.tight_layout()
        # Ekranda bir pencere acip gorselleri gosterir. Pencereyi kapatinca
        # kod bir sonraki sorguya gecer.
        plt.show()

    sorgu_ara_ve_goster("a dog")
    sorgu_ara_ve_goster("food on a table")