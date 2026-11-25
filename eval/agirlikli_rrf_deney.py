# ============================================================
# Bu script, "BM25'e dusuk agirlik verirsek hibrit CLIP'e yetisir
# mi?" sorusunu OLCER.
#
# ON-KAYITLI KURALLAR (sonuclari gormeden belirlendi):
#   1. Agirlik SADECE dev setinde (500 sorgu) secilir.
#   2. Secim olcutu: dev MRR@5 en yuksek olan BM25 agirligi.
#      Esitlikte KUCUK agirlik.
#   3. Secilen agirlik test setlerinde BIR KEZ olculur. Izgara
#      test sonucuna bakilarak DEGISTIRILMEZ.
#
# CLIP agirligi 1.0'da sabit; sadece BM25 agirligi degisir.
# RRF'nin k=60 sabiti ve aday havuzu (20) oynatilmaz.
# ============================================================

# json: test/dev setlerini okumak, sonuclari kaydetmek icin
import json
# numpy: dizi islemleri icin
import numpy as np
# tqdm: ilerleme cubugu icin
from tqdm import tqdm

# evaluate_v2'den ortak parcalar (bu import arama index'lerini de yukler
# ve search klasorunu Python yoluna ekler)
from evaluate_v2 import K, idlere_cevir, ort_ve_hata, KATEGORI_DOSYASI, CAPTION_DOSYASI
# Metrik fonksiyonlari: onceki degerlendirmelerle AYNI formuller
from evaluate import precision_at_k, recall_at_k, mrr
# Eslemeli bootstrap: bootstrap_v2'deki ayni fonksiyon
from bootstrap_v2 import eslemeli_bootstrap
# Ham arama fonksiyonlari ve RRF (yeni agirlik parametresiyle)
from hybrid_search import _clip_ile_ara, _bm25_ile_ara
from rerank import reciprocal_rank_fusion

# Dosya yollari
DEV_DOSYASI = "eval/dev_insan_caption.json"
SONUC_DOSYASI = "eval/sonuclar_agirlikli_rrf.json"

# Denenecek BM25 agirliklari (kucukten buyuge SIRALI olmali: esitlikte
# kucuk agirligi secme kurali buna dayaniyor)
AGIRLIKLAR = [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]
# Her yontemden alinacak aday sayisi (hibrit_ara ile AYNI: 20)
HAVUZ_K = 20


def recall_metrik(getirilen, dogru):
    # Recall@5: eski degerlendirmeyle ayni fonksiyon ve ayni K
    return recall_at_k(getirilen, dogru, K)


def precision_metrik(getirilen, dogru):
    # Precision@5: kategori seti icin
    return precision_at_k(getirilen, dogru, K)


def aday_havuzu(test_seti):
    # Her sorgu icin CLIP ve BM25'in ilk 20'sini BIR KEZ alip saklariz;
    # agirliklari degistirirken aramayi tekrar calistirmaya gerek kalmaz
    havuz = []
    for kayit in tqdm(test_seti):
        sorgu = kayit["sorgu"]
        havuz.append({
            "clip": idlere_cevir(_clip_ile_ara(sorgu, k=HAVUZ_K)),
            "bm25": idlere_cevir(_bm25_ile_ara(sorgu, k=HAVUZ_K)),
            # Dogru cevaplar (set: hizli "icinde mi" kontrolu)
            "dogru": set(idlere_cevir(kayit["dogru_gorseller"])),
        })
    return havuz


def birlestir(aday, bm25_agirlik):
    # CLIP agirligi 1.0, BM25 agirligi parametre
    birlesik = reciprocal_rank_fusion(
        [aday["clip"], aday["bm25"]], agirliklar=[1.0, bm25_agirlik]
    )
    # hibrit_ara gibi ilk K sonucu al (sadece kimlikleri)
    return [kimlik for kimlik, skor in birlesik[:K]]


def skorlar(havuz, bm25_agirlik, metrik):
    # Her sorgu icin metrik skoru, numpy dizisi olarak (sorgu sirasi korunur)
    return np.array([
        metrik(birlestir(a, bm25_agirlik), a["dogru"]) for a in havuz
    ])


def dev_ile_agirlik_sec():
    # Dev setini oku ve aday havuzunu olustur
    with open(DEV_DOSYASI, "r", encoding="utf-8") as f:
        dev_seti = json.load(f)
    print(f"Dev seti: {len(dev_seti)} sorgu icin adaylar toplaniyor...")
    havuz = aday_havuzu(dev_seti)

    print("\n--- DEV SONUCLARI (agirlik secimi) ---")
    print(f"{'BM25 agirligi':<14} | {'Recall@5':<19} | {'MRR@5':<19}")
    print("-" * 56)

    tablo = []
    for w in AGIRLIKLAR:
        r = skorlar(havuz, w, recall_metrik)
        m = skorlar(havuz, w, mrr)
        r_ort, r_se = ort_ve_hata(r)
        m_ort, m_se = ort_ve_hata(m)
        print(f"{w:<14} | {r_ort:.4f} +/- {r_se:.4f} | {m_ort:.4f} +/- {m_se:.4f}")
        tablo.append({"w": w, "recall": r_ort, "mrr": m_ort})

    # Secim kurali: MRR en yuksek; ">" kullandigimiz icin esitlikte
    # (AGIRLIKLAR kucukten buyuge sirali) KUCUK agirlik kalir
    secilen = tablo[0]
    for satir in tablo[1:]:
        if satir["mrr"] > secilen["mrr"]:
            secilen = satir
    print(f"\nSECILEN BM25 agirligi (dev MRR@5'e gore): {secilen['w']}")
    return secilen["w"], tablo


