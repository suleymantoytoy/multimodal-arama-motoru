# Karar Gunlugu

Bu dosya, proje boyunca alinan her mimari kararin "neden"ini tutar.

---

## Faz 0 - Proje Baslangici

**Tarih:** [buraya bugunun tarihini yaz]

**Neden bu proje?**
Multi-modal embedding (CLIP), vektor veritabani mimarisi (FAISS), hibrit
bilgi getirimi (semantic + BM25 + RRF) ve objektif degerlendirme
(precision@k, recall@k, MRR) konularini tek bir projede, uctan uca
birlestirmek icin secildi. Amac tek bir kutuphaneyi kullanmak degil,
sistemin ic mekanigini anlamak ve olcebilmek.

**Teknoloji yigini kararlari:**
- Embedding modeli: OpenCLIP (ViT-B/32 ile basliyoruz, gerekirse ViT-L/14'e geciyoruz)
  - Neden: acik kaynak, iyi belgelenmis, metin ve gorseli ayni vektor uzayina goruyor
- Vektor veritabani: FAISS (yerel, ucretsiz)
  - Neden: sunucu gerektirmiyor, farkli index tiplerini (Flat/IVF/HNSW) kendimiz kiyaslayabiliyoruz
- Keyword arama: rank-bm25
  - Neden: hafif, hizli kurulum, hibrit aramanin klasik kanadi icin yeterli
- Birlestirme: Reciprocal Rank Fusion (RRF)
  - Neden: basit, az parametre hassasiyeti, kanitlanmis bir yontem

*(Sonraki kararlar asagiya eklenecek - her faz sonunda bir kayit.)*

## Faz 1 - Embedding Cekirdegi Sonuclari

300 gorsellik test setinde CLIP (ViT-B/32) ile metin->gorsel arama
mekanizmasi dogrulandi. "food on a table" sorgusunda 5/5 sonuc dogru,
"a dog" sorgusunda 4/5 sonuc dogru (1 sonucta CLIP kurk dokusunu
kopekle karistirdi - bu bir gozlem, Faz 4 degerlendirme setine
"zor/kafa karistirici" ornek olarak eklenecek).

Benzerlik skorlari 0.2-0.3 araliginda cikti - bu CLIP icin normal,
mutlak skor degil siralamanin dogrulugu onemli.

**TODO / Faz 2-4'te ele alinacak:** "a dog" sorgusunda kurk dokusuyla
karisan 1 sonuc gozlemlendi (ViT-B/32'nin bilinen bir sinirlamasi).
Faz 2'de veri seti 5.000'e cikinca ve Faz 4'te gercek degerlendirme
seti kurulunca:
  1. Bu tur hatalarin ne siklikta oldugunu olc (sadece 1 ornek degil,
     istatistiksel bir oran).
  2. Eger oran yuksekse (orn. %10+), ViT-L/14'e gecmeyi degerlendir
     ve HIZ/DOGRULUK trade-off'unu (Faz 2'deki index karsilastirmasi
     gibi) sayisal olarak raporla.
  3. Eger oran dusukse (orn. %2-3), mevcut modelle devam et, bunu
     eval_raporu.md'de bir "bilinen sinirlama" olarak belgele.

## Faz 2 - Index Karsilastirma Sonuclari (5.000 gorsel, CPU)

## Faz 2 - Duzeltme: Genisletilmis Benchmark (25 sorgu, 5 tekrar)

Ilk benchmark sadece 10 sorgu ve tek olcumle yapilmisti - istatistiksel
guven artirmak icin 25 sorguya cikarildi, her sorgu 5 kez tekrarlanip
ortalamasi alindi.

| Index | Ort. Sure (ms) | Flat ile Ortusme |
|-------|---------------|-------------------|
| Flat  | 0.816         | %100 (referans)   |
| IVF   | 0.004         | %68.8             |
| HNSW  | 0.052         | %94.8             |

Sonuc onceki (kucuk olcekli) benchmark ile TUTARLI cikti - HNSW
karari degismedi, hala en iyi hiz/dogruluk dengesini veriyor.
Bu, ilk benchmark'in tesadufen "sansli" bir sonuc olmadigini,
gercekten guvenilir oldugunu gosteriyor.

| Index | Ort. Sure (ms) | Flat ile Ortusme |
|-------|---------------|-------------------|
| Flat  | 0.79          | %100 (referans)   |
| IVF   | 0.24          | %65               |
| HNSW  | 0.10          | %97               |

**Karar: HNSW, production/varsayilan index olarak secildi.**
Gerekce: Flat'e gore ~8x daha hizli, dogruluk kaybi ihmal edilebilir
duzeyde (%97 ortusme). IVF'nin dusuk ortusme orani (%65), varsayilan
nprobe=1 ayarindan kaynaklaniyor - nprobe artirilarak iyilestirilebilir
ama bu ekstra bir parametre ayari gerektirir, HNSW ekstra ayar
gerektirmeden zaten iyi sonuc verdigi icin HNSW tercih edildi.

Not: 5.000 gorsel gibi kucuk-orta bir olcekte Flat bile pratikte
"yavas" sayilmaz (0.79ms) - asil fark cok daha buyuk veri setlerinde
(orn. 1 milyon+ gorsel) ortaya cikar. Bu projede HNSW'yi secmemizin
nedeni "zorunluluk" degil, "doğru mühendislik pratiği" - gercek
sistemlerde boyle secilir.

## Faz 2 - Duzeltme: Batch Isleme Eklendi

Ilk versiyonda embedding cikarma gorselleri TEK TEK isliyordu.
Yol haritasindaki tavsiyeye uyularak batch_size=32 ile toplu
isleme gecildi (encode_images_batch fonksiyonu).

**Sonuc (5.000 gorsel, CPU):**
- Toplam sure: 215.4 saniye (3.59 dakika)
- Gorsel basina ortalama: 43.08 ms
- Basari orani: 5000/5000 (hic bozuk/okunamaz gorsel cikmadi)

Bu sayilar Faz 6'daki README'de "sistem performansi" bolumunde
somut veri olarak kullanilacak.

## Faz 3 - BLIP Caption Uretimi Tamamlandi

5.000 gorselin tamami icin BLIP (Salesforce/blip-image-captioning-base)
ile otomatik caption uretildi, data/metadata.json'a kaydedildi.

**Sure raporu:**
- 500 gorsellik test: 451.5 saniye (0.903 sn/gorsel)
- Tahmin: 5.000 gorsel icin ~75.2 dakika
- Gercek: 5.000 gorsel icin 72.4 dakika (tahminle tutarli, CLIP'te
  oldugu gibi "once kucuk olcekte olc, sonra buyu" yaklasimi burada
  da dogrulandi)

BLIP, CLIP'e gore ~20 kat daha yavas (CLIP: 0.043 sn/gorsel batch ile,
BLIP: 0.903 sn/gorsel) - bu beklenen bir durum, CLIP sadece bir vektor
hesaplarken BLIP kelime kelime bir cumle "uretiyor" (generation),
bu dogasi geregi daha yavas bir islem.

## Faz 3 - BM25 Dogrulama Notu

"bananas" sorgusunda ilk 5 sonucun caption'i AYNI gorunuyordu
("a bunch of bananas" x5) - bunun bir hata olup olmadigi kontrol
edildi. Dosya yollarina bakildiginda 5 FARKLI gorsel dosyasi
oldugu dogrulandi (000000003661.jpg, 000000006012.jpg, vb.) -
BLIP'in benzer sahneler icin benzer/ozdes genel caption uretmesi
normal bir davranis, sistem hatasi degil.

Bu gozlem, hibrit aramanin (CLIP + BM25) neden anlamli oldugunu
gosteriyor: BM25 sadece METNE (caption'a) bakiyor, ayni caption'li
farkli gorselleri AYIRT EDEMIYOR. CLIP ise dogrudan GORSELE baktigi
icin bu gorselleri birbirinden ayirt edebilir - iki yontemin
BIRLESTIRILMESI (RRF ile) bu zayifligi telafi ediyor.

## Faz 3 - RRF Dogrulama Testi

reciprocal_rank_fusion() fonksiyonu, elle hazirlanmis basit bir
ornekle test edildi. Iki farkli listede (CLIP ve BM25 sonucu)
ortak gecen elemanlarin (A ve C), sadece tek listede gecenlerden
(B, D, E, F) daha yuksek RRF skoru aldigi dogrulandi. Mekanizma
beklendigi gibi calisiyor.

## Faz 3 - Hibrit Arama Uctan Uca Test Edildi

hybrid_search.py ile CLIP (semantic) + BM25 (keyword) + RRF
birlestirme mekanizmasi uctan uca calisiyor. Her iki yontemden
20'ser aday toplanip RRF ile birlestiriliyor, nihai olarak en
iyi k sonuc donduruluyor.

Mimari karar: Aday havuzu (k=20), nihai sonuc sayisindan (k=10)
BUYUK tutuldu - bu, RRF'ye daha genis bir secim alani sunarak,
sadece tek bir yontemin ilk-10'una giren ama digerinde daha asagida
kalan sonuclarin da degerlendirmeye girmesini sagliyor.

## Faz 4 - Test Seti Olusturuldu (Karar Degisikligi)

Ilk tasarimda caption'dan "ilk 2 kelime" seklinde kisa bir sorgu
turetme yontemi planlanmisti, ama bu YANLIS kelimeyi secme riski
tasidigi fark edildi (onemli kelime cumlenin sonunda olabilir).
Karar: caption'in TAMAMI dogrudan sorgu olarak kullanildi - bilgi
kaybi riski ortadan kalkti, ama "gercekci kisa kullanici sorgusu"
simulasyonundan feragat edildi (bu, sistemin dogru calisip
calismadigini olcme amacini etkilemiyor).

50 sorguluk test seti, data/metadata.json'dan rastgele (seed=42,
tekrarlanabilir) secilen gorsellerin BLIP caption'larindan olusturuldu.

## Faz 3.75 Tamamlandı: Esik (Threshold) Mantigi

akilli_ara() fonksiyonu eklendi, esik=0.25 olarak ilk tahmin kondu.

Test sonuclari:
- "a dog" -> skor 0.2902 -> yerel (dogru davranis)
- "a dog walking on the moon" -> skor 0.2415 -> harici (dogru davranis)

Esik, iki ornegi net ayirdigi icin 0.25 olarak sabitlendi. Daha fazla
sorguyla (orn. 10-15 farkli somut/soyut/hayali sorgu) kalibrasyon
yapilirsa esik degeri hassaslastirilabilir, ama simdilik yeterli.

