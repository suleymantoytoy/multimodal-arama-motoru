# ============================================================
# Bu script, BLIP'ten BAGIMSIZ iki yeni test setiyle (kategori ve
# insan caption) uc yaklasimi (CLIP, BM25, Hibrit) olcer.
#
# Eski evaluate.py'ye DOKUNMUYORUZ: raporlanan ilk sonuclar
# (BLIP caption'li 50 sorgu) oldugu gibi tekrarlanabilir kalsin.
# Metrik fonksiyonlarini (precision/recall/mrr) eski dosyadan
# yeniden kullaniyoruz, boylece iki degerlendirme AYNI formullerle
# hesaplanir.
#
# k=5 kullaniyoruz (eski degerlendirmeyle ayni). Bu yuzden MRR de
# "ilk 5 icinde" hesaplanir (MRR@5): ilk dogru cevap 5. siranin
# disindaysa o sorgu icin 0 sayilir.
# ============================================================

# json: test setlerini okumak, sonuclari kaydetmek icin
import json
# os: dosya yolu islemleri icin
import os
# sys: Python modul arama yoluna klasor eklemek icin
import sys
# numpy: ortalama ve standart sapma hesabi icin
import numpy as np
# tqdm: terminalde ilerleme cubugu gostermek icin
from tqdm import tqdm

# search klasorunu Python yoluna ekle (hybrid_search'u import edebilmek icin)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Metrik fonksiyonlari eski evaluate.py'den: bu dosya "eval" klasorunden
# calistirildigi icin "evaluate" modulu dogrudan bulunur
from evaluate import precision_at_k, recall_at_k, mrr
# Katman gecisleri (Unsplash vb.) OLMADAN saf arama kalitesini olcmek icin
# alt arama fonksiyonlarini aliyoruz (eski degerlendirmedeki gibi)
from hybrid_search import _clip_ile_ara, _bm25_ile_ara, hibrit_ara

# Girdi test setleri (build_test_set_v2.py uretmisti)
KATEGORI_DOSYASI = "eval/test_kategori.json"
CAPTION_DOSYASI = "eval/test_insan_caption.json"
# Sonuclarin kaydedilecegi dosya (raporda kullanmak icin)
SONUC_DOSYASI = "eval/sonuclar_v2.json"

# Her sorgu icin kac sonuc getirilecek (eski degerlendirmeyle ayni)
K = 5


def gorsel_id(dosya_yolu):
    # Windows'taki "\" karakterini "/" yap
    temiz = dosya_yolu.replace("\\", "/")
    # Yoldan sadece dosya adini al
    dosya_adi = os.path.basename(temiz)
    # Uzantiyi at ve sayiya cevir: "000000000139.jpg" -> 139
    return int(os.path.splitext(dosya_adi)[0])


def idlere_cevir(dosya_listesi):
    # Bir dosya yolu listesini, gorsel ID listesine cevirir (sira korunur)
    return [gorsel_id(d) for d in dosya_listesi]


def uc_yontemle_ara(sorgu):
    # CLIP ve BM25 dogrudan dosya yolu listesi dondurur
    clip_sonuc = idlere_cevir(_clip_ile_ara(sorgu, k=K))
    bm25_sonuc = idlere_cevir(_bm25_ile_ara(sorgu, k=K))
    # hibrit_ara (dosya_yolu, skor) cifti dondurur: sadece dosya yollarini al
    hibrit_sonuc = idlere_cevir([dosya for dosya, skor in hibrit_ara(sorgu, k=K)])
    # Uc yaklasimin sonucunu bir sozlukte topla
    return {
        "Sadece CLIP": clip_sonuc,
        "Sadece BM25": bm25_sonuc,
        "Hibrit (RRF)": hibrit_sonuc,
    }


def ort_ve_hata(degerler):
    # Ortalama ve "standart hata" (SE): ortalamanin ne kadar oynak oldugunu
    # gosterir. Kucuk fark gordugumuzde, bunun tesadufi olup olmadigini
    # anlamamiza yardim eder.
    dizi = np.array(degerler, dtype=float)
    ortalama = dizi.mean()
    # ddof=1: ornek standart sapmasi; sqrt(n) ile bol -> standart hata
    hata = dizi.std(ddof=1) / np.sqrt(len(dizi))
    return float(ortalama), float(hata)


