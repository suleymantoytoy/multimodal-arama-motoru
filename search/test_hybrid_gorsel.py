# ============================================================
# Bu script, hibrit_ara() fonksiyonunun bulduğu sonuclari, dosya
# adlarini elle aramaya GEREK KALMADAN, dogrudan ekranda GORSEL
# olarak gosterir.
#
# ONCEKI VERSIYONDAN FARKI: Artik sorgulari KOD ICINE YAZILI olarak
# tutmuyoruz - program calisinca TERMINALDE senden sorguyu soruyor,
# sen yaziyorsun. Boylece her yeni sorgu denemek istediginde dosyayi
# ACIP DUZENLEMENE gerek kalmiyor.
# ============================================================

import matplotlib.pyplot as plt
from PIL import Image

from hybrid_search import hibrit_ara


def sorgu_ara_ve_goster(sorgu_metni, k=5):
    """
    hibrit_ara() fonksiyonunu cagirir, donen sonuclari (dosya
    yolu + RRF skoru ciftlerini) ekranda kucuk resimler halinde
    yan yana gosterir.
    """
    sonuclar = hibrit_ara(sorgu_metni, k=k)

    fig, eksenler = plt.subplots(1, k, figsize=(4 * k, 4))
    fig.suptitle(f"Hibrit Arama Sorgusu: '{sorgu_metni}'", fontsize=16)

    for sira, (dosya_yolu, skor) in enumerate(sonuclar):
        gorsel = Image.open(dosya_yolu)
        eksenler[sira].imshow(gorsel)
        eksenler[sira].set_title(f"#{sira+1}\nRRF: {skor:.4f}", fontsize=10)
        eksenler[sira].axis("off")

    plt.tight_layout()
    plt.show()


# ============================================================
# ANA DONGU: Program calisinca surekli terminalde sorgu bekler.
# Sen bir sorgu yazip Enter'a basinca, sonuclari gorsel olarak
# gosterir, pencereyi kapatinca tekrar sorgu sorar. Cikmak icin
# "q" yazip Enter'a basman yeterli.
# ============================================================
if __name__ == "__main__":
    print("Hibrit arama test araci. Cikmak icin 'q' yazip Enter'a bas.\n")

    while True:
        # input(): terminalde kullaniciya bir mesaj gosterip, onun
        # yazdigi metni (Enter'a basana kadar olani) geri dondurur.
        sorgu = input("Aranacak sorguyu yaz: ").strip()

        # strip(): basta/sonda bosluk varsa temizler. Eger sorgu
        # bossa (sadece Enter'a basildiysa) veya "q" ise, dongudden
        # cikiyoruz.
        if sorgu.lower() == "q":
            print("Cikiliyor...")
            break

        if not sorgu:
            print("Bos sorgu girdin, tekrar dene.\n")
            continue

        sorgu_ara_ve_goster(sorgu)