## Faz 3.75 - Görsel Üretim Katmanı Kararı:
 Ücretli API (DALL-E) yerine tamamen ücretsiz/yerel bir kurulum seçildi: diffusers + sd-turbo (görsel üretim, tek adımlı, CPU-dostu) ve flan-t5-small (prompt zenginleştirme, transformers üzerinden yerel). Gerekçe: maliyet sıfır, API anahtarı bağımlılığı yok, projenin "gerçek ve gösterilebilir" felsefesiyle tutarlı.
 
 flan-t5-small denendi, çıktı kalitesi yetersiz (girdiyi olduğu gibi tekrarlıyor), gerçek bir API'ye geçildi.

## Faz 3.75 - Prompt Zenginleştirme Katmanı:
 İlk denemede flan-t5-small (küçük, yerel HF modeli) kullanıldı, ama çıktı kalitesi yetersizdi (girdiyi anlamsızca tekrarlıyordu, gerçek bir zenginleştirme yapmıyordu). Bu denemeden vazgeçildi. Yerine Ollama (yerel çalışan, ücretsiz, API anahtarı gerektirmeyen LLM sunucusu) ile llama3.1:latest modeli kullanıldı — sonuç kalitesi çok daha iyi (ışıklandırma, kompozisyon, atmosfer detayları içeren gerçek prompt engineering çıktısı). Not: ilk çağrıda model belleğe yüklenirken (~4.9 GB) gecikme oluyor (soğuk başlangıç), bu yüzden timeout 30'dan 120 saniyeye çıkarıldı.

## Faz 3.75 - Bilinen Sınırlama:
sd-turbo (hızlı, az adımlı, damıtılmış model) alışılmadık kelime kombinasyonlarında (örn. "dog" + "spacesuit") "compositional binding" sorunu yaşıyor — güçlü çağrışımlı kelime (spacesuit → insan/astronot) baskın öğeyi (dog) eziyor, tamamen insan figürü üretiyor. Basit sahnelerde ("dog on moon surface with craters/stars") sonuç kabul edilebilir kalitede. Bu, modelin bilinen bir zayıflığı — hız/kalite trade-off'unun bedeli, saklanmadı.

## Faz 3.75 - Prompt Zenginlestirme ve Gorsel Uretim Katmani

### Prompt Zenginlestirme (LLM Katmani)

Ilk denemede flan-t5-small (kucuk, yerel bir Hugging Face modeli,
transformers uzerinden) kullanildi. Sonuc yetersizdi - model girdiyi
ANLAMSIZCA TEKRARLIYORDU ("a dog walking on the moon is a dog
walking on the moon" gibi), gercek bir zenginlestirme yapmiyordu.
Bu denemeden vazgecildi.

Yerine Ollama (yerel calisan, ucretsiz, API anahtari gerektirmeyen
bir LLM sunucusu, localhost:11434) ile llama3.1:latest modeli
kullanilmaya baslandi. Sonuc kalitesi cok daha iyi - isiklandirma,
kompozisyon, atmosfer detaylari iceren gercek prompt engineering
ciktisi.

Karsilasilan ve cozulen sorunlar:
- Ilk cagrida model bellege yuklenirken (~4.9 GB) gecikme oluyordu,
  30 saniyelik timeout yetersiz kaliyordu -> 120 saniyeye cikarildi.
- Ollama'nin urettigi zengin promptlar (150+ kelime) Stable
  Diffusion'in metin kodlayicisi CLIP'in 77 token sinirini asiyordu,
  promptun sonu sessizce kesiliyordu (log'da "truncated" uyarisi
  goruldu) -> Ollama'ya verilen talimata "60 kelimenin altinda kal"
  kisiti eklendi, sorun cozuldu.

### Gorsel Uretim Katmani

Ilk denemede stabilityai/sd-turbo (yerel, diffusers uzerinden,
damitilmis/distilled bir model) kullanildi. Hizli (CPU'da 4 adimda
~20 saniye) ama ciddi bir kalite sorunu ortaya cikti: "compositional
binding" zayifligi - model, guclu cagrisimli kelimeleri (orn.
"spacesuit") baskin ogeye (orn. "dog") tercih ediyor, tamamen alakasiz
bir sonuc (bir insan/astronot figuru) uretebiliyor. Test: "a dog
walking on the moon" + "spacesuit" iceren zenginlestirilmis prompt
-> tamamen bir astronot gorseli cikti, kopek yoktu. "Spacesuit"
kelimesi kaldirilinca ("dog on moon surface with craters/stars")
sonuc kabul edilebilir kaliteye dondu - yani sorun modelin genel
kopek algisi degil, ozellikle guclu insan cagrisimi yapan kelimelerle
kompozisyon kurma zayifligiydi.

Karar: sd-turbo, damitilmis oldugu icin bu zayifligi adim sayisini
artirarak (num_inference_steps) tam cozemiyor - damitma, modelin
ince kompozisyon becerisini hiz icin feda etmesi anlamina geliyor.
Bu yuzden yerel/damitilmis modelden vazgecilip Hugging Face
Inference API uzerinden FLUX.1-schnell modeline gecildi:
- Tam adimli, damitilmamis, kompozisyon/prompt sadakati konusunda
  bilinen sekilde daha guclu bir model.
- CPU yukumuz yok (bulutta calisiyor), hizli donuyor.
- Ucretsiz katman var, ama bir Hugging Face hesabi + API token
  (HF_TOKEN) gerektiriyor - "API anahtari gerektirmez" hedefinden
  kucuk bir sapma, ama para gerektirmiyor, sadece ucretsiz kayit.
- HF_TOKEN, .env dosyasina eklendi, python-dotenv ile okunuyor -
  projenin Unsplash API anahtarinda kullandigi yontemle tutarli.

Ders: Ucretsiz/yerel/hizli secimlerin (sd-turbo) bir bedeli oldugunu
gozlemledik - bu bedel bazen "hicbir zaman calismaz" degil, "bazi
spesifik durumlarda sessizce yanlis sonuc verir" seklinde ortaya
cikiyor (compositional binding). Boyle durumlarda sonucu saklamadan
raporlamak ve daha guclu bir alternatife gecmek, "gunu kurtarmaktan"
daha onemli - bu proje boyunca benimsedigimiz ilkeyle (Faz 4'teki
"sonuc kotu ciksa da saklama" prensibi) tutarli bir karar.

### Durum (bu kaydin yazildigi an itibariyle)

- Prompt zenginlestirme: TAMAMLANDI (Ollama + llama3.1).
- Gorsel uretim: FLUX.1-schnell'e gecis kararlastirildi, entegrasyon
  kodu yaziliyor, henuz test edilmedi.
- Bir sonraki adim: search/image_generation.py'yi HF Inference API'ye
  istek atacak sekilde yeniden yazip test etmek, sonra uc katmani
  (yerel -> harici -> uretim) akilli_ara() icinde birlestirmek.

### Guncelleme: FLUX.1-schnell Testi Basarili

Test sorgusu: "a dog walking on the moon"
Sonuc: uretilen_61107.png - kopek net, tanınabilir, gercekci sekilde
ay yuzeyinde yuruyor, dramatik isiklandirma ve golgeler dogru
yerlerde. sd-turbo'da yasanan compositional binding sorunu burada
gorulmedi - "spacesuit" gibi guclu cagrisimli bir kelime olmadan
bile FLUX, sd-turbo'nun tek basina kopegi kaybettigi durumdan
cok daha inandirici bir sonuc uretti.

## Faz 3.75 - Gorsel Uretim Katmani: TAMAMLANDI.

## Faz 3.75 - akilli_ara() Uc Katman Birlestirme Karari

Harici (Unsplash) katmanindan uretim katmanina GECIS KOSULU olarak
"Unsplash bos sonuc donduruyorsa" secildi (basit yontem). Unsplash'in
kendi arama motoru guclu oldugu icin pratikte NEREDEYSE HICBIR ZAMAN
bos donmez - yani uretim katmani, su anki tasarimda SADECE gercek
hata durumlarinda (rate limit, baglanti sorunu) tetiklenir.

Gelecek gelistirme (yapilmadi, notu dusuldu): Unsplash sonuclarini
KALITE acisindan degerlendirmek icin, donen ilk gorseli indirip kendi
CLIP modelimizle yeniden puanlamak, skor hala dusukse uretime gecmek
- bu, "Unsplash bir sey buldu ama alakasiz" durumunu da yakalar.
Su an icin kapsam disi birakildi (zaman/karmasiklik dengesi).

## Faz 4 - Değerlendirme Raporu Tamamlandı

50 sorguluk test setiyle Sadece CLIP / Sadece BM25 / Hibrit (RRF)
karşılaştırması yapıldı ve sonuçlar analiz edildi. Detaylı sayısal
sonuçlar ve "BM25 neden suni şekilde yüksek çıktı" analizi artık
roadmap'in öngördüğü gibi ayrı bir dosyada: **bkz. `docs/eval_raporu.md`**.

Özet: Hibrit (RRF) en iyi çıkmadı çünkü test sorguları BLIP
caption'larının tamamıydı - bu BM25'e (kelime eşleştirme) haksız bir
avantaj verdi. Gerçek kullanıcı sorgularında (kısa, eksik kelimeli)
CLIP ve Hibrit'in öne çıkması beklenir - bu, `docs/eval_raporu.md`'de
detaylandırıldı.

## Faz 5 - FastAPI Servisi Calisiyor

api/main.py ile /health, /search/text, /search/image endpoint'leri
kuruldu. Swagger arayuzunden (/docs) manuel test edildi:
/search/text "a dog" sorgusuyla HTTP 200 donduruyor, akilli_ara()
fonksiyonunun tum katmanlarina (yerel/harici/uretim) dogru sekilde
erisiyor.

## Faz 5 - Streamlit Arayuzu Calisiyor

ui/app.py ile FastAPI servisine baglanan bir arayuz kuruldu.
"a dog" sorgusuyla test edildi: 4 sonuc dogru gorsellerle,
RRF skorlariyla ve "kendi veri setimde bulundu" kaynak
bilgisiyle basariyla goruntulendi.

## Faz 5 - Duzeltme: Unsplash Sonuclari CLIP ile Yeniden Puanlaniyor

