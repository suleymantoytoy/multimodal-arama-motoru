# ============================================================
# Bu script, degerlendirme icin IKI YENI test seti olusturur.
# Ikisi de COCO'nun INSAN YAZIMI anotasyonlarini kullanir; BLIP'ten
# TAMAMEN BAGIMSIZDIR. Boylece BM25'in "kendi caption'ini arama"
# avantaji ortadan kalkar.
#
# 1) eval/test_kategori.json
#    Sorgu: kisa kategori adi ("dog", "pizza"). Dogru cevaplar: o
#    kategoriyi iceren TUM gorseller. Olcut: Precision@5.
#
# 2) eval/test_insan_caption.json
#    Sorgu: bir gorselin 5 insan caption'indan RASTGELE biri.
#    Dogru cevap: kaynak gorsel. Olcutler: Recall@5, MRR.
# ============================================================

# json: JSON dosyalarini okumak/yazmak icin
import json
# os: dosya adi islemleri icin
import os
# random: tekrarlanabilir rastgele secim icin
import random
# statistics: medyan hesaplamak icin
import statistics

# Girdi dosyalari
METADATA_DOSYASI = "data/metadata.json"
INSTANCES_DOSYASI = "data/annotations/instances_val2017.json"
CAPTIONS_DOSYASI = "data/annotations/captions_val2017.json"

# Cikti dosyalari
KATEGORI_CIKTI = "eval/test_kategori.json"
CAPTION_CIKTI = "eval/test_insan_caption.json"

# Bir kategoriyi teste almak icin bizim 5.000 icinde en az kac gorselde
# gecmesi gerektigi (toaster=8, hair drier=9 bu yuzden disarida kalir)
MIN_GORSEL = 20

# "person" kategorisi gorsellerin %54'unde var, rastgele bir gorsel bile
# cogu zaman "dogru" sayilir - olcum anlamsizlasir, bu yuzden disarida
DISLANAN_KATEGORILER = {"person"}

# Insan caption setindeki sorgu sayisi (eski sette 50'ydi, daha guvenilir
# istatistik icin 200 yapiyoruz)
CAPTION_SORGU_SAYISI = 200

# Sonuclar HER calistirmada ayni cikmali (tekrarlanabilirlik)
SEED = 42


def dosya_id(dosya_yolu):
    # Windows "\" karakterini "/" yap
    temiz = dosya_yolu.replace("\\", "/")
    # Yoldan dosya adini al: ".../000000000139.jpg" -> "000000000139.jpg"
    dosya_adi = os.path.basename(temiz)
    # Uzantiyi at ve sayiya cevir: "000000000139" -> 139
    return int(os.path.splitext(dosya_adi)[0])


def json_oku(yol):
    # Dosyayi UTF-8 ile acip JSON'u Python nesnesine cevir
    with open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def json_yaz(yol, veri):
    # ensure_ascii=False: Turkce/ozel karakterler bozulmadan yazilsin
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def kategori_seti_olustur(metadata, id_to_dosya, instances):
    # Bizim 5.000 gorselin ID kumesi
    yerel_idler = set(id_to_dosya.keys())

    # Kategori ID -> kategori adi (orn. 18 -> "dog")
    kategori_adlari = {k["id"]: k["name"] for k in instances["categories"]}
    # Kategori ID -> o kategoriyi iceren (bizdeki) gorsel ID'leri
    kategori_gorselleri = {kid: set() for kid in kategori_adlari}
    for ann in instances["annotations"]:
        # Sadece bizim veri setimizde olan gorselleri say
        if ann["image_id"] in yerel_idler:
            kategori_gorselleri[ann["category_id"]].add(ann["image_id"])

    test_seti = []
    # Kategori adina gore alfabetik sirayla gez (cikti her seferinde ayni sirada)
    for kid in sorted(kategori_adlari, key=lambda k: kategori_adlari[k]):
        ad = kategori_adlari[kid]
        idler = kategori_gorselleri[kid]
        # Dislanan kategoriyi atla
        if ad in DISLANAN_KATEGORILER:
            continue
        # Cok az gorseli olan kategoriyi atla
        if len(idler) < MIN_GORSEL:
            continue
        test_seti.append({
            # Sorgu dogrudan COCO kategori adi
            "sorgu": ad,
            # Dogru cevaplar: dosya yollari, metadata'daki YAZILISIYLA
            # (eski test setinde de boyle yapmistik)
            "dogru_gorseller": sorted(id_to_dosya[i] for i in idler),
            # Rastgele secimle beklenen precision: kategori orani
            "rastgele_precision": len(idler) / len(yerel_idler),
        })
    return test_seti


