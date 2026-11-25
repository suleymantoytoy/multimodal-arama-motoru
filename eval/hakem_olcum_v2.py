# ============================================================
# Bu script, URETIMDEKI gorsel hakemin (search/visual_judge.py ->
# gorsel_hakem_onayla) etiketli veride ne yaptigini OLCER.
#
# Populasyon: CLIP skoru uretimdeki esigi (0.25) gecen adaylar,
# cunku uretimde hakem SADECE bunlari gorur. Olculenler:
#   - Hakemin ISABETLERI kabul orani (yuksek olmali)
#   - Hakemin ISABETSIZLERI kabul orani (dusuk olmali)
# Karsilastirma referansi: CLIP esigi tek basina bunlarin hepsini
# gecirir (isabetsizlerin %63'u gecmisti).
#
# Uretimdeki fonksiyonu OLDUGU GIBI cagirir (384 kucultme dahil).
# Hakemin ekrana yazdigi mesajlari yakalayip, cagrinin HATA ile
# bitip bitmedigini ayirt eder (hata = kabul/red sayilmaz).
#
# Sonuclar her cagridan sonra eval/hakem_sonuclari_v2.json'a yazilir;
# script yarida kesilirse (gunluk token siniri vb.) ayni komutla
# kaldigi yerden devam eder.
# ============================================================

# os, sys: dosya yollari ve Python modul yolu icin
import os
import sys
# json: skor ve sonuc dosyalarini okumak/yazmak icin
import json
# io, contextlib: hakemin ekrana yazdigi mesajlari yakalamak icin
import io
import contextlib
# time: cagrilar arasi bekleme icin
import time
# random: aday sirasini sabit seed'le karistirmak icin
import random
# tempfile: indirilen fotografi gecici dosyaya yazmak icin
import tempfile
# requests: fotograflari indirmek icin
import requests
# tqdm: ilerleme cubugu icin
from tqdm import tqdm

# search klasorunu Python yoluna ekle (visual_judge'i import edebilmek icin)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))
# Uretimdeki hakem fonksiyonu
from visual_judge import gorsel_hakem_onayla

# Girdi: clip_analiz_v2.py'nin yazdigi skor dosyasi
SKOR_DOSYASI = "eval/clip_skorlari_v2.json"
# Cikti: hakem sonuclari (devam edebilmek icin her cagridan sonra guncellenir)
SONUC_DOSYASI = "eval/hakem_sonuclari_v2.json"
# Uretimdeki guncel CLIP esigi (hybrid_search.py'deki HARICI_ESIK)
CLIP_ESIGI = 0.25
# Iki hakem cagrisi arasinda bekleme (saniye): dakikada 3 gorsel, 8K token sinirinin altinda
BEKLEME = 20
# Bu kadar ARDISIK hata olursa dur (gunluk token siniri gibi durumlar)
ARDISIK_HATA_LIMITI = 5
# Indirme sirasinda kullanilacak tanitici baslik
BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}


def anahtar_uret(sorgu, url):
    # Her (sorgu, fotograf) cifti icin benzersiz anahtar
    return sorgu + "|" + url


def sonuclari_yukle():
    # Onceki calistirmadan kalan sonuclar varsa oku (hata ile bitenler tekrar denenir)
    if not os.path.exists(SONUC_DOSYASI):
        return {}
    with open(SONUC_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def sonuclari_kaydet(sonuclar):
    # Tum sonuclari diske yaz
    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)


def rapor_yazdir(sonuclar, toplam_aday):
    # Hata ile bitmeyen (gecerli) cagrilar
    gecerli = [k for k in sonuclar.values() if not k["hata"]]
    hatali = len(sonuclar) - len(gecerli)
    isabetli = [k for k in gecerli if k["isabet"]]
    isabetsiz = [k for k in gecerli if not k["isabet"]]
    kabul_isabetli = sum(1 for k in isabetli if k["karar"])
    kabul_isabetsiz = sum(1 for k in isabetsiz if k["karar"])
    yeniden_429 = sum(1 for k in sonuclar.values() if k["yeniden_deneme_429"])

    print("\n=== HAKEM OLCUMU (CLIP >= %.2f olan adaylar) ===" % CLIP_ESIGI)
    print(f"Toplam aday: {toplam_aday} | hakemden gecen (kayitli): {len(sonuclar)} "
          f"| hata ile biten: {hatali} | henuz sorulmayan: {toplam_aday - len(sonuclar)}")
    print(f"429 nedeniyle yeniden denenen cagri: {yeniden_429}")
    if isabetli:
        print(f"Hakem ISABETLERI kabul etti : {kabul_isabetli}/{len(isabetli)} "
              f"({kabul_isabetli / len(isabetli):.1%})")
    if isabetsiz:
        print(f"Hakem ISABETSIZLERI kabul etti: {kabul_isabetsiz}/{len(isabetsiz)} "
              f"({kabul_isabetsiz / len(isabetsiz):.1%})  "
              f"(CLIP esigi tek basina bunlarin hepsini gecirir)")

    # Kaynaga gore ayrim
    for kaynak in ("unsplash", "openverse"):
        alt = [k for k in gecerli if k["kaynak"] == kaynak]
        if alt:
            print(f"  [{kaynak}] {len(alt)} aday: isabet kabul "
                  f"{sum(1 for k in alt if k['isabet'] and k['karar'])}/{sum(1 for k in alt if k['isabet'])}, "
                  f"isabetsiz kabul {sum(1 for k in alt if not k['isabet'] and k['karar'])}/{sum(1 for k in alt if not k['isabet'])}")

    # Sorguya gore tablo
    print(f"\n{'Sorgu':<42} | {'isabet kabul':<13} | {'isabetsiz kabul':<15}")
    print("-" * 76)
    sorgular = sorted({k["sorgu"] for k in gecerli})
    for sorgu in sorgular:
        s = [k for k in gecerli if k["sorgu"] == sorgu]
        i = [k for k in s if k["isabet"]]
        n = [k for k in s if not k["isabet"]]
        print(f"{sorgu:<42} | {sum(1 for k in i if k['karar'])}/{len(i):<11} | "
              f"{sum(1 for k in n if k['karar'])}/{len(n):<13}")


