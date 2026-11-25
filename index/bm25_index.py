# ============================================================
# Bu dosya, BLIP'in urettigi caption'lar (metin aciklamalar) uzerinde
# KLASIK ANAHTAR KELIME ARAMASI yapan bir BM25 index'i kurar.
#
# BM25 NEDIR? "Best Matching 25" - arama motorlarinin (eskiden
# Google'in bile) kullandigi, kelime frekansina dayali klasik bir
# siralama algoritmasi. CLIP'in yaptigi "anlam benzerligi" (semantic
# similarity) ile TAMAMEN FARKLI bir mantik kullanir:
#
#   CLIP (semantic): "kirmizi araba" yazinca, o kelimeleri metin
#   olarak icermeyen ama ANLAM olarak alakali gorselleri de bulabilir
#   (orn. caption'da "araba" gecmese bile gorselin CLIP vektoru
#   "araba" ile yakinsa bulunur).
#
#   BM25 (keyword/anahtar kelime): "kirmizi araba" yazinca, SADECE
#   caption'inda GERCEKTEN "kirmizi" VE/VEYA "araba" KELIMELERI GECEN
#   sonuclari bulur. Anlam onemli degil, KELIMENIN KENDISI onemli.
#
# NEDEN IKISINE DE IHTIYACIMIZ VAR? Cunku bazen kullanici cok spesifik
# bir kelime arar (orn. bir marka ismi, bir ozel isim) ve CLIP bunu
# "anlamca" yakalayamayabilir - BM25 boyle durumlarda daha guvenilir.
# Bir sonraki adimda (hybrid_search.py) ikisini BIRLESTIRECEGIZ.
# ============================================================

import json
from rank_bm25 import BM25Okapi

METADATA_DOSYASI = "data/metadata.json"


def bm25_index_kur():
    """
    metadata.json'daki tum caption'lari okuyup, bir BM25 index'i
    kurar. Ayrica, sonuc dondururken hangi index numarasinin hangi
    gorsele ait oldugunu bilmemiz gerektigi icin, dosya yollarinin
    listesini de geri donduruyoruz.
    """
    with open(METADATA_DOSYASI, "r", encoding="utf-8") as f:
        metadata_listesi = json.load(f)

    # BM25, her belgeyi (bizim durumumuzda her caption'i) bir KELIME
    # LISTESI olarak bekler, tek bir cumle (string) olarak degil.
    # Ornek: "a dog running in a park" -> ["a", "dog", "running", "in", "a", "park"]
    # .split() fonksiyonu, bir metni bosluklardan bolerek kelime
    # listesine cevirir - basit ama etkili bir "tokenization" yontemi.
    tokenize_edilmis_caption_listesi = [
        kayit["caption"].lower().split() for kayit in metadata_listesi
    ]
    # .lower(): tum harfleri kucuk harfe ceviriyoruz - boylece "Dog"
    # ile "dog" ayni kelime olarak sayilir, buyuk/kucuk harf farki
    # aramayi etkilemez.

    # BM25Okapi: rank_bm25 kutuphanesinin sundugu, en yaygin kullanilan
    # BM25 versiyonu. Kendisine tokenize edilmis (kelimelere bolunmus)
    # belgelerin (caption'larin) listesini veriyoruz, o da kendi
    # icinde hangi kelimenin hangi belgede kac kere gectigini
    # hesaplayip bir "index" olusturuyor.
    bm25 = BM25Okapi(tokenize_edilmis_caption_listesi)

    # Hangi index numarasinin (0, 1, 2, ...) hangi GORSEL DOSYASINA
    # ait oldugunu bilmemiz lazim - bu listeyi de saklayip donduruyoruz.
    # Ayni "\" / "/" sorunu burada da var - normalize ediyoruz.
    dosya_yollari = [kayit["dosya"].replace("\\", "/") for kayit in metadata_listesi]
    caption_listesi = [kayit["caption"] for kayit in metadata_listesi]

    return bm25, dosya_yollari, caption_listesi


def bm25_ara(bm25, dosya_yollari, caption_listesi, sorgu, k=10):
    """
    Verilen bir BM25 index'inde, sorgu metnine gore arama yapar.

    sorgu: aranacak metin (orn. "a red car")
    k: kac tane sonuc dondurulecek
    """
    # Sorguyu da AYNI SEKILDE (kucuk harfe cevirip kelimelere bolerek)
    # hazirliyoruz - index'i olustururken kullandigimiz yontemle
    # TUTARLI olmasi lazim, yoksa karsilastirma anlamsiz olur.
    sorgu_kelimeleri = sorgu.lower().split()

    # bm25.get_scores(): verilen sorgu kelimelerine gore, index'teki
    # HER BIR belge (caption) icin bir BM25 skoru hesaplar. Sonuc,
    # belge sayisi kadar uzunlukta bir sayi listesi doner - her sayi,
    # o caption'in sorguyla ne kadar "eslesip eslesmedigini" gosterir
    # (yuksek skor = daha alakali).
    skorlar = bm25.get_scores(sorgu_kelimeleri)

    # numpy kullanmadan, Python'un kendi araclariyla en yuksek skorlu
    # k taneyi buluyoruz. sorted() ile (index, skor) ciftlerini
    # skora gore BUYUKTEN KUCUGE siraliyoruz (reverse=True), sonra
    # ilk k taneyi aliyoruz.
    indeks_skor_ciftleri = list(enumerate(skorlar))
    siralanmis = sorted(indeks_skor_ciftleri, key=lambda x: x[1], reverse=True)
    en_iyi_k = siralanmis[:k]

    sonuclar = []
    for indeks, skor in en_iyi_k:
        sonuclar.append({
            "dosya": dosya_yollari[indeks],
            "caption": caption_listesi[indeks],
            "skor": skor,
        })

    return sonuclar


# Bu dosya dogrudan calistirildiginda, birkac ornek sorguyla
# BM25 aramasini test ediyoruz.
if __name__ == "__main__":
    print("BM25 index kuruluyor...")
    bm25, dosya_yollari, caption_listesi = bm25_index_kur()
    print("Index hazir.\n")

    test_sorgulari = ["dog", "bananas", "living room television"]

    for sorgu in test_sorgulari:
        print(f"--- Sorgu: '{sorgu}' ---")
        sonuclar = bm25_ara(bm25, dosya_yollari, caption_listesi, sorgu, k=5)
        for sira, sonuc in enumerate(sonuclar, start=1):
            print(f"{sira}. {sonuc['caption']}  (skor: {sonuc['skor']:.2f})")
        print()