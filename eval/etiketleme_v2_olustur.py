# ============================================================
# Bu script, 12 sorgu x 2 kaynak (Unsplash + Openverse) icin KOR
# ETIKETLEME sayfasi uretir. Her sorgunun adaylari karisik sirayla
# tek izgarada gosterilir; kaynak ve orijinal sira sayfada GORUNMEZ,
# indirilen etiket dosyasina yazilir.
#
# ON-KAYITLI ISABET KURALI (sonuclar gorulmeden belirlendi):
# fotograf sorgudaki seyi NET gosteriyorsa isabet; emin degilsen
# ISARETLEME. Her sorgunun ozel kurali SORGULAR listesinde.
# Uretim koduna (search/) dokunmaz.
# ============================================================

# sys, os: search klasorunu Python yoluna eklemek icin
import sys
import os
# json: aday ve etiket dosyalarini yazmak icin
import json
# random: fotograflari karistirmak icin (sabit seed)
import random
# time: surum numarasi uretmek ve API'lere nazik davranmak icin
import time
# requests: Openverse API'sini cagirmak icin
import requests
# webbrowser: sayfayi tarayicida acmak icin
import webbrowser
# Path: dosya yolunu tarayicinin anlayacagi adrese cevirmek icin
from pathlib import Path

# search klasorunu Python yoluna ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "search"))

# Unsplash arama fonksiyonu (uretimdekiyle ayni)
from external_search import unsplash_ile_ara
# Sorgu zenginlestirme (su anki uretim talimatiyla)
from prompt_engineer import arama_sorgusu_zenginlestir

# (sorgu, isabet kurali) - 12 sorgu, turlere gore
SORGULAR = [
    ("winged dog", "kanatli koepek (kanat kostumu/prop dahil); duz koepek degil"),
    ("a cat with a mustache", "belirgin ve KALIN biyikli kedi; duz kedi degil"),
    ("a horse with horns", "boynuzlu at (prop/kostum dahil); duz at degil"),
    ("a dog wearing sunglasses", "gunes gozlugu takan koepek; duz koepek degil"),
    ("a cat riding a skateboard", "kaykay uzerinde duran/suren kedi; kaykay yoksa degil"),
    ("a horse standing in snow", "karda duran at; kar yoksa veya at yoksa degil"),
    ("a blue car in front of a yellow house", "mavi araba VE arkasinda sari ev; ikisi birden sart"),
    ("a cup on top of a laptop", "fincan/bardak bir dizustu bilgisayarin USTUNDE; yaninda ise degil"),
    ("a man holding an umbrella next to a dog", "semsiye tutan adam VE yaninda koepek; uc oge birden sart"),
    ("a minimalist workspace with plants", "sade/minimalist calisma masasi VE bitkiler gorunuyor"),
    ("a red bicycle", "kirmizi bir bisiklet gorunuyor (kolay kontrol sorgusu)"),
    ("eiffel tower at night", "gece cekilmis Eyfel Kulesi (kolay kontrol sorgusu)"),
]
# Her kaynaktan alinacak aday sayisi
ADAY_SAYISI = 8
# Karistirma icin sabit seed
SEED = 33
# Openverse'e her istekte gonderilecek tanitici baslik (iyi uygulama)
OPENVERSE_BASLIK = {"User-Agent": "multimodal-arama-motoru-ogrenci-projesi"}
# Cikti dosyalari
ADAY_DOSYASI = "eval/etiket_adaylari_v2.json"
HTML_DOSYASI = "eval/etiketleme_v2.html"


def openverse_ara(arama_sorgusu, k):
    # Openverse goruntu arama uc noktasi (hesap/anahtar gerektirmeden)
    url = "https://api.openverse.org/v1/images/"
    # Istek parametreleri: sorgu ve sonuc sayisi
    parametreler = {"q": arama_sorgusu, "page_size": k}
    try:
        cevap = requests.get(url, params=parametreler, headers=OPENVERSE_BASLIK, timeout=20)
        # 200 disinda bir sey dondu: durumu ve govdenin basini yazdir, bos liste dondur
        if cevap.status_code != 200:
            print(f"    Openverse HATA: HTTP {cevap.status_code}: {cevap.text[:200]}")
            return []
        # JSON govdesinden sonuc listesini al (alan adi yoksa bos liste)
        sonuclar = cevap.json().get("results", [])
        adaylar = []
        for s in sonuclar:
            # Ekranda ve puanlamada kucuk surumu kullan (hizli); yoksa tam surum
            gosterim = s.get("thumbnail") or s.get("url")
            # Gosterilecek adres yoksa bu sonucu atla
            if not gosterim:
                continue
            adaylar.append({
                "url": gosterim,
                "tam_url": s.get("url"),
                "sahip": s.get("creator"),
                "lisans": s.get("license"),
            })
        return adaylar
    except Exception as hata:
        # Baglanti vb. hata: mesaji yazdir, bos liste dondur
        print(f"    Openverse ISTISNA: {type(hata).__name__}: {hata}")
        return []


