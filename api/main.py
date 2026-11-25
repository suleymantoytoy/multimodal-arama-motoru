# ============================================================
# Bu dosya, projenin FastAPI servisini olusturur. Su ana kadar
# yazdigimiz tum arama mantigini (akilli_ara: yerel -> harici ->
# uretim) bir HTTP API'sinin arkasina koyuyoruz - boylece Streamlit
# arayuzu, Docker container'i veya baska herhangi bir istemci
# (mobil uygulama dahil) bu API'ye istek atarak arama yapabilir.
#
# FASTAPI NEDIR? Python'da hizli, modern bir web API framework'u.
# Fonksiyonlarimizin ustune "decorator" (@app.post gibi) ekleyerek,
# onlari otomatik olarak HTTP endpoint'lerine ceviriyor - ayrica
# kendiliginden bir test arayuzu (Swagger, /docs adresinde) uretiyor.
# ============================================================

import sys
import os

# search klasorundeki akilli_ara() fonksiyonunu import edebilmek
# icin, o klasoru Python'un arama yoluna ekliyoruz.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

# FastAPI uygulamasini olusturuyoruz - title/description, Swagger
# arayuzunda (/docs) gorunecek basliktir.
app = FastAPI(
    title="Multi-Modal Semantik Arama API",
    description="Metin veya gorsel ile CLIP+BM25+RRF hibrit arama, "
                 "yerelde bulunamazsa Unsplash'e, o da bulamazsa "
                 "AI goersel uretimine duser.",
)


# ------------------------------------------------------------
# Pydantic MODELI: FastAPI, bir istegin GOVDESININ (body) nasil
# gorunmesi gerektigini bilmek icin boyle bir "sema" (schema) sinifi
# ister. Kullanici /search/text endpoint'ine istek atarken, govdede
# {"sorgu": "...", "k": 10} seklinde bir JSON gondermesi gerekecek -
# bu sinif, o JSON'un YAPISINI tanimliyor. FastAPI, gelen veriyi
# OTOMATIK olarak bu sinifin kurallarina gore DOGRULAR (orn. "sorgu"
# eksikse, otomatik olarak anlamli bir hata doner - bizim elle
# kontrol etmemize gerek kalmaz).
# ------------------------------------------------------------
class MetinSorgusu(BaseModel):
    sorgu: str
    k: Optional[int] = 10  # k belirtilmezse varsayilan 10 kullanilir


# ------------------------------------------------------------
# Bu degiskenler, "akilli_ara" fonksiyonunu SADECE ILK ISTEKTE
# import edip, sonrasinda tekrar tekrar KULLANMAK icin var. Boyle
# yapmazsak, her istek geldiginde CLIP/BLIP modellerini yeniden
# yuklemeye calisirdik - bu ÇOK YAVAS olurdu. "Lazy loading"
# (tembel yukleme) denen bu yontem, ilk istegi biraz yavaslatir
# ama sonraki TUM istekleri hizlandirir.
# ------------------------------------------------------------
_akilli_ara = None


def _arama_fonksiyonunu_yukle():
    """
    hybrid_search modulundeki akilli_ara fonksiyonunu, SADECE
    ilk cagrildiginda import eder ve bir daha import etmez -
    boylece FastAPI baslatilirken degil, ILK ARAMA ISTEGI
    geldiginde modeller yuklenir (bu, API'nin baslatma suresini
    kisaltir, ama ilk arama biraz gecikmeli olur - kabul edilebilir
    bir trade-off).
    """
    global _akilli_ara
    if _akilli_ara is None:
        from hybrid_search import akilli_ara
        _akilli_ara = akilli_ara
    return _akilli_ara


# ------------------------------------------------------------
# ENDPOINT 1: Saglik kontrolu (health check)
# Bu, "API ayakta mi, calisiyor mu" diye kontrol etmek icin
# kullanilan STANDART bir endpoint - gercek sistemlerde (Docker,
# Kubernetes gibi ortamlarda) servisin hayatta olup olmadigini
# otomatik kontrol etmek icin kullanilir.
# ------------------------------------------------------------
@app.get("/health")
def saglik_kontrolu():
    return {"durum": "calisiyor"}


# ------------------------------------------------------------
# ENDPOINT 2: Metin ile arama
# POST istegi kullaniyoruz (GET degil) cunku istemci bize bir
# "govde" (body - sorgu metni gibi) gonderiyor; GET istekleri
# genelde govde tasimaz, sadece URL parametreleri tasir.
# ------------------------------------------------------------
@app.post("/search/text")
def metin_ile_ara(istek: MetinSorgusu):
    """
    istek: MetinSorgusu sinifina uygun bir JSON govdesi
    (orn. {"sorgu": "a dog", "k": 5}) - FastAPI bunu OTOMATIK
    olarak Python objesine cevirir, biz dogrudan istek.sorgu
    seklinde erisebiliriz.
    """
    akilli_ara = _arama_fonksiyonunu_yukle()

    try:
        sonuc = akilli_ara(istek.sorgu, k=istek.k)
        return sonuc
    except Exception as hata:
        # HTTPException: FastAPI'ye ozel bir hata turu - bu,
        # istemciye DUZGUN bir HTTP hata kodu (500 = sunucu hatasi)
        # ve anlamli bir mesajla cevap donmemizi saglar, ham bir
        # Python hatasi/traceback GORUNMEZ istemciye.
        raise HTTPException(status_code=500, detail=f"Arama sirasinda hata: {hata}")


