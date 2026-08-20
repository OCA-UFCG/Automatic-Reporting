def formatar_numero_ptbr(valor: object, decimais: int = 0) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        texto_valor = str(valor).strip()
        try:
            numero = float(texto_valor.replace(".", "").replace(",", "."))
        except ValueError:
            return texto_valor
    texto = f"{numero:,.{decimais}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")
