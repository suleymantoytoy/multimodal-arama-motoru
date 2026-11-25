# ============================================================
# Bu script, etiketler_v2.json'daki TUM adaylari mevcut CLIP
# (ViT-B/32) ile puanlar ve uc seyi olcer:
#   1) HAVUZ KALITESI: her kaynagin adaylari arasinda kac isabet var
#   2) AYIRT ETME GUCU: ayni sorguda her (isabetli, isabetsiz) cift
#      icin CLIP isabetliye daha yuksek skor veriyor mu (AUC;
#      0.5 = sans, 1.0 = mukemmel; esit skor 0.5 sayilir)
#   3) ESIK ETKISI: 0.24 ve 0.25 esikleri isabetlerin kacini tutuyor,
#      isabetsizlerin kacini geciriyor
# Skorlar eval/clip_skorlari_v2.json'a kaydedilir (sonraki adimda
# yeniden indirmek gerekmesin). Uretim koduna DOKUNMAZ.
# ============================================================

# os, sys: dosya yollari ve Python modul yolu icin
import os
import sys
# json: etiket ve skor dosyalarini okumak/yazmak icin
import json
# tempfile: indirilen fotografi gecici dosyaya yazmak icin
import tempfile
# requests: fotograflari indirmek icin
import requests
# numpy: AUC hesabi ve vektor carpimi icin
import numpy as np
# tqdm: ilerleme cubugu icin
from tqdm import tqdm

# embeddings klasorunu Python yoluna ekle (clip_encoder'i import edebilmek icin)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "embeddings"))
# Uretimdeki CLIP fonksiyonlari
from clip_encoder import encode_text, encode_image

# Girdi: indirdigin etiket dosyasi
ETIKET_DOSYASI = "eval/etiketler_v2.json"
# Cikti: skorlar (sonraki adimda yeniden kullanilacak)
SKOR_DOSYASI = "eval/clip_skorlari_v2.json"
# Raporlanacak esikler: eski (0.24) ve uretimdeki guncel (0.25) HARICI_ESIK
ESIKLER = [0.24, 0.25]
# Indirme sirasinda kullanilacak tanitici baslik (bazi siteler baslik olmadan reddeder)
BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}
# Kolay kontrol sorgulari: ayri raporlanir
KONTROL_SORGULARI = {"a red bicycle", "eiffel tower at night"}


def gorsel_skoru(url, sorgu_vektoru):
    # Fotografi indir; basarisizsa None dondur (sessizce 0.0 yazmiyoruz)
    try:
        cevap = requests.get(url, headers=BASLIK, timeout=20)
        cevap.raise_for_status()
        # Gecici dosyaya yaz (encode_image dosya yolu bekliyor)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as gecici:
            gecici.write(cevap.content)
            yol = gecici.name
        # CLIP ile gorselin vektorunu cikar
        gorsel_vektoru = encode_image(yol)
        # Gecici dosyayi sil
        os.remove(yol)
        # Kosinus benzerligi: uretimdeki ile ayni (vektorler normalize)
        return float(np.dot(gorsel_vektoru, sorgu_vektoru))
    except Exception as hata:
        # Hata turunu goster, None dondur
        print(f"    indirme/puanlama HATASI: {type(hata).__name__}: {str(hata)[:100]}")
        return None


def auc(skor_isabet, skor_isabetsiz):
    # Her (isabetli, isabetsiz) cift icin isabetli yuksekse 1, esitse 0.5, dusukse 0
    h = np.array(skor_isabet)[:, None]
    n = np.array(skor_isabetsiz)[None, :]
    return float(((h > n) + 0.5 * (h == n)).mean())


