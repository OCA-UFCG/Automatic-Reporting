"""JSON com tags para os tipos que o contexto do relatório carrega.

`Decimal`, `date` e `tuple` passam por ramos diferentes da formatação (coerce_para_float
e afins): um `json.dumps` simples os devolveria como float/str/list, e o texto renderizado
mudaria. Usado pelo snapshot do laboratório e pelo harness do relatório congelado.
"""

from datetime import date, datetime
from decimal import Decimal


def codificar(valor):
    """Valor Python -> JSON com tags, para os tipos voltarem iguais no replay (Decimal,
    date e tuple seguem ramos diferentes de coerce_para_float e afins)."""
    if isinstance(valor, Decimal):
        return {"__decimal__": str(valor)}
    if isinstance(valor, datetime):  # antes de date: datetime é subclasse de date
        return {"__datetime__": valor.isoformat()}
    if isinstance(valor, date):
        return {"__date__": valor.isoformat()}
    if isinstance(valor, tuple):
        return {"__tuple__": [codificar(v) for v in valor]}
    if isinstance(valor, list):
        return [codificar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: codificar(v) for k, v in valor.items()}
    return valor


def decodificar(valor):
    if isinstance(valor, list):
        return [decodificar(v) for v in valor]
    if isinstance(valor, dict):
        if len(valor) == 1:
            (tag, conteudo), = valor.items()
            if tag == "__decimal__":
                return Decimal(conteudo)
            if tag == "__datetime__":
                return datetime.fromisoformat(conteudo)
            if tag == "__date__":
                return date.fromisoformat(conteudo)
            if tag == "__tuple__":
                return tuple(decodificar(v) for v in conteudo)
        return {k: decodificar(v) for k, v in valor.items()}
    return valor