"a dog walking on the moon" sorgusunda, Unsplash kelime bazli
eslesme yaptigi icin "gokyuzunde ay varken cekilmis kopek"
fotograflari getirdi - bu GERCEK ama YANLIS turde bir eslesme
(kullanicinin kastettigi "ayin yuzeyinde" sahnesi degildi).

Onceden "gelecek gelistirme" olarak ertelenen ozellik simdi
eklendi: Unsplash'in ilk sonucu, kendi CLIP modelimizle YENIDEN
PUANLANIYOR. Bu skor da esigin (0.25) altindaysa, sistem uretim
katmanina geciyor. Bu, "Unsplash bir sey buldu ama alakasiz"
durumunu artik yakalayabiliyor.

## Faz 5 - FLUX Kredisi Tukendi, Otomatik Yedek Plan Eklendi

k=4 ile 4 gorsel uretme testi sirasinda HF Inference API'nin
aylik ucretsiz kredisi tukendi (402 Payment Required hatasi).
Bu, ucretsiz/API-tabanli servislerin bilinen bir riskiydi (onceden
not dusulmustu).

Cozum: image_generation.py'ye OTOMATIK yedek plan eklendi. FLUX
basarisiz olursa (402 dahil herhangi bir hata), sistem otomatik
olarak yerel sd-turbo modeline duser - bu model ucretsiz, sinirsiz,
internet gerektirmez. Kalite FLUX'tan dusuk (bilinen compositional
binding zayifligi var) ama sistem ARTIK HICBIR ZAMAN tamamen
durmuyor. Kullanilan model (FLUX veya sd-turbo) sonuca eklenip
kullaniciya bildiriliyor.

## Faz 5 - Duzeltme: Gorsel Aramada Esik/Yedek Plan Mantigi Eklendi