def calistir():
    # Etiketleri oku
    with open(ETIKET_DOSYASI, "r", encoding="utf-8") as f:
        etiketler = json.load(f)

    # Her adayi puanla
    for blok in etiketler:
        print(f"\n'{blok['sorgu']}' puanlaniyor...")
        # Sorgu vektoru: uretimdeki gibi KULLANICININ YAZDIGI orijinal sorgu
        sorgu_vektoru = encode_text(blok["sorgu"])
        for aday in tqdm(blok["adaylar"]):
            aday["clip_skoru"] = gorsel_skoru(aday["url"], sorgu_vektoru)

    # Skorlari kaydet (etiketlerle birlikte)
    with open(SKOR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(etiketler, f, ensure_ascii=False, indent=2)
    print(f"\nSkorlar kaydedildi: {SKOR_DOSYASI}")

    # ---------------- 1) HAVUZ KALITESI ----------------
    print("\n=== HAVUZ KALITESI (isabet / aday sayisi) ===")
    print(f"{'Sorgu':<42} | {'Unsplash':<9} | {'Openverse':<9}")
    print("-" * 66)
    toplam = {"unsplash": [0, 0, 0], "openverse": [0, 0, 0]}  # isabet, aday, isabetli sorgu
    for blok in etiketler:
        hucre = {}
        for kaynak in ("unsplash", "openverse"):
            adaylar = [a for a in blok["adaylar"] if a["kaynak"] == kaynak]
            isabet = sum(1 for a in adaylar if a["isabet"])
            hucre[kaynak] = f"{isabet}/{len(adaylar)}"
            toplam[kaynak][0] += isabet
            toplam[kaynak][1] += len(adaylar)
            toplam[kaynak][2] += 1 if isabet > 0 else 0
        print(f"{blok['sorgu']:<42} | {hucre['unsplash']:<9} | {hucre['openverse']:<9}")
    for kaynak, (isabet, aday, sorgu_sayisi) in toplam.items():
        print(f"TOPLAM {kaynak}: {isabet}/{aday} isabet, en az 1 isabeti olan sorgu: {sorgu_sayisi}/{len(etiketler)}")

    # ---------------- 2) AYIRT ETME GUCU (CLIP) ----------------
    print("\n=== CLIP AYIRT ETME GUCU (AUC; 0.5 = sans, 1.0 = mukemmel) ===")
    print(f"{'Sorgu':<42} | {'isabet':<6} | {'isabetsiz':<9} | AUC")
    print("-" * 70)
    auclar = {}
    for blok in etiketler:
        # Skoru olan (indirilebilen) adaylar
        gecerli = [a for a in blok["adaylar"] if a["clip_skoru"] is not None]
        isabetli = [a["clip_skoru"] for a in gecerli if a["isabet"]]
        isabetsiz = [a["clip_skoru"] for a in gecerli if not a["isabet"]]
        # AUC icin her iki siniftan da en az bir ornek lazim
        if isabetli and isabetsiz:
            auclar[blok["sorgu"]] = auc(isabetli, isabetsiz)
            sonuc = f"{auclar[blok['sorgu']]:.3f}"
        else:
            sonuc = "hesaplanamadi (bir sinif bos)"
        print(f"{blok['sorgu']:<42} | {len(isabetli):<6} | {len(isabetsiz):<9} | {sonuc}")
    zor = [v for k, v in auclar.items() if k not in KONTROL_SORGULARI]
    kolay = [v for k, v in auclar.items() if k in KONTROL_SORGULARI]
    if zor:
        print(f"\nOrtalama AUC, 10 ana sorgu ({len(zor)} hesaplanabildi): {np.mean(zor):.3f}")
    if kolay:
        print(f"Ortalama AUC, kolay kontrol sorgulari ({len(kolay)}): {np.mean(kolay):.3f}")

    # ---------------- 3) ESIK ETKISI ----------------
    tum = [a for b in etiketler for a in b["adaylar"] if a["clip_skoru"] is not None]
    isabetli = [a["clip_skoru"] for a in tum if a["isabet"]]
    isabetsiz = [a["clip_skoru"] for a in tum if not a["isabet"]]
    for esik in ESIKLER:
        print(f"\n=== ESIK {esik} ===")
        if isabetli:
            tutulan = sum(1 for s in isabetli if s >= esik)
            print(f"Isabetlerin esigi gecen orani   : {tutulan}/{len(isabetli)} ({tutulan / len(isabetli):.1%})")
        if isabetsiz:
            gecen = sum(1 for s in isabetsiz if s >= esik)
            print(f"Isabetsizlerin esigi gecen orani: {gecen}/{len(isabetsiz)} ({gecen / len(isabetsiz):.1%})")

    # Indirilemeyen aday sayisi
    basarisiz = sum(1 for b in etiketler for a in b["adaylar"] if a["clip_skoru"] is None)
    print(f"\nIndirilemeyen/puanlanamayan aday: {basarisiz} (metriklere dahil edilmedi)")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()