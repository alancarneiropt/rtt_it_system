import os
import sys

# Garante que tesseract_cmd está configurado
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image

def get_latest_image(folder):
    if not os.path.exists(folder):
        print(f"Pasta {folder} não encontrada.")
        return None
    
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        print("Nenhuma imagem encontrada na pasta.")
        return None
        
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

media_folder = os.path.join(r'c:\Users\Ielber.Silva\Desktop\rtt_it_system', 'media', 'comprovativos_abastecimento')
latest_image = get_latest_image(media_folder)

if latest_image:
    print(f"--- LENDO IMAGEM: {os.path.basename(latest_image)} ---")
    try:
        img = Image.open(latest_image)
        # 1. Teste básico
        texto_ocr = pytesseract.image_to_string(img, lang='por+eng')
        print("\n=== TEXTO EXTRAÍDO PELO TESSERACT ===")
        print(texto_ocr)
        print("=====================================\n")
        
        # 2. Testar as nossas regexes no texto extraído
        import re
        texto_clean = texto_ocr.upper()
        
        print("--- A TESTAR REGEX DE VALOR ---")
        padroes_valor = [
            r'TOTAL\s*EUR\s*([0-9]+\s*[.,]\s*[0-9]{2})',
            r'(?:TOTAL|VALOR|PAGAR|EUR|€)\s*(?:DO)?\s*(?:DOCUMENTO)?\s*[:\-=]?\s*([0-9]+\s*[.,]\s*[0-9]{2})',
            r'([0-9]+\s*[.,]\s*[0-9]{2})\s*(?:EUR|€|EUROS)',
        ]
        valor = None
        for i, p in enumerate(padroes_valor):
            matches = re.findall(p, texto_clean)
            if matches:
                print(f"Regra {i+1} casou! -> {matches[0]}")
                valor = float(matches[0].replace(' ', '').replace(',', '.'))
                print(f"Valor convertido: {valor}")
                break
        if not valor:
            print("NENHUMA REGRA DE VALOR CASOU!")
            
        print("\n--- A TESTAR REGEX DE LITROS ---")
        padroes_litros = [
            r'([0-9]+\s*[.,]\s*[0-9]{2,3})\s*L\b',
            r'(?:LITROS|LITROS:|LTS|QTD|QUANT|VOL)\s*[:\-=]?\s*([0-9]+\s*[.,]\s*[0-9]{2,3})',
            r'([0-9]+\s*[.,]\s*[0-9]{2,3})\s*(?:LITROS|LTS|L\b)',
        ]
        litros = None
        for i, p in enumerate(padroes_litros):
            matches = re.findall(p, texto_clean)
            if matches:
                print(f"Regra {i+1} casou! -> {matches[0]}")
                litros = float(matches[0].replace(' ', '').replace(',', '.'))
                print(f"Litros convertidos: {litros}")
                break
        if not litros:
            print("NENHUMA REGRA DE LITROS CASOU!")

    except Exception as e:
        print(f"ERRO DE OCR: {e}")
        import traceback
        traceback.print_exc()
