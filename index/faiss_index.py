# ============================================================
# Bu dosya, FAISS kutuphanesini kullanarak 3 FARKLI index tipi
# kurar. Amac: hangi index tipinin bizim veri boyutumuz (5.000
# gorsel) icin en iyi hiz/dogruluk dengesini verdigini olcmek.
#
# Ucu de ayni islevi gorur ("en yakin vektorleri bul") ama farkli
# yontemlerle:
#
# 1. FLAT   -> "Kaba kuvvet". Sorgu vektorunu, TUM 5.000 vektorle
#              tek tek karsilastirir. En yavas ama %100 dogru -
#              bunu "dogru cevap" referansi olarak kullanacagiz.
#
# 2. IVF    -> "Inverted File Index". Once tum vektorleri gruplara
#              (kumelere) ayirir, sorgu geldiginde sadece en yakin
#              birkac grubun icinde arama yapar. Cok daha hizli
#              ama YAKLASIK sonuc verir (en iyi sonucu kacirabilir).
#
# 3. HNSW   -> "Hierarchical Navigable Small World". Vektorler
#              arasinda bir "graf" (agac benzeri baglanti yapisi)
#              kurar, aramayi bu graf uzerinde gezerek yapar.
#              Genelde IVF'den daha dogru, Flat'ten daha hizlidir -
#              hiz/dogruluk dengesi en iyi olan tip genelde budur.
# ============================================================

import faiss
import numpy as np
import json
import time

EMBEDDING_DOSYASI = "data/full_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/full_image_paths.json"


def index_kur(embedding_matrisi):
    """
    Ayni embedding matrisinden UC farkli index kurar ve hepsini
    bir sozlukte (dictionary) dondurur.
    """
    boyut = embedding_matrisi.shape[1]  # 512 (her vektorun uzunlugu)
    n = embedding_matrisi.shape[0]  # 5000 (kac vektor oldugu)

    # ------------------------------------------------------------
    # 1. FLAT INDEX
    # IndexFlatIP: "IP" = Inner Product (ic carpim). Vektorler
    # normalize edilmis oldugu icin bu, cosine similarity'ye esdeger.
    # ------------------------------------------------------------
    flat_index = faiss.IndexFlatIP(boyut)
    flat_index.add(embedding_matrisi)  # tum vektorleri index'e ekle

    # ------------------------------------------------------------
    # 2. IVF INDEX
    # nlist: veriyi kac "kumeye" bolecegimiz. Genel kural: veri
    # sayisinin karekoku civari iyi bir baslangic. 5000'in karekoku
    # ~70, biz yuvarlak bir sayi olan 50 kullanacagiz.
    #
    # IVF'nin, kullanilmadan once "egitilmesi" (train) gerekir -
    # bu, veriye bakarak kumelerin nasil olusturulacagina karar verme
    # islemidir.
    # ------------------------------------------------------------
    nlist = 50
    quantizer = faiss.IndexFlatIP(boyut)  # IVF'nin ic mekanizmasi icin bir "olcum" index'i
    ivf_index = faiss.IndexIVFFlat(quantizer, boyut, nlist, faiss.METRIC_INNER_PRODUCT)
    ivf_index.train(embedding_matrisi)  # kumeleri olustur
    ivf_index.add(embedding_matrisi)  # vektorleri ekle

    # ------------------------------------------------------------
    # 3. HNSW INDEX
    # M: her vektorun graf icinde kac komsuya baglanacagi. Yuksek M
    # = daha dogru ama daha fazla bellek/yavas kurulum. 32 yaygin
    # bir varsayilan deger.
    # ------------------------------------------------------------
    M = 32
    hnsw_index = faiss.IndexHNSWFlat(boyut, M, faiss.METRIC_INNER_PRODUCT)
    hnsw_index.add(embedding_matrisi)

    return {
        "flat": flat_index,
        "ivf": ivf_index,
        "hnsw": hnsw_index,
    }


def index_kaydet(index_sozlugu):
    """Her index'i ayri bir dosyaya diske yazar."""
    for isim, index in index_sozlugu.items():
        faiss.write_index(index, f"index/{isim}_index.faiss")
    print("Tum index'ler diske kaydedildi (index/ klasorunde).")


if __name__ == "__main__":
    print("Embedding'ler yukleniyor...")
    embedding_matrisi = np.load(EMBEDDING_DOSYASI)
    print(f"Yuklendi: {embedding_matrisi.shape}")

    print("\n3 farkli index kuruluyor (Flat, IVF, HNSW)...")
    baslangic = time.time()
    index_sozlugu = index_kur(embedding_matrisi)
    print(f"Kurulum suresi: {time.time() - baslangic:.2f} saniye")

    index_kaydet(index_sozlugu)