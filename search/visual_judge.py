# ============================================================
# Bu dosya, CLIP esigini gecen gorsellerin kullanici sorgusunu
# gercekten karsilayip karsilamadigini Groq VLM (qwen/qwen3.8-27b)
# ile denetler.
# ============================================================

import os
import io
import time
import base64
from PIL import Image
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

VLM_MODEL = "qwen/qwen3.8-27b"

_vlm_client = None


def _client_olustur():
    global _vlm_client
    if _vlm_client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY bulunamadi (.env dosyasini kontrol et).")
        _vlm_client = Groq(api_key=GROQ_API_KEY)
    return _vlm_client


def _gorseli_kucult_ve_kodla(gorsel_yolu, maks_boyut=384):
    """Gorseli 384x384 boyuta kuculterek token harcamasini ve gecikmeyi azaltir."""
    with Image.open(gorsel_yolu) as img:
        img = img.convert("RGB")
        img.thumbnail((maks_boyut, maks_boyut))
        tampon = io.BytesIO()
        img.save(tampon, format="JPEG", quality=80)
        return base64.b64encode(tampon.getvalue()).decode("utf-8")


def gorsel_hakem_onayla(gorsel_yolu, sorgu_metni):
    """
    Gorsel sorguyu tam olarak karsiliyorsa True, aksi halde False dondurur.
    """
    talimat = (
        "You are a strict visual relevance judge for an image search engine.\n"
        f"User query: '{sorgu_metni}'\n\n"
        "Does this image clearly and accurately show EVERY key element, attribute, "
        "color, and spatial relation in the user query?\n"
        "Strict Rules:\n"
        "1. Every requested object, color, and feature must be clearly visible.\n"
        "2. If a specific feature/costume is requested (e.g. wings, horns, mustache), "
        "it must actually be on that subject. A normal collar, bandana, scarf, or bow tie "
        "does NOT count as wings.\n"
        "3. Spatial relations (in front of, on top of, riding) and colors (e.g. blue car AND yellow house) "
        "must both be true at the same time.\n"
        "Answer with ONLY one word: yes or no."
    )

    client = _client_olustur()
    b64_gorsel = _gorseli_kucult_ve_kodla(gorsel_yolu)

    for deneme in range(2):
        try:
            cevap = client.chat.completions.create(
                model=VLM_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": talimat},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_gorsel}"},
                        },
                    ],
                }],
                temperature=0.0,
                max_completion_tokens=10,
                reasoning_effort="none",
            )

            yanit = (cevap.choices[0].message.content or "").strip().lower()
            onay = yanit.startswith("yes")
            print(f"    [VLM Hakem] Karar: {'ONAY (yes)' if onay else 'RED (no)'} (yanit: {yanit!r})")
            return onay

        except Exception as hata:
            if deneme == 0 and "429" in str(hata):
                print("    [VLM Hakem] Hiz siniri (429), 2 sn beklenip tekrar deneniyor...")
                time.sleep(2.0)
                continue
            # Hata durumunda onaysiz/alakasiz gorselin sizmasini onlemek icin False donuyoruz
            print(f"    [VLM Hakem UYARI] Cagri basarisiz ({hata}), guvenlik icin RED sayildi.")
            return False
    return False