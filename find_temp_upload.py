import os
import tempfile
import glob
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

temp_dir = tempfile.gettempdir()
print(f"Buscando arquivos temporários recentes em: {temp_dir}")

# Busca arquivos criados nos últimos 10 minutos
import time
now = time.time()

# Encontra arquivos recentes no diretório temporário
recent_files = []
for f in glob.glob(os.path.join(temp_dir, "*")):
    try:
        mtime = os.path.getmtime(f)
        if now - mtime < 600: # 10 minutos
            recent_files.append((f, mtime))
    except:
        pass

recent_files.sort(key=lambda x: x[1], reverse=True)

print(f"Encontrados {len(recent_files)} arquivos recentes.")
for f, mtime in recent_files[:10]:
    size = os.path.getsize(f)
    print(f" - {os.path.basename(f)} | {size} bytes | Modificado há {int(now - mtime)}s")
    
    # Se for um arquivo de tamanho razoável e puder ser uma imagem, tenta abrir
    if size > 100000: # > 100KB
        try:
            img = Image.open(f)
            print(f"   [!] IMAGEM ENCONTRADA: {os.path.basename(f)} ({img.size})")
            
            # Executa o pré-processamento e OCR
            gray = img.convert('L')
            width, height = gray.size
            resized = gray.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(resized)
            enhanced = enhancer.enhance(2.0)
            
            texto = pytesseract.image_to_string(enhanced, lang='por+eng')
            print("\n=== TEXTO EXTRAÍDO ===")
            print(texto)
            print("======================\n")
            break
        except Exception as e:
            # Não é uma imagem válida, tudo bem
            pass
