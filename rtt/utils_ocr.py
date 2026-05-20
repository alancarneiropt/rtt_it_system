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
        # 3. Aumentar o contraste (1.7 é o ponto ideal para evitar fusão de dígitos como 5 -> 9)
        enhancer = ImageEnhance.Contrast(resized)
        enhanced = enhancer.enhance(1.7)
        
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

        # Extração preventiva do Preço Unitário para validação matemática
        # Faixa de 0.000 a 3.999 perfeitamente específica para preços de combustível
        preco_unitario = None
        preco_match = re.search(r'(?<![0-9.])([0-3][.,][0-9]{3})(?![0-9])', texto_clean)
        if preco_match:
            try:
                preco_unitario = float(preco_match.group(1).replace(',', '.'))
            except ValueError:
                pass

        def extrair_numero_flexivel(texto, padroes):
            for p in padroes:
                matches = re.findall(p, texto)
                if matches:
                    val_match = matches[0]
                    if isinstance(val_match, tuple):
                        val_match = val_match[0]
                    num_str = val_match.replace(' ', '')
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
        # Suporta delimitadores opcionais (dois-pontos, hífens) e variações comuns de moedas
        padroes_valor = [
            r'TOTAL\s*[:\-=]*\s*(?:EUR|€|FUR|FUA|EUB|EUP|PTE|ESC|USD|GBP)?\s*[:\-=]*\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
            r'(?:TOTAL|VALOR|PAGAR)\s*[:\-=]*\s*(?:EUR|€|FUR|FUA|EUB|EUP|PTE|ESC)?\s*[:\-=]*\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
            r'(?:EUR|€|FUR|FUA|EUB|EUP)\s*[:\-=]*\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2})(?![0-9])',
        ]
        valor = extrair_numero_flexivel(texto_clean, padroes_valor)

        # 1. Regra de Ouro da BOMBA para Litros:
        # A linha que indica os litros quase sempre contém a palavra BOMBA (ou misreads como BORBA, FONT, BONB, BOB, etc.).
        for linha in texto_clean.split('\n'):
            if any(k in linha for k in ['BOMB', 'BORB', 'PUMP', 'BOM', 'BONB', 'BOB', 'FONT', 'B0M']):
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
                r'(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})\s*(?:L|1|I|l|\|)\b',
                r'(?:LITROS|LTS|QTD|VOL)\s*[:\-=]?\s*(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})(?![0-9])',
                r'(?<![0-9.])([0-9]+\s*[.,]?\s*[0-9]{2,3})(?![0-9])\s*(?:LITROS|LTS|L\b)',
            ]
            litros_regex = extrair_numero_flexivel(texto_clean, padroes_litros)
            if litros_regex and 1.0 <= litros_regex <= 150.0:
                litros = litros_regex
            else:
                litros = None

        # 3. Regra Matemática de Validação e Correção Inteligente (Autocorretor)
        # Se temos o preço unitário e o valor total, calculamos o volume matematicamente.
        # Se os litros lidos falharam ou são incoerentes, substituímos pelo valor calculado.
        if preco_unitario and valor:
            try:
                litros_calculados = round(valor / preco_unitario, 2)
                if 1.0 <= litros_calculados <= 150.0:
                    if not litros or abs(litros - litros_calculados) > 0.5:
                        print(f"Litros corrigidos matematicamente: {litros} -> {litros_calculados} ({valor} / {preco_unitario})")
                        litros = litros_calculados
            except Exception as e:
                print(f"Erro na validacao matematica: {e}")

    # 2. Se falhar completamente, não geramos valores falsos.
    # Simplesmente retornamos o que conseguimos (que pode ser None/vazio)
    
    return {
        'valor': valor,
        'litros': litros,
        'texto_ocr': texto_ocr
    }

