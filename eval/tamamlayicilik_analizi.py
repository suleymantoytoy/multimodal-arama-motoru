# ============================================================
# Bu script, "BM25, CLIP'in kacirdigini HIC yakaliyor mu?" sorusunu
# OLCER (tamamlayicilik analizi).
#
# Her sorgu icin hedef gorselin CLIP'te ve BM25'te KACINCI SIRADA
# ciktigina bakar ve dort durumu sayar:
#   - ikisi de buldu
#   - SADECE CLIP buldu
#   - SADECE BM25 buldu
#   - ikisi de bulamadi
# Sonra esit agirlikli hibritin bu durumlardan hangilerini
# kurtardigini, hangilerini kaybettigini olcer.
#
# Neden ilk 20? RRF, her yontemin ilk 20'sini birlestiriyor
# (hibrit_ara ile AYNI havuz). Bu yuzden hem ilk 5 hem ilk 20
# icin ayri ayri sayiyoruz.
#
# YORUMLAMA KURALI (sonuclar gorulmeden belirlendi): "sadece
# BM25 buldu" sayisi "sadece CLIP buldu" sayisindan cok daha
# kucukse BM25 neredeyse hicbir sey eklemiyor. Sayilar yakinsa
# sorun BM25 degil, BIRLESTIRME yontemidir.
# ============================================================

# json: test/dev setlerini okumak icin
import json
# tqdm: terminalde ilerleme cubugu gostermek icin
from tqdm import tqdm

# evaluate_v2'den ortak parcalar (bu import arama index'lerini de yukler
# ve search klasorunu Python yoluna ekler)
from evaluate_v2 import K, idlere_cevir, CAPTION_DOSYASI
# Ham arama fonksiyonlari: sadece dosya yollari listesi dondururler
from hybrid_search import _clip_ile_ara, _bm25_ile_ara
# RRF: esit agirlikli (varsayilan) hibriti yeniden olusturmak icin
from rerank import reciprocal_rank_fusion

# Girdi dosyalari
DEV_DOSYASI = "eval/dev_insan_caption.json"
# Her yontemden alinacak aday sayisi (hibrit_ara ile AYNI: 20)
HAVUZ_K = 20


def sira_bul(liste, hedef):
    # Hedef gorsel listede varsa 1'den baslayan sirasini, yoksa None dondurur
    for sira, kimlik in enumerate(liste, start=1):
        if kimlik == hedef:
            return sira
    return None


def bulundu(sira, esik):
    # Sira biliniyorsa VE esigin icindeyse "bulundu" sayilir
    return sira is not None and sira <= esik


def yuzde(sayi, toplam):
    # Sayiyi yuzdeye cevir (okunakli yazdirmak icin)
    return 100.0 * sayi / toplam


