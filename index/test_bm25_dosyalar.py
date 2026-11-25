# ============================================================
# Bu, sadece BM25'in "bananas" sorgusu icin GERCEKTEN farkli
# dosyalari mi buldugunu, yoksa ayni dosyayi mi tekrar tekrar mi
# gosterdigini kontrol etmek icin yazilmis KUCUK bir test scripti.
# ============================================================

from bm25_index import bm25_index_kur, bm25_ara

# BM25 index'ini kuruyoruz (bm25_index.py'deki fonksiyonu cagirarak).
bm25, dosya_yollari, caption_listesi = bm25_index_kur()

# "bananas" sorgusu icin en iyi 5 sonucu aliyoruz.
sonuclar = bm25_ara(bm25, dosya_yollari, caption_listesi, "bananas", k=5)

# Her sonucun SADECE dosya adini yazdiriyoruz - boylece caption'lar
# ayni olsa bile, gercekten FARKLI dosyalar mi diye gozle kontrol
# edebiliyoruz.
print("'bananas' sorgusu icin bulunan dosyalar:")
for sonuc in sonuclar:
    print(f"  - {sonuc['dosya']}")