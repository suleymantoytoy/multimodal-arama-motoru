# ============================================================
# Bu dosya, Reciprocal Rank Fusion (RRF) algoritmasini icerir.
#
# PROBLEM: Elimizde IKI farkli arama sonucu var:
#   1. CLIP (semantic) aramasinin sonuc siralamasi
#   2. BM25 (keyword) aramasinin sonuc siralamasi
# Bu ikisinin SKORLARI birbiriyle KARSILASTIRILAMAZ - CLIP'in
# skorlari 0-1 arasi cosine similarity, BM25'inkiler ise 0'dan
# yukari (10, 20 gibi) sinirsiz sayilar olabilir. Ikisini dogrudan
# toplayip "ortalama" almak ANLAMSIZ olur - farkli olcum birimleri.
#
# COZUM: RRF, SKORLARI DEGIL, SIRALARI (rank) kullanir. Yani "bu
# gorsel CLIP'te 3. sirada, BM25'te 7. sirada" gibi bilgiyi kullanir -
# skorlarin BUYUKLUGU onemli degil, sadece SIRASI onemli. Bu, RRF'yi
# hem basit hem de "adil" (iki farkli sistemi taraf tutmadan
# birlestiren) bir yontem yapar.
#
# FORMUL: Her gorsel icin, HER LISTEDE bulundugu sira numarasina
# gore bir "RRF skoru" hesaplanir:
#
#     RRF_skoru = sum( 1 / (k + sira) )
#
# Bu toplam, gorselin GECTIGI HER LISTE icin ayri ayri hesaplanip
# TOPLANIR. Yani bir gorsel hem CLIP'te hem BM25'te ust siralarda
# ciktiysa, iki kere "puan" alir ve toplam RRF skoru yuksek cikar -
# bu da onun NIHAI siralamada one cikmasini saglar.
#
# k=60 SABITI NEREDEN GELIYOR? Bu, RRF'nin orijinal akademik
# makalesinde (Cormack, Clarke, Buettcher 2009) onerilen ve
# pratikte iyi sonuc verdigi gozlemlenen standart bir deger.
# k'nin gorevi: siralamanin BASINDAKI (1., 2., 3. sira) farklarin
# etkisini biraz "yumusatmak" - k olmasa 1. sira ile 2. sira arasi
# skor farki cok BUYUK olurdu (1/1=1.0 vs 1/2=0.5, yani %50 fark),
# k=60 eklenince bu fark kuculuyor (1/61=0.0164 vs 1/62=0.0161,
# yani sadece %2 fark) - boylece siralamanin ALT kisimlarindaki
# kucuk farklar da anlamli katki yapabiliyor.
# ============================================================


def reciprocal_rank_fusion(sonuc_listeleri, k=60, agirliklar=None):
    """
    Birden fazla arama sonucu listesini RRF ile tek bir siralamada
    birlestirir.

    agirliklar: (YENI, istege bagli) her listenin katkisini carpan
    agirlik listesi, sonuc_listeleri ile AYNI uzunlukta olmali.
    None verilirse tum listeler esit agirlikli (1.0) sayilir; bu,
    eski davranisla BIREBIR aynidir.

    Formul: RRF_skoru = sum( agirlik / (k + sira) )
    """
    # Agirlik verilmediyse her liste icin 1.0 kullan (eski davranis)
    if agirliklar is None:
        agirliklar = [1.0] * len(sonuc_listeleri)
    # Agirlik sayisi liste sayisiyla uyusmuyorsa sessizce yanlis hesaplamak
    # yerine hemen hata ver
    if len(agirliklar) != len(sonuc_listeleri):
        raise ValueError("agirliklar, sonuc_listeleri ile ayni uzunlukta olmali")

    # Her kimligin toplam RRF skorunu bu sozlukte biriktiriyoruz
    rrf_skorlari = {}

    # zip: her listeyi KENDI agirligiyla birlikte geziyoruz
    for liste, agirlik in zip(sonuc_listeleri, agirliklar):
        # Listedeki her elemani 1'den baslayan sira numarasiyla geziyoruz
        for sira, kimlik in enumerate(liste, start=1):
            # Katki payi: agirlik / (k + sira). Agirlik 1.0 ise eski formulle ayni
            katki = agirlik / (k + sira)
            # Onceki skora ekle (kimlik ilk kez goruluyorsa 0'dan basla)
            rrf_skorlari[kimlik] = rrf_skorlari.get(kimlik, 0) + katki

    # Skora gore buyukten kucuge sirala
    siralanmis_sonuclar = sorted(
        rrf_skorlari.items(), key=lambda x: x[1], reverse=True
    )

    return siralanmis_sonuclar


# Bu dosya dogrudan calistirildiginda, RRF'nin nasil calistigini
# GORECEKTIGIMIZ basit, elle hazirlanmis bir ornekle test ediyoruz -
# gercek CLIP/BM25 verisi kullanmadan, sadece MANTIGIN dogru
# calistigini dogruluyoruz.
if __name__ == "__main__":
    # Elle hazirlanmis, sahte (ornek) iki arama sonucu listesi.
    clip_sonucu = ["A", "B", "C", "D"]
    bm25_sonucu = ["C", "A", "E", "F"]

    print("CLIP sonucu (sirali):", clip_sonucu)
    print("BM25 sonucu (sirali):", bm25_sonucu)

    birlesik = reciprocal_rank_fusion([clip_sonucu, bm25_sonucu])

    print("\nRRF ile birlesmis nihai siralama:")
    for kimlik, skor in birlesik:
        print(f"  {kimlik}: {skor:.4f}")

    # BEKLENEN SONUC: "A" ve "C" ikisi de HER IKI listede de var
    # (A: CLIP'te 1., BM25'te 2. | C: CLIP'te 3., BM25'te 1.) -
    # bu yuzden A ve C'nin RRF skoru, sadece TEK bir listede olan
    # B, D, E, F'den DAHA YUKSEK cikmali. Bu, hibrit aramanin
    # temel mantigi: "iki yontemde de one cikan sonuc, kazanir."