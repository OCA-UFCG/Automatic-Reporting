"""Gráficos do relatório por área (services/graficos_area.py). Os PNGs vão para
tmp_path; nada toca o banco."""

from decimal import Decimal
from pathlib import Path

from services import graficos_area
from services.relatorio_estado import graficos_da_unidade


def test_nordeste_tem_o_grafico_do_idhm_em_desenvolvimento_social(tmp_path: Path):
    graficos = graficos_area.gerar_graficos_da_area("desenvolvimento-social", "Nordeste", {}, tmp_path, "area_nordeste")

    assert graficos == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}
    assert (tmp_path / graficos["grafico_idhm_componentes"]).is_file()


def test_desenvolvimento_social_de_outra_area_nao_tem_grafico(tmp_path: Path):
    assert graficos_area.gerar_graficos_da_area("desenvolvimento-social", "Caatinga", {}, tmp_path, "x") == {}


def test_grafico_que_falha_fica_de_fora(tmp_path: Path, monkeypatch):
    def falha(_output_dir: Path, _safe: str) -> str:
        raise ValueError("sem dado")

    monkeypatch.setitem(graficos_area.GRAFICOS_DA_AREA, ("desenvolvimento-social", "Semiárido"), {"grafico_x": falha})

    assert graficos_area.gerar_graficos_da_area("desenvolvimento-social", "Semiárido", {}, tmp_path, "x") == {}


def test_valores_fixos_conferem_com_o_texto_do_doc():
    # Os números que o Doc cita no texto e nos cards (16/11/2026).
    medianas = graficos_area._MEDIANAS_DO_IDHM_NO_NORDESTE
    assert medianas["IDHM"] == (0.291, 0.420, 0.588)
    assert (medianas["Educação"][0], medianas["Educação"][-1]) == (0.108, 0.4825)
    assert (medianas["Longevidade"][-1], medianas["Renda"][-1]) == (0.7575, 0.559)


def test_handler_usa_os_graficos_da_area_com_o_sufixo_da_unidade(tmp_path: Path, monkeypatch):
    from services import relatorio_estado

    monkeypatch.setattr(relatorio_estado, "OUTPUT_DIR", tmp_path)

    graficos = graficos_da_unidade("area", "desenvolvimento-social", "Nordeste", {})

    assert graficos == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}


# Gráficos de área gerados do banco (23/11/2026): a linha da areaint_* com `area_`
# trocado por `uf_` passa pelos adaptadores do estado.

def test_troca_area_por_uf_so_no_prefixo():
    assert graficos_area.com_prefixo_do_estado({"area_pib_2023": 1, "area_nome": "Caatinga", "outra": 2}) == {
        "uf_pib_2023": 1, "uf_nome": "Caatinga", "outra": 2,
    }


def test_rosca_de_esgoto_sai_das_quantidades_da_matview():
    # Caatinga no gamma em 23/11/2026: as 7 categorias somam o total.
    linha = graficos_area.com_prefixo_do_estado({
        "area_domicilios_total_2022": 8914895, "area_esgoto_rede_geral_pluvial_2022qtd": 3303629,
        "area_esgoto_fossa_septica_2022qtd": 1624453, "area_esgoto_fossa_rudimentar_2022qtd": 3384170,
        "area_esgoto_vala_2022qtd": 200371, "area_esgoto_corpo_hidrico_2022qtd": 83734,
        "area_esgoto_outra_forma_2022qtd": 164822, "area_sem_banheiro_2022qtd": 153716,
    })

    rosca = graficos_area.rosca_de_esgoto_da_area(linha)

    assert rosca["esg_total"] == 8914895
    assert rosca["esg_fossa_septica_ou_fossa_filtro"] == 1624453
    assert sum(v for k, v in rosca.items() if k != "esg_total") == rosca["esg_total"]


def test_area_usa_os_adaptadores_do_estado_com_os_complementos_da_area(tmp_path: Path, monkeypatch):
    recebido = {}

    def falso_do_estado(slug, linha, output_dir, safe, complementos):
        recebido.update(slug=slug, linha=linha, safe=safe, complementos=complementos)
        return {"grafico_pib": "grafico_pib_area_x.png"}

    monkeypatch.setattr(graficos_area, "gerar_graficos_do_estado", falso_do_estado)

    graficos = graficos_area.gerar_graficos_da_area("economia-renda", "Nordeste", {"area_pib_2023": 5}, tmp_path, "area_x")

    assert graficos == {"grafico_pib": "grafico_pib_area_x.png"}
    assert recebido["linha"] == {"uf_pib_2023": 5}
    assert recebido["complementos"] is graficos_area.COMPLEMENTOS_DA_AREA


def test_pib_em_trilhao_vira_reais():
    from services.graficos_estado_economia import valor_absoluto_do_estado

    assert valor_absoluto_do_estado(Decimal("1.5"), "trilhão") == 1_500_000_000_000.0


def test_saude_soma_pela_coluna_de_pertencimento_da_area(monkeypatch):
    from utils.queries import saude

    sqls = []

    def falso(sql, params, descricao, buscar_todas=False):
        sqls.append(sql)
        return [(2025, 10)] if buscar_todas else (1, 2, 3, 4, 5, 6, 7, 8)

    monkeypatch.setattr(saude, "executar_query", falso)

    dados = saude.buscar_saude_do_painel_da_area("Caatinga")

    assert "i.caat_24 = 'Sim'" in sqls[0] and "e.caat_25 = 'Sim'" in sqls[1]
    assert dados["dose_etario_multifaixa"] == 8
    assert dados["estabelecimentos_saude_serie"] == [{"ano": 2025, "total_estabelecimentos": 10}]
    assert saude.buscar_saude_do_painel_da_area("Área nova") == {}


def test_handler_passa_a_linha_da_area(tmp_path: Path, monkeypatch):
    from services import relatorio_estado

    recebido = {}
    monkeypatch.setattr(relatorio_estado, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(relatorio_estado, "gerar_graficos_da_area",
                        lambda slug, nome, linha, out, sufixo: recebido.update(linha=linha, sufixo=sufixo) or {})

    graficos_da_unidade("area", "saude", "Semiárido", {"area_x": 1})

    assert recebido == {"linha": {"area_x": 1}, "sufixo": "area_semi_rido"}


def test_eixo_da_aridez_da_area_chega_ao_grafico_como_territorio():
    """Regressão de 25/11/2026: a Caatinga saía com "Área do estado" no eixo."""
    from services.graficos_estado import aridez_do_estado

    linha = {"uf_aridez_2021_valida": 1, **graficos_area.rotulo_da_aridez_da_area({})}

    assert aridez_do_estado(linha)["aridez_rotulo_eixo"] == "Área do território"
    assert graficos_area.COMPLEMENTOS_DA_AREA["meio-ambiente"] is graficos_area.rotulo_da_aridez_da_area
