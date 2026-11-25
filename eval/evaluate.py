# ============================================================
# Bu script, Faz 4'un kalbidir. 50 sorguluk test setimizi
# kullanarak uc farkli yaklasimin (CLIP, BM25, Hibrit)
# basarisini bilimsel metriklerle olcer.
#
# METRIKLER:
# 1. Precision@k: Getirilen ilk k sonucun kaci gercekten dogru?
# 2. Recall@k: Gercekten dogru olan tum sonuclarin kacini
#    ilk k icinde yakalayabildik?
# 3. MRR (Mean Reciprocal Rank): Ilk dogru cevabi kacinci
#    sirada bulduk? (1. siradaysa puan 1, 2. siradaysa 0.5 vb.)
# ============================================================

import json
import os
import sys
import numpy as np
from tqdm import tqdm

# hybrid_search icindeki arama fonksiyonlarini cagirabilmek icin 
# search klasorunu Python yoluna ekliyoruz.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Katman gecisleri (Unsplash vb.) olmadan saf arama kalitesini
# olcmek icin akilli_ara'yi degil, alt arama fonksiyonlarini aliyoruz.
from hybrid_search import _clip_ile_ara, _bm25_ile_ara, hibrit_ara

TEST_SETI_DOSYASI = "eval/test_sorgular.json"

def precision_at_k(getirilen, dogru, k):
    getirilen_k = getirilen[:k]
    ortusenler = set(getirilen_k) & set(dogru)
    return len(ortusenler) / k

def recall_at_k(getirilen, dogru, k):
    getirilen_k = getirilen[:k]
    ortusenler = set(getirilen_k) & set(dogru)
    # Eger veri setinde o sorgu icin hic dogru cevap yoksa 0'a bolme hatasini onle
    if len(dogru) == 0:
        return 0.0
    return len(ortusenler) / len(dogru)

def mrr(getirilen, dogru):
    for sira, sonuc in enumerate(getirilen, start=1):
        if sonuc in dogru:
            return 1.0 / sira
    return 0.0

def degerlendir():
    with open(TEST_SETI_DOSYASI, "r", encoding="utf-8") as f:
        test_seti = json.load(f)

    print(f"{len(test_seti)} sorgu icin degerlendirme basliyor (Her sorgu 3 kez islenecek)...\n")

    metrikler = {
        "Sadece CLIP": {"p@5": [], "r@5": [], "mrr": []},
        "Sadece BM25": {"p@5": [], "r@5": [], "mrr": []},
        "Hibrit (RRF)": {"p@5": [], "r@5": [], "mrr": []}
    }

    k = 5

    # tqdm ile ilerlemeyi terminalde gorsel olarak takip ediyoruz
    for kayit in tqdm(test_seti):
        sorgu = kayit["sorgu"]
        dogru_cevaplar = kayit["dogru_gorseller"]

        # Arama sonuclarini al
        clip_sonuclar = _clip_ile_ara(sorgu, k=k)
        bm25_sonuclar = _bm25_ile_ara(sorgu, k=k)
        
        # hibrit_ara (dosya_yolu, skor) cifti dondugu icin sadece dosya yollarini ayikliyoruz
        hibrit_ham = hibrit_ara(sorgu, k=k)
        hibrit_sonuclar = [dosya for dosya, skor in hibrit_ham]

        # 1. CLIP Metrikleri
        metrikler["Sadece CLIP"]["p@5"].append(precision_at_k(clip_sonuclar, dogru_cevaplar, k))
        metrikler["Sadece CLIP"]["r@5"].append(recall_at_k(clip_sonuclar, dogru_cevaplar, k))
        metrikler["Sadece CLIP"]["mrr"].append(mrr(clip_sonuclar, dogru_cevaplar))

        # 2. BM25 Metrikleri
        metrikler["Sadece BM25"]["p@5"].append(precision_at_k(bm25_sonuclar, dogru_cevaplar, k))
        metrikler["Sadece BM25"]["r@5"].append(recall_at_k(bm25_sonuclar, dogru_cevaplar, k))
        metrikler["Sadece BM25"]["mrr"].append(mrr(bm25_sonuclar, dogru_cevaplar))

        # 3. Hibrit Metrikleri
        metrikler["Hibrit (RRF)"]["p@5"].append(precision_at_k(hibrit_sonuclar, dogru_cevaplar, k))
        metrikler["Hibrit (RRF)"]["r@5"].append(recall_at_k(hibrit_sonuclar, dogru_cevaplar, k))
        metrikler["Hibrit (RRF)"]["mrr"].append(mrr(hibrit_sonuclar, dogru_cevaplar))

    # Sonuclari okunakli bir tablo halinde konsola yazdir
    print("\n\n--- DEGERLENDIRME SONUCLARI (k=5) ---")
    print(f"{'Yaklasim':<15} | {'Precision@5':<12} | {'Recall@5':<10} | {'MRR':<10}")
    print("-" * 55)

    for yaklasim, degerler in metrikler.items():
        ort_p = np.mean(degerler["p@5"])
        ort_r = np.mean(degerler["r@5"])
        ort_mrr = np.mean(degerler["mrr"])
        print(f"{yaklasim:<15} | {ort_p:<12.4f} | {ort_r:<10.4f} | {ort_mrr:<10.4f}")

if __name__ == "__main__":
    degerlendir()