# ============================================================
# Bu script, yeni test setlerini kurmadan ONCE bir dogrulama yapar:
# metadata.json'daki 5.000 gorselin COCO anotasyon dosyalariyla
# gercekten eslesip eslesmedigini OLCER.
#
# Eslesme mantigi: gorsel dosya adlari (orn. 000000000139.jpg)
# COCO gorsel ID'sinin kendisi. Dosya adindan sayiyi cikarip
# (139), anotasyon dosyalarindaki "image_id" ile karsilastiriyoruz.
#
# Ek olarak, sonraki adim (kategori sorgulari) icin her nesne
# kategorisinin veri setimizde KAC gorselde gectigini de gosterir.
# ============================================================

# json: JSON dosyalarini okumak icin
import json
# os: dosya adi/uzantisi islemleri icin
import os
# statistics: medyan hesaplamak icin
import statistics

# Girdi dosyalarinin yollari (proje kok klasorunden calistirilacak)
METADATA_DOSYASI = "data/metadata.json"
INSTANCES_DOSYASI = "data/annotations/instances_val2017.json"
CAPTIONS_DOSYASI = "data/annotations/captions_val2017.json"


def dosya_id(dosya_yolu):
    # Windows'taki "\" karakterini "/" yap (projede baska yerlerde de boyle yapmistik)
    temiz = dosya_yolu.replace("\\", "/")
    # Yolun sadece dosya adi kismini al: "val2017/000000000139.jpg" -> "000000000139.jpg"
    dosya_adi = os.path.basename(temiz)
    # Uzantiyi at: "000000000139.jpg" -> "000000000139"
    govde = os.path.splitext(dosya_adi)[0]
    # Basindaki sifirlarla birlikte sayiya cevir: "000000000139" -> 139
    return int(govde)


def json_oku(yol):
    # Dosyayi UTF-8 olarak acip JSON'u Python nesnesine cevir
    with open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def calistir():
    # --- 1. Bizim 5.000 gorselin ID'leri ---
    metadata = json_oku(METADATA_DOSYASI)
    # Her kayittaki "dosya" alanindan ID cikar, kume (set) olarak tut
    yerel_idler = {dosya_id(kayit["dosya"]) for kayit in metadata}

    # Elle gozle kontrol icin ilk 3 ornek: dosya yolu ve cikan ID
    print("Ornek dosya yollari ve cikarilan ID'ler:")
    for kayit in metadata[:3]:
        print(f"  {kayit['dosya']}  ->  {dosya_id(kayit['dosya'])}")

    print(f"\nmetadata.json kayit sayisi: {len(metadata)}")
    print(f"Benzersiz gorsel ID sayisi: {len(yerel_idler)}")

    # --- 2. instances_val2017.json (nesne kategorileri) ---
    instances = json_oku(INSTANCES_DOSYASI)
    # Anotasyon dosyasindaki TUM gorsellerin ID'leri
    instances_idler = {img["id"] for img in instances["images"]}
    # Kesisim: hem bizde hem COCO'da olan gorseller
    eslesen_instances = yerel_idler & instances_idler

    # --- 3. captions_val2017.json (insan caption'lari) ---
    captions = json_oku(CAPTIONS_DOSYASI)
    # Caption'i olan gorsellerin ID'leri
    caption_idler = {a["image_id"] for a in captions["annotations"]}
    eslesen_captions = yerel_idler & caption_idler

    print("\n--- ESLESME SONUCLARI ---")
    print(f"instances ile eslesen gorsel: {len(eslesen_instances)} / {len(yerel_idler)}")
    print(f"captions  ile eslesen gorsel: {len(eslesen_captions)} / {len(yerel_idler)}")

    # --- 4. Kategori basina gorsel sayisi (sadece bizim 5.000 icinde) ---
    # Kategori ID -> kategori adi sozlugu (orn. 18 -> "dog")
    kategori_adlari = {k["id"]: k["name"] for k in instances["categories"]}
    # Kategori ID -> o kategoriyi iceren gorsel ID'leri kumesi
    kategori_gorselleri = {kid: set() for kid in kategori_adlari}
    for ann in instances["annotations"]:
        # Sadece bizim veri setimizde olan gorselleri say
        if ann["image_id"] in yerel_idler:
            kategori_gorselleri[ann["category_id"]].add(ann["image_id"])

    # Her kategorinin gorsel sayisini listele (kucukten buyuge sirali)
    sayilar = sorted(
        (len(idler), kategori_adlari[kid])
        for kid, idler in kategori_gorselleri.items()
    )
    sadece_sayilar = [s for s, _ in sayilar]

    print("\n--- KATEGORI BASINA GORSEL SAYISI (bizim 5.000 icinde) ---")
    print(f"Toplam kategori: {len(sayilar)}")
    print(f"En az: {sadece_sayilar[0]} ({sayilar[0][1]})")
    print(f"Medyan: {statistics.median(sadece_sayilar)}")
    print(f"En cok: {sadece_sayilar[-1]} ({sayilar[-1][1]})")
    print("En az 5 gorseli olan kategori sayisi:",
          sum(1 for s in sadece_sayilar if s >= 5))
    print("En az 20 gorseli olan kategori sayisi:",
          sum(1 for s in sadece_sayilar if s >= 20))
    print("\nEn nadir 10 kategori:")
    for sayi, ad in sayilar[:10]:
        print(f"  {ad}: {sayi} gorsel")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()