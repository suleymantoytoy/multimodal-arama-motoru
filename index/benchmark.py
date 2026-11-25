# ============================================================
# Bu script, kurdugumuz 3 index tipini (Flat, IVF, HNSW) HIZ ve
# DOGRULUK acisindan karsilastirir.
#
# Dogruluk nasil olculur? Flat index %100 dogru kabul edilir
# (cunku o, TUM vektorleri tek tek karsilastirir - yanilma sansi
# yok). IVF ve HNSW'nin bulduğu sonuclarin, Flat'in bulduğu
# sonuclarla NE KADAR ORTUSTUGUNE bakariz. Ortusme orani ne kadar
# yuksekse, o index o kadar "guvenilir" demektir.
#
# BU VERSIYONDA IKI IYILESTIRME VAR:
#   1. Sorgu sayisi 10'dan 25'e cikarildi - daha genis bir ornek
#      uzerinden olcum yapmak, tesadufi sapmalari azaltir.
#   2. Her sorgu icin arama, TEK SEFER degil 5 KEZ tekrarlanip
#      ortalamasi aliniyor - cunku bilgisayarin o anki yuku
#      (baska programlar, isletim sistemi islemleri vb.) tek bir
#      olcumu hafifce carpitabilir. Ortalama almak bu "gurultuyu"
#      azaltir, daha guvenilir bir sure verir.
# ============================================================

import faiss
import numpy as np
import json
import time
import sys
import os

# clip_encoder.py, embeddings klasorunde - onu buradan import
# edebilmek icin Python'a "embeddings klasorune de bak" diyoruz.
# sys.path, Python'un "import ederken hangi klasorlere bakayim"
# diye kontrol ettigi liste - buraya embeddings klasorunun tam
# yolunu ekliyoruz.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "embeddings"))
from clip_encoder import encode_text

EMBEDDING_DOSYASI = "data/full_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/full_image_paths.json"

# Test edecegimiz sorgular - 25 tane, COCO veri setinde sikca
# gecen kategorileri (kopek, kedi, bisiklet, araba, mobilya vb.)
# ve biraz daha soyut/genel ifadeleri karisik olarak iceriyor.
TEST_SORGULARI = [
    "a dog",
    "a cat",
    "food on a table",
    "a person riding a bike",
    "a car on the street",
    "a group of people",
    "a bathroom",
    "an airplane",
    "a laptop computer",
    "a bowl of fruit",
    "a person playing tennis",
    "a kitchen",
    "a living room with a couch",
    "a busy street",
    "a train",
    "a boat on water",
    "children playing",
    "a birthday cake",
    "a snowy mountain",
    "a beach",
    "a stop sign",
    "an umbrella",
    "a clock",
    "a teddy bear",
    "a pizza",
]

K = 10  # her sorgu icin ilk kac sonuca bakacagiz

# Her sorguyu kac kez tekrarlayip ortalama alacagimiz. 5 tekrar,
# olcumdeki tesadufi sapmalari makul bir surede azaltmaya yeter -
# cok fazla tekrar (orn. 100) hem gereksiz uzun surer hem de
# bu olcek icin ek bir dogruluk kazandirmaz.
TEKRAR_SAYISI = 5


def index_yukle():
    """
    Faiss_index.py'de diske kaydettigimiz 3 index dosyasini
    (flat_index.faiss, ivf_index.faiss, hnsw_index.faiss) geri okur.
    """
    return {
        "flat": faiss.read_index("index/flat_index.faiss"),
        "ivf": faiss.read_index("index/ivf_index.faiss"),
        "hnsw": faiss.read_index("index/hnsw_index.faiss"),
    }


