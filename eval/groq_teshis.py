# ============================================================
# Bu script, arama_sorgusu_degiskenlik.py'de gorulen "basarisiz"
# cagrilarin NEDENINI bulmak icin Groq'un HAM yanitini gosterir.
# Uretim dosyasina (prompt_engineer.py) DOKUNMAZ: _groq_ile_sor
# fonksiyonunu sadece bu script calisirken, bellekte degistirir.
#
# ON-KAYITLI YORUMLAMA:
#   - ham = '' (bos) ve finish_reason = 'length'  -> model dusunmeye
#     harcayip cevabi yazamadan kesiliyor (token siniri)
#   - ham = girdinin aynisi                        -> model talimat
#     geregi sorguyu degistirmiyor, prompt sorunu
#   - ISTISNA satiri                               -> API hatasi
#     (hiz siniri, ag vb.)
# ============================================================

# sys, os: search klasorunu Python yoluna eklemek icin
import sys
import os
# time: cagrilar arasinda bekleme icin
import time

# search klasorunu Python yoluna ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Uretim modulunu bir butun olarak import ediyoruz (icindeki fonksiyonu degistirecegiz)
import prompt_engineer

# Sorunlu cikan uc sorgu
SORGULAR = ["dragon ball z realistic", "a red bicycle", "a kitchen"]
# Her sorgu icin tekrar sayisi
TEKRAR = 5
# Cagrilar arasinda bekleme (saniye)
BEKLEME = 3.0


def teshis_sorusu(talimat, temperature=0.8):
    # _groq_ile_sor ile AYNI cagri, ama ham yaniti ve bitis nedenini de yazdirir
    try:
        # Uretim koduyla ayni istemciyi kullan
        client = prompt_engineer._client_olustur()
        cevap = client.chat.completions.create(
            model=prompt_engineer.GROQ_MODEL,
            messages=[{"role": "user", "content": talimat}],
            temperature=temperature,
        )
        # Ilk (ve tek) yanit secenegi
        secim = cevap.choices[0]
        # Ham icerik: None, bos metin ya da gercek bir cevap olabilir
        ham = secim.message.content
        # finish_reason: 'stop' normal bitis, 'length' token siniri
        print(f"    ham={ham!r} | finish_reason={secim.finish_reason}")
        # Uretim fonksiyonuyla ayni temizlik
        return (ham or "").strip().strip('"').strip().replace("\u2011", "-")
    except Exception as hata:
        # Herhangi bir API hatasi: turunu ve mesajini yazdir
        print(f"    ISTISNA: {type(hata).__name__}: {hata}")
        return None


# Uretim modulundeki fonksiyonu SADECE bu calistirma boyunca degistir
prompt_engineer._groq_ile_sor = teshis_sorusu


def calistir():
    for sorgu in SORGULAR:
        print(f"\n=== '{sorgu}' ===")
        for i in range(TEKRAR):
            print(f"  cagri {i + 1}:")
            # Uretimdeki fonksiyonun kendisi: sonucu ve yedege dusup dusmedigini gorelim
            sonuc = prompt_engineer.arama_sorgusu_zenginlestir(sorgu)
            print(f"    -> fonksiyonun dondurdugu: {sonuc!r}")
            # Hiz sinirina takilmamak icin bekle
            time.sleep(BEKLEME)


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()