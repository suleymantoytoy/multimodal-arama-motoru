import torch
import open_clip
from tqdm import tqdm
import numpy as np
from PIL import Image

# ============================================================
# ADIM 1: Hangi donanimda calisacagimizi belirliyoruz.
# Eger bilgisayarinda/Colab'da bir GPU (cuda) varsa onu kullan,
# yoksa normal islemciyi (cpu) kullan. GPU cok daha hizli calisir.
# ============================================================
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Kullanilan cihaz: {device}")

# ============================================================
# ADIM 2: CLIP modelini yukluyoruz.
# "ViT-B-32" -> modelin mimarisi (Vision Transformer, Base boyut, 32 patch)
# "laion2b_s34b_b79k" -> bu mimarinin hangi veriyle onceden egitildigi
# (LAION adli 2 milyar goeselli bir veri setiyle egitilmis, hazir agirliklar)
#
# create_model_and_transforms() bize UC sey veriyor:
#   model      -> asil sinir agi (embedding uretecek olan)
#   _          -> egitim icin kullanilan bir transform (biz kullanmiyoruz, o yuzden _ dedik)
#   preprocess -> gorselleri modele vermeden once nasil hazirlayacagimizi soyleyen fonksiyon
#                 (boyutlandirma, kirpma, normalizasyon gibi islemleri otomatik yapar)
# ============================================================
model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="laion2b_s34b_b79k"
)

# tokenizer: bir metni (orn. "kirmizi araba") modelin anlayacagi sayisal
# forma (token'lara) ceviren arac. Goersel icin preprocess neyse, metin icin tokenizer o.
tokenizer = open_clip.get_tokenizer("ViT-B-32")

# Modeli sectigimiz cihaza (GPU/CPU) tasiyoruz.
model = model.to(device)

# model.eval(): modeli "degerlendirme moduna" aliyoruz.
# Bu, modelin egitim sirasinda kullandigi bazi rastgelelik iceren
# islemleri (dropout gibi) kapatir - biz egitmiyoruz, sadece kullaniyoruz.
model.eval()


def encode_image(image_path):
    """
    Bir gorsel dosyasinin yolunu (path) alir, CLIP'in urettigi
    512 boyutlu sayisal vektorunu (embedding) dondurur.
    """
    # Gorseli ac, RGB formatina cevir (bazi gorseller siyah-beyaz/farkli
    # formatta olabilir, CLIP hep RGB (3 renk kanali) bekler).
    image = Image.open(image_path).convert("RGB")

    # preprocess: gorseli modelin bekledigi boyuta/formata getirir.
    # unsqueeze(0): modele "tek bir gorsel gonderiyorum" demek icin
    # basina bir "batch boyutu" ekler (model normalde birden fazla
    # gorseli aynı anda islemek uzere tasarlanmis, biz tek gorsel
    # gonderdigimiz icin bu boyutu elle ekliyoruz).
    image_input = preprocess(image).unsqueeze(0).to(device)

    # torch.no_grad(): "gradyan hesaplama" (egitim icin gerekli olan
    # matematiksel takip) yapma diyoruz. Sadece tahmin/donusum
    # yaptigimiz icin bu, islemi hem hizlandirir hem bellek tasarrufu saglar.
    with torch.no_grad():
        vektor = model.encode_image(image_input)

        # L2 Normalizasyon: vektorun "uzunlugunu" 1'e esitliyoruz.
        # Bunu yapmazsak, iki vektor arasindaki benzerligi (cosine similarity)
        # dogru olcemeyiz - normalize edilmemis vektorlerde "buyukluk"
        # benzerlik hesabini bozar. Bu adim CLIP ile calisirken KRITIK.
        vektor = vektor / vektor.norm(dim=-1, keepdim=True)

    # GPU'daysa CPU'ya geri al, PyTorch tensorunu normal bir
    # numpy array'e cevir (diger kutuphanelerle -orn. FAISS- uyumlu olsun diye).
    # [0] ile "batch" boyutunu (basta elle ekledigimiz) kaldiriyoruz.
    return vektor.cpu().numpy()[0]


def encode_text(text):
    """
    Bir metin (orn. "kirmizi bir araba") alir, CLIP'in urettigi
    512 boyutlu sayisal vektorunu (embedding) dondurur.
    Yukaridaki encode_image ile MANTIK OLARAK AYNI islemi yapar,
    tek fark gorsel yerine metin isliyor olmasi.
    """
    # tokenizer bir liste bekler (birden fazla metni aynı anda
    # isleyebilmek icin), o yuzden text'i [text] seklinde listeye sariyoruz.
    text_input = tokenizer([text]).to(device)

    with torch.no_grad():
        vektor = model.encode_text(text_input)
        vektor = vektor / vektor.norm(dim=-1, keepdim=True)  # ayni normalize islemi

    return vektor.cpu().numpy()[0]

