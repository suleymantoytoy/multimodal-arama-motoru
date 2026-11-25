# ============================================================
# Bu script, degerlendirme (Faz 4) icin bir TEST SETI olusturur.
#
# YONTEM: metadata.json'dan rastgele N tane gorsel seciyoruz. Her
# birinin BLIP caption'inin TAMAMINI dogrudan sorgu olarak kullaniyoruz.
#
# NEDEN TAM CAPTION? Ilk denemede caption'dan "ilk 2 kelimeyi al"
# gibi basit bir kisaltma yontemi kullanmistik, ama bu YANLIS
# KELIMEYI secme riski tasiyordu (orn. "a red car parked next to
# a bicycle" cumlesinde asil onemli kelime sonda olan "bicycle"
# olabilir, ama basit yontem "red car" secerdi). Tam caption'i
# kullanmak bu riski TAMAMEN ORTADAN KALDIRIR - hicbir bilgi
# kaybi olmaz, cunku BLIP'in urettigi TUM aciklama sorgu olarak
# kullaniliyor.
#
# KUCUK BIR FERAGAT: Gercek kullanicilar arama motoruna bu kadar
# uzun cumleler yazmaz genelde ("a dog" yazarlar, "a dog running
# in a green park" degil) - yani bu sorgular "gercek kullanici
# davranisi" acisindan biraz yapay. Ama bu, sistemin DOGRU CALISIP
# CALISMADIGINI olcme amacimizi ETKILEMEZ - sadece bir gozlem
# olarak not ediyoruz.
#
# NEDEN GORSEL SECIMI RASTGELE? Cunku veri setinin GENELINI temsil
# eden, taraf tutmayan bir ornek istiyoruz - elle secersek
# (bilincli ya da bilincsiz) "kolay" sorgulari secme egiliminde
# olabiliriz, bu da sonuclari olduğundan iyi gosterir.
# ============================================================

import json
import random

METADATA_DOSYASI = "data/metadata.json"
TEST_SETI_DOSYASI = "eval/test_sorgular.json"

# Kac tane sorgu-cevap cifti olusturacagiz. Roadmap'te 40-60
# onerilmisti, 50 ile ortasindan bir sayi seciyoruz.
SORGU_SAYISI = 50

# random.seed(): rastgele secimi HER ZAMAN AYNI sonucu verecek
# sekilde sabitliyoruz. Bu onemli - eger seed koymazsak, script'i
# her calistirdigimizde FARKLI bir test seti cikar, bu da
# sonuclarimizin TEKRARLANABILIR (reproducible) olmasini engeller.
random.seed(42)


def calistir():
    with open(METADATA_DOSYASI, "r", encoding="utf-8") as f:
        metadata_listesi = json.load(f)

    # random.sample(): listeden, TEKRARSIZ sekilde rastgele N tane
    # eleman secer (ayni gorsel iki kere secilmez).
    secilen_kayitlar = random.sample(metadata_listesi, SORGU_SAYISI)

    test_seti = []
    for kayit in secilen_kayitlar:
        # Caption'i KISALTMIYORUZ - dogrudan TAMAMINI sorgu olarak
        # kullaniyoruz. Bu, "dogru cevabin" garantili sekilde bu
        # sorguyla eslesmesini saglar.
        sorgu = kayit["caption"]

        test_seti.append({
            "sorgu": sorgu,
            "dogru_gorseller": [kayit["dosya"]],  # simdilik TEK dogru cevap
        })

    with open(TEST_SETI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(test_seti, f, ensure_ascii=False, indent=2)

    print(f"{len(test_seti)} sorgudan olusan test seti olusturuldu.")
    print(f"Kaydedildi: {TEST_SETI_DOSYASI}")
    print("\nIlk 5 ornek:")
    for kayit in test_seti[:5]:
        print(f"  Sorgu: '{kayit['sorgu']}'")


if __name__ == "__main__":
    calistir()