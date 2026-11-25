# ============================================================
# Bu script, Groq hesabinda KULLANILABILIR modellerin listesini
# yazdirir. Tek bir istek atar, hicbir seyi degistirmez.
# Amac: gorsel (vision) destekli bir model var mi, adini TAHMIN
# etmeden gormek (model adlari Groq'ta sik degisiyor).
# ============================================================

# os: ortam degiskenini okumak icin
import os
# load_dotenv: .env dosyasindaki GROQ_API_KEY'i yuklemek icin
from dotenv import load_dotenv
# Groq: resmi Groq istemcisi
from groq import Groq

# .env dosyasini yukle (script eval klasorunden calissa da ust klasoru arar)
load_dotenv()
# Groq istemcisini .env'deki anahtarla olustur
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Hesabin erisebildigi tum modelleri al ve adlarini sirala
modeller = sorted(m.id for m in client.models.list().data)
# Her model adini ayri satirda yazdir
for ad in modeller:
    print(ad)