# Sayfanin sabit kismi: stil ve JavaScript (veri __VERI__ yerine gomulur)
SAYFA = """<!doctype html><html><head><meta charset="utf-8">
<title>Etiketleme v2</title>
<style>
body{font-family:sans-serif;margin:16px}
.kart{display:inline-block;width:200px;margin:4px;vertical-align:top}
.kart img{width:200px;height:150px;object-fit:cover;display:block}
.sayac{font-weight:bold;margin:6px 0}
button{font-size:16px;padding:8px 16px}
</style></head><body>
<h2>Isabet: fotograf, sorgudaki seyi NET gosteriyor. Emin degilsen ISARETLEME. Isaretler tarayicida kaydedilir.</h2>
<button onclick="indir()">Etiketleri indir (etiketler_v2.json)</button>
<div id="icerik"></div>
<script>
const VERI = __VERI__;
const ANAHTAR = 'etiket_v2_' + '__SURUM__';
function kaydet(){
  try {
    const d = {};
    VERI.forEach(function(b, bi){ b.adaylar.forEach(function(a, ai){
      if (document.getElementById('c_' + bi + '_' + ai).checked) d['c_' + bi + '_' + ai] = 1;
    }); });
    localStorage.setItem(ANAHTAR, JSON.stringify(d));
  } catch(e) {}
}
function yukle(){
  try {
    const d = JSON.parse(localStorage.getItem(ANAHTAR) || '{}');
    Object.keys(d).forEach(function(id){ const el = document.getElementById(id); if (el) el.checked = true; });
  } catch(e) {}
}
function say(bi){
  let n = 0;
  VERI[bi].adaylar.forEach(function(a, ai){
    if (document.getElementById('c_' + bi + '_' + ai).checked) n++;
  });
  document.getElementById('s_' + bi).textContent = 'isaretlenen: ' + n + ' / ' + VERI[bi].adaylar.length;
  kaydet();
}
function ciz(){
  const kok = document.getElementById('icerik');
  VERI.forEach(function(b, bi){
    const baslik = document.createElement('h2');
    baslik.textContent = (bi + 1) + '. ' + b.sorgu;
    kok.appendChild(baslik);
    const kural = document.createElement('div');
    kural.textContent = 'Kural: ' + b.kural;
    kok.appendChild(kural);
    const sayac = document.createElement('div');
    sayac.className = 'sayac'; sayac.id = 's_' + bi;
    kok.appendChild(sayac);
    b.adaylar.forEach(function(a, ai){
      const kart = document.createElement('label');
      kart.className = 'kart';
      const img = document.createElement('img');
      img.src = a.url; img.loading = 'lazy';
      kart.appendChild(img);
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.id = 'c_' + bi + '_' + ai;
      cb.onchange = function(){ say(bi); };
      kart.appendChild(cb);
      kart.appendChild(document.createTextNode(' isabet'));
      kok.appendChild(kart);
    });
  });
}
function indir(){
  const cikti = VERI.map(function(b, bi){
    return {sorgu: b.sorgu, arama_sorgusu: b.arama_sorgusu,
      adaylar: b.adaylar.map(function(a, ai){
        return {url: a.url, tam_url: a.tam_url, kaynak: a.kaynak,
          orijinal_sira: a.orijinal_sira,
          isabet: document.getElementById('c_' + bi + '_' + ai).checked};
      })};
  });
  const blob = new Blob([JSON.stringify(cikti, null, 2)], {type: 'application/json'});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'etiketler_v2.json';
  link.click();
}
ciz();
yukle();
VERI.forEach(function(b, bi){ say(bi); });
</script></body></html>"""


def calistir():
    # Sabit seed'li rastgele uretec
    rng = random.Random(SEED)
    veri = []
    for sorgu, kural in SORGULAR:
        # Uretimdeki gibi: once sorguyu zenginlestir, iki kaynakta da onunla ara
        arama_sorgusu = arama_sorgusu_zenginlestir(sorgu)
        print(f"'{sorgu}' -> arama sorgusu: '{arama_sorgusu}'")
        # Kaynak 1: Unsplash (uretimdeki fonksiyon)
        unsplash = unsplash_ile_ara(arama_sorgusu, k=ADAY_SAYISI) or []
        # Kaynak 2: Openverse
        openverse = openverse_ara(arama_sorgusu, ADAY_SAYISI)
        print(f"    Unsplash: {len(unsplash)} aday, Openverse: {len(openverse)} aday")

        # Iki kaynagi tek listede birlestir; kaynak ve orijinal sirayi sakla
        kayitlar = []
        for sira, a in enumerate(unsplash, start=1):
            kayitlar.append({"url": a["url"], "tam_url": a["url"],
                             "kaynak": "unsplash", "orijinal_sira": sira})
        for sira, a in enumerate(openverse, start=1):
            kayitlar.append({"url": a["url"], "tam_url": a["tam_url"],
                             "kaynak": "openverse", "orijinal_sira": sira})
        # Kaynagin ve siranin etkisini kaldirmak icin tum adaylari karistir
        rng.shuffle(kayitlar)
        veri.append({"sorgu": sorgu, "kural": kural,
                     "arama_sorgusu": arama_sorgusu, "adaylar": kayitlar})
        # API'lere nazik davran
        time.sleep(1.0)

    # Adaylari ayri dosyaya yaz (sonraki adimda puanlama icin lazim)
    with open(ADAY_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

    # Veriyi sayfaya gom; "</" dizisini kacirarak script etiketinin erken kapanmasini onle
    gomulu = json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")
    # Surum: her uretilen sayfa icin benzersiz (eski kayitli isaretler karismasin)
    surum = str(int(time.time()))
    sayfa = SAYFA.replace("__VERI__", gomulu).replace("__SURUM__", surum)
    with open(HTML_DOSYASI, "w", encoding="utf-8") as f:
        f.write(sayfa)

    print(f"\nSayfa yazildi: {HTML_DOSYASI}")
    # Sayfayi varsayilan tarayicida ac
    webbrowser.open(Path(HTML_DOSYASI).resolve().as_uri())


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()