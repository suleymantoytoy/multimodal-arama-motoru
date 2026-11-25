# ============================================================
# Bu script, data/raw_images klasorundeki gorseller icin BLIP ile
# otomatik caption (aciklama) uretir ve data/metadata.json dosyasina
# kaydeder.
#
# ONCE KUCUK OLCEKTE TEST EDIYORUZ: MAKS_GORSEL_SAYISI ile sinirli
# bir alt kumede calistirip SUREYI OLCECEGIZ. Bu sure bilgisiyle,
# TUM 5.000 gorsel icin ne kadar surecegini HESAPLAYIP, ondan sonra
# tam calistirmaya karar verecegiz - CLIP'te yaptigimiz gibi
# "once olc, sonra buyu" mantigini burada da uyguluyoruz.
# ============================================================

import os
import json
import time

from caption_generator import generate_caption

GORSEL_KLASORU = "data/raw_images"
METADATA_DOSYASI = "data/metadata.json"

# Once kucuk bir alt kumede test ediyoruz - TUM veri setine
# (5.000) gecmeden once suphesiz sure tahmini yapabilmek icin.
MAKS_GORSEL_SAYISI = 5000


def calistir():
    tum_dosyalar = [f for f in os.listdir(GORSEL_KLASORU) if f.endswith(".jpg")]
    secilen_dosyalar = tum_dosyalar[:MAKS_GORSEL_SAYISI]

    print(f"{len(secilen_dosyalar)} gorsel icin caption uretilecek...")
    print("(Bu bir SURE OLCUM testi - once kucuk oornekte deniyoruz)\n")

    metadata_listesi = []
    baslangic_zamani = time.time()

    for i, dosya_adi in enumerate(secilen_dosyalar):
        tam_yol = os.path.join(GORSEL_KLASORU, dosya_adi)
        try:
            caption = generate_caption(tam_yol)
            metadata_listesi.append({
                "dosya": tam_yol,
                "caption": caption,
            })
        except Exception as hata:
            print(f"HATA ({dosya_adi}): {hata}")

        # Her 50 gorselde bir ilerleme durumu yazdiralim, boylece
        # islemin canli oldugunu gorebiliriz (BLIP tek tek islendigi
        # icin bir ilerleme cubugu tqdm ile de kurulabilirdi, ama
        # burada basit bir sayac yeterli).
        if (i + 1) % 50 == 0:
            gecen_sure = time.time() - baslangic_zamani
            gorsel_basina_ortalama = gecen_sure / (i + 1)
            print(f"  {i+1}/{len(secilen_dosyalar)} islendi... "
                  f"(gorsel basina ortalama: {gorsel_basina_ortalama:.2f} saniye)")

    toplam_sure = time.time() - baslangic_zamani

    # Sonuclari diske kaydediyoruz.
    with open(METADATA_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(metadata_listesi, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------
    # SURE TAHMINI: 500 gorsel icin gecen sureden yola cikarak,
    # 5.000 gorsel (yani 10 kati) icin ne kadar surecegini
    # HESAPLIYORUZ - henuz gercekten 5.000'i islemeden once.
    # ------------------------------------------------------------
    gorsel_basina_ortalama = toplam_sure / len(secilen_dosyalar)
    tahmini_5000_suresi_dakika = (gorsel_basina_ortalama * 5000) / 60

    print(f"\n--- SURE RAPORU ({len(secilen_dosyalar)} gorsel) ---")
    print(f"Toplam sure: {toplam_sure:.1f} saniye ({toplam_sure/60:.2f} dakika)")
    print(f"Gorsel basina ortalama: {gorsel_basina_ortalama:.3f} saniye")
    print(f"\n>>> TAHMIN: 5.000 gorselin TAMAMI icin yaklasik "
          f"{tahmini_5000_suresi_dakika:.1f} dakika surer <<<")
    print(f"\nKaydedilen dosya: {METADATA_DOSYASI} ({len(metadata_listesi)} kayit)")


if __name__ == "__main__":
    calistir()