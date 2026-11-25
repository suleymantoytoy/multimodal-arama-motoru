# ============================================================
# Bu script, COCO val2017 icin INSAN YAZIMI anotasyon dosyalarini
# indirir. Neden gerekli? Mevcut test setimiz BLIP caption'larindan
# turetilmisti, BM25 indeksi de ayni caption'lardan kurulu oldugu
# icin BM25'e haksiz avantaj saglamisti. COCO'nun kendi insan
# etiketleri BLIP'ten TAMAMEN BAGIMSIZ oldugu icin daha adil bir
# olcum yapmamizi saglar.
#
# Indirilecek zip ~241 MB. Icinden SADECE iki dosyayi cikaracagiz:
#   - instances_val2017.json : her gorselde hangi nesne kategorileri var
#   - captions_val2017.json  : her gorsel icin 5 insan yazimi caption
# ============================================================

# os: klasor ve dosya yolu islemleri icin
import os
# zipfile: zip dosyasinin icinden belirli dosyalari cikarmak icin
import zipfile
# requests: internetten dosya indirmek icin (zaten requirements.txt'te var)
import requests
# tqdm: indirme ilerleme cubugu gostermek icin (zaten requirements.txt'te var)
from tqdm import tqdm

# COCO'nun resmi anotasyon paketi (2017 surumu)
ZIP_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"

# Dosyalari kaydedecegimiz klasor (data/ klasoru zaten git'e girmiyor)
HEDEF_KLASOR = "data/annotations"
# Indirilen zip'in gecici olarak duracagi yol
ZIP_YOLU = os.path.join(HEDEF_KLASOR, "annotations_trainval2017.zip")

# Zip'in icinden SADECE bu iki dosyayi cikaracagiz
ISTENEN_DOSYALAR = [
    "annotations/instances_val2017.json",
    "annotations/captions_val2017.json",
]


def indir():
    # exist_ok=True: klasor zaten varsa hata verme, olusturmadan gec
    os.makedirs(HEDEF_KLASOR, exist_ok=True)

    # stream=True: dosyayi tek seferde belleğe degil, parca parca indir
    cevap = requests.get(ZIP_URL, stream=True, timeout=60)
    # HTTP hatasi (404, 500 vb.) varsa burada hemen durur
    cevap.raise_for_status()

    # Toplam boyut (byte cinsinden) - ilerleme cubugunun "yuzde"sini hesaplamak icin
    toplam = int(cevap.headers.get("content-length", 0))

    # "wb": dosyayi ikili (binary) yazma modunda ac
    with open(ZIP_YOLU, "wb") as f, tqdm(
        total=toplam, unit="B", unit_scale=True, desc="Indiriliyor"
    ) as cubuk:
        # 1 MB'lik parcalar halinde oku ve diske yaz
        for parca in cevap.iter_content(chunk_size=1024 * 1024):
            # Okunan parcayi dosyaya yaz
            f.write(parca)
            # Ilerleme cubugunu yazilan byte kadar ilerlet
            cubuk.update(len(parca))


def cikar():
    # Zip dosyasini okuma modunda ac
    with zipfile.ZipFile(ZIP_YOLU) as zip_dosyasi:
        for dosya in ISTENEN_DOSYALAR:
            # Zip icindeki dosyanin icerigini oku
            icerik = zip_dosyasi.read(dosya)
            # Zip'teki "annotations/" alt klasorunu atlayip duz HEDEF_KLASOR'e yaz
            hedef = os.path.join(HEDEF_KLASOR, os.path.basename(dosya))
            with open(hedef, "wb") as f:
                f.write(icerik)
            print(f"Cikarildi: {hedef}")

    # Buyuk zip'e artik ihtiyac yok, yer kaplamasin diye siliyoruz
    os.remove(ZIP_YOLU)
    print("Zip dosyasi silindi.")


# Bu dosya dogrudan calistirildiginda (import edilmediginde) asagisi calisir
if __name__ == "__main__":
    indir()
    cikar()