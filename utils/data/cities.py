import ast
import threading

import pandas as pd

from config import CITIES_FILE
from utils.geografia import separar_cidade_uf

_cidades_cache: list[str] | None = None
_cidades_lock = threading.Lock()


def carregar_cidades() -> list[str]:
    # Cacheado e sob lock: carregar_cidades() roda tanto no request síncrono quanto
    # em threads de fundo (services/background.py). Duas chamadas concorrentes a
    # ast.literal_eval no mesmo processo corrompem o contador de recursão do parser
    # da CPython (SystemError: AST constructor recursion depth mismatch) sob carga —
    # reproduzido com 10 gerações simultâneas. O arquivo é estático, então parsear
    # uma vez e reusar resolve tanto a corrida quanto o custo repetido.
    global _cidades_cache
    if _cidades_cache is not None:
        return _cidades_cache

    with _cidades_lock:
        if _cidades_cache is None:
            _cidades_cache = _ler_cidades_do_arquivo()
        return _cidades_cache


def _ler_cidades_do_arquivo() -> list[str]:
    if not CITIES_FILE.exists():
        return []

    conteudo = CITIES_FILE.read_text(encoding="utf-8").strip()
    if not conteudo:
        return []

    try:
        cidades = ast.literal_eval(conteudo)
        if isinstance(cidades, list):
            return [str(cidade).strip() for cidade in cidades if str(cidade).strip()]
    except (ValueError, SyntaxError):
        pass

    return [linha.strip() for linha in conteudo.splitlines() if linha.strip()]


def filtrar_linhas_por_cidade(df: pd.DataFrame, cidade: str) -> pd.DataFrame:
    cidade_informada = cidade.strip()
    serie_cidades = df["nm_mun"].astype(str).str.strip()
    # 1. Exact match (case-insensitive)
    mascara_exata = serie_cidades.str.lower() == cidade_informada.lower()
    if mascara_exata.any():
        return df[mascara_exata]
    # 2. Fallback: strip state abbreviations like "(PB)" and match
    cidade_sem_uf, uf_informada = separar_cidade_uf(cidade_informada)
    serie_sem_uf = serie_cidades.str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True)
    mascara_sem_uf = serie_sem_uf.str.lower() == cidade_sem_uf.lower()
    matched = df[mascara_sem_uf]
    if matched.empty:
        return matched
    # UF de cada linha casada, extraída do próprio nm_mun ("" quando a planilha
    # não anota o estado nessa linha — não dá pra confiar cegamente nela).
    uf_das_linhas = serie_cidades[mascara_sem_uf].str.extract(r"\(([A-Za-z]{2})\)\s*$")[0].fillna("").str.upper()
    estados_diferentes = set(uf_das_linhas[uf_das_linhas != ""].unique()) - {uf_informada}
    tem_linha_sem_uf = (uf_das_linhas == "").any()

    if uf_informada:
        # 3a. Não confiar em "só há um estado diferente anotado" quando o pedido já
        # veio com UF: outras cidades homônimas em outros estados podem estar sem
        # o sufixo "(UF)" na planilha (formatação inconsistente, PR de correção do
        # bug "Presidente Dutra (BA) vs (MA)") e passariam batidas pela linha[0].
        mascara_uf = uf_das_linhas == uf_informada
        if mascara_uf.any():
            return matched[mascara_uf.values]
        if estados_diferentes and tem_linha_sem_uf:
            raise ValueError(
                f"Cidade ambígua: '{cidade_sem_uf}' encontrada em "
                f"{', '.join(sorted(estados_diferentes))} e em linha(s) sem estado anotado "
                f"na planilha; não é possível confirmar qual corresponde a "
                f"'{cidade_sem_uf} ({uf_informada})'. Corrija a anotação de estado na fonte."
            )
        if estados_diferentes:
            # Nenhuma linha corresponde à UF pedida.
            return matched.iloc[0:0]
        return matched

    # 3b. Sem UF informada: mantém a checagem de ambiguidade original (mais de um
    # estado anotado), mas também trata "algumas linhas com UF anotada, outras
    # não" como ambíguo — não dá pra saber se a linha sem sufixo é a mesma
    # cidade da(s) linha(s) com sufixo.
    estados_tags = set(uf_das_linhas[uf_das_linhas != ""].unique())
    if len(estados_tags) > 1 or (estados_tags and tem_linha_sem_uf):
        estados = sorted(estados_tags)
        raise ValueError(
            f"Cidade ambígua: '{cidade_informada}' encontrada em {', '.join(estados)}. "
            f"Indique o estado, ex: '{cidade_sem_uf} ({estados[0]})'"
        )
    return matched