def encode_images_batch(image_paths, batch_size=32):
    """
    Birden fazla gorseli TEK TEK degil, gruplar (batch) halinde isler.

    Neden batch onemli? encode_image() fonksiyonu her cagrildiginda
    modelin "unsqueeze(0)" ile tek gorsellik sahte bir grup olusturdugunu
    hatirla - yani model aslinda hep gruplar halinde calismak icin
    tasarlanmis, biz onu 1'lik gruplarla kullaniyorduk. Bu, ozellikle
    GPU'da (ve biraz da CPU'da) verimsizdir - cunku donanim, ayni anda
    birden fazla gorseli islerken cok daha verimli calisir (paralel
    hesaplama). 32 gorseli TEK TEK islemek yerine, 32'sini AYNI ANDA
    modele vermek, toplam sureyi ciddi sekilde kisaltabilir - ozellikle
    buyuk veri setlerinde (bizim 5.000 gorselimizde bile fark yaratir).

    Parametreler:
        image_paths: islenecek TUM gorsellerin dosya yollarinin listesi
        batch_size: her seferde kac gorselin AYNI ANDA islenecegi
                    (32, yaygin ve dengeli bir tercih - cok buyuk
                    olursa bellek (RAM) yetersiz kalabilir, cok kucuk
                    olursa batch'in hiz avantaji azalir)

    Donus degeri:
        (N, 512) boyutunda bir numpy array - N = basarili islenen
        gorsel sayisi, her satir bir gorselin 512 boyutlu vektoru.
        Ayrica hangi dosyalarin basariyla islendigini de donuyoruz
        (bazi gorseller bozuk olabilir, onlari atlayabiliriz).
    """
    tum_vektorler = []
    basarili_yollar = []

    # range(0, len(image_paths), batch_size): 0'dan basla, listenin
    # sonuna kadar git, ama HER SEFERINDE batch_size kadar atla.
    # Ornek: 100 gorsel, batch_size=32 ise -> 0, 32, 64, 96 seklinde
    # 4 durak olusur (son grup sadece 4 gorsel icerir, o normal).
    for baslangic_index in tqdm(range(0, len(image_paths), batch_size)):
        # Su anki grubun (batch'in) icerdigi dosya yollarini aliyoruz.
        # Python'un "slice" (dilim) ozelligini kullaniyoruz:
        # liste[baslangic:bitis] o aralikdaki elemanlari verir.
        grup_yollari = image_paths[baslangic_index : baslangic_index + batch_size]

        # Bu gruptaki HER gorseli ac, on-isle (preprocess), ama henuz
        # modele VERME - once hepsini bir listede topluyoruz.
        grup_tensorleri = []
        gecerli_yollar_bu_grupta = []

        for yol in grup_yollari:
            try:
                gorsel = Image.open(yol).convert("RGB")
                # preprocess(gorsel) tek bir gorseli islenmis hale getirir,
                # ama unsqueeze(0) YAPMIYORUZ burada - cunku birazdan
                # hepsini tek seferde "yigin" (stack) halinde birlestirecegiz.
                islenmis = preprocess(gorsel)
                grup_tensorleri.append(islenmis)
                gecerli_yollar_bu_grupta.append(yol)
            except Exception as hata:
                print(f"HATA ({yol}): {hata}")

        if not grup_tensorleri:
            # Eger bu grupta islenebilen HICBIR gorsel yoksa
            # (hepsi bozuksa), bir sonraki gruba gec.
            continue

        # torch.stack(): tek tek islenmis gorselleri (her biri (3, 224, 224)
        # gibi bir boyutta) TEK BIR buyuk tensore birlestirir. Sonuc:
        # (batch_size, 3, 224, 224) boyutunda - yani "32 tane gorsel,
        # her biri 3 renk kanali, 224x224 piksel" seklinde tek bir paket.
        toplu_tensor = torch.stack(grup_tensorleri).to(device)

        with torch.no_grad():
            # ISTE FARK BURADA: model.encode_image() BIR KERE cagriliyor
            # ama icinde 32 gorsel birden var - model bunlari kendi
            # icinde PARALEL olarak isliyor, 32 ayri cagri yapmiyoruz.
            vektorler = model.encode_image(toplu_tensor)
            # Normalize etme islemi yine ayni - her satiri (her gorselin
            # vektorunu) kendi icinde 1 uzunluguna getiriyoruz.
            vektorler = vektorler / vektorler.norm(dim=-1, keepdim=True)

        # GPU'daysa CPU'ya al, numpy'a cevir, listemize ekle.
        tum_vektorler.append(vektorler.cpu().numpy())
        basarili_yollar.extend(gecerli_yollar_bu_grupta)

    # tum_vektorler su an kucuk parcalar halinde bir liste
    # (her biri (batch_size, 512) boyutunda). np.vstack() bunlari
    # dikey olarak (satir satir) tek bir buyuk array'de birlestirir.
    embedding_matrisi = np.vstack(tum_vektorler)

    return embedding_matrisi, basarili_yollar


# ============================================================
# Bu blok, dosya DOGRUDAN calistirildiginda (python clip_encoder.py)
# devreye girer. Baska bir dosyadan bu fonksiyonlari import edersen
# (orn. "from embeddings.clip_encoder import encode_image") bu blok
# CALISMAZ - sadece test/deneme amacli buraya koyduk.
# ============================================================
if __name__ == "__main__":
    import os

    klasor = "data/raw_images"
    # Klasordeki tum .jpg uzantili dosyalarin isimlerini bir listeye topluyoruz.
    dosyalar = [f for f in os.listdir(klasor) if f.endswith(".jpg")]

    if not dosyalar:
        print("data/raw_images klasorunde hic .jpg dosyasi bulamadim!")
    else:
        # Listedeki ilk dosyayi test icin seciyoruz.
        ornek_gorsel = os.path.join(klasor, dosyalar[0])
        print(f"Test gorseli: {ornek_gorsel}")

        # Fonksiyonlarimizi gercekten calistirip sonuclarina bakiyoruz.
        gorsel_vektor = encode_image(ornek_gorsel)
        metin_vektor = encode_text("a photo")

        # .shape -> vektorun boyutunu gosterir, (512,) beklenen sonuc.
        print(f"Gorsel vektor boyutu: {gorsel_vektor.shape}")
        print(f"Metin vektor boyutu: {metin_vektor.shape}")
        print("Calisti!")