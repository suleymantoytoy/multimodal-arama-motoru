# ============================================================
# Bu script, Unsplash arama sorgusu zenginlestirmesinin GERCEKTEN
# daha iyi FOTOGRAF getirip getirmedigini GOZLE degerlendirmek icin
# bir HTML sayfasi uretir.
#
# Her sorgu icin Unsplash'e iki kez gideriz (ham ve zenginlestirilmis
# sorgu). Sonuclar iki sutunda (A ve B) gosterilir. Hangi sutunun
# hangi kol oldugu RASTGELE belirlenir ve ayri bir dosyaya yazilir;
# boylece degerlendirirken hangi kolun hangisi oldugunu BILMEZSIN.
#
# ON-KAYITLI KURALLAR (sonuclar gorulmeden belirlendi):
#   - "Isabet": fotograf istenen ozelligi GERCEKTEN gosteriyor
#     (kanatli kopek, biyikli kedi, boynuzlu at; kostum/prop dahil).
#     Duz kopek/kedi/at isabet DEGIL.
#   - Karar: her kolun ILK 3 fotografindaki isabetler, sorgular
#     toplaminda karsilastirilir. Fark >= 2 ise o kol anlamli onde;
#     fark 0 veya 1 ise fayda gosterilemedi. Tum 8 fotografin sayisi
#     ikincil bilgi.
#   - Zenginlestirme sorguyu DEGISTIRMEDIYSE, o sorgu karsilastirmaya
#     girmez.
# ============================================================

# sys, os: search klasorunu Python yoluna eklemek icin
import sys
import os
# json: anahtar dosyasini yazmak icin
import json
# random: A/B atamasini rastgele yapmak icin (sabit seed: tekrarlanabilir)
import random
# re: sorgulari karsilastirmadan once normalize etmek icin
import re
# html: sorgu metnini HTML icinde guvenle yazmak icin
import html
# webbrowser: sayfayi tarayicida acmak icin
import webbrowser
# Path: dosya yolunu tarayicinin anlayacagi adrese cevirmek icin
from pathlib import Path

# search klasorunu Python yoluna ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Unsplash arama fonksiyonu
from external_search import unsplash_ile_ara
# Sorgu zenginlestirme (su anki uretim talimatiyla)
from prompt_engineer import arama_sorgusu_zenginlestir

# Test sorgulari: "dogal olmayan ozellik" iceren uc sorgu
SORGULAR = ["winged dog", "a cat with a mustache", "a horse with horns"]
# Her aramadan alinacak aday sayisi
ADAY_SAYISI = 8
# A/B atamasi icin sabit seed
SEED = 11
# Cikti dosyalari
HTML_DOSYASI = "eval/ham_vs_zengin_gorsel.html"
ANAHTAR_DOSYASI = "eval/ham_vs_zengin_anahtar.json"


def normalize(metin):
    # Kucuk harfe cevir, noktalamayi at, fazla bosluklari tek bosluga indir
    metin = re.sub(r"[^\w\s]", "", metin.lower())
    return " ".join(metin.split())


def sutun_html(etiket, adaylar, sorgu_no):
    # Bir sutunun HTML'ini uretir: 8 fotograf, her birinin altinda isaret kutusu
    parcalar = [f'<div class="kolon"><h3>Sutun {etiket}</h3>']
    parcalar.append('<div class="sayac">ilk 3: 0 | hepsi: 0</div>')
    for sira, aday in enumerate(adaylar, start=1):
        parcalar.append(
            '<label class="kart">'
            f'<img src="{html.escape(aday["url"])}" loading="lazy">'
            f'<span>#{sira} <input type="checkbox" data-sira="{sira}" '
            'onchange="guncelle()"> isabet</span></label>'
        )
    parcalar.append("</div>")
    return "".join(parcalar)


