from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from jinja2 import Template

app = FastAPI()

TEMPLATE_STRING = """
{% for linha in dados %}
Data Nordeste – Relatório modelo
Município: {{ linha.nm_mun}}
Ano: {{ linha.ano }}

<strong>Apresentação</strong>
Data Nordeste é uma plataforma desenvolvida para centralizar o acesso a dados sobre o Nordeste e a área de atuação da Sudene, reunindo dados produzidos pela Sudene e por seus parceiros institucionais. O objetivo principal é promover a acessibilidade, a transparência e a inovação na gestão de informações estratégicas, ajudando a fortalecer o planejamento e a tomada de decisões principalmente na região Nordeste do Brasil.

A plataforma Data Nordeste nasceu do compromisso da Sudene de enfrentar um desafio histórico: a dispersão e o difícil acesso a dados confiáveis sobre o Nordeste. A ausência de uma base integrada dificultava o planejamento e a formulação de políticas públicas, além de limitar o potencial de investimentos na região.

A partir dessa realidade, a Sudene, em parceria com a Universidade Federal de Campina Grande (UFCG), concebeu uma plataforma única, voltada a transformar dados complexos em conhecimento acessível, útil e estratégico. A proposta é reunir, em um só lugar, indicadores multitemáticos sobre o Nordeste, com recortes territoriais que abranjam o Semiárido, a Caatinga e a área de atuação da autarquia.

Para tornar esse projeto viável, a Sudene conta com o apoio técnico do Observatório da Caatinga e Desertificação, da Universidade Federal de Campina Grande (UFCG), parceiro na implementação e no desenvolvimento da estrutura tecnológica do portal.

Com arquitetura moderna e escalável, a plataforma Data Nordeste é mais do que um banco de dados: é uma ferramenta viva de inteligência territorial, criada para apoiar gestores, pesquisadores, empresários e cidadãos na construção de um Nordeste mais justo, sustentável e de alta resiliência econômica.

1. Demografia

Na plataforma DataNordeste, é possível acessar painéis de dados interativos, boletins e datastories sobre demografia. A apresentação em indicadores sintéticos, gráficos comparativos, séries temporais e mapa municipal facilita a visualização da dinâmica demográfica regional. Os dados foram extraídos do Censo Demográfico do Instituto Brasileiro de Geografia e Estatística (IBGE). Além disso, estão disponíveis boletins sobre a população negra, a população idosa, a população indígena, mulheres, juventude, migração e habitação, bem como um datastory sobre "Nordeste é feminino, mas isso aparece no poder?"

O município de {{ linha.nm_mun }} possui, de acordo com o Censo {{ linha.ano }}, população residente de {{ linha.pop_total }} pessoas. Desse total {{ linha.pop_mulher }} ({{ linha.pop_mulher_per}} são do sexo feminino e {{ linha.pop_homem }} ({{ linha.pop_homem_per }}) do sexo masculino. 

De acordo com o Censo Demográfico 2022, a população feminina no Brasil é composta por cerca de 104 milhões de mulheres (51,5% da população nacional), frente a 98 milhões de homens. As mulheres são maioria em todas as regiões do País. O Nordeste é a segunda região com maior número absoluto de mulheres, cerca de 28,2 milhões de mulheres. A primeira posição é ocupada pela região Sudeste, que concentra 43,9 milhões. Neste sentido, a plataforma Data Nordeste apresenta um Data Story dedicado a esta característica demográfica.  

A taxa de crescimento populacional de {{ linha.nm_mun }} foi de {{ linha.cres_pop }} nos últimos censos do IBGE havendo uma predominância de população {{ linha.cor_raca_pri }}. Em todas as áreas de abrangência da plataforma DataNE, a população se autodeclara majoritariamente parda, seguida por branca, havendo aumento da cor ou raça indígena nos últimos dois censos e redução da cor ou raça Amarela.

No DataNE, o porte dos municípios é definido pela seguinte classificação: baixo porte (até 50 mil habitantes), médio porte (entre 50 mil e 100 mil habitantes) e grande porte (acima de 100 mil habitantes). Nesse contexto, {{ linha.nm_mun }} é um município de {{ linha.porte }} porte. O crescimento populacional de municípios de grande porte na região Nordeste ocorre, na maioria das vezes, pelo papel de polo regional que alguns deles desempenham. Quando há, entretanto, uma queda populacional, o IBGE aponta alguns motivos: 
- A transição demográfica do tamanho das famílias – menos nascimentos e envelhecimento da população
- A migração e a busca por oportunidades – êxodo para cidades médias e grandes, com fins de estudo e trabalho, uma vez que, em cidades muito pequenas, a economia muitas vezes depende de serviços prestados pelas prefeituras e de aposentadorias. A população mais jovem deve estar procurando oportunidades fora de sua cidade natal.
- O fenômeno do “Entorno” – pessoas podem estar deixando suas cidades para morar em cidades vizinhas com melhores oportunidades.
{% endfor %}
"""

@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str):
    df = pd.read_csv('demografia.csv', delimiter=";")
    linhas = df[df['nm_mun'] == cidade].to_dict("records")

    if not linhas:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

    template = Template(TEMPLATE_STRING)
    return template.render(dados=linhas)