def calistir():
    # Skorlari oku
    with open(SKOR_DOSYASI, "r", encoding="utf-8") as f:
        veri = json.load(f)

    # Populasyon: skoru olan VE uretimdeki esigi gecen adaylar
    adaylar = []
    for blok in veri:
        for a in blok["adaylar"]:
            if a["clip_skoru"] is not None and a["clip_skoru"] >= CLIP_ESIGI:
                adaylar.append({"sorgu": blok["sorgu"], "url": a["url"],
                                "kaynak": a["kaynak"], "isabet": a["isabet"],
                                "clip": a["clip_skoru"]})
    # Sabit seed'le karistir: yarida kesilen bir calistirma rastgele bir ornek olur
    random.Random(5).shuffle(adaylar)

    # Onceki sonuclari yukle; HATA ile bitenleri tekrar denemek icin "tamam" sayma
    sonuclar = sonuclari_yukle()
    tamam = {a for a, k in sonuclar.items() if not k["hata"]}
    # Hatali kayitlari sil (tekrar denenecekler)
    for anahtar in [a for a, k in sonuclar.items() if k["hata"]]:
        del sonuclar[anahtar]

    print(f"Populasyon: {len(adaylar)} aday | daha once tamamlanan: {len(tamam)}")
    ardisik_hata = 0

    for aday in tqdm(adaylar):
        anahtar = anahtar_uret(aday["sorgu"], aday["url"])
        # Daha once basariyla sorulduysa atla
        if anahtar in tamam:
            continue

        # Fotografi indir (indirilemezse kaydetmeden gec, bir sonraki calistirmada tekrar denenir)
        try:
            cevap = requests.get(aday["url"], headers=BASLIK, timeout=20)
            cevap.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as gecici:
                gecici.write(cevap.content)
                yol = gecici.name
        except Exception as hata:
            print(f"    indirme HATASI: {type(hata).__name__}: {str(hata)[:80]}")
            continue

        # Uretimdeki hakemi cagir; ekrana yazdigi mesajlari yakala
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            karar = gorsel_hakem_onayla(yol, aday["sorgu"])
        os.remove(yol)
        cikti = tampon.getvalue()
        # "UYARI": hakem cagrisi (yeniden denemeden sonra) hata ile bitti, karar GECERSIZ
        hata_mi = "UYARI" in cikti

        sonuclar[anahtar] = {
            "sorgu": aday["sorgu"], "url": aday["url"], "kaynak": aday["kaynak"],
            "isabet": aday["isabet"], "clip": aday["clip"],
            "karar": bool(karar), "hata": hata_mi,
            "yeniden_deneme_429": "429" in cikti,
            "cikti": cikti.strip()[:300],
        }
        # Her cagridan sonra kaydet (yarida kesilirse kayip olmasin)
        sonuclari_kaydet(sonuclar)

        # Ardisik hata sayacini guncelle; limit asilirsa dur
        ardisik_hata = ardisik_hata + 1 if hata_mi else 0
        if ardisik_hata >= ARDISIK_HATA_LIMITI:
            print(f"\nSon hata mesaji: {cikti.strip()[:300]}")
            print(f"\n{ARDISIK_HATA_LIMITI} ardisik hata: durduruluyor (token siniri olabilir). "
                  "Ayni komutla daha sonra kaldigi yerden devam edebilirsin.")
            break

        # Hiz sinirina takilmamak icin bekle
        time.sleep(BEKLEME)

    rapor_yazdir(sonuclar, len(adaylar))


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()