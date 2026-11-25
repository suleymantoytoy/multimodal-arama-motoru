import os
import io
import random
import urllib.parse
import requests
from PIL import Image
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

FLUX_MODELI = "black-forest-labs/FLUX.1-schnell"

_hf_client = None
_hf_kredi_bitti = False


def _hf_client_olustur():
    global _hf_client
    if _hf_client is None:
        if not HF_TOKEN:
            raise RuntimeError("HF_TOKEN bulunamadi.")
        _hf_client = InferenceClient(token=HF_TOKEN, timeout=15)
    return _hf_client


def _flux_hf_ile_uret(prompt):
    global _hf_kredi_bitti
    if _hf_kredi_bitti:
        raise RuntimeError("HF kredisi tukenmis durumda.")

    client = _hf_client_olustur()
    rastgele_seed = random.randint(0, 2**32 - 1)
    print(f"[image_generation] HF FLUX.1-schnell deneniyor (seed={rastgele_seed})...")
    try:
        return client.text_to_image(prompt, model=FLUX_MODELI, seed=rastgele_seed)
    except Exception as hata:
        # Herhangi bir kredi/odeme veya API hatasinda bu oturumda HF'yi bir daha deneme
        _hf_kredi_bitti = True
        raise hata


def _pollinations_ile_uret(prompt, model_adi="flux", timeout_sn=18):
    """
    Pollinations bulut API'si ile hizli gorsel uretir.
    enhance=false sayesinde prompt bozulmaz, kisa timeout sayesinde sistem asili kalmaz.
    """
    temiz_prompt = " ".join(prompt.replace("/", " ").replace("\n", " ").split())
    kodlanmis_prompt = urllib.parse.quote(temiz_prompt, safe="")
    rastgele_seed = random.randint(1, 99999999)
    url = (
        f"https://image.pollinations.ai/prompt/{kodlanmis_prompt}"
        f"?width=768&height=768&seed={rastgele_seed}&model={model_adi}&nologo=true&enhance=false"
    )
    basliklar = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    print(f"[image_generation] Bulut ({model_adi}) ile uretiliyor (seed={rastgele_seed})...")
    cevap = requests.get(url, headers=basliklar, timeout=timeout_sn)
    cevap.raise_for_status()
    return Image.open(io.BytesIO(cevap.content)).convert("RGB")


def gorsel_uret(prompt, cikti_klasoru="data/uretilen_gorseller", dosya_adi=None):
    os.makedirs(cikti_klasoru, exist_ok=True)

    kullanilan_model = "FLUX.1-schnell (HF)"
    try:
        gorsel = _flux_hf_ile_uret(prompt)
    except Exception:
        try:
            kullanilan_model = "FLUX.1 (Bulut)"
            gorsel = _pollinations_ile_uret(prompt, model_adi="flux", timeout_sn=18)
        except Exception as flux_hata:
            print(f"[image_generation] Bulut FLUX gecikti ({flux_hata}) -> Hizli Bulut Turbo'ya geciliyor...")
            kullanilan_model = "SDXL-Turbo (Bulut)"
            gorsel = _pollinations_ile_uret(prompt, model_adi="turbo", timeout_sn=12)

    if dosya_adi is None:
        dosya_adi = f"uretilen_{abs(hash(prompt)) % 100000}_{random.randint(1000, 9999)}.png"

    yol = os.path.join(cikti_klasoru, dosya_adi)
    gorsel.save(yol)
    print(f"[image_generation] Kaydedildi ({kullanilan_model}): {yol}")

    return yol, kullanilan_model