# Sayfanin sabit kismi: stil ve isaret sayan kucuk bir JavaScript
SAYFA_BASI = """<!doctype html><html><head><meta charset="utf-8">
<title>Ham vs Zengin</title>
<style>
body{font-family:sans-serif;margin:16px}
.cift{display:flex;gap:24px;margin-bottom:40px}
.kolon{flex:1}
.kart{display:inline-block;width:180px;margin:4px;vertical-align:top}
.kart img{width:180px;height:140px;object-fit:cover;display:block}
.sayac{font-weight:bold;margin:6px 0}
</style>
<script>
function guncelle(){
  document.querySelectorAll('.kolon').forEach(function(k){
    var ilk3=k.querySelectorAll('input[data-sira="1"]:checked,input[data-sira="2"]:checked,input[data-sira="3"]:checked').length;
    var hepsi=k.querySelectorAll('input:checked').length;
    k.querySelector('.sayac').textContent='ilk 3: '+ilk3+' | hepsi: '+hepsi;
  });
}
</script></head><body>
<h2>Isabet kurali: fotograf istenen ozelligi GERCEKTEN gosteriyor (kostum/prop dahil). Duz hayvan = isabet degil.</h2>
"""


def calistir():
    # Rastgele uretec (sabit seed: ayni calistirmada ayni A/B atamasi)
    rng = random.Random(SEED)
    bolumler = []
    anahtar = []

    for no, sorgu in enumerate(SORGULAR, start=1):
        # Zenginlestirilmis sorguyu BIR KEZ uret (degisken olabilir; anahtara yazilir)
        zengin = arama_sorgusu_zenginlestir(sorgu)
        print(f"[{no}] '{sorgu}' -> zenginlestirilmis: '{zengin}'")

        # Zenginlestirme sorguyu degistirmediyse karsilastirmaya GIRMEZ
        if normalize(zengin) == normalize(sorgu):
            print("    Sorgu degismedi, bu sorgu karsilastirmaya girmiyor.")
            anahtar.append({"sorgu": sorgu, "zengin": zengin, "dahil": False})
            continue

        # Iki kol icin Unsplash'te ara
        ham_adaylar = unsplash_ile_ara(sorgu, k=ADAY_SAYISI)
        zengin_adaylar = unsplash_ile_ara(zengin, k=ADAY_SAYISI)

        # Iki kolda ORTAK cikan fotograf sayisi (ayni URL'ler)
        ortak = len({a["url"] for a in ham_adaylar} & {a["url"] for a in zengin_adaylar})

        # A/B atamasi: yazi-tura ile hangi kol A olacak
        ham_a_mi = rng.random() < 0.5
        a_adaylar, b_adaylar = (ham_adaylar, zengin_adaylar) if ham_a_mi else (zengin_adaylar, ham_adaylar)

        # Bu sorgunun HTML bolumu (sorgu metni kasten gosterilir, kol kimligi gosterilmez)
        bolumler.append(
            f"<h2>Sorgu {no}: {html.escape(sorgu)}</h2>"
            f'<div class="cift">{sutun_html("A", a_adaylar, no)}{sutun_html("B", b_adaylar, no)}</div>'
        )
        # Anahtar: hangi sutun hangi kol (GOZLEMDEN SONRA bakilacak)
        anahtar.append({
            "sorgu": sorgu, "zengin": zengin, "dahil": True,
            "A": "ham" if ham_a_mi else "zengin",
            "B": "zengin" if ham_a_mi else "ham",
            "ham_aday_sayisi": len(ham_adaylar),
            "zengin_aday_sayisi": len(zengin_adaylar),
            "iki_kolda_ortak_fotograf": ortak,
        })

    # HTML dosyasini yaz
    with open(HTML_DOSYASI, "w", encoding="utf-8") as f:
        f.write(SAYFA_BASI + "".join(bolumler) + "</body></html>")
    # Anahtari yaz (ayri dosya, konsola YAZDIRMIYORUZ)
    with open(ANAHTAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(anahtar, f, ensure_ascii=False, indent=2)

    print(f"\nSayfa yazildi: {HTML_DOSYASI}")
    print("Anahtar dosyasini (eval/ham_vs_zengin_anahtar.json) degerlendirmeyi BITIRMEDEN ACMA.")
    # Sayfayi varsayilan tarayicida ac
    webbrowser.open(Path(HTML_DOSYASI).resolve().as_uri())


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()