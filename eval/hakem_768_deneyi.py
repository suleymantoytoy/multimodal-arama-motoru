# ============================================================
# Bu script, "384 piksele kucultme hakemin gercek isabetleri
# reddetmesinin ana nedeni mi?" sorusunu OLCER.
#
# Populasyon (eval/hakem_sonuclari_v2.json'dan):
#   A) Hakemin REDDETTIGI gercek ISABETLER (etiket isabet, karar red)
#      -> hem 384'te yeniden (kontrol: ret tekrarlaniyor mu?) hem
#         768'de sorulur
#   B) Hakemin REDDETTIGI ISABETSIZLER (etiket isabetsiz, karar red)
#      -> sadece 768'de sorulur (buyuk gorsel yanlis kabul uretiyor mu?)
#
# ON-KAYITLI KARAR KURALI (sonuclar gorulmeden belirlendi):
#   - 768'de A'nin >=5'i kabule doner VE B'nin <=1'i kabul edilirse:
#     kucultme ana neden sayilir.
#   - 384 kontrolunde A'dan >=2 ret kabule donerse: deney gurultu
#     icinde sayilir, kural UYGULANMAZ.
#   - Aksi halde kucultme ana neden sayilmaz.
#
# Uretim dosyalarina DOKUNMAZ: visual_judge'in kucultme fonksiyonu
# sadece bu script calisirken bellekte degistirilir.
# Sonuclar her cagridan sonra kaydedilir; ayni komutla devam edilir.
# ============================================================

# os, sys: dosya yollari ve Python modul yolu icin
import os
import sys
# json: sonuc dosyalarini okumak/yazmak icin
import json
# io, contextlib: hakemin ekrana yazdigi mesajlari yakalamak icin
import io
import contextlib
# time: cagrilar arasi bekleme icin
import time
# random: gorev sirasini sabit seed'le karistirmak icin
import random
# tempfile: indirilen fotografi gecici dosyaya yazmak icin
import tempfile
# requests: fotograflari indirmek icin
import requests
# tqdm: ilerleme cubugu icin
from tqdm import tqdm

# search klasorunu Python yoluna ekle (visual_judge'i import edebilmek icin)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))
# Uretimdeki hakem modulu (fonksiyonu modul uzerinden cagiracagiz)
import visual_judge

# Girdi: onceki hakem olcumunun sonuclari
GIRDI_DOSYASI = "eval/hakem_sonuclari_v2.json"
# Cikti: bu deneyin sonuclari (devam edebilmek icin her cagridan sonra guncellenir)
CIKTI_DOSYASI = "eval/hakem_768_sonuclari.json"
# Iki hakem cagrisi arasinda bekleme (saniye): dakikada 3 gorsel
BEKLEME = 20
# Bu kadar ardisik hata olursa dur
ARDISIK_HATA_LIMITI = 5
# Indirme sirasinda kullanilacak tanitici baslik
BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}

# Kucultme fonksiyonunun ORIJINALI (degistirmeden once sakliyoruz)
ORIJINAL_KODLA = visual_judge._gorseli_kucult_ve_kodla


def boyutlu_hakem(yol, sorgu, boyut):
    # Hakemin kullandigi kucultme fonksiyonunu GECICI olarak verilen boyutla degistir
    visual_judge._gorseli_kucult_ve_kodla = lambda gorsel_yolu, maks_boyut=384: ORIJINAL_KODLA(gorsel_yolu, boyut)
    try:
        # Uretimdeki hakem fonksiyonunu aynen cagir
        return visual_judge.gorsel_hakem_onayla(yol, sorgu)
    finally:
        # Ne olursa olsun orijinal fonksiyonu geri koy
        visual_judge._gorseli_kucult_ve_kodla = ORIJINAL_KODLA


def anahtar_uret(kayit, boyut):
    # Her (sorgu, fotograf, boyut) uclusu icin benzersiz anahtar
    return f"{kayit['sorgu']}|{kayit['url']}|{boyut}"


def sonuclari_yukle():
    # Onceki calistirmadan kalan sonuclar varsa oku
    if not os.path.exists(CIKTI_DOSYASI):
        return {}
    with open(CIKTI_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def sonuclari_kaydet(sonuclar):
    # Tum sonuclari diske yaz
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)


