# ============================================================
# Bu script, evaluate_v2.py'nin bulgularini ESLEMELI BOOTSTRAP ile
# test eder. Soru: "Hibrit ile CLIP (veya BM25) arasindaki fark
# GERCEK mi, yoksa 77/200 sorgunun sansindan mi?"
#
# Yontem: her sorgu icin iki yontemin skor FARKI hesaplanir. Sonra
# sorgular yerine koyarak 10.000 kez yeniden cekilir, her cekilista
# ortalama fark alinir. Bu 10.000 ortalamanin %2,5 - %97,5
# yuzdelikleri %95 guven araligini verir. Aralik 0'i ICERMIYORSA
# fark buyuk olasilikla gercektir.
#
# "Eslemeli": ayni sorgu uzerindeki iki skor birlikte alindigi icin,
# iki yontemin BIRLIKTE zorlandigi sorgular farki bozmaz. Bagimsiz
# standart hata hesabindan daha hassastir.
# ============================================================

# json: test setlerini okumak, sorgu bazli sonuclari kaydetmek icin
import json
# numpy: dizi islemleri ve rastgele ornekleme icin
import numpy as np
# tqdm: terminalde ilerleme cubugu gostermek icin
from tqdm import tqdm

# evaluate_v2'den ortak parcalari yeniden kullaniyoruz: ayni dosya
# yollari, ayni K, ayni arama sarmalayicisi. (Bu import ayni zamanda
# search klasorunu Python yoluna ekler ve arama index'lerini yukler.)
from evaluate_v2 import (
    KATEGORI_DOSYASI, CAPTION_DOSYASI, K, idlere_cevir, uc_yontemle_ara,
)
# Metrik fonksiyonlari: evaluate_v2 ile AYNI formuller
from evaluate import precision_at_k, recall_at_k, mrr

# Sorgu bazli skorlarin kaydedilecegi dosya (sonraki adimda lazim olacak)
SORGU_BAZLI_DOSYA = "eval/sorgu_bazli_v2.json"

# Bootstrap tekrar sayisi ve tekrarlanabilirlik icin seed
BOOTSTRAP_TEKRAR = 10000
SEED = 42

# Uc yontemin adlari (evaluate_v2'deki ile ayni)
YONTEMLER = ["Sadece CLIP", "Sadece BM25", "Hibrit (RRF)"]


def sorgu_bazli_hesapla(test_seti, metrik_fonksiyonlari):
    # Cikti: {metrik_adi: {yontem: [her sorgu icin skor, ...]}}
    sonuc = {m: {y: [] for y in YONTEMLER} for m in metrik_fonksiyonlari}

    for kayit in tqdm(test_seti):
        # Dogru cevaplari ID'ye cevir (set: hizli "icinde mi" kontrolu)
        dogru = set(idlere_cevir(kayit["dogru_gorseller"]))
        # Uc yontemle ara
        aramalar = uc_yontemle_ara(kayit["sorgu"])
        for yontem, getirilen in aramalar.items():
            for metrik_adi, fonksiyon in metrik_fonksiyonlari.items():
                # Bu sorgunun bu yontemdeki bu metrik skorunu ekle
                sonuc[metrik_adi][yontem].append(fonksiyon(getirilen, dogru))

    # Listeleri numpy dizisine cevir (matematik islemleri icin)
    return {m: {y: np.array(v) for y, v in d.items()} for m, d in sonuc.items()}


def eslemeli_bootstrap(a, b):
    # Sorgu bazli fark: pozitifse "a" yontemi o sorguda daha iyi
    fark = a - b
    n = len(fark)
    # Sabit seed'li uretec: sonuc her calistirmada ayni cikar
    rng = np.random.default_rng(SEED)
    # (10000 x n) boyutunda rastgele sorgu indeksleri, YERINE KOYARAK
    indeksler = rng.integers(0, n, size=(BOOTSTRAP_TEKRAR, n))
    # Her cekilis icin ortalama fark (10000 tane ortalama)
    ortalamalar = fark[indeksler].mean(axis=1)
    # %95 guven araligi: %2,5 ve %97,5 yuzdelikleri
    alt, ust = np.percentile(ortalamalar, [2.5, 97.5])
    return float(fark.mean()), float(alt), float(ust)


