# ============================================================
# Bu dosya, BLIP modelini kullanarak bir gorsele bakip, o gorseli
# ACIKLAYAN bir metin (caption) uretir. Ornek: bir kopek fotografini
# verirsen, "a dog running in a park" gibi bir cumle doner.
#
# BU NEDEN ONEMLI? CLIP, gorseli dogrudan bir vektore ceviriyordu -
# ama BM25 (Faz 3'un bir sonraki adiminda yazacagimiz) klasik
# anahtar kelime aramasi, VEKTOR degil METIN uzerinde calisir.
# Yani gorsellerimizin "aranabilir" bir metin karsiligina ihtiyacimiz
# var - BLIP bize bunu sagliyor.
#
# CLIP ile BLIP'in farki: CLIP "bu gorsel ile bu metin ne kadar
# benzer" diye KARSILASTIRMA yapar. BLIP ise "bu gorsel ne anlatiyor"
# diye SIFIRDAN bir cumle URETIR (generation). Farkli bir model,
# farkli bir gorev.
# ============================================================

import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

# Ayni CLIP'te oldugu gibi, GPU varsa onu kullaniyoruz, yoksa CPU.
device = "cuda" if torch.cuda.is_available() else "cpu"

# BlipProcessor: gorseli, BLIP modelinin bekledigi formata (boyut,
# normalize edilmis piksel degerleri vb.) donusturen arac - CLIP'teki
# "preprocess" fonksiyonuna benzer bir gorevi var.
#
# "Salesforce/blip-image-captioning-base": Salesforce firmasinin
# yayinladigi, gorsellere aciklama uretmek icin ozel egitilmis,
# nispeten kucuk/hizli bir BLIP modeli (daha buyuk "large" versiyonu
# da var ama base, ogrenme asamasi icin yeterli ve daha hizli).
model_adi = "Salesforce/blip-image-captioning-base"

processor = BlipProcessor.from_pretrained(model_adi)
model = BlipForConditionalGeneration.from_pretrained(model_adi).to(device)

# model.eval(): CLIP'te oldugu gibi, modeli "sadece kullanim" moduna
# aliyoruz, egitim sirasinda kullanilan rastgelelik iceren islemleri
# kapatiyoruz.
model.eval()


def generate_caption(image_path):
    """
    Bir gorsel dosyasinin yolunu alir, BLIP ile o gorseli aciklayan
    bir cumle (caption) uretir ve metni geri dondurur.
    """
    # Gorseli ac, RGB'ye cevir (CLIP'teki ile ayni sebep - model hep
    # 3 renk kanalli gorsel bekler).
    gorsel = Image.open(image_path).convert("RGB")

    # processor(gorsel, return_tensors="pt"): gorseli modele
    # verilecek forma getirir. "pt" = PyTorch tensoru formatinda
    # dondur demek (baska kutuphaneler icin "tf" (TensorFlow) gibi
    # secenekler de olabilir, biz PyTorch kullandigimiz icin "pt").
    girdi = processor(gorsel, return_tensors="pt").to(device)

    with torch.no_grad():
        # model.generate(): BLIP'e "bu gorsel icin bir cumle URET"
        # diyoruz. Bu, CLIP'teki encode_image()'dan FARKLI bir islem -
        # orada tek bir vektor donuyordu, burada modelin kelime kelime
        # URETTIGI bir cumlenin token (sayisal kod) hali donuyor.
        #
        # max_new_tokens=30: modelin uretecegi cumlenin en fazla kac
        # kelime/parca (token) uzunlugunda olabilecegini sinirliyoruz -
        # cok uzun, gereksiz detayli cumleler uretmesini engelliyoruz.
        cikti = model.generate(**girdi, max_new_tokens=30)

    # processor.decode(): modelin urettigi sayisal token'lari, tekrar
    # OKUNABILIR bir metne (insan dili cumlesine) ceviriyoruz.
    # skip_special_tokens=True: modelin ic mekanizmasinda kullandigi,
    # "cumle burada basliyor/bitiyor" gibi ozel isaretleri (token'lari)
    # cikti metninden temizler - biz sadece duz, okunabilir cumleyi
    # istiyoruz.
    caption = processor.decode(cikti[0], skip_special_tokens=True)

    return caption


# Bu dosya dogrudan calistirildiginda, tek bir ornek gorsel uzerinde
# hizli bir test yapiyoruz.
if __name__ == "__main__":
    import os

    klasor = "data/raw_images"
    dosyalar = [f for f in os.listdir(klasor) if f.endswith(".jpg")]

    if not dosyalar:
        print("data/raw_images klasorunde hic .jpg dosyasi bulamadim!")
    else:
        # Ilk 3 gorseli test edelim, tek gorselle yetinmeyelim -
        # boylece modelin genel olarak makul cumleler urettigini
        # birden fazla ornekte gorebiliriz.
        for dosya_adi in dosyalar[:3]:
            tam_yol = os.path.join(klasor, dosya_adi)
            uretilen_caption = generate_caption(tam_yol)
            print(f"{dosya_adi} -> {uretilen_caption}")