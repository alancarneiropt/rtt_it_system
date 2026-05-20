import re
import random

def processar_recibo_ocr(file_obj):
    """
    Processa uma imagem de recibo/fatura de combustível e extrai:
    - valor (Decimal ou float)
    - litros (Decimal ou float)
    - texto_ocr (texto completo extraído)
    """
    valor = None
    litros = None
    texto_ocr = ""

    # 1. Tentativa de OCR real usando PyTesseract se disponível
    try:
        from PIL import Image, ImageOps, ImageEnhance
        import pytesseract
        import sys
        
        # No Windows, é preciso indicar onde o Tesseract está instalado
        if sys.platform == 'win32':
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
        # Abre a imagem
        img = Image.open(file_obj)
        
        # --- PRÉ-PROCESSAMENTO PARA TELEMÓVEIS (MELHORA A CAPTURA DE PONTOS/VÍRGULAS) ---
        # 1. Converter para escala de cinza
        gray = img.convert('L')
        # 2. Redimensionar para o dobro do tamanho (pontos pequenos ficam legíveis)
        width, height = gray.size
        resized = gray.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        # 3. Aumentar o contraste
        enhancer = ImageEnhance.Contrast(resized)
        enhanced = enhancer.enhance(2.0)
        
        # Converte para string usando modo 4 (Assume a single column of text of variable sizes) - ideal para recibos
        texto_ocr = pytesseract.image_to_string(enhanced, lang='por+eng', config='--psm 4')
        print(f"--- OCR TEXT EXTRACTION (PRE-PROCESSED) ---")
        print(texto_ocr)
        print("---------------------------")
            
    except Exception as e:
        print(f"--- OCR ERROR: {e} ---")
        texto_ocr = ""

    # Se obtivemos texto real, tentamos extrair com as novas regexes resilientes
    if texto_ocr.strip():
        texto_clean = texto_ocr.upper()

        def extrair_numero_flexivel(texto, padroes):
            for p in padroes:
                matches = re.findall(p, texto)
                if matches:
                    num_str = matches[0].replace(' ', '')
                    # Se o OCR comeu o ponto decimal (ex: 10250) mas sabemos que tem cêntimos
                    if '.' not in num_str and ',' not in num_str and len(num_str) > 2:
                        num_str = num_str[:-2] + '.' + num_str[-2:]
                    else:
                        num_str = num_str.replace(',', '.')
                    try:
                        return float(num_str)
                    except ValueError:
                        pass
            return None

        # Regex inteligente para Valor (Total)
        # O Total de combustível vem SEMPRE após EUR, € ou a palavra TOTAL/VALOR.
        # Isto evita 100% de falsos positivos com preços unitários (ex: 1.639 EUR/L)
        padroes_valor = [
            r'TOTAL\s*(?:EUR|€)?\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
            r'(?:TOTAL|VALOR|PAGAR)\s*(?:EUR|€)?\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
            r'(?:EUR|€)\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
        ]
        valor = extrair_numero_flexivel(texto_clean, padroes_valor)

        # 1. Regra de Ouro da BOMBA para Litros:
        # A linha que indica os litros quase sempre contém a palavra BOMBA (ou misreads como BORBA, BOMB, BOM).
        # Extraímos o primeiro número decimal dessa linha, ignorando erros no 'L' (ex: '37.21.14' vira 37.21).
        for linha in texto_clean.split('\n'):
            if any(k in linha for k in ['BOMB', 'BORB', 'PUMP', 'BOM']):
                match = re.search(r'(?<![0-9.])([0-9]+[.,][0-9]{2,3})', linha)
                if match:
                    try:
                        num_str = match.group(1).replace(',', '.')
                        val_litros = float(num_str)
                        if 1.0 <= val_litros <= 150.0:
                            litros = val_litros
                            break
                    except ValueError:
                        pass

        # 2. Fallback de Regex inteligente para Litros se a regra da Bomba falhar ou for absurda
        if not litros or litros < 1.0 or litros > 150.0:
            padroes_litros = [
                r'(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})\s*(?:L|1|I|l)\b',
                r'(?:LITROS|LTS|QTD|VOL)\s*[:\-=]?\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})(?![0-9])',
                r'(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})(?![0-9])\s*(?:LITROS|LTS|L\b)',
            ]
            litros_regex = extrair_numero_flexivel(texto_clean, padroes_litros)
            if litros_regex and 1.0 <= litros_regex <= 150.0:
                litros = litros_regex
            else:
                litros = None

        # 3. Regra Matemática de Fallback Extremo (Total / Preço Unitário)
        # Se falhou a leitura dos litros (como no caso de linhas ignoradas pelo OCR), tentamos
        # ler o Preço Unitário (3 casas decimais, ex: 1.959 ou 1.344) e calcular os litros dividindo o total pelo preço.
        if not litros and valor:
            preco_match = re.search(r'(?<![0-9.])([1-2][.,][0-9]{3})(?![0-9])', texto_clean)
            if preco_match:
                try:
                    preco_unitario = float(preco_match.group(1).replace(',', '.'))
                    if preco_unitario > 0:
                        litros = round(valor / preco_unitario, 2)
                        print(f"Litros calculados matematicamente: {litros} ({valor} / {preco_unitario})")
                except ValueError:
                    pass

    # 2. Se falhar completamente, não geramos valores falsos.
    # Simplesmente retornamos o que conseguimos (que pode ser None/vazio)
    
    return {
        'valor': valor,
        'litros': litros,
        'texto_ocr': texto_ocr
    }