def karsilastirma_yazdir(baslik, metrikler):
    print(f"\n=== {baslik} ===")
    # Kontrol: ortalamalar evaluate_v2'deki degerlerle AYNI olmali
    for metrik_adi, yontem_skorlari in metrikler.items():
        ozet = ", ".join(f"{y}={yontem_skorlari[y].mean():.4f}" for y in YONTEMLER)
        print(f"[kontrol] {metrik_adi} ortalamalari: {ozet}")

    print(f"\n{'Metrik':<9} | {'Karsilastirma':<22} | {'Ort. fark':<9} | "
          f"{'%95 guven araligi':<20} | Sonuc")
    print("-" * 85)
    # Iki karsilastirma: hibrit-CLIP ve hibrit-BM25
    ciftler = [("Hibrit (RRF)", "Sadece CLIP"), ("Hibrit (RRF)", "Sadece BM25")]
    for metrik_adi, yontem_skorlari in metrikler.items():
        for ilk, ikinci in ciftler:
            ort, alt, ust = eslemeli_bootstrap(yontem_skorlari[ilk], yontem_skorlari[ikinci])
            # Aralik 0'i icermiyorsa (ikisi de ayni isaretliyse) fark "gercek"
            if alt > 0:
                sonuc = f"{ilk.split()[0]} DAHA IYI (gercek)"
            elif ust < 0:
                sonuc = f"{ilk.split()[0]} DAHA KOTU (gercek)"
            else:
                sonuc = "AYIRT EDILEMIYOR"
            etiket = f"{ilk.split()[0]} - {ikinci.split()[-1]}"
            print(f"{metrik_adi:<9} | {etiket:<22} | {ort:+.4f}   | "
                  f"[{alt:+.4f}, {ust:+.4f}]  | {sonuc}")


def calistir():
    # --- Kategori seti ---
    with open(KATEGORI_DOSYASI, "r", encoding="utf-8") as f:
        kategori_seti = json.load(f)
    print("Kategori seti hesaplaniyor...")
    kategori_skorlari = sorgu_bazli_hesapla(
        kategori_seti, {"P@5": lambda g, d: precision_at_k(g, d, K)}
    )

    # --- Insan caption seti ---
    with open(CAPTION_DOSYASI, "r", encoding="utf-8") as f:
        caption_seti = json.load(f)
    print("Insan caption seti hesaplaniyor...")
    caption_skorlari = sorgu_bazli_hesapla(
        caption_seti,
        {"Recall@5": lambda g, d: recall_at_k(g, d, K),
         "MRR@5": mrr},
    )

    # Sonuclari yazdir
    karsilastirma_yazdir("KATEGORI SETI (77 sorgu)", kategori_skorlari)
    karsilastirma_yazdir("INSAN CAPTION SETI (200 sorgu)", caption_skorlari)

    # Sorgu bazli skorlari kaydet (sonraki adimda agirlikli RRF icin lazim)
    kayit = {
        "kategori": {
            "sorgular": [k["sorgu"] for k in kategori_seti],
            "skorlar": {m: {y: v.tolist() for y, v in d.items()}
                        for m, d in kategori_skorlari.items()},
        },
        "insan_caption": {
            "sorgular": [k["sorgu"] for k in caption_seti],
            "skorlar": {m: {y: v.tolist() for y, v in d.items()}
                        for m, d in caption_skorlari.items()},
        },
    }
    with open(SORGU_BAZLI_DOSYA, "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=2)
    print(f"\nSorgu bazli skorlar kaydedildi: {SORGU_BAZLI_DOSYA}")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()