def karsilastir(metrik_adi, a, b, ad_a, ad_b):
    # Eslemeli bootstrap ile iki yapilandirmanin farkini test eder
    ort, alt, ust = eslemeli_bootstrap(a, b)
    if alt > 0:
        sonuc = f"{ad_a} DAHA IYI (gercek)"
    elif ust < 0:
        sonuc = f"{ad_a} DAHA KOTU (gercek)"
    else:
        sonuc = "AYIRT EDILEMIYOR"
    etiket = f"{ad_a} - {ad_b}"
    print(f"{metrik_adi:<9} | {etiket:<24} | {ort:+.4f}   | "
          f"[{alt:+.4f}, {ust:+.4f}]  | {sonuc}")


def testte_olc(w_secilen):
    # Uc yapilandirma: CLIP-only (w=0), esit agirlikli hibrit (w=1.0), secilen
    yapilandirmalar = {"CLIP": 0.0, "Esit": 1.0, "Secilen": w_secilen}
    ozet = {}

    # ------------------ INSAN CAPTION TEST SETI ------------------
    with open(CAPTION_DOSYASI, "r", encoding="utf-8") as f:
        caption_seti = json.load(f)
    print(f"\nTest (insan caption, {len(caption_seti)} sorgu) adaylari toplaniyor...")
    havuz = aday_havuzu(caption_seti)

    # Her yapilandirma icin sorgu bazli skorlar
    r = {ad: skorlar(havuz, w, recall_metrik) for ad, w in yapilandirmalar.items()}
    m = {ad: skorlar(havuz, w, mrr) for ad, w in yapilandirmalar.items()}

    print("\n=== TEST: INSAN CAPTION ===")
    print(f"{'Yapilandirma':<14} | {'Recall@5':<19} | {'MRR@5':<19}")
    print("-" * 56)
    for ad, w in yapilandirmalar.items():
        r_ort, r_se = ort_ve_hata(r[ad])
        m_ort, m_se = ort_ve_hata(m[ad])
        print(f"{ad + f' (w={w})':<14} | {r_ort:.4f} +/- {r_se:.4f} | {m_ort:.4f} +/- {m_se:.4f}")
        ozet.setdefault("insan_caption", {})[ad] = {"w": w, "recall": r_ort, "mrr": m_ort}
    # Tutarlilik kontrolu: onceki sonuclarla birebir ayni olmali
    print("[kontrol] Beklenen: CLIP Recall 0.6550 / MRR 0.5226 ; "
          "Esit Recall 0.5750 / MRR 0.3798")

    print(f"\n{'Metrik':<9} | {'Karsilastirma':<24} | {'Ort. fark':<9} | "
          f"{'%95 guven araligi':<20} | Sonuc")
    print("-" * 90)
    for referans in ["CLIP", "Esit"]:
        # Secilen agirlik zaten o referansla ayniysa kendisiyle kiyaslamanin anlami yok
        if yapilandirmalar[referans] == w_secilen:
            print(f"(Secilen agirlik '{referans}' ile ayni, karsilastirma atlandi)")
            continue
        karsilastir("Recall@5", r["Secilen"], r[referans], "Secilen", referans)
        karsilastir("MRR@5", m["Secilen"], m[referans], "Secilen", referans)

    # ------------------ KATEGORI TEST SETI ------------------
    with open(KATEGORI_DOSYASI, "r", encoding="utf-8") as f:
        kategori_seti = json.load(f)
    print(f"\nTest (kategori, {len(kategori_seti)} sorgu) adaylari toplaniyor...")
    havuz_k = aday_havuzu(kategori_seti)
    p = {ad: skorlar(havuz_k, w, precision_metrik) for ad, w in yapilandirmalar.items()}

    print("\n=== TEST: KATEGORI ===")
    print(f"{'Yapilandirma':<14} | {'Precision@5':<19}")
    print("-" * 36)
    for ad, w in yapilandirmalar.items():
        p_ort, p_se = ort_ve_hata(p[ad])
        print(f"{ad + f' (w={w})':<14} | {p_ort:.4f} +/- {p_se:.4f}")
        ozet.setdefault("kategori", {})[ad] = {"w": w, "precision": p_ort}
    print("[kontrol] Beklenen: CLIP 0.8727 ; Esit 0.9039")

    print(f"\n{'Metrik':<9} | {'Karsilastirma':<24} | {'Ort. fark':<9} | "
          f"{'%95 guven araligi':<20} | Sonuc")
    print("-" * 90)
    for referans in ["CLIP", "Esit"]:
        if yapilandirmalar[referans] == w_secilen:
            print(f"(Secilen agirlik '{referans}' ile ayni, karsilastirma atlandi)")
            continue
        karsilastir("P@5", p["Secilen"], p[referans], "Secilen", referans)
    return ozet


def calistir():
    # 1) Agirligi SADECE dev setinde sec
    w_secilen, dev_tablosu = dev_ile_agirlik_sec()
    # 2) Secilen agirligi test setlerinde BIR KEZ olc
    test_ozeti = testte_olc(w_secilen)
    # 3) Hepsini kaydet (rapor yazarken kullanacagiz)
    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"secilen_w": w_secilen, "dev": dev_tablosu, "test": test_ozeti},
                  f, ensure_ascii=False, indent=2)
    print(f"\nSonuclar kaydedildi: {SONUC_DOSYASI}")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()