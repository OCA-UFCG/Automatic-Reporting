"""A prévia do painel precisa montar o mesmo contexto que o relatório.

Regressão: `montar_contexto_de_previa` tinha uma implementação própria, reduzida
— consultava a view do perfil e parava aí. Sem fallback para CSV e sem as
consultas de enriquecimento, ela devolvia dois campos (`nm_mun`, `sigla_uf`)
enquanto o relatório real tinha dezenas. Na tela, todo `$placeholder` aparecia
cru e dava a impressão de que o contrato estava errado.

Nenhum destes testes toca o banco.
"""

from services import contexto as contexto_mod
from services.admin import montar_contexto_de_previa


def test_previa_usa_o_fallback_de_csv_como_o_relatorio(monkeypatch):
    """Banco fora do ar não pode esvaziar a prévia: o relatório cai para o CSV."""
    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: (
            [{"nm_mun": "Campina Grande (PB)", "pop_total_2022": 419387}],
            contexto_mod.ORIGEM_CSV_SEM_BANCO,
        ),
    )
    monkeypatch.setattr(contexto_mod, "_preencher_cache", lambda *a, **k: None)

    ctx, aviso = montar_contexto_de_previa("demografia", "Campina Grande (PB)")

    assert ctx["pop_total_2022"] == 419387
    assert aviso is not None, "o editor precisa saber que está vendo o cenário degradado"
    assert "túnel" in aviso, "sem conexão, a ação é abrir o túnel — o aviso precisa dizer isso"


def test_aviso_distingue_sem_conexao_de_cidade_ausente(monkeypatch):
    """As duas causas do fallback pedem ações opostas de quem opera o painel.

    Dizer "banco fora do ar" quando o banco respondeu e só faltava a cidade
    manda a pessoa procurar o problema no lugar errado.
    """
    monkeypatch.setattr(contexto_mod, "_preencher_cache", lambda *a, **k: None)

    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: (
            [{"nm_mun": "X (PB)"}],
            contexto_mod.ORIGEM_CSV_SEM_CIDADE,
        ),
    )
    _, aviso = montar_contexto_de_previa("demografia", "X (PB)")

    assert "respondeu" in aviso
    assert "túnel" not in aviso, "o túnel está bem; o problema é outro"


def test_previa_nao_avisa_quando_o_dado_veio_da_view(monkeypatch):
    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: (
            [{"nm_mun": "Campina Grande (PB)"}],
            contexto_mod.ORIGEM_VIEW,
        ),
    )
    monkeypatch.setattr(contexto_mod, "_preencher_cache", lambda *a, **k: None)

    _, aviso = montar_contexto_de_previa("demografia", "Campina Grande (PB)")

    assert aviso is None


def test_previa_recebe_as_consultas_de_enriquecimento(monkeypatch):
    """O que faltava antes: características, indicadores, população em situação de rua…"""
    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: (
            [{"nm_mun": "Campina Grande (PB)"}],
            contexto_mod.ORIGEM_VIEW,
        ),
    )

    def cache_falso(cache, linha_base, slugs):
        cache.dados.update(
            {
                "caracteristicas": {"area_km2": 593.0},
                "indicadores": {"idhm": 0.72},
                "rua": {"pop_rua": 120},
                "demografia": {"pop_total_2022": 419387},
            }
        )
        cache.consultado = True

    monkeypatch.setattr(contexto_mod, "_preencher_cache", cache_falso)

    ctx, _ = montar_contexto_de_previa("demografia", "Campina Grande (PB)")

    assert ctx["area_km2"] == 593.0
    assert ctx["idhm"] == 0.72
    assert ctx["pop_rua"] == 120
    assert ctx["pop_total_2022"] == 419387


def test_previa_carrega_a_data_do_relatorio(monkeypatch):
    """`$data_relatorio` e `$hora_relatorio` são placeholders como os outros."""
    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: ([{"nm_mun": "X (PB)"}], contexto_mod.ORIGEM_VIEW),
    )
    monkeypatch.setattr(contexto_mod, "_preencher_cache", lambda *a, **k: None)

    ctx, _ = montar_contexto_de_previa("demografia", "X (PB)")

    assert "data_relatorio" in ctx
    assert "hora_relatorio" in ctx


def test_enriquecimento_respeita_o_macrotema(monkeypatch):
    """Dados de saúde não vazam para um contexto de saneamento."""
    monkeypatch.setattr(
        contexto_mod,
        "carregar_linha_base",
        lambda slug, dados, cidade: ([{"nm_mun": "X (PB)"}], contexto_mod.ORIGEM_VIEW),
    )

    def cache_falso(cache, linha_base, slugs):
        cache.dados.update(
            {
                "perfil_saude": {"leitos": 10},
                "esgotamento": {"esgoto_rede_2022": 55.5},
            }
        )
        cache.consultado = True

    monkeypatch.setattr(contexto_mod, "_preencher_cache", cache_falso)

    ctx, _ = montar_contexto_de_previa("saneamento", "X (PB)")

    assert ctx["esgoto_rede_2022"] == 55.5
    assert "leitos" not in ctx
