import math


def coerce_para_float(valor: object, default: float | None = 0.0) -> float | None:
    """Converte um valor (possivelmente string com vírgula decimal, None ou NaN) em float.

    Usado pelos módulos de plotting para normalizar valores vindos de CSV/banco
    antes de gerar gráficos. `default` é o que volta quando `valor` é None,
    não conversível ou não finito (NaN/Inf).
    """
    if valor is None:
        return default

    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return default

    if not math.isfinite(numero):
        return default

    return numero


def categoria_variacao(variacao: object) -> str | None:
    if variacao is None:
        return None
    try:
        valor = float(variacao)
    except (TypeError, ValueError):
        return None
    if valor > 0:
        return "aumento"
    if valor < 0:
        return "redução"
    return "estabilidade"


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
