# ============================================================
# Bu script, Groq gorsel modeline (qwen/qwen3.8-27b) AYNI fotografi
# uc boyutta (384, 768, orijinal) gonderip her biri icin HARCANAN
# GIRDI TOKEN sayisini OLCER. Amac: uretimdeki 384 piksele
# kucultmenin token'i gercekten azaltip azaltmadigini gormek ve 768
# pikselle yapilacak bir deneyin maliyetini bilmek.
# Uretimdeki hakemle ayni ayarlar (reasoning_effort="none", cikti
# siniri 10); sadece soru metni daha kisa (uretimde yaklasik 250 token
# daha uzun), bu yuzden farklari karsilastirin, mutlak degerleri degil.
# ============================================================

# os, json, io, time, base64: dosya, JSON, bellek, bekleme ve metin kodlama islemleri icin
import os
import json
import io
import time
import base64
# requests: fotografi indirmek icin
import requests
# Image: fotografi kucultmek icin
from PIL import Image
# load_dotenv: .env dosyasindaki GROQ_API_KEY'i yuklemek icin
from dotenv import load_dotenv
# Groq: resmi Groq istemcisi
from groq import Groq

# .env dosyasini yukle
load_dotenv()
# Groq istemcisini olustur
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Olculecek model
MODEL = "qwen/qwen3.8-27b"
# Etiket dosyasi: icinden ilk Unsplash fotografini alacagiz
ETIKET_DOSYASI = "eval/etiketler_v2.json"
# Denenecek boyutlar (None: kucultme yok, orijinal boyut)
BOYUTLAR = [384, 768, None]
# Cagrilar arasi bekleme (saniye): dakikalik token sinirina takilmamak icin
BEKLEME = 25
# Indirme sirasinda kullanilacak tanitici baslik
BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}


def ilk_unsplash_url():
    # Etiket dosyasindaki ilk Unsplash adayinin tam boyutlu adresini bul
    with open(ETIKET_DOSYASI, "r", encoding="utf-8") as f:
        veri = json.load(f)
    for blok in veri:
        for aday in blok["adaylar"]:
            if aday["kaynak"] == "unsplash":
                return aday["tam_url"]
    raise RuntimeError("Etiket dosyasinda Unsplash adayi bulunamadi.")


def kodla(gorsel, maks_boyut):
    # Uretimdeki gibi: kopya uzerinde thumbnail ile kucult, JPEG kalite 80, base64'e cevir
    kopya = gorsel.copy()
    if maks_boyut:
        kopya.thumbnail((maks_boyut, maks_boyut))
    tampon = io.BytesIO()
    kopya.save(tampon, format="JPEG", quality=80)
    return kopya.size, len(tampon.getvalue()), base64.b64encode(tampon.getvalue()).decode("utf-8")


# Fotografi indir ve ac
url = ilk_unsplash_url()
print(f"Fotograf: {url[:80]}...")
cevap_http = requests.get(url, headers=BASLIK, timeout=30)
cevap_http.raise_for_status()
gorsel = Image.open(io.BytesIO(cevap_http.content)).convert("RGB")
print(f"Orijinal boyut: {gorsel.size}\n")

for maks in BOYUTLAR:
    # Bu boyutta kodla
    boyut, bayt, b64 = kodla(gorsel, maks)
    etiket = f"maks {maks}" if maks else "orijinal"
    try:
        sonuc = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Does this photo show a dog? Answer with only one word: yes or no."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            temperature=0.0,
            max_completion_tokens=10,
            reasoning_effort="none",
        )
        k = sonuc.usage
        print(f"[{etiket}] boyut={boyut} dosya={bayt // 1024} KB | girdi token={k.prompt_tokens} "
              f"cikti token={k.completion_tokens} | cevap={sonuc.choices[0].message.content!r}")
    except Exception as hata:
        print(f"[{etiket}] HATA: {type(hata).__name__}: {str(hata)[:200]}")
    # Dakikalik token sinirina takilmamak icin bekle
    time.sleep(BEKLEME)