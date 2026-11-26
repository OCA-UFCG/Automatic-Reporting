"""Quais Docs a atualização baixa (scripts/atualizar_docs.py e POST /docs/atualizar,
services/atualizacao_docs.py). Regressão de 16/11/2026: o script só
cobria município e estado, e o Doc de área (Nordeste, Caatinga…) ficava congelado no
output/docs_cache/ com a primeira cópia baixada, mesmo depois de corrigido no Google."""

from services.atualizacao_docs import docs_configurados as _docs_configurados

URL_AREA_DEMOGRAFIA = "https://docs.google.com/document/d/area-demografia/edit"
URL_AREA_DESENVOLVIMENTO_SOCIAL = "https://docs.google.com/document/d/area-dessoc/edit"


def test_inclui_doc_de_area_de_tema_com_matview(monkeypatch):
    monkeypatch.setenv("DEMOGRAFIA_AREA_DOCS_URL", URL_AREA_DEMOGRAFIA)

    assert ("demografia (área)", URL_AREA_DEMOGRAFIA) in _docs_configurados()


def test_inclui_doc_de_area_de_tema_de_texto_fixo(monkeypatch):
    # Desenvolvimento social não tem matview de área (AREAS_DO_TEMA_DE_TEXTO_FIXO),
    # mas tem Doc de área e precisa ser atualizado do mesmo jeito.
    monkeypatch.setenv(
        "DESENVOLVIMENTO_SOCIAL_AREA_DOCS_URL", URL_AREA_DESENVOLVIMENTO_SOCIAL
    )

    docs = _docs_configurados()

    assert ("desenvolvimento-social (área)", URL_AREA_DESENVOLVIMENTO_SOCIAL) in docs


def test_pula_tema_sem_doc_de_area(monkeypatch):
    monkeypatch.delenv("SAUDE_AREA_DOCS_URL", raising=False)

    rotulos = [rotulo for rotulo, _ in _docs_configurados()]

    assert "saude (área)" not in rotulos