def benchmark_calistir():
    print("Index'ler yukleniyor...")
    indexler = index_yukle()

    # Her index tipi icin, tum sorgular boyunca biriken TOPLAM
    # sureyi ve (Flat haric) ortusme oranlarini burada toplayacagiz.
    sonuclar = {isim: {"toplam_sure": 0.0, "ortusme_oranlari": []} for isim in indexler}

    print(f"{len(TEST_SORGULARI)} sorgu, her biri {TEKRAR_SAYISI} kez tekrarlanacak...\n")

    # Her sorgu icin, UCU DE index'te ayni sorguyla arama yapacagiz.
    for sorgu in TEST_SORGULARI:
        # Sorguyu vektore ceviriyoruz - bu islemi sorgu basina SADECE
        # BIR KEZ yapiyoruz (metni vektore cevirmek de zaman alir,
        # ama biz sadece ARAMA suresini olcmek istiyoruz, embedding
        # cikarma suresini degil - o yuzden bunu tekrar dongusunun
        # DISINDA yapiyoruz).
        sorgu_vektoru = encode_text(sorgu).reshape(1, -1).astype("float32")

        # Flat index'in bulduğu sonuclari burada saklayacagiz - digerlerini
        # bununla (dogru kabul ettigimiz referansla) karsilastiracagiz.
        flat_sonuc_indeksleri = None

        for isim, index in indexler.items():
            # Bu sorgu + bu index icin yapilan TUM tekrarlarin
            # surelerini burada topluyoruz.
            bu_kombinasyonun_sureleri = []

            for tekrar in range(TEKRAR_SAYISI):
                baslangic = time.time()
                _, I = index.search(sorgu_vektoru, K)
                gecen_sure = time.time() - baslangic
                bu_kombinasyonun_sureleri.append(gecen_sure)

            # 5 tekrarin ORTALAMASINI aliyoruz - tek bir olcume
            # guvenmek yerine.
            ortalama_sure = np.mean(bu_kombinasyonun_sureleri)
            sonuclar[isim]["toplam_sure"] += ortalama_sure

            # Dogruluk (ortusme) karsilastirmasi icin en son yapilan
            # aramanin sonucunu kullaniyoruz (hepsi ayni sonucu
            # verir zaten, cunku ayni sorgu ayni index'te araniyor -
            # sadece SURE olcumu tekrarlaniyor, sonuc degismez).
            if isim == "flat":
                flat_sonuc_indeksleri = set(I[0])
            else:
                bu_sonuc = set(I[0])
                ortusen = len(bu_sonuc & flat_sonuc_indeksleri)
                oran = ortusen / K
                sonuclar[isim]["ortusme_oranlari"].append(oran)

    # ------------------------------------------------------------
    # Sonuclari okunakli bir tabloya dokuyoruz.
    #
    # Not: Basliklari degiskenlere atadik cunku "Flat'e Gore" gibi
    # icinde Turkce kesme isareti (') olan bir metni dogrudan f-string
    # icinde yazarsak, Python o kesme isaretini string'in bittigi yer
    # saniyor ve SyntaxError veriyor. Degiskene atayip f-string icinde
    # sadece degiskeni kullanmak bu sorunu tamamen ortadan kaldirir.
    # ------------------------------------------------------------
    baslik_1 = "Index Tipi"
    baslik_2 = "Ort. Sure (ms)"
    baslik_3 = "Flat ile Ortusme"

    print(f"\n{baslik_1:<10} {baslik_2:<18} {baslik_3:<20}")
    print("-" * 50)

    for isim, veri in sonuclar.items():
        # Ortalama sureyi saniyeden milisaniyeye ceviriyoruz (*1000)
        # cunku bu kadar kucuk sureler icin ms daha okunakli.
        ort_sure_ms = (veri["toplam_sure"] / len(TEST_SORGULARI)) * 1000

        if isim == "flat":
            referans_yazisi = "(referans)"
            print(f"{isim:<10} {ort_sure_ms:<18.3f} {referans_yazisi:<20}")
        else:
            ort_ortusme = np.mean(veri["ortusme_oranlari"]) * 100
            print(f"{isim:<10} {ort_sure_ms:<18.3f} {ort_ortusme:<20.1f}%")


if __name__ == "__main__":
    benchmark_calistir()