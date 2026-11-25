import sys
import os
import tempfile
import requests
import numpy as np
import faiss
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "embeddings"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "index"))

from clip_encoder import encode_text, encode_image
from bm25_index import bm25_index_kur, bm25_ara
from rerank import reciprocal_rank_fusion

HARICI_ESIK = 0.25
EMBEDDING_DOSYASI = "data/full_embeddings.npy"
YOL_LISTESI_DOSYASI = "data/full_image_paths.json"
HNSW_INDEX_DOSYASI = "index/hnsw_index.faiss"

print("Hibrit arama sistemi baslatiliyor (index'ler yukleniyor)...")

_hnsw_index = faiss.read_index(HNSW_INDEX_DOSYASI)
with open(YOL_LISTESI_DOSYASI, "r") as f:
    _clip_dosya_yollari_ham = json.load(f)
    _clip_dosya_yollari = [yol.replace("\\", "/") for yol in _clip_dosya_yollari_ham]

_bm25, _bm25_dosya_yollari, _bm25_caption_listesi = bm25_index_kur()

print("Hazir.\n")


def _clip_ile_ara(sorgu_metni, k=20):
    sorgu_vektoru = encode_text(sorgu_metni).reshape(1, -1).astype("float32")
    _, I = _hnsw_index.search(sorgu_vektoru, k)
    return [_clip_dosya_yollari[indeks] for indeks in I[0]]


def _bm25_ile_ara(sorgu_metni, k=20):
    sonuclar = bm25_ara(_bm25, _bm25_dosya_yollari, _bm25_caption_listesi, sorgu_metni, k=k)
    return [sonuc["dosya"] for sonuc in sonuclar]


def hibrit_ara(sorgu_metni, k=10):
    clip_sonuclari = _clip_ile_ara(sorgu_metni, k=20)
    bm25_sonuclari = _bm25_ile_ara(sorgu_metni, k=20)
    birlesik_siralama = reciprocal_rank_fusion([clip_sonuclari, bm25_sonuclari])
    return birlesik_siralama[:k]


def _en_iyi_clip_skoru(sorgu_metni):
    sorgu_vektoru = encode_text(sorgu_metni).reshape(1, -1).astype("float32")
    D, _ = _hnsw_index.search(sorgu_vektoru, 1)
    return float(D[0][0])


def _gorsel_indir(gorsel_url):
    cevap = requests.get(gorsel_url, timeout=6)
    cevap.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as gecici_dosya:
        gecici_dosya.write(cevap.content)
        return gecici_dosya.name


def _aday_indir_gorevi(aday):
    try:
        yol = _gorsel_indir(aday["url"])
        return aday, yol
    except Exception:
        return aday, None


def _unsplash_sonucunu_clip_ile_puanla(gorsel_url, sorgu_metni):
    gecici_yol = None
    try:
        gecici_yol = _gorsel_indir(gorsel_url)
        gorsel_vektoru = encode_image(gecici_yol)
        sorgu_vektoru = encode_text(sorgu_metni)
        return float(np.dot(gorsel_vektoru, sorgu_vektoru))
    except Exception as hata:
        print(f"Unsplash gorseli puanlanirken hata: {hata}")
        return 0.0
    finally:
        if gecici_yol and os.path.exists(gecici_yol):
            os.remove(gecici_yol)


def _tek_ai_gorsel_uret_gorevi(args):
    """Paralel AI uretimi icin tekil gorev fonksiyonu."""
    sorgu_metni, varyasyon_no = args
    from prompt_engineer import zenginlestir_prompt
    from image_generation import gorsel_uret

    try:
        zengin_prompt = zenginlestir_prompt(sorgu_metni, varyasyon_no=varyasyon_no)
        uretilen_yol, kullanilan_model = gorsel_uret(zengin_prompt)
        return {
            "dosya": uretilen_yol,
            "kaynak": "ai_uretim",
            "model": kullanilan_model,
            "prompt": zengin_prompt,
        }
    except Exception as hata:
        print(f"[akilli_ara] AI Gorsel (varyasyon {varyasyon_no}) BASARISIZ: {hata}")
        return None


def _ai_ile_eksikleri_uret(sorgu_metni, adet):
    """
    ONEMLI HIZLANDIRMA: Istenen adet kadar AI gorselini SIRAYLA degil,
    ThreadPoolExecutor ile AYNI ANDA (paralel) uretir. Boylece 4 gorsel
    uretimi 4 kat surmez, tek gorsel suresinde (~10-15 sn) biter.
    """
    print(f"[akilli_ara] {adet} adet AI gorseli PARALEL olarak uretiliyor...")
    gorevler = [(sorgu_metni, i) for i in range(adet)]

    with ThreadPoolExecutor(max_workers=min(adet, 4)) as havuz:
        sonuclar = list(havuz.map(_tek_ai_gorsel_uret_gorevi, gorevler))

    uretilenler = []
    son_prompt = None
    for s in sonuclar:
        if s is not None:
            son_prompt = s.pop("prompt", None)
            uretilenler.append(s)

    return uretilenler, son_prompt