def rapor_yazdir(sonuclar, gorevler):
    # Gecerli (hata ile bitmeyen) kayitlar
    gecerli = [k for k in sonuclar.values() if not k["hata"]]
    print("\n=== 768 PIKSEL DENEYI ===")
    print(f"Gorev: {len(gorevler)} | kayitli: {len(sonuclar)} | gecerli: {len(gecerli)} "
          f"| henuz sorulmayan: {len(gorevler) - len(gecerli)}")

    def sayim(grup, boyut):
        # Verilen grup ve boyut icin (kabul, gecerli cagri) sayisi
        alt = [k for k in gecerli if k["grup"] == grup and k["boyut"] == boyut]
        return sum(1 for k in alt if k["karar"]), len(alt)

    a384 = sayim("A", 384)
    a768 = sayim("A", 768)
    b768 = sayim("B", 768)
    print(f"A (gercek isabet, onceden REDDEDILEN) 384 yeniden : kabul {a384[0]}/{a384[1]}  (kontrol; 0 beklenir)")
    print(f"A (gercek isabet, onceden REDDEDILEN) 768         : kabul {a768[0]}/{a768[1]}  (kural: >=5)")
    print(f"B (isabetsiz, onceden REDDEDILEN)     768         : kabul {b768[0]}/{b768[1]}  (kural: <=1)")

    # Sorguya gore A'daki donusler
    print("\nA grubunda sorguya gore (384 yeniden / 768 kabul):")
    sorgular = sorted({k["sorgu"] for k in gecerli if k["grup"] == "A"})
    for sorgu in sorgular:
        k384 = [k for k in gecerli if k["grup"] == "A" and k["sorgu"] == sorgu and k["boyut"] == 384]
        k768 = [k for k in gecerli if k["grup"] == "A" and k["sorgu"] == sorgu and k["boyut"] == 768]
        print(f"  {sorgu:<42} | 384: {sum(1 for k in k384 if k['karar'])}/{len(k384)} "
              f"| 768: {sum(1 for k in k768 if k['karar'])}/{len(k768)}")

    # B'de yeni kabul edilenlerin sorgusu
    kabul_b = [k for k in gecerli if k["grup"] == "B" and k["boyut"] == 768 and k["karar"]]
    if kabul_b:
        print("\nB'de 768'de KABUL edilen isabetsizler (gozle kontrol et):")
        for k in kabul_b:
            print(f"  {k['sorgu']} | {k['url'][:90]}")


def calistir():
    # Onceki hakem sonuclarini oku
    with open(GIRDI_DOSYASI, "r", encoding="utf-8") as f:
        onceki = json.load(f)
    # Hata ile bitmeyen kayitlar
    gecerli_onceki = [k for k in onceki.values() if not k["hata"]]
    # A: gercek isabet, hakem reddetti; B: isabetsiz, hakem reddetti
    grup_a = [k for k in gecerli_onceki if k["isabet"] and not k["karar"]]
    grup_b = [k for k in gecerli_onceki if (not k["isabet"]) and not k["karar"]]
    print(f"A (reddedilen isabet): {len(grup_a)} | B (reddedilen isabetsiz): {len(grup_b)}")

    # Gorev listesi: A icin hem 384 hem 768, B icin sadece 768
    gorevler = []
    for k in grup_a:
        gorevler.append((k, "A", 384))
        gorevler.append((k, "A", 768))
    for k in grup_b:
        gorevler.append((k, "B", 768))
    # Sabit seed ile karistir: yarida kesilirse rastgele bir ornek elde kalir
    random.Random(9).shuffle(gorevler)

    # Onceki sonuclari yukle; HATA ile bitenleri tekrar denemek icin sil
    sonuclar = sonuclari_yukle()
    tamam = {a for a, k in sonuclar.items() if not k["hata"]}
    for anahtar in [a for a, k in sonuclar.items() if k["hata"]]:
        del sonuclar[anahtar]

    ardisik_hata = 0
    for kayit, grup, boyut in tqdm(gorevler):
        anahtar = anahtar_uret(kayit, boyut)
        # Daha once basariyla sorulduysa atla
        if anahtar in tamam:
            continue

        # Fotografi indir (indirilemezse kaydetmeden gec; sonraki calistirmada tekrar denenir)
        try:
            cevap = requests.get(kayit["url"], headers=BASLIK, timeout=20)
            cevap.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as gecici:
                gecici.write(cevap.content)
                yol = gecici.name
        except Exception as hata:
            print(f"    indirme HATASI: {type(hata).__name__}: {str(hata)[:80]}")
            continue

        # Hakemi verilen boyutla cagir; ekrana yazdigi mesajlari yakala
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            karar = boyutlu_hakem(yol, kayit["sorgu"], boyut)
        os.remove(yol)
        cikti = tampon.getvalue()
        # "UYARI": hakem cagrisi hata ile bitti, karar GECERSIZ
        hata_mi = "UYARI" in cikti

        sonuclar[anahtar] = {
            "sorgu": kayit["sorgu"], "url": kayit["url"], "grup": grup, "boyut": boyut,
            "karar": bool(karar), "hata": hata_mi, "cikti": cikti.strip()[:300],
        }
        # Her cagridan sonra kaydet
        sonuclari_kaydet(sonuclar)

        # Ardisik hata sayacini guncelle; limit asilirsa dur
        ardisik_hata = ardisik_hata + 1 if hata_mi else 0
        if ardisik_hata >= ARDISIK_HATA_LIMITI:
            print(f"\n{ARDISIK_HATA_LIMITI} ardisik hata: durduruluyor.")
            print(f"Son hata mesaji: {cikti.strip()[:300]}")
            break

        # Hiz sinirina takilmamak icin bekle
        time.sleep(BEKLEME)

    rapor_yazdir(sonuclar, gorevler)


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()