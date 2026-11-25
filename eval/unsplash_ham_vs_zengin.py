# ============================================================
# Bu script, Unsplash arama sorgusu zenginlestirmesinin GERCEKTEN
# daha iyi fotograf getirip getirmedigini OLCER.
#
# Her sorgu icin Unsplash'e IKI KEZ gideriz:
#   (a) HAM sorgu (kullanicinin yazdigi)
#   (b) ZENGINLESTIRILMIS sorgu (arama_sorgusu_zenginlestir ciktisi)
# Donen adaylarin HEPSI, uretimdeki gibi ORIJINAL sorguyla CLIP ile
# puanlanir. Sonra kac adayin HARICI_ESIK'i gectigine bakariz.
#
# ON-KAYITLI KARAR KURALI (sonuclar gorulmeden belirlendi):
#   - Zenginlestirilmis toplamda daha cok aday geciriyorsa: DEGERLI
#   - Esit veya ham onde ise: olculebilir kazanc YOK
#   - Sorgu sayisi kucuk (6): tek tek sorgulara degil TOPLAMA bakilir
#
# NOT: Unsplash demo anahtarinin saatlik sinirina takilmamak icin
# 6 sorgu x 2 arama = 12 API istegi yapar.
# ============================================================

# sys, os: search klasorunu Python yoluna eklemek icin
import sys
import os
# statistics: medyan hesaplamak icin
import statistics

# search klasorunu Python yoluna ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Puanlama fonksiyonu ve esik (bu import arama index'lerini de yukler)
from hybrid_search import _unsplash_sonucunu_clip_ile_puanla, HARICI_ESIK
# Unsplash arama fonksiyonu
from external_search import unsplash_ile_ara
# Sorgu zenginlestirme (su anki uretim talimatiyla)
from prompt_engineer import arama_sorgusu_zenginlestir

# Test sorgulari: yerel esigin ALTINDA kalan, yani gercekte Unsplash'e dusen sorgular
SORGULAR = [
    "winged dog",
    "dragon ball z realistic",
    "a dog walking on the moon",
    "hippie style outfit",
    "a medieval castle under siege",
    "gothic vampire portrait",
]
# Her aramadan alinacak aday sayisi (uretimde k*2; k=4 icin 8)
ADAY_SAYISI = 8


def puanla(arama_sorgusu, orijinal_sorgu):
    # Unsplash'te ara
    adaylar = unsplash_ile_ara(arama_sorgusu, k=ADAY_SAYISI)
    # Bos donerse bos liste dondur
    if not adaylar:
        return []
    # Her adayi ORIJINAL sorguyla CLIP ile puanla (uretimdeki gibi)
    return [_unsplash_sonucunu_clip_ile_puanla(a["url"], orijinal_sorgu) for a in adaylar]


def ozet(skorlar):
    # Esigi gecen aday sayisi, en yuksek skor, medyan
    gecen = sum(1 for s in skorlar if s >= HARICI_ESIK)
    en_yuksek = max(skorlar) if skorlar else 0.0
    medyan = statistics.median(skorlar) if skorlar else 0.0
    return gecen, en_yuksek, medyan


def calistir():
    # Toplamlar icin sayaclar
    toplam_ham = 0
    toplam_zengin = 0
    print(f"HARICI_ESIK = {HARICI_ESIK}, her aramada {ADAY_SAYISI} aday\n")
    print(f"{'Sorgu':<30} | {'HAM gecen/en yuksek/medyan':<30} | ZENGIN gecen/en yuksek/medyan")
    print("-" * 100)

    for sorgu in SORGULAR:
        # Zenginlestirilmis sorguyu BIR KEZ uret (degisken olabilir, cikti gosterilecek)
        zengin_sorgu = arama_sorgusu_zenginlestir(sorgu)
        # Iki kolu da puanla
        ham = puanla(sorgu, sorgu)
        zengin = puanla(zengin_sorgu, sorgu)
        g1, e1, m1 = ozet(ham)
        g2, e2, m2 = ozet(zengin)
        toplam_ham += g1
        toplam_zengin += g2
        print(f"{sorgu:<30} | {g1}/{len(ham)}  {e1:.3f}  {m1:.3f}".ljust(66)
              + f" | {g2}/{len(zengin)}  {e2:.3f}  {m2:.3f}")
        print(f"   zenginlestirilmis sorgu: '{zengin_sorgu}'")

    print("\n--- TOPLAM (esigi gecen aday) ---")
    print(f"HAM: {toplam_ham}  |  ZENGIN: {toplam_zengin}  (en fazla {ADAY_SAYISI * len(SORGULAR)})")


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()