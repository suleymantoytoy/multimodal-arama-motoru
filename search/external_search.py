# ============================================================
# Bu dosya, Unsplash ve Openverse API'lerini kullanarak INTERNETTEN
# gorsel arar. Yerel veri setimizde (5.000 COCO gorseli) yeterli
# eslesme bulunamadiginda devreye giren "YEDEK PLAN" (fallback)
# katmanidir.
# ============================================================

import os
import requests
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_ARAMA_URL = "https://api.unsplash.com/search/photos"
OPENVERSE_ARAMA_URL = "https://api.openverse.org/v1/images/"
OPENVERSE_BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}


def unsplash_ile_ara(sorgu_metni, k=5):
    """Unsplash API'sinden gorsel adaylari getirir."""
    if not UNSPLASH_ACCESS_KEY:
        print("UYARI: UNSPLASH_ACCESS_KEY bulunamadi (.env dosyasini kontrol et).")
        return []

    parametreler = {
        "query": sorgu_metni,
        "per_page": k,
        "client_id": UNSPLASH_ACCESS_KEY,
    }

    try:
        cevap = requests.get(UNSPLASH_ARAMA_URL, params=parametreler, timeout=10)
        cevap.raise_for_status()
        veri = cevap.json()

        sonuclar = []
        for gorsel in veri.get("results", []):
            sonuclar.append({
                "url": gorsel["urls"]["regular"],
                "fotografci": gorsel["user"]["name"],
                "kaynak": "unsplash",
            })
        return sonuclar

    except requests.exceptions.RequestException as hata:
        print(f"Unsplash arama hatasi: {hata}")
        return []


def openverse_ile_ara(sorgu_metni, k=5):
    """Openverse API'sinden (API anahtari gerektirmez) ek gorsel adaylari getirir."""
    parametreler = {"q": sorgu_metni, "page_size": k}
    try:
        cevap = requests.get(
            OPENVERSE_ARAMA_URL, params=parametreler, headers=OPENVERSE_BASLIK, timeout=15
        )
        if cevap.status_code != 200:
            return []

        sonuclar = []
        for s in cevap.json().get("results", []):
            gorsel_url = s.get("thumbnail") or s.get("url")
            if not gorsel_url:
                continue
            sonuclar.append({
                "url": gorsel_url,
                "fotografci": s.get("creator") or "Anonim",
                "kaynak": "openverse",
            })
        return sonuclar
    except Exception as hata:
        print(f"Openverse arama hatasi: {hata}")
        return []


def harici_kaynaklarda_ara(sorgu_metni, k=8):
    """
    Hem Unsplash hem Openverse uzerinde arama yaparak aday havuzunu
    birlestirir. Boylece tek bir stok fotograf sitesinin sinirlarina
    takilmayiz.
    """
    unsplash_adaylari = unsplash_ile_ara(sorgu_metni, k=k)
    openverse_adaylari = openverse_ile_ara(sorgu_metni, k=max(4, k // 2))
    return unsplash_adaylari + openverse_adaylari


if __name__ == "__main__":
    test_sorgusu = "dog wearing wings"
    sonuclar = harici_kaynaklarda_ara(test_sorgusu, k=4)
    for i, s in enumerate(sonuclar, 1):
        print(f"{i}. [{s['kaynak']}] {s['url']} ({s['fotografci']})")