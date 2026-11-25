# ============================================================
# Bu script, agirlikli RRF icin bir AYAR (dev) seti olusturur.
#
# NEDEN AYRI BIR SET? BM25 agirligini mevcut test setinde ayarlayip
# AYNI test setiyle raporlarsak, agirligi test sorgularina "uydurmus"
# oluruz ve sonuc oldugundan iyi gorunur. Bu yuzden agirligi BASKA
# gorsellerle (dev) secip, test setinde sadece BIR KEZ olcuyoruz.
#
# Dev seti, test setindeki 200 gorselin DISINDAN secilir: ayni
# gorselin baska bir caption'ini kullansaydik hedef gorsel ayni
# kalir, ayar test setine "sizmis" olurdu.
# ============================================================

# random: tekrarlanabilir rastgele secim icin
import random

# build_test_set_v2'deki yardimci fonksiyonlari yeniden kullaniyoruz
# (ayni dosya adi->ID donusumu, ayni JSON okuma/yazma)
from build_test_set_v2 import dosya_id, json_oku, json_yaz

# Girdi dosyalari
METADATA_DOSYASI = "data/metadata.json"
CAPTIONS_DOSYASI = "data/annotations/captions_val2017.json"
# Test setindeki gorselleri disarida tutmak icin okuyoruz
TEST_CAPTION_DOSYASI = "eval/test_insan_caption.json"
# Cikti dosyasi
DEV_CIKTI = "eval/dev_insan_caption.json"

# 500 sorgu: komsu agirliklar arasindaki fark kucuk olacagi icin,
# secimin gurultulu olmamasi adina test setinden (200) daha buyuk
DEV_SORGU_SAYISI = 500
# Test setindeki seed'den (42) FARKLI bir seed
SEED = 7


def calistir():
    # metadata.json'dan "gorsel ID -> dosya yolu" sozlugu
    metadata = json_oku(METADATA_DOSYASI)
    id_to_dosya = {dosya_id(k["dosya"]): k["dosya"] for k in metadata}

    # COCO'nun insan caption'lari
    captions = json_oku(CAPTIONS_DOSYASI)

    # Test setinde kullanilan gorsellerin ID'leri (dev'den DISLANACAK)
    test_seti = json_oku(TEST_CAPTION_DOSYASI)
    test_idler = {dosya_id(d) for k in test_seti for d in k["dogru_gorseller"]}

    # Gorsel ID -> caption listesi (sadece bizim gorseller, test haric)
    gorsel_captionlari = {}
    for ann in captions["annotations"]:
        gid = ann["image_id"]
        if gid in id_to_dosya and gid not in test_idler:
            gorsel_captionlari.setdefault(gid, []).append(ann["caption"].strip())

    # Sabit seed'li ayri bir uretec: sonuc her calistirmada ayni cikar
    rastgele = random.Random(SEED)
    # ID'leri siralayip ornekliyoruz (tekrarlanabilirlik icin)
    secilen_idler = rastgele.sample(sorted(gorsel_captionlari), DEV_SORGU_SAYISI)

    # Her secilen gorselin caption'larindan rastgele birini sorgu yap
    dev_seti = []
    for gid in secilen_idler:
        dev_seti.append({
            "sorgu": rastgele.choice(gorsel_captionlari[gid]),
            "dogru_gorseller": [id_to_dosya[gid]],
        })

    # Guvenlik kontrolu: dev ve test gorselleri KESINLIKLE ortusmemeli
    assert set(secilen_idler).isdisjoint(test_idler), "Dev ve test ortusuyor!"

    json_yaz(DEV_CIKTI, dev_seti)
    print(f"Dev seti: {len(dev_seti)} sorgu -> {DEV_CIKTI}")
    print(f"Test ile ortusen gorsel sayisi: 0 (assert gecti)")
    print("Ilk 3 ornek sorgu:")
    for kayit in dev_seti[:3]:
        print(f"  '{kayit['sorgu']}'")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()