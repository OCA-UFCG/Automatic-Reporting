import math

# As views escrevem strings-sentinela em vez de NULL quando não têm o dado.
# Filtrar num consumidor só não basta: a capa omitia o card enquanto a prosa
# imprimia "o município tem Não há dados unidades de conservação".
_SENTINELAS_SEM_DADO = frozenset(
    {
        "não há dados",
        "nao ha dados",
        "sem dados",
        "sem informação",
        "sem informacao",
        "não informado",
        "nao informado",
        "n/d",
        "nd",
        "-",
        "--",
    }
)


def valor_sem_sentinela(valor: object) -> object:
    """Converte as strings-sentinela da view em None; devolve o resto intacto."""
    if not isinstance(valor, str):
        return valor
    # Igualdade, não substring: "Não há dados suficientes" é conteúdo.
    if valor.strip().rstrip(".").casefold() in _SENTINELAS_SEM_DADO:
        return None
    return valor


def limpar_sentinelas(linha: dict) -> dict:
    """Aplica `valor_sem_sentinela` a todas as colunas de uma linha da view."""
    return {coluna: valor_sem_sentinela(valor) for coluna, valor in linha.items()}


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
