# ============================================================
# Bu script, Groq'taki gorsel modelin (qwen/qwen3.8-27b) bir
# fotograf icin GERCEKTE kac token harcadigini ve dusunme modunun
# (thinking) acik olup olmadigini OLCER. Ayni soruyu iki kez sorar:
#   1) varsayilan ayarlarla
#   2) reasoning_effort="none" ile (dusunmeyi kapatmayi dener)
# Hicbir seyi degistirmez, sadece iki istek atar.
# ============================================================

# os: ortam degiskenini okumak icin
import os
# base64: yerel fotografi API'ye gondermek icin metne cevirmek
import base64
# time: sure olcmek ve iki istek arasinda beklemek icin
import time
# load_dotenv: .env dosyasindaki GROQ_API_KEY'i yuklemek icin
from dotenv import load_dotenv
# Groq: resmi Groq istemcisi
from groq import Groq

# .env dosyasini yukle
load_dotenv()
# Groq istemcisini .env'deki anahtarla olustur
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Test edilecek model (hesabinda gordugumuz ad)
MODEL = "qwen/qwen3.8-27b"
# Yerel bir COCO fotografi (daha once "a dog" aramasinda ilk sonuc olarak ciktigi icin
# icinde koepek oldugunu biliyoruz; cevap "yes" olmali)
GORSEL_YOLU = "data/raw_images/000000361571.jpg"
# Yargic sorusu: sadece tek kelime cevap istiyoruz
SORU = "Does this photo show a dog? Answer with only one word: yes or no."


def gorseli_kodla(yol):
    # Dosyayi ikili modda acip base64 metnine cevir
    with open(yol, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def dene(ad, **ek_parametreler):
    # Hangi denemeyi yaptigimizi yazdir
    print(f"\n=== {ad} ===")
    try:
        # Sureyi olcmek icin baslangic zamani
        baslangic = time.time()
        cevap = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": SORU},
                    # Fotografi base64 olarak gonder
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{gorseli_kodla(GORSEL_YOLU)}"}},
                ],
            }],
            # Cikti ust siniri: dusunme acik ve uzunsa burada kesilir, bunu gorecegiz
            max_completion_tokens=512,
            **ek_parametreler,
        )
        # Gecen sure (saniye)
        sure = time.time() - baslangic
        # Ilk (ve tek) cevap secenegi
        secim = cevap.choices[0]
        print(f"  icerik: {secim.message.content!r}")
        # finish_reason: "stop" normal bitis, "length" token siniri
        print(f"  finish_reason: {secim.finish_reason}")
        # Varsa dusunme metninin uzunlugu (alan adi modele gore degisebilir)
        dusunme = getattr(secim.message, "reasoning", None)
        print(f"  dusunme metni uzunlugu: {len(dusunme) if dusunme else 0} karakter")
        # Token kullanimi: asil merak ettigimiz sayilar
        k = cevap.usage
        print(f"  token: girdi={k.prompt_tokens}, cikti={k.completion_tokens}, toplam={k.total_tokens}")
        print(f"  sure: {sure:.1f} sn")
    except Exception as hata:
        # Gecersiz parametre, hiz siniri vb.: hata turunu ve mesajini aynen yazdir
        print(f"  HATA: {type(hata).__name__}: {hata}")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    # 1) Varsayilan ayarlar
    dene("varsayilan")
    # Dakikalik token sinirina takilmamak icin bekle
    time.sleep(20)
    # 2) Dusunmeyi kapatmayi dene
    dene("reasoning_effort=none", reasoning_effort="none")