Bir anime/cizim karakteri yuklenip "benzer bul" denendiginde
(COCO'daki gercek fotograflarla alakasi olmayan bir gorsel),
sistem alakasiz sonuclar donduruyordu (vazo, mankenler vb.) -
CLIP'in yuzeysel gorsel ozelliklere (renk, siluet) tutunmasi.

Kok neden: /search/image endpoint'i, metin aramasindaki gibi bir
ESIK KONTROLU yapmiyordu, skor ne olursa olsun yerel sonuclari
donduruyordu.

Cozum: Gorsel arama da artik esik kontrolu yapiyor. Yerel skor
dusukse, BLIP ile yuklenen gorsel METNE cevriliyor (caption
uretiliyor), bu caption akilli_ara()'ya gonderiliyor - boylece
gorsel sorgular da harici (Unsplash) ve uretim (AI) katmanlarindan
faydalanabiliyor.

## Faz 5 - Onemli Bulgu: Gorsel Arama Esigi Yanlis Kalibre Edilmisti

Bir anime karakteri gorseli yuklenip test edildiginde, CLIP skoru
0.5655 cikti - bu, metin aramasi icin belirledigimiz esigin (0.25)
COK ustunde, ama gercekte gorsel TAMAMEN alakasizdi (COCO'daki bir
vazo fotografiyla eslesti).

Kok neden: Gorsel-gorsel CLIP benzerlik skorlari, metin-gorsel
skorlarindan DOGAL OLARAK daha yuksek cikar (renk/kompozisyon gibi
yuzeysel ozellikler paylasildigi icin). Ayni esigi (0.25) her iki
tur sorgu icin de kullanmak YANLISTI.

Cozum: /search/image endpoint'i icin AYRI ve daha yuksek bir esik
(0.75) belirlendi. Bu, ilk kalibrasyon - daha fazla test ornegiyle
(hem benzer hem alakasiz gorsel ciftleriyle) hassaslastirilabilir.

Ders: Bir esik degerinin bir sorgu TURU icin (metin) dogru
calismasi, BASKA bir sorgu turu (gorsel) icin de dogru calisacagi
anlamina gelmiyor - her giris turunun kendi skor dagilimi olabilir,
ayri ayri kalibre edilmesi gerekiyor.

## Faz 5 - Ertelenen Ozellik: Gercek Reverse Image Search

Test sirasinda fark edildi: sistem "bu karakterin gercek/var olan
baska gorsellerini bul" (Google Images tarzi reverse image search)
YAPAMIYOR - cunku kurdugumuz mimari SEMANTIK arama (CLIP ile anlam
benzerligi) + AI URETIM (FLUX/sd-turbo ile yeni gorsel cizme)
temelli. Ikisi de "internette var olan GERCEK bir gorseli bulma"
islevi gormuyor.

Gercek reverse image search (Google Cloud Vision Web Detection,
Bing Visual Search, TinEye) arastirildi - hepsi kredi karti
dogrulamasi veya ucretli kullanim gerektiriyor, projenin "kart
bilgisi istemeyen ucretsiz servisler" tercihiyle CELISIYOR.

Karar: Bu ozellik EKLENMEDI, bilinen bir sinirlama olarak
belgelendi. Ileride istenirse Google Cloud Vision ile eklenebilir
(gelecek gelistirme notu).

## Faz 5 - Docker: Kismi Tamamlandi (Bilinen Sinirlama)

Dockerfile.api, Dockerfile.ui ve docker-compose.yml dosyalari
yazildi ve mimarisi dogrulandi (ilk basarili build'lerde her iki
servis de ayakta kalkip birbirleriyle iletisim kurdu - /search/text
ve /search/image endpoint'leri container icinde CALISTI).

Ancak surec sirasinda Windows ortamina ozgu, birbirinden bagimsiz
BIRDEN FAZLA altyapi sorunu yasandi: sanallastirma ayari kapaliydi,
WSL kurulu degildi, ucuncu parti antivirus (360 Total Security)
build suresini 4+ saate cikardi, ve en sonunda Docker'in kendi
imaj veritabani bozuldu ("Images list" hatasi, cozulemedi).

Karar: Docker Desktop'i yeniden kurup sorunu cozmeye zaman
harcamak yerine, mevcut CALISAN durumda (yerel uvicorn + streamlit
ile tam fonksiyonel sistem) birakildi. Dockerfile'lar ve
docker-compose.yml REPODA KALIYOR - bunlar Docker bilgisi ve
mimari tasarimi kanitliyor, sadece bu ortamda sorunsuz calistigi
DOGRULANAMADI.

Bu, roadmap'in kendi "onceligini bil, gereksiz yere takilma"
felsefesiyle tutarli bir karar - CV'de "Docker ile paketlendi"
yerine "Docker ile paketlenebilir (Dockerfile ve docker-compose.yml hazir, ancak bu ortamda dogrulanamadi)" ifadesini kullanmak daha durustur.

## Faz 6 - Entegrasyon Testi Yazildi

tests/test_api.py ile /health ve /search/text endpoint'lerini
dogrulayan basit bir entegrasyon testi eklendi. Test, sonucun
ICERIGINI degil YAPISINI kontrol ediyor (kaynak alani var mi,
gecerli bir deger mi, sonuc listesi bos mu) - bu, "sistem coktu mu"
sorusuna cevap veriyor, "sonuclar mukemmel mi" sorusuna degil (o
Faz 4'un isiydi). Test calistirildi, ikisi de basarili.

## Faz 6 - Demo Video Atlandi

Demo videosu (roadmap'in Hafta 23 hedefi) bilinçli olarak atlandi -
projenin teknik iceriğine/kalitesine hicbir katkisi olmayan, sadece
sunum amacli bir materyal. Entegrasyon testi (asil teknik gereksinim)
zaten yazilip basariyla calistirildi. Istenirse ileride mulakat
oncesi kolayca eklenebilir.

## PROJE TAMAMLANDI

9 basari kriterinden 8'i tam, 1'i (Docker) kismi tamamlandi -
nedeni yukarida detayli belgelendi. Faz 0'dan Faz 6'ya kadar
tum fazlar tamamlandi.

Bu proje boyunca ogrenilen en onemli ders: bir seyin "iyi
gorunmesi" ile "gercekten dogru calistigini olcmek" arasindaki
fark. Bircok noktada (BM25'in suni yuksekligi, Unsplash'in
alakasiz ama "bulunmus" sonuclari, esik degerlerinin farkli
sorgu turlerinde farkli kalibre edilmesi gerektigi) ilk bakista
"calisiyor" gorunen bir sey, daha yakindan bakildiginda duzeltme
gerektirdi. Bu duzeltmelerin HER BIRI kayit altina alindi - bu
da projenin en degerli ciktilarindan biri: sadece calisan bir
sistem degil, o sistemin NASIL bu hale geldiginin tam kaydi.

## Faz 6 - Duzeltme: Uretilen Goersellerde Cesitlilik Sorunu

Ayni prompt ile k=4 goersel uretildiginde, sonuclarin BIRBIRINE
COK BENZER (bazen neredeyse ozdes) ciktigi gozlemlendi. Kok neden:
her cagrida seed (rastgele sayi tohumu) belirtilmedigi icin model/
API varsayilan/sabit bir seed kullaniyordu.

Cozum: Hem FLUX (HF Inference API) hem sd-turbo (yerel) cagrilarina
her seferinde RASTGELE bir seed eklendi - artik ayni prompt'tan
k farkli, gercekten CESITLI goersel uretilebiliyor.

## Faz 6 - Esik Kalibrasyonu Tamamlandi (0.25 -> 0.29)

Ilk esik (0.25) sadece 2 ornekle belirlenmisti, yetersiz cikti.
30 sorguluk (15 ilgili, 15 ilgisiz) bir kalibrasyon seti olusturulup
CLIP skorlari olculdu.

**Bulgu 1 - CLIP skorlari kismen cakisiyor:** Ilgili grubun en dusuk
skoru (0.2803, "a group of people") ile ilgisiz grubun en yuksek
skoru (0.2892, "gothic vampire portrait") arasinda net bir bosluk
YOK - bu, CLIP'in ham benzerlik skorlarinin mutlak olarak
karsilastirilabilir olmadigini gosteren BILINEN bir sinirlama.

**Bulgu 2 - BM25 de guvenilir bir "hakem" degil:** Gri bolgedeki
alakasiz sorgularda ("dragon ball z realistic" BM25=5.84, "a medieval
castle under siege" BM25=8.61) beklenenden YUKSEK BM25 skorlari
cikti - COCO caption'larinda "ball" veya "castle" gibi kelimelerin
TESADUFEN gecmesi (orn. top/topla ilgili fotograflar) yuzunden. Bu
yaklasimdan (BM25'i gri bolge hakemi yapmak) VAZGECILDI.

**Karar:** Esik, 30 orneklik VERIYLE 0.29 olarak belirlendi. Bu deger
%93.3 dogruluk veriyor (28/30 dogru siniflandirma). Bilinen 2 hata:
"a group of people" (ilgili ama esigin altinda kaliyor, gereksiz
yere harici/uretime dusuyor - bu DUSUK MALIYETLI bir hata, Unsplash
zaten "a group of people" icin makul sonuc bulur) ve "gothic vampire
portrait" (ilgisiz ama esigin ustunde kaliyor, yanlislikla yerel
sonuc gosteriyor - bu DAHA MALIYETLI bir hata tipi ama tek bir
sinir-durumu ornegi).

**Felsefe:** Mukemmel bir ayrim (100% dogruluk) bu sinyalle
teorik olarak mumkun degil - CLIP'in dogasi bu. %93.3 dogruluk,
"tahminle 0.25" yerine "olcerek 0.29" secmenin somut kanitidir ve
projenin genel ilkesiyle (once olc, sonra karar ver) tutarlidir.

## Faz 6 - Duzeltme: Prompt Cesitliligi Eklendi

Uretilen goersellerin hala birbirine cok benzedigi (sadece seed
degil, PROMPT'un kendisi de neredeyse ozdes oldugu icin) fark edildi.
Cozum: zenginlestir_prompt() fonksiyonuna varyasyon_no parametresi
eklendi, her cagrida Ollama'ya farkli bir kamera acisi/kompozisyon
yonlendirmesi (close-up, wide shot, action pose, vb.) veriliyor.
Artik hem prompt hem seed varyasyon gosteriyor.

## Faz 6 - Bilinen Sinirlama: Hassas Metin/Logo Uretimi

Kullanici, "HAS TICARET" yazan, belirli geometrik kurallara sahip
(ucgen boyutu, kirmizi cizginin konumu) bir logo tarif etti. Model
metni DOGRU yazdi ama GEOMETRIK talimatlari (ucgenin tam boyutu,
cizginin tam konumu) tutarli sekilde takip edemedi.

Bu, FLUX dahil TUM diffusion tabanli goersel uretim modellerinin
BILINEN bir zayifligi - bu modeller "sahne/nesne" tarifi icin
egitilmis, hassas VEKTOREL/GEOMETRIK grafik tasarimi icin degil.
Cozulmeyecek bir sinirlama olarak kabul edildi ve belgelendi -
boyle bir ihtiyac icin (logo tasarimi) doğru arac zaten bir
goersel uretim modeli degil, bir VEKTOR/GRAFIK TASARIM araci
(Illustrator, Canva, veya ozel logo-uretim modelleri) olurdu.

## Faz 6 - Kritik Bulgu: Unsplash icin AYRI Esik Gerekiyor

"winged dog" sorgusunda 8 adaydan sadece 1'i esigi (0.29) gecti,
ve o da beklenen kaliteyi vermiyordu. search/unsplash_esik_kalibrasyon.py
ile "a dog", "a cat", "a bicycle", "a kitchen" gibi KESINLIKLE
alakali oldugu bilinen sorgularin Unsplash sonuclari test edildi.

**Bulgu:** Unsplash gorsellerinin CLIP skorlari, COCO gorsellerine
gore SISTEMATIK OLARAK daha dusuk cikiyor. Orn. "a kitchen" icin
Unsplash'in 5 sonucundan HICBIRI 0.29'u gecemedi (en yuksegi 0.2780).
Bu, COCO icin kalibre edilen esigin (0.29) Unsplash gorselleri icin
YANLIS/COK YUKSEK oldugunu KANITLIYOR.

**Olasi neden:** Unsplash, profesyonel/stuudyo kalitesinde
fotograflardan olusuyor, COCO ise gundelik/amator fotograflardan -
CLIP'in bu iki "gorsel alan" arasinda farkli bir skor dagilimi
uretmesi olasi (ayrintili arastirilmadi, gozlemsel bir hipotez).

**Cozum:** Unsplash yeniden puanlamasi icin AYRI bir sabit
(HARICI_ESIK = 0.24) tanimlandi, 20 orneklik (4 sorgu x 5 sonuc)
veriyle kalibre edildi (medyan ~0.273, coğu "kesin alakali" skor
0.24 ustunde).

**Ders:** Bir esik degerinin bir VERI KAYNAGI (COCO) icin dogru
olmasi, BASKA bir veri kaynagi (Unsplash) icin de dogru olacagi
anlamina gelmiyor - farkli kaynaklarin kendi kalibrasyonu olmali.
Bu, daha once "goersel arama icin ayri esik gerekiyordu" bulgusuyla
AYNI DERSIN bir baska tekrari.

## Faz 6 - Google Custom Search Denemesi: Vazgecildi

"Google Gorsellerinden direkt cekelim" fikriyle Google Cloud hesabi
acildi, Custom Search API etkinlestirildi, Programmable Search
Engine kuruldu. Ancak arastirma sonucu DOGRULANDI: Google, 20 Ocak
2026'dan itibaren YENI olusturulan arama motorlarinda "tum web'de
ara" ozelligini KALDIRDI (sadece 50 domain'e kadar arama yapilabiliyor),
ve Custom Search JSON API'nin kendisi YENI musterilere KAPATILMIS
durumda.

Karar: Bu yoldan VAZGECILDI - Google'in kendi politika degisikligi
nedeniyle yeni hesaplar icin teknik olarak mumkun degil. Zaten
calisir durumda olan Unsplash + ayri kalibre edilmis esik
(HARICI_ESIK = 0.24) cozumuyle devam edildi.

Ders: Harici bir servise bagimli bir mimari kurarken, o servisin
POLITIKA degisikliklerinin projeyi nasil etkileyebilecegini onceden
tam ongoremeyebilirsin - bu durumda hizli pivot edip zaten CALISAN
bir alternatife donmek, saplanip kalmaktan daha dogru bir muhendislik
karari.

## Faz 6 - Unsplash Arama Sorgusu Zenginlestirme Eklendi

Kullanicinin gosterdigi ornek goersel (profesyonel bir "kopek +
melek kanadi kostumu" cekimi), Unsplash'te GERCEKTEN var olan
turden bir goersel oldugu halde "winged dog" gibi kisa bir sorguyla
BULUNAMIYORDU. Kok neden: Unsplash'in kendi arama motoru, kisa/
belirsiz sorgularda somut anahtar kelime eslesmesi YAKALAYAMIYOR.

Cozum: arama_sorgusu_zenginlestir() fonksiyonu eklendi - Ollama,
kullanicinin KISA sorgusunu, bir stok fotograf sitesinin
indeksleyecegi SOMUT anahtar kelimelere ceviriyor (orn. "winged dog"
-> "dog angel wings costume"). CLIP ile yeniden puanlama hala
ORIJINAL kullanici sorgusuyla yapiliyor - zenginlestirme sadece
Unsplash'e giden ARAMA sorgusunu etkiliyor, alaka kontrolunu degil.

## [Groq'a Gecis Tamamlandi]

**Sorun:** Ollama'nin yerel 8B modeli (llama3.1), nuansli talimatlari
zayif takip ediyordu (orn. "winged dog" sorgusunu bir illustrasyon
olarak yorumlamisti).

**Denenen ve basarisiz olan modeller:** Once llama-3.3-70b-versatile,
sonra llama-3.1-8b-instant denendi, ikisi de 404 model_not_found
hatasi verdi. Arastirma sonucu ANLASILDI: Groq, 2026'da bu iki
modeli ucretsiz/gelistirici katmanindan kaldirip Enterprise
fiyatlandirmasina tasimis (16.08.2026'da tamamen kapanacaklar).

**Ayrica bulunan ikinci bug:** `prompt_engineer.py` dosyasinda
`GROQ_API_KEY = os.getenv("gsk_...")` satirinda, os.getenv()'e
degisken ADI yerine yanlislikla ANAHTARIN KENDISI verilmisti.
`os.getenv("GROQ_API_KEY")` olarak duzeltildi.

**Cozum:** GROQ_MODEL = "openai/gpt-oss-20b" olarak degistirildi -
Groq'un hala ucretsiz katmanda aktif sundugu bir "production"
modeli. Test sorgulariyla ("winged dog", "dragon ball z realistic",
"a dog walking on the moon") dogrulandi, Ollama'dan DAHA IYI sonuc
verdi (orn. "winged dog" icin dogru "dog wearing wings" arama
sorgusu uretti, dragon ball z'yi dogru Goku/Ultra Instinct olarak
tanidi).

**Karar:** Groq (openai/gpt-oss-20b) ile DEVAM EDILIYOR, Ollama'ya
bagimlilik kaldirildi.

## Faz 6 - Bagimlilik Temizligi (requirements.txt)

Groq gecisi sonrasi requirements.txt, projedeki GERCEK import'larla
karsilastirildi (findstr ile search/, api/, ui/, embeddings/, index/,
eval/, tests/ klasorleri tarandi). Uc eksik bulundu:
- matplotlib: search/test_hybrid_gorsel.py kullaniyor, listede yoktu.
- huggingface_hub: image_generation.py dogrudan import ediyor; baska
  paketlerle dolayli kuruldugu icin calisiyordu ama acikca listelenmemisti.
- diffusers + accelerate: yerel sd-turbo yedegi icin gerekli. Bunlar
  fonksiyon ICINDE import edildigi icin (satir basinda degil) ilk
  taramada gorunmedi; ayri bir findstr ile bulundu. Eksik kalsaydi,
  temiz bir kurulumda FLUX kredisi bittiginde yedek plan sessizce
  calismayacakti.

Alt sinirlar tahminle degil, `pip show` ile OLCULEN kurulu surumlerden
alindi (groq 1.7.0, diffusers 0.40.0, accelerate 1.15.0,
huggingface_hub 1.31.0, matplotlib 3.11.2).

Ders: "Calisiyor" gorunen bir ortam, eksik bagimliliklari gizleyebilir
(her sey zaten kurulu oldugu icin). Gercek dogrulama, SIFIRDAN kurulan
bir ortamda yapilir - bu adim henuz yapilmadi, teslim oncesi yapilacak.

## Faz 6 - Degerlendirme Genisletildi: BLIP'ten Bagimsiz Test Setleri

Eski 50 sorguluk set BLIP caption'larindan turetilmisti, BM25 indeksi de
ayni caption'lardan kurulu oldugu icin BM25'e haksiz avantaj sagliyordu.
COCO'nun INSAN YAZIMI anotasyonlariyla (instances_val2017.json,
captions_val2017.json) iki yeni set kuruldu. Gorsel ID eslesmesi once
OLCULDU: 5000/5000 gorsel iki dosyayla da eslesti.

Set 1 - Kategori (77 kisa sorgu, "dog", "pizza" gibi): "person" (%54
gorselde var, olcum anlamsiz) ve 20'den az gorselli kategoriler (toaster,
hair drier) disarida. Dogru cevap: kategoriyi iceren tum gorseller.
Rastgele secimle beklenen Precision@5 (taban) = 0.0310.
Set 2 - Insan caption (200 sorgu): her gorselin 5 insan caption'indan
rastgele biri sorgu, dogru cevap kaynak gorsel. seed=42.

| Yaklasim | P@5 (kategori) | Recall@5 (caption) | MRR@5 (caption) |
|---|---|---|---|
| CLIP | 0.8727 +/- 0.0276 | 0.6550 +/- 0.0337 | 0.5226 +/- 0.0318 |
| BM25 | 0.8519 +/- 0.0290 | 0.2100 +/- 0.0289 | 0.1127 +/- 0.0190 |
| Hibrit (RRF) | 0.9039 +/- 0.0205 | 0.5750 +/- 0.0350 | 0.3798 +/- 0.0289 |

(+/- standart hata. k=5, bu yuzden MRR de MRR@5.)

Bulgular:
1. BM25'in "suni yukseklik" aciklamasi DOGRULANDI: BLIP'ten bagimsiz
   sorgularda MRR 0.878 -> 0.113.
2. Kisa kategori sorgularinda uc yontem birbirinden AYIRT EDILEMIYOR
   (hibrit-CLIP farki yaklasik 0.9 standart hata). Hibritin ustunlugu
   iddia EDILEMEZ.
3. Insan caption sorgularinda hibrit CLIP'ten GERIDE (MRR farki 3+
   standart hata). BEKLENTI (hibritin kisa/gercekci sorguda one cikmasi)
   BU KISMIYLA YANLIS CIKTI. Hipotez (olculmedi): BM25, BLIP'in kisa/genel
   caption'lari uzerinde calistigi icin insan cumlelerinde gurultulu
   siralama uretiyor; esit agirlikli RRF bu gurultuyu CLIP'e karistiriyor.

Karsilastirmalar bagimsiz-ornek varsayimiyla yapildi; ayni sorgular
uzerinde eslemeli (paired) test daha hassas olur - yapilmadi.

## Faz 6 - Eslemeli Bootstrap: Hibrit Kisa Sorgularda CLIP'ten GERIDE

evaluate_v2.py'deki farklarin gercek olup olmadigini test etmek icin
eslemeli bootstrap (10.000 tekrar, seed=42, sorgular yerine koyarak
yeniden cekildi, %95 guven araligi) uygulandi. Ortalamalar
evaluate_v2 ile birebir ayni cikti (tutarlilik kontrolu gecti).

| Metrik | Karsilastirma | Ort. fark | %95 aralik | Sonuc |
|---|---|---|---|---|
| P@5 (kategori) | Hibrit - CLIP | +0.0312 | [-0.0052, +0.0675] | Ayirt edilemiyor |
| P@5 (kategori) | Hibrit - BM25 | +0.0519 | [+0.0078, +0.0961] | Sinirda (asagiya bak) |
| Recall@5 (caption) | Hibrit - CLIP | -0.0800 | [-0.1350, -0.0300] | Hibrit daha kotu |
| Recall@5 (caption) | Hibrit - BM25 | +0.3650 | [+0.2900, +0.4400] | Hibrit daha iyi |
| MRR@5 (caption) | Hibrit - CLIP | -0.1428 | [-0.1907, -0.0945] | Hibrit daha kotu |
| MRR@5 (caption) | Hibrit - BM25 | +0.2671 | [+0.2160, +0.3195] | Hibrit daha iyi |

Bulgular:
1. Hibrit, insan caption sorgularinda CLIP'ten GERCEKTEN geride. Bu,
   "gercekci sorguda hibrit one cikar" beklentisini kismen curutuyor.
2. Hibrit, BM25'ten acik ara iyi.
3. Kategori setinde hibrit-CLIP farki ayirt edilemiyor; hibritin
   ustunlugu iddia EDILEMEZ.
4. Hibrit-BM25 (kategori, P@5) alt siniri +0.008, sinirda. 6
   karsilastirma yapildigi icin yaklasik (tam Bonferroni degil) bir
   duzeltmeyle aralik 0'i icerir; bu sonuc "gercek" olarak raporlanmaz.
   Caption setindeki hibrit-CLIP farklari ayni duzeltmeyle buyuk
   olasilikla anlamli kalir (hesap dogrulanmadi, yaklasik).

Olasi neden (OLCULMEDI, hipotez): BM25, BLIP'in kisa/genel caption'lari
uzerinde calisiyor; insan cumlelerindeki kelimeler orada gecmedigi icin
siralamasi gurultulu, esit agirlikli RRF bu gurultuyu CLIP'e karistiriyor.
Sonraki adim bu hipotezi agirlikli RRF ile sinamak.

## Faz 6 - Agirlikli RRF Denemesi: BM25'e Agirlik Vermek Hibriti Kurtarmadi

Soru: BM25'e dusuk agirlik verilirse hibrit, CLIP'e yetisir mi?

Tasarim (sonuclar gorulmeden sabitlendi): rerank.py'ye istege bagli
"agirliklar" parametresi eklendi (varsayilan esit agirlik; eski
davranis birebir korundu, rerank.py testi ayni ciktiyi verdi). CLIP
agirligi 1.0'da sabit, BM25 agirligi {0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0}.
RRF k=60 ve aday havuzu (20) degistirilmedi. Agirlik SADECE dev setinde
secildi: test setindeki 200 gorselin DISINDAN 500 gorsel, seed=7,
gorsel basina rastgele bir insan caption'i (assert ile test ile
ortusmedigi dogrulandi). Secim kurali: dev MRR@5 en yuksek agirlik,
esitlikte kucuk. Secilen agirlik test setlerinde BIR KEZ olculdu.

Dev sonuclari (500 sorgu):

| BM25 agirligi | Recall@5 | MRR@5 |
|---|---|---|
| 0.0 | 0.6600 | 0.4950 |
| 0.1 | 0.6500 | 0.4595 |
| 0.2 | 0.6220 | 0.4184 |
| 0.3 | 0.6020 | 0.4002 |
| 0.5 | 0.6020 | 0.3959 |
| 0.75 | 0.6000 | 0.3900 |
| 1.0 | 0.5560 | 0.3679 |

Secilen agirlik: 0.0 (saf CLIP). Egri neredeyse tek yonlu dusuyor.
Komsu agirliklar arasindaki tek tek farklar standart hata icinde,
guvenilir olan egrinin GENEL YONU ve uclar arasindaki fark. w=0'in
izgara kenarinda cikmasi izgara darligi degil: CLIP-only zaten alt
sinir, yani BM25'in eklenen her payi bu sorgu turunda sonucu kotulestiriyor.

Test sonuclari: onceki sonuclarla birebir tutarli (kontrol satirlari
gecti). Insan caption: secilen (=CLIP) Recall 0.6550, MRR 0.5226;
esit agirlikli hibrit 0.5750, 0.3798. Kategori P@5: secilen 0.8727,
esit 0.9039 (fark -0.0312, aralik [-0.0675, +0.0052], ayirt edilemiyor).
NOT: test setinde "secilen - esit" karsilastirmasi, onceki bootstrap'in
isaret cevrilmis AYNISIDIR (secilen = CLIP); yeni kanit sayilmaz.
Bagimsiz dogrulama dev setidir (ayni yon, 500 farkli gorsel).

Sonuc: BLIP caption'lari uzerindeki BM25 ile kurdugumuz hibrit, cumle
tarzi sorgularda CLIP'ten kotu, kisa kategori sorgularinda ayirt
edilemez; agirlikla kurtarilamadi. Nedeni hala OLCULMEDI.

Sinirlar: agirlik sadece insan-caption sorgularinda secildi (kategori
icin ayri dev seti yok). Sadece BM25 agirligi arandi (RRF k ve havuz
boyutu sabit). Uretim kodu (hibrit_ara, akilli_ara) DEGISTIRILMEDI;
hibritin varsayilan kalip kalmayacagi acik karar.

Sonraki adim: BM25'in CLIP'in kacirdigini hic yakalayip yakalamadigini
(tamamlayicilik) sorgu bazli sonuclardan olcmek.

## Faz 6 - Tamamlayicilik Analizi: BM25 Yeni Aday Getirmiyor

Soru: BM25, CLIP'in kacirdigini hic yakaliyor mu? Her sorgu icin hedef
gorselin CLIP ve BM25 ilk 5 / ilk 20 icinde olup olmadigina bakildi
(insan caption sorgulari, tek hedef; kategori seti bu analize uygun
degil, cok sayida dogru cevap var).

Yorumlama kurali sonuclar gorulmeden yazildi: "sadece BM25 buldu" sayisi
"sadece CLIP buldu"dan cok kucukse BM25 yeni bilgi eklemiyor.

| Olcum | Dev (500) | Test (200) |
|---|---|---|
| CLIP ilk 5'te buldu | 330 (%66.0) | 131 (%65.5) |
| BM25 ilk 5'te buldu | 105 (%21.0) | 42 (%21.0) |
| Sadece CLIP buldu (ilk 5) | 233 | 99 |
| Sadece BM25 buldu (ilk 5) | 8 | 10 |
| BM25 ilk 20'de buldu, CLIP ilk 20'de bulamadi | 12 (%2.4) | 9 (%4.5) |
| Hibrit (esit agirlik) ilk 5'te buldu | 278 (%55.6) | 115 (%57.5) |

Hibritin "sadece CLIP buldu" sorgulardan kaybi: dev 69/233, test 23/99.
"Sadece BM25 buldu" sorgulardan kurtardigi: dev 5/8, test 4/10.

Bulgular:
1. BM25 yeni aday neredeyse hic getirmiyor (ilk 20'de en fazla %2.4,
   dev). Kural geregi: BM25 bu sorgu turunde yeni bilgi eklemiyor.
2. Esit agirlikli RRF bunun bedelini oduyor (dev'de net -52 sorgu).
3. Cikarmayla tahmin: hibrit "ikisi de bulamadi" grubundan yaklasik 12
   sorguyu ilk 5'e tasimis gorunuyor (BM25'in siralama destegi). Bu
   dogrudan SAYILMADI, "ikisi de buldu" grubunun korundugu varsayimina
   dayaniyor; her halde 69 kayip karsisinda kucuk.

DUZELTME: analiz scriptindeki "Birlesim (ust sinir, mukemmel
birlestirme)" etiketi yanlis. Bu sayi sadece iki ilk-5 listesi arasinda
secim yapmanin tavani; RRF ilk 20'lik havuzlari birlestirdigi icin ilk
5 icin gercek tavan ilk-20 birlesimidir (dev %85.2).

Sinirlar: kategori sorgularinda tamamlayicilik olculmedi. BM25'in zayif
olma NEDENI (BLIP caption'larinin kisa/jenerik olmasi) hala hipotez.
Uretim kodu (hibrit_ara) DEGISTIRILMEDI; hibritin varsayilan kalip
kalmayacagi acik karar.

## Faz 6 - Prompt Motoru: Tire Duzeltmesi ve Bir Gozlem

Groq modeli prompt'larda bazen ASCII olmayan tire (U+2011) uretiyordu;
_groq_ile_sor icinde duz tireyle degistirildi, ciktilarda dogrulandi.
Ek koruma: model cevabi bos (None) gelirse hata vermek yerine
bos metin kullaniliyor, cagiran fonksiyon sablon yedegine dusuyor.

Gozlem (OLCULMEDI): "a dog walking on the moon" icin Unsplash arama
sorgusu iki calistirmada farkli cikti ("dog walking moon surface",
"dog wearing astronaut suit moon"). Ikincisi kullanicinin soylemedigi
bir oge (astronot kiyafeti) ekliyor. Neden: temperature=0.8 ve
"nitelik dogal olamiyorsa kostum" talimatinin fazla genellenmesi
(hipotez). Sonraki adim: ayni sorguyu tekrar tekrar calistirip
degiskenligi saymak, sonra arama sorgusu icin dusuk temperature
denemek.

## Faz 6 - Arama Sorgusu Zenginlestirme: Degiskenlik Olcumu

Soru: Groq, ayni sorgu icin her calistirmada farkli Unsplash arama
sorgusu uretiyor mu, ve bu sorun mu? Tasarim (sonuclar gorulmeden):
6 sorgu x 10 tekrar x iki temperature (0.8 mevcut, 0.2). Sadece
degiskenlik olculdu; Unsplash'ten gelen fotograflarin KALITESI
olculmedi.

Bulgular:
1. Temperature 0.2, degiskenligi olculebilir bicimde azaltmadi
   (ortalama farkli cikti sayisi 4.3 vs 4.2; T=0.2'de bir cagri orijinal
   sorguyu dondurdu, nedeni ayirt edilemedi). Temperature dusurulmedi.
2. Asil sorun ICERIK KAYMASI: model sorguya kullanicinin soylemedigi
   ogeler ekliyor. "a dog walking on the moon" icin T=0.8'de 8/10 cikti
   uzay kiyafeti (space suit / spacesuit / astronaut suit) iceriyor
   (T=0.2'de 5/9). "a kitchen" icin 10/10 cikti "modern" ekliyor.
   "dragon ball z realistic" icin 5/10 cikti cosplay/costume ekliyor.
3. Stabil olanlar: "winged dog" 20/20 cikti "wings" iceriyor, "a cat
   wearing sunglasses" 20/20 ayni cikti.

Hipotez (henuz kanitlanmadi): "dogal olmayan nitelik -> kostum" kurali
(winged dog icin yazilmisti) yer/eylem durumlarina da genelleniyor.
Sonraki adim: talimati daraltmak (kostum istisnasi sadece vucut parcasi/
ozellik icin; ifadede olmayan oge eklenmesin) ve ayni testi tekrarlamak.

On-kayitli basari olcutleri: (1) ay sorgusunda suit icerenler 8/10'dan
<=2/10'a, (2) "winged dog" ciktilari "wing" + "wearing"/"costume" icermeye
devam etmeli, (3) "cat wearing sunglasses" 10/10 ayni, "kitchen"de
"modern" belirgin azalmali.

Sinir: bu degisikligin NIHAI sonuclara (CLIP ile yeniden puanlanan
Unsplash fotograflari, uretim katmanina dusme orani) etkisi OLCULMEDI.

## Faz 6 - Arama Sorgusu Talimati Daraltildi: Kismi Sonuc, Yeni Sorunlar

Talimat daraltildi (KURAL 1: ifadede olmayan oge ekleme; KURAL 2:
kostum istisnasi sadece vucut parcasi/ozellik icin, yer/eylem icin
degil). Ayni 120 cagrilik test tekrarlandi.

On-kayitli olcutler (4'u de saglandi): ay sorgusunda uzay kiyafeti
8/10 -> 0/10 (T=0.8); "winged dog" 20/20 "wings" + "wearing"/"costume"
icerdi; "cat wearing sunglasses" 20/20 ayni; "kitchen"de "modern"
kayboldu.

Olcutlerin YAKALAMADIGI iki yeni sorun:
1. "Basarisiz" cagri (cikti == orijinal sorgu veya Groq hatasi)
   1/120'den 31/120'ye cikti: "dragon ball z realistic" 18/20, "a red
   bicycle" 9/20, "a kitchen" 4/20. Basarisizlikta fonksiyon orijinal
   sorguyu dondurur, yani ozel isimli sorgularda zenginlestirme buyuk
   olcude devre disi kalmis olabilir (5.9'daki eski sorun). Test
   scripti "model girdiyi aynen yazdi" ile "Groq hatasi"ni AYIRMIYOR
   (tasarim hatasi); hatalar konsolda gorunmedigi icin API hatasi daha
   az olasi, ama bos yanit mi aynen yansitma mi bilinmiyor.
2. Dejenere tekrarlar: basarili 16 "a kitchen" cagrisinin 7'si "kitchen
   kitchen kitchen"; "red bicycle red bicycle" de goruldu. Hipotez
   (kanitlanmadi): "3-6 kelime" alt siniri ile KURAL 1 catisiyor.

Karar: yeni talimat teshis bitene kadar KANITLANMAMIS sayilir. Sonraki
adim: eval/groq_teshis.py ile ham yanit ve finish_reason'i gormek.
Nihai sonuclara (Unsplash fotograflari, uretim katmanina dusme orani)
etkisi hala OLCULMEDI.

## Faz 6 - Arama Sorgusu Teshisi: "Basarisiz" Cagrilarin Nedeni

eval/groq_teshis.py ile 15 cagrinin HAM yaniti incelendi: istisna yok,
bos yanit yok, finish_reason hepsinde "stop". Yani sorun API degil;
model, ozellikle KURAL 1 (oge ekleme) sonrasi, somut sorgulari AYNEN
geri yaziyor ("dragon ball z realistic" -> "dragon ball z realistic").

DUZELTME (kendi onceki yorumuma): bir onceki kayitta "ozel isimli
sorgularda zenginlestirme devre disi, 5.9'daki eski soruna donus"
demistim; bu fazla iddialiydi. 5.9, anahtar kelimesi eksik kisa
sorgularla ("winged dog") ilgiliydi ve o sorgu 20/20 dogru calisiyor.
Somut bir sorguyu ("a red bicycle", "a kitchen") degistirmemek tek
basina kusur degil. Ayrica test scriptinin "basarisiz" metrigi
"aynen geri yazma" ile "Groq hatasi"ni ayirt etmedigi icin sorunun
buyuklugunu (31/120) abartiyordu. Ham sorgunun Unsplash'te zenginlestirilmis
sorgudan daha kotu/iyi sonuc verip vermedigi OLCULMEDI.

Gercek kusur: kelime tekrari ("kitchen kitchen kitchen": ilk testte
7/16, teshiste 1/5). Hipotez (kanitlanmadi): "3-6 kelime" alt siniri
kisa sorgularda tekrara yol aciyor.

Duzeltme denemesi: talimatta "3-6 words" -> "at most 6 words" ve
KURAL 3 (somut sorguyu degistirme, ayni kelimeyi iki kez yazma).
Olcutler (sonuclar gorulmeden): kelime tekrarli cikti 60 cagrida <=1;
ay sorgusunda uzay kiyafeti 0; "winged dog" 10/10 "wing" +
("wearing"/"costume"); "cat wearing sunglasses" 10/10 ayni. "Aynen geri
yazma" sadece raporlanir. Temperature artik 0.8'de sabit (0.2 isimize
yaramadi).

## Faz 6 - Arama Sorgusu Talimati: Metin Olcutleri Saglandi, Etkisi Hala Olculmedi

Talimatta "3-6 words" -> "at most 6 words" ve KURAL 3 (somut sorguyu
degistirme, ayni kelimeyi iki kez yazma) eklendi. 60 cagrilik test.

On-kayitli olcutler: kelime tekrari 0/60 (olcut <=1, saglandi); ay
sorgusunda uzay kiyafeti 0/10 (saglandi); "winged dog" 10/10 "wing" +
("wearing"/"costume") (saglandi); "a cat wearing sunglasses" iki farkli
cikti verdi (6x "a cat wearing sunglasses", 4x "cat wearing
sunglasses"): olcut "10/10 ayni cikti" olarak yazilmisti ve YAZILDIGI
HALIYLE SAGLANMADI; fark yalnizca "a" artikeli, icerik ayni.

Gozlem: aynen geri yazma 52/60. Zenginlestirme artik somut sorgularda
neredeyse hicbir sey yapmiyor; degisen tek sorgu "winged dog".
"dragon ball z realistic" 10/10 aynen dondu; onceki surumde
cosplay/costume ekleniyordu. Bu davranisin kaybi iyi mi kotu mu
OLCULMEDI: simdiye kadar sadece cikti METNINE baktik, Unsplash'ten
donen fotograflara degil.

Sonraki adim: eval/unsplash_ham_vs_zengin.py. 6 sorgu (yerel esigin
altinda kalip Unsplash'e dusenler), ham ve zenginlestirilmis sorgu,
8 aday, ORIJINAL sorguyla CLIP puani, kac aday HARICI_ESIK'i geciyor.
On-kayitli karar kurali: zengin toplamda daha cok aday geciriyorsa
degerli; esit veya ham onde ise olculebilir kazanc yok. Sorgu sayisi
kucuk (6), toplama bakilir.

## Faz 6 - Arama Sorgusu Zenginlestirme: Unsplash'te Olculebilir Kazanc Yok

6 sorgu (yerel esigin altinda kalip Unsplash'e dusenler), her biri ham
ve zenginlestirilmis sorguyla Unsplash'e gonderildi (8 aday), adaylar
ORIJINAL sorguyla CLIP ile puanlandi (HARICI_ESIK = 0.24).

Sonuc: esigi gecen aday HAM 38/48, ZENGIN 36/48. On-kayitli kurala
gore (esit veya ham onde -> olculebilir kazanc yok) zenginlestirmenin
olculebilir bir faydasi gosterilemedi.

Sinirlar (onemli):
1. 6 sorgunun 4'unde zenginlestirme sorguyu DEGISTIRMEDI, yani gercek
   karsilastirma sadece 2 sorguda: "winged dog" (6 vs 5) ve "a dog
   walking on the moon" (5 vs 4). Farklar tek aday; Unsplash siralama
   degiskenligi veya CLIP gurultusunden ayirt edilemez.
2. Olcut zayif: adaylarin ~%79'u esigi geciyor (38/48), esik bu
   sorgularda neredeyse hicbir seyi elemiyor. "CLIP esigini gecen aday
   sayisi" fotografin gercekten istenen sahneyi (ornegin kanatli kopek)
   gosterip gostermedigini olcmez; 5.9'daki asil sorun buydu ve bu test
   onu sinamaz.
3. "winged dog": en yuksek skor iki kolda ayni (0.346, buyuk olasilikla
   ayni fotograf); medyan zenginde daha dusuk (0.255 vs 0.286). Altı
   sorguyla bu bir iddiaya donusturulemez.
4. Sadece SU ANKI talimat olculdu; eski talimatin (cosplay/costume
   ekleyen surum) etkisi olculmedi.

Karar: uretim kodu DEGISTIRILMEDI. Sonraki adim (sirasiyla): "winged
dog" icin iki kolun ilk 3 fotografini gozle karsilastirmak; sonuca gore
zenginlestirmeyi koruma/kaldirma karari. Kaldirilirsa her harici aramada
bir Groq cagrisi (gecikme + hiz siniri riski) azalir.

## Faz 6 - Arama Sorgusu Zenginlestirme: Kor Gozlemle Fayda Gosterildi (Sinirli)

Onceki CLIP-esigi testi zayif bir olcutle (esigi gecen aday sayisi,
38 vs 36) fayda gosteremedi; 5.9'daki asil soruyu sinamiyordu. Bu
yuzden A/B kor gozlem yapildi (eval/ham_vs_zengin_gorsel.py): ham ve
zenginlestirilmis sorgu ile Unsplash'ten 8'er fotograf, sutunlar
rastgele A/B atandi, anahtar degerlendirme bitene kadar acilmadi.

On-kayitli kural: "isabet" = fotograf istenen ozelligi GERCEKTEN
gosteriyor (kostum/prop dahil, duz hayvan degil). Karar olcutu: her
kolun ilk 3 fotografindaki isabet toplami; fark >= 2 ise o kol anlamli
onde, 0-1 ise fayda gosterilemedi. "Biyikli kedi" icin kural sonradan
(anahtar acilmadan) netlestirildi: yalnizca belirgin ve kalin biyik
isabet sayildi; isaretler degismedi.

Sonuc (ilk 3 / hepsi):
- winged dog: ham 1/1, zengin ("dog wearing wings") 2/2
- a cat with a mustache: ham 0/0, zengin ("cat wearing mustache") 1/3
- a horse with horns: zenginlestirme sorguyu degistirmedi, karsilastirmaya
  girmedi
- Toplam ilk 3: ham 1, zengin 3 -> fark 2: on-kayitli esik saglandi
  (esikte).

Sinirlar:
1. Fark tam esikte (2); tek bir fotografin farkli isaretlenmesi sonucu
   "fayda gosterilemedi"ye cevirirdi.
2. "winged dog" farki tek fotograftan geliyor (iki sutunda en az dort
   ortak fotograf var); "a cat with a mustache" daha guclu (3 vs 0).
3. Iki sorgu, tek degerlendirici; kor atama on yargiyi azaltir,
   ortadan kaldirmaz.
4. Sadece "dogal olmayan ozellik" turu test edildi. Diger sorgularda
   zenginlestirme neredeyse hic mudahale etmiyor (52/60 aynen geri
   yazma), etkisi orada notr.
5. Anahtar dosyasindaki "iki_kolda_ortak_fotograf" alani URL'leri
   karsilastirdigi icin YANLIS (ekran goruntulerinde ortak fotograflar
   gorunuyor, ayni fotografin URL parametreleri farkli); kullanilmamali.

Karar: zenginlestirme KORUNUYOR, uretim kodu DEGISTIRILMEDI. Daha guclu
kanit istenirse 6-8 "dogal olmayan ozellik" sorgusuyla tekrarlanabilir.

## Faz 6 - Temiz Kurulum Testi Tamamlandi (API ve Arayuz Dahil)

requirements.txt, proje disinda (C:\temp\test_venv) sifirdan kurulan
bir sanal ortamda dogrulandi. Ilk kurulum denemesi disk doluluguyla
("No space left on device") yarida kesildi; yer acildiktan sonra
ortam silinip yeniden kuruldu.

Dogrulananlar (hepsi temiz ortamin Python'uyla):
- Tum dogrudan import edilen paketler hatasiz yuklendi.
- search/hybrid_search.py ve search/prompt_engineer.py calisti
  (15 Ekim).
- uvicorn ile API ayaga kalkti; tests/test_api.py 2/2 gecti
  (/health ve /search/text).
- streamlit ile arayuz acildi; "a dog" sorgusu 4 koepek gorseli,
  RRF skorlari ve "Kendi veri setimde bulundu" etiketiyle sonuc verdi.

Sinirlar: yerel sd-turbo yedegi (FLUX kredisi bitince devreye giren
yol) temiz ortamda CALISTIRILMADI, yalnizca import edildigi
dogrulandi. Gorsel yukleyerek arama (/search/image) ve harici/uretim
katmanlari (Unsplash, Groq, FLUX) bu testte sinanmadi; sadece yerel
metin aramasi yolu sinandi.

## Faz 6 - Uretim Kodu Degisiklikleri (OLCULMEDEN eklendi)

Eklenenler: (1) search/visual_judge.py: Groq qwen/qwen3.8-27b ile
evet/hayir gorsel hakem (384x384'e kucultme, reasoning_effort="none",
temperature=0, hata/429'da False). (2) Openverse kaynagi ve Unsplash ile
birlestiren harici_kaynaklarda_ara(). (3) Her sorgu icin 3 arama
sorgusu varyasyonu. (4) Gorsel uretimde Pollinations bulut yedegi,
HF kredi bitince kisa devre. (5) Kismi AI tamamlama: bulunan gercek
fotograflar korunur, eksikler AI ile uretilir; arayuzde ayri
etiketler. (6) Paralel indirme/uretim (ThreadPoolExecutor).
(7) HARICI_ESIK 0.24 -> 0.25.

Durum: bu degisikliklerin HICBIRI etiketli veride olculmedi.
Gerekce notu: esik degisikligi tek bir ornege (0.2442 alan duz Corgi
fotografi) dayaniyor, 20 orneklik kalibrasyonla degil.

Bilinen riskler (dogrulanmadi): hakem 429'da False dondugu icin hiz
siniri dogru fotograflari da eleyebilir (model: 30 RPM, 8K TPM,
olculen ~1.8K token/gorsel, yani ~4 gorsel/dk); kucultmenin token
tasarrufu belgeyle celisiyor (belge: 2048 token/gorsel) ve ince
ayrintilari silebilir; Pollinations ve Openverse kullanim/hiz sinirlari
dogrulanmadi; Unsplash demo anahtari saatlik sinirli.

Sonraki adim: canli aramada API logunu incelemek; etiketli veride
CLIP ve hakemi karsilastirmak (eval/etiketler_v2.json).

## Faz 6 - Uretim Kodu Canli Test: "a winged dog" (Tek Calistirma)

Hakem 4 adaya cagri yapti, 429 yok. Sonuc: 3 gercek fotograf (kanatli
koepek, kostum/prop dahil) + 1 AI gorseli. Onceki calistirmada 2/4
dogru gercek fotograf vardi. Tek sorgu, tek calistirma: yon gosterir,
hakemin faydasini kanitlamaz.

Gozlemler: (1) AI ile tamamlanan 4. gorselde kanat gorunmuyor ve
"pollinations.ai" filigrani var; hakem AI gorsellerini denetlemiyor.
(2) Openverse 15 sn zaman asimina ugradi, katki 0. (3) Pembe kanatli
koepek CLIP 0.2526 ile 0.25 esigini 0.0026 farkla gecti; esik
isabetleri kesebilir. (4) Hakeme en iyi k+1 aday gittigi icin esigi
gevsetmek hakem cagri sayisini en fazla k+1'de tutar.

Koddan okunan, CALISTIRILMAYAN bulgular: api/main.py'de gorsel
arama yolunda akilli_ara'ya gorsel esigi (0.75) metin esigi olarak
geciyor, yerel katman hep atlaniyor olabilir; yerel katmanda hakem
6 adaya kadar soruluyor (dakikalik token sinirini asabilir).

Sonraki adim: etiketli veride hakemin dogrulugunu ve CLIP onfiltresinin
isabet kaybini olcmek.

## Faz 6 - Duzeltme: Puanlanamayan Adaylarin Nedeni Belli Oldu

Onceki kayitta "73/177 aday puanlanamadi, neden bilinmiyor" yazilmisti.
clip_analiz_v2.py'nin tam ciktisi incelendi: TUM hata satirlari
api.openverse.org adresini gosteriyor (cogu 20 sn ReadTimeout, bir
tanesi HTTP 424). Aritmetik uyumlu: Unsplash 96/96 puanlandi, Openverse
yalnizca 8/81 puanlandi (73 hata; 25 isabet ve 48 isabetsiz).

Sonuclar: (1) CLIP olcumleri (AUC, esik etkisi) fiilen YALNIZCA Unsplash
icin gecerli (104 puanlanan adayin 96'si Unsplash); Openverse icin CLIP
hakkinda sonuc YOK. (2) Havuz kalitesi sayilari (Unsplash 44/96,
Openverse 28/81) etiketlerden geldigi icin indirme hatasindan
etkilenmedi. (3) Hatanin NEDENI (Openverse kucuk resim servisi
yavasligi, anonim istek siniri vs.) hala hipotez; tarayicida ayni
resimler yuklenebildi.

Uretim sonucu: canli aramada da Openverse aramasi 15 sn zaman asimina
ugradi ve adaylarin hepsi Unsplash'ten geldi; uretimdeki indirme
zaman asimi 6 sn. Openverse su an uretimde fiilen katki vermiyor ve
sirali cagrildigi icin her aramaya en fazla 15 sn ekliyor. Karar
(duzelt/cikar) hakem olcumunden sonra.

Onceki kayitta Unsplash'te de eksiklik olabilecegi ihtimali dusunulmustu;
hata satirlari bunu desteklemiyor.

Sonraki adim: eval/hakem_olcum_v2.py ile hakemin CLIP esigini gecen 83
adayda dogrulugunu olcmek. On-kayitli kural: hakem isabetlerin >=%80'ini
kabul eder VE esigi gecen isabetsizlerin <=%25'ini kabul ederse faydali;
aksi halde "fayda gosterilemedi". Ornek kucuk (47/36), yaklasik +/-15 puan
belirsizlik.

## Faz 6 - Hakem Olcumu (ARA SONUC, 49/83 gecerli cagri)

Populasyon: CLIP >= 0.25 olan 83 aday (47 isabet, 36 isabetsiz).
Uretimdeki gorsel_hakem_onayla oldugu gibi cagrildi. 54 kayit alindi
(5'i hata ile bitti, 29 aday henuz sorulmadi); gecerli 49 cagri (30
isabet, 19 isabetsiz), adaylar sabit seed ile karistirilmisti.
Neredeyse tamami Unsplash (Openverse'ten tek aday).

On-kayitli kural: isabet kabul >= %80 VE isabetsiz kabul <= %25.
Sonuc: isabet kabul 24/30 = %80.0 (TAM SINIRDA; bir fazla ret kurali
bozardi), isabetsiz kabul 1/19 = %5.3. Kural harfiyen saglaniyor ama
sonuc KESIN DEGIL: kaba Wilson araliklari yaklasik %63-90 ve %1-25
(iki aralik da esigi kapsiyor).

Sorguya gore: reddedilen 6 isabet su sorgularda: umbrella (3/3), skateboard
(1/1), mustache (1/3), workspace (1/4). Hakem uc ogeli/iliskili sorgularda
daha katı gorunuyor (hipotez: talimat "her oge" diyor, 384 kucultme kucuk
ogeleri silebilir; alternatif: etiketler bu sorgularda cömert). Hakemin
yarari da gorundu: blue car/yellow house icin CLIP esigini gecen 7 yanlis
fotografin 7'si de reddedildi.

Sorun: 49 basari sonrasi 5 ardisik hata (429). Hangi sinirin dolduguna
dair hata mesaji kaydedilmemisti; 49 cagri ~90-100K token ve gunluk
200K sinirinin altinda, yani aciklama belirsiz. Betige hata metni kaydi
eklendi.

Sonraki adim: uyusmazliklarin gozle kontrolu (hakem mi etiket mi hakli),
kalan 34 adayin olcumu, sonra kural 83 adayin TAMAMI uzerinden
degerlendirilecek.

## Faz 6 - Hakem Uyusmazliklari: Gozle Inceleme (KOR DEGIL)

Hakem ile etiketin ayrildigi 7 fotograf (hakem RED + etiket ISABET: 6;
hakem KABUL + etiket ISABETSIZ: 1) tek sayfada gosterildi ve kullanici
her biri icin karar verdi. Inceleme kor degildi (kararlar gorunuyordu).

Sonuc: hakem haklı 1 (workspace/white desk: etiket fazla katiydi),
etiket haklı 6 (hakem gercek isabeti reddetti: umbrella x3, skateboard,
mustache, workspace).

Ikincil okuma (yanli olabilir): duzeltilmis etiketlerle hakem gercek
isabetlerin 25/31'ini (%80.6, kaba aralik %64-91) kabul etti ve 18
isabetsizin 0'ini kabul etti. Ön-kayitli birincil sonuc DEGISMEDI:
24/30 ve 1/19 (etiketlerin ilk hali).

Bulgular: (1) Hakem temkinli: dogrulanan yanlis kabul yok, gercek
isabetlerin ~%19'unu reddediyor. (2) Retler uc ogeli sorguda yogun
(umbrella 3/3); ekran goruntusunde uc fotografta da kopek kucuk.
Hipotez (DENENMEDI): 384 kucultme kucuk nesneyi siliyor + "her oge"
katiligi. (3) Etiket gurultusu: incelenen 7 uyusmazligin 1'inde
etiket hataliydi; uyusan ciftler incelenmedi.

Karar baskisi: gercek fotograf varken AI gosterme (yanlis ret) mi,
yanlis fotograf gosterme (yanlis kabul) mi daha kotu: URUN KARARI,
henuz verilmedi.

Sonraki adim: kalan 34 adayin olcumu, sonra 6 yanlis ret + 18
isabetsiz fotografin 768 piksel ile yeniden sorulmasi. On-kayitli
kural: 6 retten >=4 kabule donerse VE isabetsizlerden 0'i kabul
edilirse kucultme ana neden sayilir; aksi halde sayilmaz.

## Faz 6 - Hakem Olcumu TAMAMLANDI (83/83 aday)

Populasyon: CLIP >= 0.25 olan 83 aday (47 isabet, 36 isabetsiz);
78'i Unsplash, 5'i Openverse. 83 cagrinin hepsi gecerli (hata 0).

On-kayitli kural: isabet kabul >= %80 VE isabetsiz kabul <= %25.
Sonuc: 38/47 = %80.9 (SINIRDA; bir fazla ret kurali bozardi) ve
2/36 = %5.6. Kural harfiyen saglandi. Kaba Wilson araliklari: ~%67-90
ve ~%2-18: yanlis kabulun dusuklugu makul guvenle soylenebilir,
isabet kabulunun >=%80 oldugu soylenemez.

CLIP esigi (0.25) tek basina: isabetlerin %100'unu, isabetsizlerin
%100'unu (36/36) gecirdi. Hakem: isabetsizlerin 34/36'sini eledi,
isabetlerin 9/47'sini (%19) kaybetti.

Sorguya gore (SONUCLARA BAKILARAK yapilan kesif gruplamasi): basit
sorgularda (sunglasses, horse in snow, red bicycle, eiffel, winged dog)
isabet kabul 29/29; iliski/ince nitelik sorgularinda (umbrella 1/5,
skateboard 0/1, mustache 3/6, workspace 5/6) 9/18 (%50). Uc sorguda
(blue car/yellow house, cup on laptop, horse with horns) havuzda isabet
yoktu; hakem 17 isabetsizin 17'sini reddetti.

Acik noktalar: (1) 83'e cikan kayittan 4 yeni uyusmazlik (3 ret, 1
yanlis kabul) gozle incelenmedi; 7 incelenenin 1'inde etiket hatali
cikmisti. (2) Ilk calistirmadaki 5 ardisik 429 aciklanamadi; ikinci
calistirmada 34 cagri hatasiz bitti. Mesaj saatlerinden (yaklasik)
hata ile yeniden baslama arasi ~10 dk gorunuyor: gunluk token siniri
aciklamasiyla pek uyusmuyor, dakikalik sinir veya gecici servis sorunu
daha olasi (CIKARIM). Uretimde hakem cagrilari aralıksiz ve 429'da
yalnizca 2 sn beklenip 1 kez yeniden deneniyor; dakikalik token siniri
icin yetersiz olabilir, basarisizlikta gorsel REDDEDILIYOR. Olculmedi.
(3) Olcum neredeyse tamamen Unsplash; Openverse'te CLIP asamasinda
indirme sorunu var.

Sonraki adim: yeni 4 uyusmazligin incelenmesi; eval/token_olcum.py ile
kucultmenin token etkisinin olculmesi; 768 piksel deneyi. On-kayitli
kural: 9 reddedilen isabetten >=5 kabule doner VE 384'te reddedilen
34 isabetsizden <=1'i yeni kabul edilirse kucultme ana neden sayilir;
aksi halde sayilmaz.

## Faz 6 - Token Olcumu: Kucultme Token Tasarrufu SAGLAMIYOR

Ayni Unsplash fotografi (1080x720) 384, 768 ve orijinal boyutta
Groq qwen/qwen3.8-27b'ye gonderildi: girdi token UCUNDE DE 1823
(onceki yerel COCO fotografi ~640x480 icin de 1823 cikmisti). Yani bu
aralikta gorsel basina token sabit.

Sonuc: ozetteki "384'e kucultme token tuketimini azaltti" iddiasi
YANLIS cikti; kucultme sadece yukleme boyutunu/gecikmeyi azaltiyor ve
ince ayrintilari silebiliyor. Buyuk gorsel token acisindan ucretsiz.
Sinirlar: tek fotograf; olcumdeki soru metni uretimdekinden kisa
(uretimdeki prompt'un token'i olculmedi).

## Faz 6 - Hakem Uyusmazliklari (11 uyusmazlik, KOR DEGIL, 2. inceleme)

83 kayitlik tam olcumde uyusmazlik sayisi 11: kullanici hepsini
inceledi; hakem yalnizca 1'inde haklı (beyaz masa/workspace: etiket
hataliydi), 10'unda etiket haklı (YORUM: kullanici mesaji bu sekilde
anlasildi). Duzeltilmis etiketlerle ikincil okuma: hakem gercek
isabetlerin 39/48'ini (%81.3, kaba aralik ~%68-90) kabul etti, gercek
isabetsizlerin 1/35'ini (%2.9, ~%1-15). Birincil on-kayitli sonuc
(38/47, 2/36) degismedi. Sinirlar: yalnizca uyusmazliklar incelendi;
uyusan ciftlerdeki etiket hatalari gorulmedi; duzeltme hakem lehine
tek yonlu olabilir.

Sonraki adim: eval/hakem_768_deneyi.py. Gruplar: A = hakemin reddettigi
9 gercek isabet (384 yeniden + 768), B = reddettigi 34 isabetsiz (768).
On-kayitli kural: A'nin >=5'i 768'de kabule doner VE B'nin <=1'i kabul
edilirse kucultme ana neden sayilir; 384 kontrolunde >=2 ret kabule
donerse deney gurultu icinde sayilir ve kural uygulanmaz; aksi halde
ana neden sayilmaz. Ornek kucuk (9/34), pilot.