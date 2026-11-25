# Değerlendirme Raporu (Faz 4)

Bu rapor, 50 sorguluk rastgele seçilmiş bir test seti üzerinde `Sadece CLIP`, `Sadece BM25` ve `Hibrit (RRF)` yaklaşımlarının performansını değerlendirmektedir. Faz 6'da, BLIP'ten bağımsız iki ek test setiyle yapılan genişletilmiş değerlendirme aynı dosyanın ikinci yarısında yer alır.

Test seti: `eval/test_sorgular.json` (BLIP caption'larından, seed=42 ile rastgele seçilmiş 50 sorgu-görsel çifti).
Metrikler: `eval/evaluate.py` (precision@k, recall@k, MRR - elle yazılmış, standart bilgi getirimi formülleri).

## Sayısal Sonuçlar (k=5)

| Yaklaşım | Precision@5 | Recall@5 | MRR |
| :--- | :--- | :--- | :--- |
| Sadece CLIP | 0.1000 | 0.5000 | 0.3680 |
| Sadece BM25 | 0.1880 | 0.9400 | 0.8783 |
| Hibrit (RRF) | 0.1640 | 0.8200 | 0.6213 |

Not: Her sorgunun tek bir doğru cevabı olduğu için Precision@5 teorik olarak en fazla 0.20 olabilir (5 sonuçtan en çok 1'i doğru). Bu tablodaki Precision değerleri bu tavana göre okunmalıdır.

## Analiz ve Beklenmeyen Sonuçların Gerekçesi

Tabloya bakıldığında BM25 modelinin hem CLIP'i hem de Hibrit yaklaşımı belirgin bir farkla geçtiği görülmektedir. Hibrit yaklaşımın en iyi sonucu vermesi beklenirken geride kalmasının nedeni, **test setinin oluşturulma metodolojisidir.**

* **BM25'in Suni Başarısı:** `build_test_set.py` dosyasında, her bir test görseli için BLIP tarafından üretilen caption'ların *tamamı* hiçbir kısaltma yapılmadan doğrudan arama sorgusu olarak kullanılmıştır. BM25 bir kelime eşleştirme algoritması olduğu için, indekslediği metnin birebir aynısı aratıldığında mükemmele yakın (~%94 Recall) bir eşleşme bulmuştur. Bu, gerçek kullanıcı davranışını yansıtmayan, teste özgü bir avantajdır.
* **CLIP'in Gerçek Performansı:** CLIP modeli, metin ile metni değil; metin ile görseli eşleştirmektedir. Kelime kopyası çekme şansı olmamasına rağmen, anlamsal uzayda ilk 5 sonuç içinde doğru görseli %50 oranında bulabilmesi, modelin multimodel anlama yeteneğinin güçlü olduğunu kanıtlamaktadır.
* **Hibrit (RRF) Durumu:** Hibrit model, BM25'in "mükemmel" listesi ile CLIP'in anlamsal listesini birleştirdiği için, BM25'in metin eşleştirmesindeki suni avantajını bir miktar törpülemiş ve iki metrik arasında bir dengeye (0.62 MRR) oturmuştur.

**Not (Faz 6 ile güncellendi):** Bu bölümün ilk halinde, gerçek kullanımda (kısa, spesifik olmayan veya hatalı sorgularda) BM25'in başarısının düşeceği ve CLIP ile Hibrit yaklaşımın öne çıkacağı öngörülmüştü. BLIP'ten bağımsız setlerle yapılan ek değerlendirme (aşağıda) bu öngörüyü **yalnızca yarısıyla** doğruladı: BM25'in başarısı gerçekten çöktü ve hem CLIP hem Hibrit onu geçti, ancak Hibrit, CLIP'i geçemedi.

## Ek Değerlendirme: BLIP'ten Bağımsız Test Setleri (Faz 6)

### Neden gerekti?

İlk değerlendirmedeki 50 sorgu BLIP caption'larından, BM25 indeksi de aynı caption'lardan kuruluydu: BM25 fiilen kendi metnini arıyordu. Bu bölüm, COCO'nun insan yazımı anotasyonlarıyla (BLIP'ten bağımsız) kurulan iki ek test setinin sonuçlarını ve bunların istatistiksel analizini içerir. Görsel ID eşleşmesi önce ölçüldü: 5.000 görselin tamamı iki anotasyon dosyasıyla da eşleşti.

### Test setleri

1. **Kategori seti (77 sorgu):** "dog", "pizza" gibi kısa kategori adları. Doğru cevap: o kategoriyi içeren tüm görseller. "person" (görsellerin %54'ünde var, ölçüm anlamsız kalır) ve 20'den az görselli kategoriler (toaster, hair drier) dışarıda. Rastgele seçimle beklenen Precision@5 = 0.031.
2. **İnsan caption seti (200 sorgu):** 200 rastgele görselin her birinin 5 insan caption'ından biri sorgu. Doğru cevap: kaynak görsel (tek hedef). Tek hedefli sette Recall@5, "ilk 5'te bulma oranı" demektir.
3. **Dev seti (500 sorgu):** Ağırlıklı RRF denemesinde ağırlık seçimi için, test setindeki görsellerin DIŞINDAN seçildi (seed=7).

Tüm sorgularda k=5; bu yüzden MRR de MRR@5'tir (ilk doğru cevap 5. sıradan aşağıdaysa 0).

### Sonuçlar

| Yaklaşım | P@5 (kategori) | Recall@5 (caption) | MRR@5 (caption) |
| :--- | :--- | :--- | :--- |
| CLIP | 0.8727 ± 0.0276 | 0.6550 ± 0.0337 | 0.5226 ± 0.0318 |
| BM25 | 0.8519 ± 0.0290 | 0.2100 ± 0.0289 | 0.1127 ± 0.0190 |
| Hibrit (RRF) | 0.9039 ± 0.0205 | 0.5750 ± 0.0350 | 0.3798 ± 0.0289 |

(± standart hata.) Karşılaştırma için, ilk (BLIP tabanlı) setteki BM25 MRR'ı 0.8783'tü; BLIP'ten bağımsız sorgularda 0.1127'ye düştü. Yukarıdaki "BM25 yapay şekilde yüksek" analizi bu sayıyla doğrulandı.

### İstatistiksel karşılaştırma (eşlemeli bootstrap)

10.000 tekrar, seed=42, sorgular yerine koyarak yeniden çekildi, %95 güven aralığı.

| Metrik | Karşılaştırma | Ort. fark | %95 aralık | Sonuç |
| :--- | :--- | :--- | :--- | :--- |
| P@5 (kategori) | Hibrit − CLIP | +0.0312 | [−0.0052, +0.0675] | Ayırt edilemiyor |
| P@5 (kategori) | Hibrit − BM25 | +0.0519 | [+0.0078, +0.0961] | Sınırda* |
| Recall@5 (caption) | Hibrit − CLIP | −0.0800 | [−0.1350, −0.0300] | Hibrit daha kötü |
| Recall@5 (caption) | Hibrit − BM25 | +0.3650 | [+0.2900, +0.4400] | Hibrit daha iyi |
| MRR@5 (caption) | Hibrit − CLIP | −0.1428 | [−0.1907, −0.0945] | Hibrit daha kötü |
| MRR@5 (caption) | Hibrit − BM25 | +0.2671 | [+0.2160, +0.3195] | Hibrit daha iyi |

\* Alt sınır 0'a çok yakın. Altı karşılaştırma yapıldığı için yaklaşık bir çoklu-karşılaştırma düzeltmesiyle aralık 0'ı içerir; bu sonuç "kesin" olarak raporlanmaz (düzeltme yaklaşıktır, tam Bonferroni değildir).

### Ağırlıklı RRF denemesi

BM25'e düşük ağırlık verilirse hibrit CLIP'e yetişir mi? Tasarım sonuçlar görülmeden sabitlendi: ağırlık sadece dev setinde seçildi, test setlerinde bir kez ölçüldü. CLIP ağırlığı 1.0'da sabit, BM25 ağırlığı {0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0}; RRF k=60 ve aday havuzu (20) sabit.

| BM25 ağırlığı | Dev Recall@5 | Dev MRR@5 |
| :--- | :--- | :--- |
| 0.0 | 0.6600 | 0.4950 |
| 0.1 | 0.6500 | 0.4595 |
| 0.2 | 0.6220 | 0.4184 |
| 0.3 | 0.6020 | 0.4002 |
| 0.5 | 0.6020 | 0.3959 |
| 0.75 | 0.6000 | 0.3900 |
| 1.0 | 0.5560 | 0.3679 |

Eğri neredeyse tek yönlü düşüyor; seçilen ağırlık 0.0 (saf CLIP). Komşu ağırlıklar arasındaki tek tek farklar standart hata içinde, güvenilir olan eğrinin genel yönü. Test sonuçları önceki değerlerle birebir tutarlı (seçilen ağırlık CLIP ile aynı olduğu için "seçilen − eşit" karşılaştırması önceki bootstrap'in işaret çevrilmiş aynısıdır, yeni kanıt sayılmaz; bağımsız doğrulama dev setidir).

### Tamamlayıcılık analizi

Soru: BM25, CLIP'in kaçırdığını hiç yakalıyor mu? (İnsan caption sorguları, tek hedef.)

| Ölçüm | Dev (500) | Test (200) |
| :--- | :--- | :--- |
| CLIP ilk 5'te buldu | %66.0 | %65.5 |
| BM25 ilk 5'te buldu | %21.0 | %21.0 |
| Sadece CLIP buldu (ilk 5) | 233 | 99 |
| Sadece BM25 buldu (ilk 5) | 8 | 10 |
| BM25 ilk 20'de buldu, CLIP ilk 20'de bulamadı | 12 (%2.4) | 9 (%4.5) |
| Hibrit ilk 5'te buldu | %55.6 | %57.5 |

Hibrit, "sadece CLIP buldu" sorgulardan dev'de 69/233, test'te 23/99 tanesini kaybetti; "sadece BM25 buldu" sorgulardan dev'de 5/8, test'te 4/10 tanesini kurtardı.

### Sonuç

- Cümle tarzı insan sorgularında, BLIP caption'ları üzerinde kurulan BM25 ile yapılan eşit ağırlıklı hibrit, CLIP'ten **daha kötü** (Recall ve MRR farkları güven aralıklarıyla destekleniyor) ve düşük ağırlıkla kurtarılamadı.
- Kısa kategori sorgularında hibrit-CLIP farkı **ayırt edilemiyor**; hibritin üstünlüğü iddia edilemez.
- Hibrit her durumda BM25'ten iyi; BM25 tek başına insan sorgularında zayıf.
- BM25, CLIP'in ilk 20'de bulamadığı hedefleri nadiren yakalıyor; yani bu sorgu türünde yeni bilgi eklemiyor.
- İlk analizde yazılan beklenti ("kısa, eksik kelimeli sorgularda CLIP ve hibrit öne çıkar") **yalnızca yarısıyla doğru çıktı**: ikisi de BM25'i geçiyor, ama hibrit CLIP'i geçemiyor.

### Sınırlar (açıkça belirtilmeli)

- İnsan caption setinde tek doğru cevap var; aynı sahneyi gösteren başka bir görsel "yanlış" sayılır, bu mutlak skorları aşağı çeker (yöntemlerin göreli kıyasını etkilemez).
- Kategori setinde doğru cevaplar COCO anotasyonlarından geliyor; kategori anotasyonu eksik (örneğin küçük/arka plan nesne) görseller "yanlış" sayılır, Precision'ı aşağı çeker.
- Ağırlık yalnızca insan-caption sorgularında seçildi; kategori için ayrı bir dev seti yok. Yalnızca BM25 ağırlığı arandı.
- BM25'in zayıf olmasının NEDENİ (BLIP caption'larının kısa ve jenerik olması) bir hipotezdir, **ölçülmedi**.
- Altı istatistiksel karşılaştırma yapıldı; sınıra yakın sonuçlar düzeltme sonrası anlamsızlaşabilir.
- Üretim kodu (`hibrit_ara`) değiştirilmedi. Karar: hibrit mimari korunuyor, bulgu bir ablation sonucu olarak belgeleniyor; olası iyileştirme yönü BM25 metin kaynağının (örneğin daha zengin caption'lar) geliştirilmesi. COCO etiketlerini BM25 metnine eklemek kategori test setiyle sızıntı yaratacağı için tercih edilmez.

## Not: Değerlendirme Kapsamı

Bu rapordaki değerlendirmeler SADECE yerel katman (CLIP + BM25 + RRF) üzerinde yapılmıştır. Faz 3.5 (harici Unsplash arama) ve Faz 3.75 (AI görsel üretim) katmanları bu değerlendirmelerin kapsamı dışındadır - onlar "yerelde yoksa ne olur" sorusuna ayrı bir cevaptır, ana değerlendirme metodolojisini değiştirmez (bkz. `guncelleme_kaydi.pdf`, Bölüm 3).