def kategori_setini_degerlendir():
    # Test setini oku
    with open(KATEGORI_DOSYASI, "r", encoding="utf-8") as f:
        test_seti = json.load(f)

    print(f"\n=== KATEGORI SETI: {len(test_seti)} kisa sorgu ===")
    # Her yaklasim icin Precision@5 listesi tutuyoruz
    precisionlar = {y: [] for y in ["Sadece CLIP", "Sadece BM25", "Hibrit (RRF)"]}
    # Rastgele secimle beklenen precision (taban deger), sorgu basina
    taban = []

    for kayit in tqdm(test_seti):
        # Dogru cevaplari ID'ye cevir (set: hizli "icinde mi" kontrolu)
        dogru = set(idlere_cevir(kayit["dogru_gorseller"]))
        taban.append(kayit["rastgele_precision"])
        # Uc yontemle ara
        sonuclar = uc_yontemle_ara(kayit["sorgu"])
        for yontem, getirilen in sonuclar.items():
            precisionlar[yontem].append(precision_at_k(getirilen, dogru, K))

    # Tabanin ortalamasi
    taban_ort = float(np.mean(taban))
    print(f"\nRastgele secimle beklenen Precision@5 (taban): {taban_ort:.4f}")
    print(f"{'Yaklasim':<14} | {'Precision@5':<20} | {'Tabana gore kat':<15}")
    print("-" * 56)

    ozet = {"taban_precision": taban_ort}
    for yontem, degerler in precisionlar.items():
        ort, hata = ort_ve_hata(degerler)
        print(f"{yontem:<14} | {ort:.4f} +/- {hata:.4f}   | {ort / taban_ort:>6.1f}x")
        ozet[yontem] = {"precision@5": ort, "se": hata}
    return ozet


def caption_setini_degerlendir():
    # Test setini oku
    with open(CAPTION_DOSYASI, "r", encoding="utf-8") as f:
        test_seti = json.load(f)

    print(f"\n=== INSAN CAPTION SETI: {len(test_seti)} sorgu ===")
    # Her yaklasim icin Recall@5 ve MRR listeleri
    recall_l = {y: [] for y in ["Sadece CLIP", "Sadece BM25", "Hibrit (RRF)"]}
    mrr_l = {y: [] for y in ["Sadece CLIP", "Sadece BM25", "Hibrit (RRF)"]}

    for kayit in tqdm(test_seti):
        # Tek dogru cevap var (kaynak gorsel)
        dogru = set(idlere_cevir(kayit["dogru_gorseller"]))
        sonuclar = uc_yontemle_ara(kayit["sorgu"])
        for yontem, getirilen in sonuclar.items():
            recall_l[yontem].append(recall_at_k(getirilen, dogru, K))
            mrr_l[yontem].append(mrr(getirilen, dogru))

    print(f"\n{'Yaklasim':<14} | {'Recall@5':<20} | {'MRR@5':<20}")
    print("-" * 60)
    ozet = {}
    for yontem in recall_l:
        r_ort, r_hata = ort_ve_hata(recall_l[yontem])
        m_ort, m_hata = ort_ve_hata(mrr_l[yontem])
        print(f"{yontem:<14} | {r_ort:.4f} +/- {r_hata:.4f}   | {m_ort:.4f} +/- {m_hata:.4f}")
        ozet[yontem] = {"recall@5": r_ort, "recall_se": r_hata,
                        "mrr@5": m_ort, "mrr_se": m_hata}
    return ozet


def calistir():
    # Iki seti sirayla degerlendir
    kategori_ozet = kategori_setini_degerlendir()
    caption_ozet = caption_setini_degerlendir()

    # Sonuclari JSON olarak kaydet (eval_raporu.md'yi yazarken kullanacagiz)
    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"kategori": kategori_ozet, "insan_caption": caption_ozet},
                  f, ensure_ascii=False, indent=2)
    print(f"\nSonuclar kaydedildi: {SONUC_DOSYASI}")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()