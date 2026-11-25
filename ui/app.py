import os
import streamlit as st
import requests
from PIL import Image

API_ADRESI = os.getenv("API_ADRESI", "http://127.0.0.1:8000")

st.set_page_config(page_title="Semantik Gorsel Arama Motoru", layout="wide")

st.title("🔍 Semantik Görsel Arama Motoru")
st.caption(
    "Önce kendi veri setimde ararım, bulamazsam internetten (Unsplash & Openverse) "
    "getirip Görsel Hakem (VLM) ile doğrularım, eksik kalanları yapay zeka ile üretirim."
)

sorgu = st.text_input("Ne aramak istersin?", placeholder="orn. a winged dog")
k = st.slider("Kaç sonuç gösterilsin?", min_value=1, max_value=10, value=4)

st.divider()
st.subheader("📷 Veya bir görsel yükleyerek benzerlerini bul")

yuklenen_dosya = st.file_uploader("Görsel seç", type=["jpg", "jpeg", "png", "webp", "bmp", "gif"])
gorsel_ara_butonu = st.button("🔎 Bu Görsele Benzerlerini Bul")


def _ogeyi_goster(oge):
    """Listedeki her bir sonucu kendi veri yapisina gore ekrana basar."""
    if isinstance(oge, (list, tuple)):
        dosya_yolu, skor = oge
        st.image(Image.open(dosya_yolu), use_container_width=True)
        st.caption(f"📁 Yerel Veri Seti (RRF: {skor:.4f})")
    elif isinstance(oge, dict):
        if oge.get("kaynak") == "ai_uretim" or "dosya" in oge:
            st.image(Image.open(oge["dosya"]), use_container_width=True)
            model_adi = oge.get("model", "AI")
            st.caption(f"🎨 AI ile üretildi ({model_adi})")
        elif "url" in oge:
            st.image(oge["url"], use_container_width=True)
            platform = oge.get("kaynak", "web").capitalize()
            st.caption(f"📷 {oge.get('fotografci', 'Anonim')} ({platform})")
    elif isinstance(oge, str):
        st.image(Image.open(oge), use_container_width=True)
        st.caption("📁 Yerel Görsel Arama")


if gorsel_ara_butonu and yuklenen_dosya is not None:
    with st.spinner("Aranıyor..."):
        try:
            dosyalar = {"dosya": (yuklenen_dosya.name, yuklenen_dosya.getvalue())}
            cevap = requests.post(
                f"{API_ADRESI}/search/image",
                files=dosyalar,
                params={"k": k},
                timeout=300,
            )
            cevap.raise_for_status()
            sonuc = cevap.json()

            skor_bilgisi = sonuc.get("en_iyi_skor", 0.0)
            kaynak = sonuc.get("kaynak", "bilinmiyor")

            if kaynak == "yerel_gorsel_arama":
                st.success(f"Yüklediğin görsele en yakın sonuçlar (kendi veri setimizden, skor: {skor_bilgisi:.4f}):")
            elif kaynak == "harici":
                st.info(
                    f"Kendi veri setimde yeterli benzerlik yoktu (skor: {skor_bilgisi:.4f}) - "
                    f"görselin şu tarifiyle arandı: *{sonuc.get('gorselden_uretilen_tarif', '')}*"
                )
            elif kaynak == "uretilen":
                st.warning(
                    f"Kendi veri setimde ve internette bulunamadı (skor: {skor_bilgisi:.4f}) - "
                    f"AI ile üretildi, tarif: *{sonuc.get('gorselden_uretilen_tarif', '')}*"
                )

            sonuclar_listesi = sonuc.get("sonuclar", [])
            if sonuclar_listesi:
                sutunlar = st.columns(len(sonuclar_listesi))
                for sutun, oge in zip(sutunlar, sonuclar_listesi):
                    with sutun:
                        _ogeyi_goster(oge)

        except Exception as hata:
            st.error(f"Bir hata oluştu: {hata}")

ara_butonu = st.button("🔎 Ara")

if ara_butonu and sorgu.strip():
    with st.spinner("Aranıyor ve Görsel Hakem ile doğrulanıyor... (eksik sonuç varsa AI ile tamamlanabilir)"):
        try:
            cevap = requests.post(
                f"{API_ADRESI}/search/text",
                json={"sorgu": sorgu, "k": k},
                timeout=300,
            )
            cevap.raise_for_status()
            sonuc = cevap.json()

        except requests.exceptions.ConnectionError:
            st.error(
                "API'ye bağlanılamadı! `uvicorn api.main:app --reload` "
                "komutunun ayrı bir terminalde çalıştığından emin ol."
            )
            st.stop()
        except Exception as hata:
            st.error(f"Bir hata oluştu: {hata}")
            st.stop()

    kaynak = sonuc.get("kaynak")
    kismi_uretim = sonuc.get("kismi_uretim", False)

    if kaynak == "yerel":
        st.success(f"✅ Kendi veri setimde bulundu ve Görsel Hakem ile doğrulandı (CLIP skoru: {sonuc['en_iyi_skor']:.3f})")
    elif kaynak == "harici" and kismi_uretim:
        st.info(
            "🌐✨ İnternette (Unsplash/Openverse) aranan kriterleri tam karşılayan sınırlı sayıda gerçek fotoğraf bulundu; "
            "eksik kalan sonuçlar **Yapay Zeka (AI)** ile üretilerek tamamlandı."
        )
    elif kaynak == "harici":
        st.info("🌐 Kendi veri setimde yeterli sonuç yoktu, bu görseller internetten getirilip Görsel Hakem ile doğrulandı.")
    elif kaynak == "uretilen":
        st.warning(
            f"🎨 Ne kendi veri setimde ne de internette doğrulanmış sonuç bulunabildi - "
            f"bu görseller YAPAY ZEKA TARAFINDAN ÜRETİLDİ.\n\n"
            f"Kullanılan son zenginleştirilmiş prompt: *{sonuc.get('zenginlestirilmis_prompt', '')}*"
        )

    sonuclar = sonuc.get("sonuclar", [])

    if not sonuclar:
        st.warning("Hiç sonuç bulunamadı.")
    else:
        sutunlar = st.columns(len(sonuclar))
        for sutun, oge in zip(sutunlar, sonuclar):
            with sutun:
                _ogeyi_goster(oge)