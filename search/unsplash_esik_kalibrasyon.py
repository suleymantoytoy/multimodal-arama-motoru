# ============================================================
# Bu script, "0.29 esiginin Unsplash gorselleri icin de dogru olup
# olmadigini" OLCEREK test eder - tahmin etmeyelim, COCO'da yaptigimiz
# gibi burada da GERCEK veriyle kalibre edelim.
#
# MANTIK: "a dog" gibi, Unsplash'te KESINLIKLE gercekten alakali
# gorseller olmasi beklenen bir sorgu kullanip, Unsplash'in donduğu
# ilk birkac sonucun CLIP skorlarina bakiyoruz. Eger bu skorlar da
# 0.29'un ALTINDA kaliyorsa, bu SORUNUN esik degil, Unsplash
# gorsellerinin CLIP tarafindan SISTEMATIK OLARAK daha dusuk
# puanlanmasi oldugunu KANITLAR.
# ============================================================

import sys
import os

sys.path.append(os.path.dirname(__file__))
from hybrid_search import _unsplash_sonucunu_clip_ile_puanla
from external_search import unsplash_ile_ara

# "a dog" -> Unsplash'te KESINLIKLE gercek, acik ara alakali
# kopek fotograflari olmasi beklenir. Eger bunlarin CLIP skoru da
# dusuk cikarsa, sorun Unsplash gorsellerinin DOGASINDA.
KESIN_ILGILI_SORGULAR = ["a dog", "a cat", "a bicycle", "a kitchen"]


def calistir():
    for sorgu in KESIN_ILGILI_SORGULAR:
        print(f"\n--- Sorgu: '{sorgu}' ---")
        adaylar = unsplash_ile_ara(sorgu, k=5)
        for aday in adaylar:
            skor = _unsplash_sonucunu_clip_ile_puanla(aday["url"], sorgu)
            print(f"  CLIP skoru: {skor:.4f}")


if __name__ == "__main__":
    calistir()