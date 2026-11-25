import os

with open("sadece_kodlar.txt", "w", encoding="utf-8") as cikti_dosyasi:
    for kok_dizin, klasorler, dosyalar in os.walk("."):
        # Veri, ortam ve eval klasörlerini atla (sadece ana mimari kodları gelsin)
        if any(haric in kok_dizin for haric in [".git", "venv", "env", "__pycache__", "data", "val2017", "eval", ".pytest_cache"]):
            continue
            
        for dosya in dosyalar:
            # Sadece Python, Markdown ve Docker dosyalarını al (.json hariç)
            if dosya.endswith((".py", ".md", "Dockerfile.api", "Dockerfile.ui", ".yml")): 
                dosya_yolu = os.path.join(kok_dizin, dosya)
                cikti_dosyasi.write(f"\n\n{'='*40}\n--- DOSYA: {dosya_yolu} ---\n{'='*40}\n\n")
                try:
                    with open(dosya_yolu, "r", encoding="utf-8") as f:
                        cikti_dosyasi.write(f.read())
                except Exception:
                    cikti_dosyasi.write("Dosya okunamadi.\n")