def analiz_et(set_adi, dosya_yolu):
    # Test/dev setini oku
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        test_seti = json.load(f)
    n = len(test_seti)
    print(f"\n{'=' * 60}\n{set_adi}: {n} sorgu\n{'=' * 60}")

    # Her sorgu icin hedefin CLIP, BM25 ve hibritteki sirasi
    kayitlar = []
    for kayit in tqdm(test_seti):
        sorgu = kayit["sorgu"]
        # Tek dogru cevap var: ilk (ve tek) eleman
        hedef = idlere_cevir(kayit["dogru_gorseller"])[0]
        # Iki yontemin ilk 20'si (RRF'nin gordugu havuz)
        clip = idlere_cevir(_clip_ile_ara(sorgu, k=HAVUZ_K))
        bm25 = idlere_cevir(_bm25_ile_ara(sorgu, k=HAVUZ_K))
        # Esit agirlikli hibrit siralamasi (yalnizca kimlikler)
        hibrit = [kimlik for kimlik, skor in reciprocal_rank_fusion([clip, bm25])]
        kayitlar.append({
            "clip": sira_bul(clip, hedef),
            "bm25": sira_bul(bm25, hedef),
            "hibrit": sira_bul(hibrit, hedef),
        })

    # Dort durumu iki farkli esik icin say: ilk 5 ve ilk 20
    for esik in [K, HAVUZ_K]:
        ikisi = sadece_clip = sadece_bm25 = hicbiri = 0
        for k_ in kayitlar:
            c = bulundu(k_["clip"], esik)
            b = bulundu(k_["bm25"], esik)
            if c and b:
                ikisi += 1
            elif c:
                sadece_clip += 1
            elif b:
                sadece_bm25 += 1
            else:
                hicbiri += 1

        print(f"\n--- Hedef ILK {esik} ICINDE mi? ---")
        print(f"  Ikisi de buldu    : {ikisi:4d}  (%{yuzde(ikisi, n):5.1f})")
        print(f"  SADECE CLIP buldu : {sadece_clip:4d}  (%{yuzde(sadece_clip, n):5.1f})")
        print(f"  SADECE BM25 buldu : {sadece_bm25:4d}  (%{yuzde(sadece_bm25, n):5.1f})")
        print(f"  Ikisi de bulamadi : {hicbiri:4d}  (%{yuzde(hicbiri, n):5.1f})")
        clip_toplam = ikisi + sadece_clip
        birlesim = ikisi + sadece_clip + sadece_bm25
        print(f"  CLIP tek basina   : %{yuzde(clip_toplam, n):5.1f}")
        # Birlesim: "mukemmel bir birlestirme" ile ulasilabilecek ust sinir
        print(f"  Birlesim (ust sinir, mukemmel birlestirme): %{yuzde(birlesim, n):5.1f}")

        # Hibritin ilk 5'i (nihai sonuc) bu durumlari nasil etkiledi? Sadece
        # ilk 5 icin anlamli, cunku hibrit_ara nihai olarak ilk K'yi donduruyor.
        if esik == K:
            # Sadece CLIP'in buldugu sorgulardan hibritin KAYBETTIKLERI
            kaybedilen = sum(
                1 for k_ in kayitlar
                if bulundu(k_["clip"], K) and not bulundu(k_["bm25"], K)
                and not bulundu(k_["hibrit"], K)
            )
            # Sadece BM25'in buldugu sorgulardan hibritin KURTARDIKLARI
            kurtarilan = sum(
                1 for k_ in kayitlar
                if bulundu(k_["bm25"], K) and not bulundu(k_["clip"], K)
                and bulundu(k_["hibrit"], K)
            )
            # Hibritin toplam isabeti
            hibrit_toplam = sum(1 for k_ in kayitlar if bulundu(k_["hibrit"], K))
            print(f"\n  Hibrit (esit agirlik) ilk 5'te buldu: %{yuzde(hibrit_toplam, n):5.1f}")
            print(f"  'Sadece CLIP buldu' {sadece_clip} sorgudan hibritin KAYBETTIGI: {kaybedilen}")
            print(f"  'Sadece BM25 buldu' {sadece_bm25} sorgudan hibritin KURTARDIGI: {kurtarilan}")

    # Ek bakis: BM25 hedefi buluyorsa (ilk 20), CLIP'te hedef genelde kacinci sirada?
    # Cok geride mi (RRF'nin kurtarmasi zor) yoksa yakin mi?
    clip_siralari = [k_["clip"] for k_ in kayitlar
                     if bulundu(k_["bm25"], HAVUZ_K) and k_["clip"] is not None]
    bm25_yok_clip_var = sum(1 for k_ in kayitlar
                            if bulundu(k_["bm25"], HAVUZ_K) and k_["clip"] is None)
    print(f"\n  BM25'in ilk 20'sinde buldugu {sum(1 for k_ in kayitlar if bulundu(k_['bm25'], HAVUZ_K))} "
          f"sorgudan CLIP'in ilk 20'sinde HIC bulamayanlar: {bm25_yok_clip_var}")


def calistir():
    # Ana analiz: 500'luk dev seti (test setine yeni bir bakis yapmiyoruz)
    analiz_et("DEV (insan caption)", DEV_DOSYASI)
    # Ikinci bakis: 200'luk test seti (kesif amacli, zaten gorulmustu)
    analiz_et("TEST (insan caption)", CAPTION_DOSYASI)


# Dosya dogrudan calistirildiginda asagisi calisir
if __name__ == "__main__":
    calistir()