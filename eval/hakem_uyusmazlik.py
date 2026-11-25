# ============================================================
# Bu script, hakem ile SENIN etiketlerin farkli oldugu fotograflari
# (hakem kabul etti ama sen "isabet degil" dedin, ya da hakem reddetti
# ama sen "isabet" dedin) tek bir sayfada gosterir. Amac: her
# uyusmazlikta kimin haklı oldugunu GOZLE kontrol etmek. Bu KOR
# degildir (kararlari biliyorsun); uyusmazligin nedenini anlamak icin.
# Hata ile biten cagrilar (karar gecersiz) dahil edilmez.
# ============================================================

# json: sonuc dosyasini okumak icin
import json
# html: metni HTML icinde guvenle yazmak icin
import html
# webbrowser: sayfayi tarayicida acmak icin
import webbrowser
# Path: dosya yolunu tarayicinin anlayacagi adrese cevirmek icin
from pathlib import Path

# Girdi: hakem_olcum_v2.py'nin yazdigi sonuc dosyasi
SONUC_DOSYASI = "eval/hakem_sonuclari_v2.json"
# Cikti: uyusmazliklarin gosterilecegi sayfa
HTML_DOSYASI = "eval/hakem_uyusmazlik.html"

# Sonuclari oku
with open(SONUC_DOSYASI, "r", encoding="utf-8") as f:
    sonuclar = json.load(f)

# Hata ile bitmeyen ve hakem karari etiketten FARKLI olan kayitlar
uyusmazliklar = [k for k in sonuclar.values()
                 if not k["hata"] and bool(k["isabet"]) != bool(k["karar"])]

# Iki tur uyusmazligi say
yanlis_red = [k for k in uyusmazliklar if k["isabet"] and not k["karar"]]
yanlis_kabul = [k for k in uyusmazliklar if not k["isabet"] and k["karar"]]
print(f"Hakem REDDETTI ama sen ISABET demistin: {len(yanlis_red)}")
print(f"Hakem KABUL ETTI ama sen ISABETSIZ demistin: {len(yanlis_kabul)}")

# Sayfa govdesini olustur: her uyusmazlik icin bir kart
kartlar = []
for k in uyusmazliklar:
    kartlar.append(
        '<div class="kart">'
        f'<img src="{html.escape(k["url"])}">'
        f'<div><b>Sorgu:</b> {html.escape(k["sorgu"])}</div>'
        f'<div>Senin etiketin: <b>{"ISABET" if k["isabet"] else "ISABETSIZ"}</b></div>'
        f'<div>Hakem: <b>{"KABUL" if k["karar"] else "RED"}</b></div>'
        f'<div>CLIP skoru: {k["clip"]:.3f}</div>'
        '</div>'
    )

# Sayfayi yaz
sayfa = (
    '<!doctype html><html><head><meta charset="utf-8"><title>Uyusmazlik</title>'
    '<style>body{font-family:sans-serif;margin:16px}'
    '.kart{display:inline-block;width:340px;margin:8px;vertical-align:top}'
    '.kart img{width:340px;height:260px;object-fit:contain;background:#eee;display:block}'
    '</style></head><body>'
    '<h2>Hakem ile etiket uyusmazliklari: her fotograf icin kim haklı?</h2>'
    + "".join(kartlar) + '</body></html>'
)
with open(HTML_DOSYASI, "w", encoding="utf-8") as f:
    f.write(sayfa)

print(f"Sayfa yazildi: {HTML_DOSYASI}")
# Sayfayi varsayilan tarayicida ac
webbrowser.open(Path(HTML_DOSYASI).resolve().as_uri())