def akilli_ara(sorgu_metni, k=10, esik=0.29):
    from visual_judge import gorsel_hakem_onayla

    en_iyi_skor = _en_iyi_clip_skoru(sorgu_metni)
    print(f"[akilli_ara] '{sorgu_metni}' icin en iyi yerel CLIP skoru: {en_iyi_skor:.4f} (esik: {esik})")

    # --- KATMAN 1: YEREL ARAMA + VLM HAKEM ---
    if en_iyi_skor >= esik:
        yerel_adaylar = hibrit_ara(sorgu_metni, k=min(k + 2, 6))
        onaylanan_yerel = []
        print(f"[akilli_ara] Yerel adaylar VLM Hakem ile dogrulaniyor...")
        for dosya_yolu, rrf_skoru in yerel_adaylar:
            if gorsel_hakem_onayla(dosya_yolu, sorgu_metni):
                onaylanan_yerel.append((dosya_yolu, rrf_skoru))
                if len(onaylanan_yerel) >= k:
                    break

        if len(onaylanan_yerel) >= k or (len(onaylanan_yerel) > 0 and en_iyi_skor >= 0.32):
            return {
                "kaynak": "yerel",
                "en_iyi_skor": en_iyi_skor,
                "sonuclar": onaylanan_yerel[:k],
            }
        print("[akilli_ara] Yerel adaylar VLM Hakem'i gecemedi - HARICI aramaya geciliyor...")

    # --- KATMAN 2: HARICI ARAMA + PARALEL INDIRME + CLIP + VLM HAKEM ---
    from external_search import unsplash_ile_ara, openverse_ile_ara
    from prompt_engineer import arama_sorgulari_uret

    arama_sorgulari = arama_sorgulari_uret(sorgu_metni)
    print(f"[akilli_ara] Harici arama varyasyonlari: {arama_sorgulari}")

    harici_adaylar = []
    gorulen_temel_urller = set()

    # Maksimum 2 varyasyon + Openverse ile aday havuzunu makul boyutta (maks ~12 aday) tut
    for alt_sorgu in arama_sorgulari[:2]:
        for aday in unsplash_ile_ara(alt_sorgu, k=5):
            temel_url = aday["url"].split("?")[0]
            if temel_url not in gorulen_temel_urller:
                gorulen_temel_urller.add(temel_url)
                harici_adaylar.append(aday)

    for aday in openverse_ile_ara(arama_sorgulari[0], k=3):
        temel_url = aday["url"].split("?")[0]
        if temel_url not in gorulen_temel_urller:
            gorulen_temel_urller.add(temel_url)
            harici_adaylar.append(aday)

    onaylanan_harici = []
    en_iyi_harici_skor = 0.0

    if harici_adaylar:
        print(f"[akilli_ara] {len(harici_adaylar)} aday paralel indiriliyor ve CLIP ile puanlaniyor...")
        sorgu_vektoru = encode_text(sorgu_metni)
        indirilen_adaylar = []

        with ThreadPoolExecutor(max_workers=10) as havuz:
            indirilen_ciftler = list(havuz.map(_aday_indir_gorevi, harici_adaylar))

        for aday, gecici_yol in indirilen_ciftler:
            if not gecici_yol:
                continue
            try:
                gorsel_vektoru = encode_image(gecici_yol)
                skor = float(np.dot(gorsel_vektoru, sorgu_vektoru))
                en_iyi_harici_skor = max(en_iyi_harici_skor, skor)
                print(f"  - [{aday['kaynak']}] {aday['url'][:48]}... CLIP skoru: {skor:.4f}")

                if skor >= HARICI_ESIK:
                    indirilen_adaylar.append((aday, skor, gecici_yol))
                else:
                    os.remove(gecici_yol)
            except Exception:
                if os.path.exists(gecici_yol):
                    os.remove(gecici_yol)

        indirilen_adaylar.sort(key=lambda x: x[1], reverse=True)

        if indirilen_adaylar:
            # Sadece en yuksek skorlu (k + 1) adayi VLM Hakem'e sor (hiz icin)
            maks_vlm_adayi = k + 1
            print(f"[akilli_ara] En iyi {min(len(indirilen_adaylar), maks_vlm_adayi)} aday VLM Hakem ile denetleniyor...")
            for idx, (aday, skor, gecici_yol) in enumerate(indirilen_adaylar):
                if idx < maks_vlm_adayi and len(onaylanan_harici) < k:
                    if gorsel_hakem_onayla(gecici_yol, sorgu_metni):
                        onaylanan_harici.append(aday)
                if os.path.exists(gecici_yol):
                    os.remove(gecici_yol)

        if len(onaylanan_harici) >= k:
            return {
                "kaynak": "harici",
                "en_iyi_skor": en_iyi_skor,
                "harici_clip_skoru": en_iyi_harici_skor,
                "sonuclar": onaylanan_harici[:k],
            }

        if 0 < len(onaylanan_harici) < k:
            eksik_adet = k - len(onaylanan_harici)
            print(
                f"[akilli_ara] Web'de {len(onaylanan_harici)}/{k} dogru gorsel onaylandi. "
                f"Eksik {eksik_adet} gorsel AI ile PARALEL tamamlanacak..."
            )
            uretilen_ekler, son_prompt = _ai_ile_eksikleri_uret(sorgu_metni, eksik_adet)
            return {
                "kaynak": "harici",
                "kismi_uretim": True,
                "en_iyi_skor": en_iyi_skor,
                "harici_clip_skoru": en_iyi_harici_skor,
                "zenginlestirilmis_prompt": son_prompt,
                "sonuclar": onaylanan_harici + uretilen_ekler,
            }

        print("[akilli_ara] Harici adaylarin HICBIRI VLM Hakem'i gecemedi - TAM URETIME geciliyor...")
    else:
        print("[akilli_ara] Harici kaynaklarda hic sonuc bulunamadi - TAM URETIME geciliyor...")

    # --- KATMAN 3: TAM AI URETIM (PARALEL) ---
    uretilen_sonuclar, son_kullanilan_prompt = _ai_ile_eksikleri_uret(sorgu_metni, k)
    return {
        "kaynak": "uretilen",
        "en_iyi_skor": en_iyi_skor,
        "zenginlestirilmis_prompt": son_kullanilan_prompt,
        "sonuclar": uretilen_sonuclar,
    }