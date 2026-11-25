# ============================================================
# Bu script, esik degerini (threshold) TAHMINLE degil, GERCEK
# VERIYLE kalibre etmek icin yazildi.
#
# MANTIK: Elimizde iki tur sorgu var:
#   1. "Ilgili" sorgular - COCO veri setinde GERCEKTEN karsiligi
#      olmasi beklenen seyler (orn. "a dog", "a bicycle")
#   2. "Ilgisiz" sorgular - COCO'da KESINLIKLE karsiligi OLMAYAN
#      seyler (orn. "hippie style", "dragon ball z")
#
# Ikisi icin de en iyi CLIP skorunu olcup, bu iki grubun skor
# DAGILIMLARININ nerede AYRISTIGINI (hangi sayida "ilgili" grubun
# skorlari "ilgisiz" grubunkinden bariz sekilde yuksek kaliyor)
# gozlemleyip, esigi ORAYA gore ayarlayacagiz.
#
# YENI (bu surumde): Onceki calistirmada "ilgili" ve "ilgisiz"
# skorlarinin CAKISTIGI (net bir bosluk olmadigi) gorulmustu. Bu
# yuzden, cakismanin oldugu "gri bolge"deki sorgular icin BM25
# skorunu da olcup, BM25'in CLIP'in kararsiz kaldigi yerlerde
# ikinci bir sinyal olarak ise yarayip yaramadigina bakiyoruz.
# ============================================================

import sys
import os

# hybrid_search.py'yi import edebilmek icin bu klasoru (search/)
# Python'un arama yoluna ekliyoruz.
sys.path.append(os.path.dirname(__file__))

# NOT: hybrid_search.py import edildigi anda, o dosyanin en ustundeki
# "Hibrit arama sistemi baslatiliyor..." kodu da CALISIR (index'ler
# diskten yuklenir). Bu YAVAS ama SADECE BIR KEZ olur - asagida
# kullanacagimiz butun fonksiyon ve degiskenler bu import sayesinde
# hazir hale gelir.
from hybrid_search import (
    _en_iyi_clip_skoru,   # CLIP ile en iyi skoru donduren fonksiyon
    _bm25,                # BM25 index nesnesinin kendisi
    _bm25_dosya_yollari,  # BM25 index'indeki dosya yollari listesi
    _bm25_caption_listesi,  # BM25 index'indeki caption listesi
)
from bm25_index import bm25_ara


# Bunlarin COCO'da GERCEKTEN karsiligi olmasi beklenir.
ILGILI_SORGULAR = [
    "a dog", "a cat", "a bicycle", "a person eating",
    "a kitchen", "a bus", "a group of people", "a bathroom",
    "an airplane", "a laptop computer", "a bowl of fruit",
    "a person playing tennis", "a living room", "a train",
    "a birthday cake",
]

# Bunlarin COCO'da KESINLIKLE karsiligi OLMAMASI beklenir -
# stil/tema/karakter isimleri, COCO sadece gundelik fotograflardan olusuyor.
ILGISIZ_SORGULAR = [
    "hippie style outfit", "dragon ball z realistic",
    "a dog walking on the moon", "cyberpunk city at night",
    "watercolor painting of a forest", "aizen from bleach anime",
    "a medieval castle under siege", "steampunk robot",
    "a mermaid swimming in a coral reef", "gothic vampire portrait",
    "abstract geometric pattern", "a spaceship battle in space",
    "a fairy tale forest with glowing mushrooms",
    "a samurai warrior at sunset", "a superhero flying over a city",
]

# Onceki calistirmada CLIP skorlarinin CAKISTIGI (ilgili en dusuk:
# 0.2803, ilgisiz en yuksek: 0.2892) "supheli" sorgular. Bunlar icin
# BM25 skorunu da olceceğiz.
GRI_BOLGE_SORGULARI = {
    "ilgili": [
        "a group of people",         # CLIP: 0.2803 (en dusuk ilgili)
    ],
    "ilgisiz": [
        "gothic vampire portrait",       # CLIP: 0.2892 (en yuksek ilgisiz - suphelisi bu)
        "dragon ball z realistic",       # CLIP: 0.2826
        "hippie style outfit",           # CLIP: 0.2598
        "a medieval castle under siege", # CLIP: 0.2622
    ],
}


def _en_iyi_bm25_skoru(sorgu_metni):
    """
    Verilen sorgu icin BM25 arama sonuclarindaki EN YUKSEK skoru
    dondurur. Amac: CLIP skoru "gri bolge"de (belirsiz) kaldiginda,
    BM25'in bu sorgu icin anlamli bir keyword eslesmesi bulup
    bulamadigina bakmak.

    bm25_ara() imzasi (hybrid_search.py'deki _bm25_ile_ara()'dan
    kopyalandi): bm25_ara(bm25, dosya_yollari, caption_listesi,
    sorgu_metni, k) ve donus degeri {"dosya":..., "caption":...,
    "skor":...} seklinde sozluklerden olusan, skora gore SIRALI
    bir liste.
    """
    sonuclar = bm25_ara(_bm25, _bm25_dosya_yollari, _bm25_caption_listesi, sorgu_metni, k=1)
    if not sonuclar:
        return 0.0
    return sonuclar[0]["skor"]


def calistir():
    print("--- ILGILI sorgularin skorlari (yuksek olmasi beklenir) ---")
    ilgili_skorlar = []
    for sorgu in ILGILI_SORGULAR:
        skor = _en_iyi_clip_skoru(sorgu)
        ilgili_skorlar.append(skor)
        print(f"  '{sorgu}': {skor:.4f}")

    print("\n--- ILGISIZ sorgularin skorlari (dusuk olmasi beklenir) ---")
    ilgisiz_skorlar = []
    for sorgu in ILGISIZ_SORGULAR:
        skor = _en_iyi_clip_skoru(sorgu)
        ilgisiz_skorlar.append(skor)
        print(f"  '{sorgu}': {skor:.4f}")

    print(f"\nIlgili sorgularin EN DUSUK skoru: {min(ilgili_skorlar):.4f}")
    print(f"Ilgisiz sorgularin EN YUKSEK skoru: {max(ilgisiz_skorlar):.4f}")
    print("\nOneri: esik degeri, bu iki sayinin ARASINDA bir yerde olmali.")

    # --- GRI BOLGE: CLIP + BM25 karsilastirmasi ---
    # Bu blok, yukaridaki olcumden SONRA calisiyor (mantik sirasi
    # dogru: once CLIP'in nerede kararsiz kaldigini olcuyoruz, sonra
    # o kararsiz bolgeyi BM25 ile inceliyoruz).
    print("\n--- GRI BOLGE: CLIP + BM25 karsilastirmasi ---")
    print("(Amac: BM25, CLIP'in kararsiz kaldigi sorgularda ayirt edici mi?)\n")

    for grup, sorgu_listesi in GRI_BOLGE_SORGULARI.items():
        print(f"[{grup.upper()}]")
        for sorgu in sorgu_listesi:
            clip_skoru = _en_iyi_clip_skoru(sorgu)
            bm25_skoru = _en_iyi_bm25_skoru(sorgu)
            print(f"  '{sorgu}': CLIP={clip_skoru:.4f}  BM25={bm25_skoru:.4f}")
        print()


if __name__ == "__main__":
    calistir()