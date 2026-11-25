# ============================================================
# Bu script, Groq'un ayni sorgu icin urettigi Unsplash arama
# sorgusunu OLCER. Su an uc seye bakar:
#   - farkli cikti sayisi (degiskenlik)
#   - girdiyi AYNEN geri yazma sayisi (sadece gozlem, kotu sayilmaz)
#   - KELIME TEKRARI sayisi ("kitchen kitchen kitchen" gibi, gercek kusur)
#
# ON-KAYITLI OLCUTLER (sonuclar gorulmeden belirlendi):
#   1. Kelime tekrarli cikti: 60 cagrida en fazla 1
#   2. "a dog walking on the moon": uzay kiyafeti iceren cikti 0 kalmali
#   3. "winged dog": 10/10 cikti "wing" + ("wearing" veya "costume") icermeli
#   4. "a cat wearing sunglasses": 10/10 ayni cikti
#   5. Aynen geri yazma: SADECE raporlanir, hedef yok
# ============================================================

# sys, os: search klasorunu Python yoluna eklemek icin
import sys
import os
# time: Groq hiz sinirina takilmamak icin bekleme
import time
# re: ciktiyi karsilastirmadan once normalize etmek icin
import re
# Counter: her cikti kac kez geldi, saymak icin
from collections import Counter

# search klasorunu Python yoluna ekle (prompt_engineer'i import edebilmek icin)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Sorgu zenginlestirme fonksiyonu
from prompt_engineer import arama_sorgusu_zenginlestir

# Test sorgulari (onceki testle AYNI altisi)
SORGULAR = [
    "a dog walking on the moon",
    "winged dog",
    "dragon ball z realistic",
    "a cat wearing sunglasses",
    "a red bicycle",
    "a kitchen",
]
# Her sorgu icin tekrar sayisi
TEKRAR = 10
# Iki cagri arasinda bekleme suresi (saniye)
BEKLEME = 2.0
# Temperature: mevcut uretim degeri (0.2 isimize yaramadi, bkz. karar gunlugu)
TEMPERATURE = 0.8


def normalize(metin):
    # Kucuk harfe cevir, noktalama isaretlerini at, fazla bosluklari tek bosluga indir
    metin = metin.lower()
    metin = re.sub(r"[^\w\s]", "", metin)
    return " ".join(metin.split())


def olc(sorgu):
    # Ayni sorguyu TEKRAR kez calistir
    ciktilar = []
    # Girdiyi aynen geri yazan cagri sayisi
    ayni = 0
    # Ayni kelimeyi birden fazla iceren cikti sayisi
    tekrarli = 0
    for _ in range(TEKRAR):
        # Groq hata verirse fonksiyon orijinal sorguyu dondurur ve konsola
        # "Groq cagrisi basarisiz oldu" yazar; o mesaji gorursen "ayni" sayisi sismis olabilir
        sonuc = arama_sorgusu_zenginlestir(sorgu, temperature=TEMPERATURE)
        # Karsilastirma icin normalize et
        n = normalize(sonuc)
        # Kelime listesi: tekrar var mi diye bakmak icin
        kelimeler = n.split()
        # Kume (set) benzersiz kelimeleri tutar; uzunluk farkliysa bir kelime tekrar etmis
        if len(kelimeler) != len(set(kelimeler)):
            tekrarli += 1
        # Cikti orijinal sorguyla ayniysa "aynen geri yazma" say
        if n == normalize(sorgu):
            ayni += 1
        ciktilar.append(n)
        # Hiz sinirina takilmamak icin bekle
        time.sleep(BEKLEME)
    return ciktilar, ayni, tekrarli


def calistir():
    # Ozet tablo icin sonuclari biriktir
    ozet = []
    for sorgu in SORGULAR:
        print(f"\n=== '{sorgu}' ===")
        ciktilar, ayni, tekrarli = olc(sorgu)
        sayac = Counter(ciktilar)
        print(f"  {len(sayac)} FARKLI cikti | aynen geri yazma: {ayni}/{TEKRAR} "
              f"| kelime tekrarli: {tekrarli}/{TEKRAR}")
        # En sik gelenden en seyrege dogru her ciktiyi ve kac kez geldigini yaz
        for cikti, adet in sayac.most_common():
            print(f"    {adet}x  {cikti}")
        ozet.append((sorgu, len(sayac), ayni, tekrarli))

    # Ozet tablo
    print("\n\n--- OZET ---")
    print(f"{'Sorgu':<28} | {'Farkli':<7} | {'Aynen':<7} | {'Tekrarli':<8}")
    print("-" * 58)
    for sorgu, farkli, ayni, tekrarli in ozet:
        print(f"{sorgu:<28} | {farkli:<7} | {ayni:<7} | {tekrarli:<8}")
    # Olcut 1 icin toplam
    toplam_tekrarli = sum(t for _, _, _, t in ozet)
    print(f"\nToplam kelime tekrarli cikti: {toplam_tekrarli}/{TEKRAR * len(SORGULAR)} (olcut: en fazla 1)")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()