# ------------------------------------------------------------
# ENDPOINT 3: Gorsel ile arama
# Burada govde JSON degil, bir DOSYA YUKLEMESI (multipart/form-data)
# - bu yuzden Pydantic modeli yerine FastAPI'nin UploadFile turunu
# kullaniyoruz.
# ------------------------------------------------------------
@app.post("/search/image")
async def gorsel_ile_ara(dosya: UploadFile = File(...), k: int = 10, esik: float = 0.75):
    # NOT: Gorsel-gorsel CLIP karsilastirmalari, metin-gorsel
    # karsilastirmalardan DOGAL OLARAK daha yuksek skorlar uretir -
    # CLIP, iki gorsel arasinda renk/kompozisyon gibi yuzeysel
    # ozellikleri bile "benzerlik" olarak sayabiliyor. Bu yuzden
    # metin aramasinda kullandigimiz esik (0.25) burada COK DUSUK
    # kaliyor - test edildi: alakasiz bir anime karakteri ile COCO
    # veri setindeki bir vazo gorseli arasinda bile 0.57 gibi
    # YANILTICI YUKSEK bir skor cikti. 0.75, ilk kalibrasyon olarak
    # kondu - daha fazla ornekle test edilip ayarlanabilir.
    """
    ONCEKI VERSIYONDAN FARKI: Artik skor kontrolu yapiyor. Yuklenen
    gorsel, yerel veri setimizle (COCO - gercek fotograflar) YETERINCE
    benzemiyorsa (orn. bir anime/cizim karakteri yuklendiyse), sonuc
    ALAKASIZ olabiliyordu. Simdi:
      1. Once yerelde ara, EN IYI skoru kontrol et.
      2. Skor esigin USTUNDEYSE: yerel sonuclari dondur (eskisi gibi).
      3. Skor esigin ALTINDAYSA: BLIP ile yuklenen gorseli TARIF ET
         (bir caption uret), sonra bu caption'i akilli_ara()'ya
         gonder - bu da otomatik olarak harici (Unsplash) veya
         uretim (AI) katmanlarina duser, tipki metin aramasinda
         oldugu gibi.
    """
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "embeddings"))
    from clip_encoder import encode_image
    from hybrid_search import _hnsw_index, _clip_dosya_yollari, akilli_ara

    try:
        gecici_yol = f"./_gecici_{dosya.filename}"
        icerik = await dosya.read()
        with open(gecici_yol, "wb") as f:
            f.write(icerik)

        sorgu_vektoru = encode_image(gecici_yol).reshape(1, -1).astype("float32")

        # D: benzerlik skorlari, I: index numaralari
        D, I = _hnsw_index.search(sorgu_vektoru, k)
        en_iyi_skor = float(D[0][0])

        if en_iyi_skor >= esik:
            # Yerelde YETERINCE benzer bir sey var - eskisi gibi devam.
            sonuclar = [_clip_dosya_yollari[i] for i in I[0]]
            os.remove(gecici_yol)
            return {
                "kaynak": "yerel_gorsel_arama",
                "en_iyi_skor": en_iyi_skor,
                "sonuclar": sonuclar,
            }

        # Yerelde YETERSIZ - BLIP ile gorseli TARIF EDIP, o tarifi
        # akilli_ara()'ya (metin tabanli uc katmanli zincire) gonderiyoruz.
        print(f"[search/image] Yerel skor dusuk ({en_iyi_skor:.4f}) - BLIP ile gorsel tarif ediliyor...")
        from caption_generator import generate_caption
        uretilen_caption = generate_caption(gecici_yol)
        os.remove(gecici_yol)

        print(f"[search/image] Uretilen tarif: '{uretilen_caption}' - akilli_ara()'ya yonlendiriliyor...")
        sonuc = akilli_ara(uretilen_caption, k=k, esik=esik)
        # Kullanicinin, bu aramanin ASLINDA gorselden turetilmis bir
        # metin sorgusuyla yapildigini bilmesi icin, uretilen caption'i
        # da sonuca ekliyoruz.
        sonuc["gorselden_uretilen_tarif"] = uretilen_caption
        return sonuc

    except Exception as hata:
        raise HTTPException(status_code=500, detail=f"Gorsel arama sirasinda hata: {hata}")