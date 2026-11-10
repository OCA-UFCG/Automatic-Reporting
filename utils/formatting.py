import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


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


def arredondar_meio_para_cima(numero: Decimal | float, decimais: int) -> Decimal:
    """O arredondamento que `formatar_numero_ptbr` imprime: 999.995 com 2 casas -> Decimal("1000.00").

    Exposto para quem precisa decidir algo pelo número já arredondado (o sufixo
    k/M/B dos rótulos do FNE) sem divergir do texto que sai formatado.
    """
    # Pelo repr, não pelo float: 1141.165 é 1141.16499… em binário.
    exato = numero if isinstance(numero, Decimal) else Decimal(repr(numero))

    return exato.quantize(Decimal(1).scaleb(-decimais), rounding=ROUND_HALF_UP)


def formatar_numero_ptbr(valor: object, decimais: int = 0) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        texto_valor = str(valor).strip()
        try:
            numero = float(texto_valor.replace(".", "").replace(",", "."))
        except ValueError:
            return texto_valor
    if math.isfinite(numero):
        try:
            numero = arredondar_meio_para_cima(valor if isinstance(valor, Decimal) else numero, decimais)
        except InvalidOperation:
            pass
    texto = f"{numero:,.{decimais}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")
