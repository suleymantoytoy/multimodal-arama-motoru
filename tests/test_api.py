# ============================================================
# Bu dosya, projenin UCTAN UCA calistigini dogrulayan basit bir
# entegrasyon testidir. "Entegrasyon testi" demek: tek bir fonksiyonu
# degil, BIRDEN FAZLA parcanin (API + arama mantigi + modeller)
# BIRLIKTE dogru calistigini test etmek demek.
#
# NASIL CALISTIRILIR? Once API'nin AYAKTA olmasi lazim (ayri bir
# terminalde "uvicorn api.main:app --reload" calisiyor olmali),
# sonra bu test dosyasi calistirilir - test, GERCEK bir HTTP istegi
# atar, tipki Swagger arayuzunde elle yaptigimiz gibi, ama bu sefer
# OTOMATIK ve TEKRARLANABILIR sekilde.
# ============================================================

import requests

API_ADRESI = "http://127.0.0.1:8000"


def test_saglik_kontrolu():
    """
    /health endpoint'inin calistigini ve dogru formatta cevap
    verdigini kontrol eder.
    """
    cevap = requests.get(f"{API_ADRESI}/health")

    # assert: bu kosul DOGRU degilse, test BASARISIZ sayilir ve
    # bir hata firlatir. Testin "iddia ettigi" sey budur.
    assert cevap.status_code == 200, "Health check basarisiz oldu!"
    assert cevap.json().get("durum") == "calisiyor", "Beklenmeyen cevap formati!"

    print("test_saglik_kontrolu: BASARILI")


def test_metin_arama():
    """
    /search/text endpoint'inin basit bir sorguya DOGRU FORMATTA
    cevap verdigini kontrol eder. Sonucun ICERIGINI (hangi gorsel
    geldi gibi) degil, sadece YAPISININ dogru oldugunu kontrol
    ediyoruz - bu, "sistem coktu mu" sorusuna cevap veren bir test,
    "sonuclar mukemmel mi" sorusuna degil (o, Faz 4'teki evaluate.py'nin isi).
    """
    cevap = requests.post(
        f"{API_ADRESI}/search/text",
        json={"sorgu": "a dog", "k": 3},
        timeout=180,  # uretim katmanina duserse uzun surebilir
    )

    assert cevap.status_code == 200, "Metin arama istegi basarisiz oldu!"

    veri = cevap.json()
    assert "kaynak" in veri, "Cevapta 'kaynak' alani eksik!"
    assert veri["kaynak"] in ["yerel", "harici", "uretilen"], "Gecersiz kaynak degeri!"
    assert "sonuclar" in veri, "Cevapta 'sonuclar' alani eksik!"
    assert len(veri["sonuclar"]) > 0, "Hic sonuc donmedi!"

    print(f"test_metin_arama: BASARILI (kaynak: {veri['kaynak']})")


if __name__ == "__main__":
    print("Entegrasyon testleri baslatiliyor...\n")
    print("NOT: API'nin ayri bir terminalde calisiyor olmasi gerekiyor")
    print("(uvicorn api.main:app --reload)\n")

    test_saglik_kontrolu()
    test_metin_arama()

    print("\nTum testler basariyla tamamlandi!")