def caption_seti_olustur(id_to_dosya, captions):
    yerel_idler = set(id_to_dosya.keys())

    # Gorsel ID -> o gorselin insan caption'lari listesi
    gorsel_captionlari = {}
    for ann in captions["annotations"]:
        if ann["image_id"] in yerel_idler:
            # setdefault: anahtar yoksa bos liste olustur, sonra ekle
            gorsel_captionlari.setdefault(ann["image_id"], []).append(
                # strip(): COCO caption'lari sonunda satir sonu icerebiliyor
                ann["caption"].strip()
            )

    # Rastgele secimi sabitlemek icin AYRI bir uretec (global seed'e bagimli olmasin)
    rastgele = random.Random(SEED)
    # Tekrarlanabilir olmasi icin ID'leri once siraliyoruz, sonra ornekliyoruz
    secilen_idler = rastgele.sample(sorted(gorsel_captionlari), CAPTION_SORGU_SAYISI)

    test_seti = []
    for gid in secilen_idler:
        # Bu gorselin 5 caption'indan rastgele BIRINI sorgu yap
        sorgu = rastgele.choice(gorsel_captionlari[gid])
        test_seti.append({
            "sorgu": sorgu,
            "dogru_gorseller": [id_to_dosya[gid]],
        })
    return test_seti


def calistir():
    # metadata.json'daki kayitlari oku
    metadata = json_oku(METADATA_DOSYASI)
    # Gorsel ID -> metadata'daki dosya yolu (yazildigi haliyle)
    id_to_dosya = {dosya_id(k["dosya"]): k["dosya"] for k in metadata}

    # Anotasyon dosyalarini oku
    instances = json_oku(INSTANCES_DOSYASI)
    captions = json_oku(CAPTIONS_DOSYASI)

    # --- Kategori seti ---
    kategori_seti = kategori_seti_olustur(metadata, id_to_dosya, instances)
    json_yaz(KATEGORI_CIKTI, kategori_seti)
    dogru_sayilari = [len(k["dogru_gorseller"]) for k in kategori_seti]
    print(f"Kategori seti: {len(kategori_seti)} sorgu -> {KATEGORI_CIKTI}")
    print(f"  Dogru gorsel sayisi (sorgu basina): en az {min(dogru_sayilari)}, "
          f"medyan {statistics.median(dogru_sayilari)}, en cok {max(dogru_sayilari)}")
    # Rastgele precision'in ortalamasi: "sansa birakilsa" beklenen taban deger
    ort_taban = statistics.mean(k["rastgele_precision"] for k in kategori_seti)
    print(f"  Rastgele secimle beklenen ortalama precision: {ort_taban:.4f}")

    # --- Insan caption seti ---
    caption_seti = caption_seti_olustur(id_to_dosya, captions)
    json_yaz(CAPTION_CIKTI, caption_seti)
    print(f"\nInsan caption seti: {len(caption_seti)} sorgu -> {CAPTION_CIKTI}")
    print("  Ilk 5 ornek sorgu:")
    for kayit in caption_seti[:5]:
        print(f"    '{kayit['sorgu']}'")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()