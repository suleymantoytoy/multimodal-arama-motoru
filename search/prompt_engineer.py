# ============================================================
# Bu dosya, Faz 3.75'in "prompt engineering" katmanidir.
# Hem stok fotograf aramasi icin coklu anahtar kelime varyasyonlari
# uretir, hem de AI gorsel uretim modeli icin ana ozneyi kaybetmeyen
# net promptlar olusturur.
# ============================================================

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"

SABLON_ONEK = "A clear, photorealistic close-up or medium shot of "
SABLON_SONEK = ", sharp focus on the main subject, natural lighting, high quality, 4k"

_groq_client = None


def _client_olustur():
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY bulunamadi (.env dosyasini kontrol et).")
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _groq_ile_sor(talimat, temperature=0.6):
    try:
        client = _client_olustur()
        cevap = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": talimat}],
            temperature=temperature,
        )
        sonuc = (cevap.choices[0].message.content or "").strip().strip('"').strip()
        sonuc = sonuc.replace("\u2011", "-")
        return sonuc
    except Exception as hata:
        print(f"Groq cagrisi basarisiz oldu ({hata}).")
        return None


def zenginlestir_prompt(kullanici_sorgusu, varyasyon_no=0):
    """
    Kullanicinin sorgusunu AI gorsel uretim modeli (FLUX) icin zenginlestirir.
    ONEMLI: 'Wide establishing shot' gibi ana ozneyi manzarada kaybettiren
    ve 'kanatli kopek' yerine 'kartal' cizilmesine yol acan acilar kaldirildi.
    """
    varyasyon_ipuclari = [
        "Framing: clear medium shot at eye level, studio lighting.",
        "Framing: close-up portrait shot in a natural outdoor setting, soft sunlight.",
        "Framing: full-body shot standing clearly in the center of the frame, cinematic lighting.",
        "Framing: three-quarter angle shot, warm golden hour lighting, shallow depth of field.",
    ]
    ipucu = varyasyon_ipuclari[varyasyon_no % len(varyasyon_ipuclari)]

    talimat = (
        "Rewrite the following user query into a clear, photorealistic image generation prompt.\n\n"
        "CRITICAL RULES:\n"
        "1. The FIRST sentence MUST explicitly state the main subject and all requested objects/colors "
        f"from '{kullanici_sorgusu}'. Never replace or omit the main subject.\n"
        "2. If the query combines an animal with an unusual attribute (e.g. 'a winged dog', 'a cat with a mustache'), "
        "describe the actual animal clearly first (e.g. 'A real photorealistic dog with a clear canine face and four legs, "
        "wearing realistic angel/feathered wings on its back'). NEVER turn the animal into a bird or eagle.\n"
        "3. Keep the subject large and clearly visible in the center. Do NOT write poetic metaphors or distant landscapes.\n"
        f"4. {ipucu}\n"
        "5. Keep the ENTIRE response under 45 words. Reply with ONLY the prompt, no quotes, no slashes."
        f"\n\nUser query: {kullanici_sorgusu}"
    )

    sonuc = _groq_ile_sor(talimat, temperature=0.5)
    if sonuc and len(sonuc) > 15:
        return sonuc

    return f"{SABLON_ONEK}{kullanici_sorgusu}{SABLON_SONEK}"


def arama_sorgusu_zenginlestir(kullanici_sorgusu, temperature=0.4):
    """Geriye donuk uyumluluk icin tekil arama sorgusu dondurur."""
    sorgular = arama_sorgulari_uret(kullanici_sorgusu)
    return sorgular[0] if sorgular else kullanici_sorgusu


def arama_sorgulari_uret(kullanici_sorgusu):
    """
    Tek bir arama terimiyle sinirli kalmamak icin 3 farkli stok fotograf
    arama sorgusu uretir (orn. 'dog wearing wings', 'dog angel wings costume',
    'dog bat wings'). Boylece Unsplash'te daha fazla gercek fotograf yakalanir.
    """
    talimat = (
        "Generate 3 short, distinct stock-photo search queries (each 2 to 5 words) "
        "to find real photographs matching the user phrase.\n\n"
        "RULES:\n"
        "1. If the phrase gives an animal a feature it cannot naturally have (e.g. wings on a dog, horns on a horse, "
        "mustache on a cat), generate variations for a REAL photoshoot with costumes/props:\n"
        "   Example for 'a winged dog':\n"
        "   dog wearing wings\n"
        "   dog angel wings costume\n"
        "   dog halloween wings\n"
        "2. If the phrase is already a literal scene (e.g. 'a blue car in front of a yellow house'), "
        "provide 3 concise keyword variations keeping the key nouns and colors.\n"
        "3. Reply with ONLY the 3 queries, one per line, no numbering, no bullets, no quotes.\n\n"
        f"Phrase: {kullanici_sorgusu}"
    )

    sonuc = _groq_ile_sor(talimat, temperature=0.4)
    if sonuc:
        satirlar = [
            s.strip().strip("-*1234567890. \"'")
            for s in sonuc.splitlines()
            if len(s.strip()) > 2
        ]
        # Tekrarlari kaldirirken sirayi koru
        benzersiz = []
        for s in satirlar:
            if s.lower() not in [b.lower() for b in benzersiz]:
                benzersiz.append(s)
        if benzersiz:
            return benzersiz[:3]

    return [kullanici_sorgusu]