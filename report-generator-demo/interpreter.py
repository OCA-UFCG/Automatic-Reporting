import argparse
import pandas as pd
from jinja2 import Template

parser = argparse.ArgumentParser(description="Gerador de relatórios")
parser.add_argument(
    '--city', 
    '-c', 
    type=str, 
    required=True, 
    help="Nome da cidade que você deseja gerar relatório sobre"
)
args = parser.parse_args()

df = pd.read_csv('https://raw.githubusercontent.com/OCA-UFCG/Automatic-Reporting/refs/heads/main/report-generator-demo/demografia.csv', delimiter=";")
linhas = df[df['nm_mun'] == args.city].to_dict('records')


TEMPLATE_STRING = """
{% for linha in dados %}

<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Data Nordeste – Relatório modelo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 920px;
            margin: 32px auto;
            padding: 0 24px;
            line-height: 1.65;
            font-size: 16px;
            color: #222;
        }
        h1 {
            font-size: 30px;
            font-weight: 700;
            margin: 0 0 14px 0;
        }
        h2 {
            font-size: 24px;
            font-weight: 700;
            margin: 30px 0 10px 0;
        }
        p {
            margin: 0 0 14px 0;
            text-align: justify;
        }
        .field {
            font-size: 17px;
            margin-bottom: 8px;
        }
        .field strong {
            font-weight: 700;
        }
        .indent {
            text-indent: 1.5em;
        }
        ul {
            margin: 8px 0 16px 28px;
        }
        li {
            margin-bottom: 6px;
        }
    </style>
</head>
<body>
<h1>Data Nordeste – Relatório modelo</h1>
<p class="field"><strong>Município:</strong> {{ linha.nm_mun }}</p>
<p class="field"><strong>Ano:</strong> {{ linha.ano }}</p>

<h2>Apresentação</h2>
<p class="indent">Data Nordeste é uma plataforma desenvolvida para centralizar o acesso a dados sobre o Nordeste e a área de atuação da Sudene, reunindo dados produzidos pela Sudene e por seus parceiros institucionais. O objetivo principal é promover a acessibilidade, a transparência e a inovação na gestão de informações estratégicas, ajudando a fortalecer o planejamento e a tomada de decisões principalmente na região Nordeste do Brasil.</p>

<p class="indent">A plataforma Data Nordeste nasceu do compromisso da Sudene de enfrentar um desafio histórico: a dispersão e o difícil acesso a dados confiáveis sobre o Nordeste. A ausência de uma base integrada dificultava o planejamento e a formulação de políticas públicas, além de limitar o potencial de investimentos na região.</p>

<p class="indent">A partir dessa realidade, a Sudene, em parceria com a Universidade Federal de Campina Grande (UFCG), concebeu uma plataforma única, voltada a transformar dados complexos em conhecimento acessível, útil e estratégico. A proposta é reunir, em um só lugar, indicadores multitemáticos sobre o Nordeste, com recortes territoriais que abranjam o Semiárido, a Caatinga e a área de atuação da autarquia.</p>

<p class="indent">Para tornar esse projeto viável, a Sudene conta com o apoio técnico do Observatório da Caatinga e Desertificação, da Universidade Federal de Campina Grande (UFCG), parceiro na implementação e no desenvolvimento da estrutura tecnológica do portal.</p>

<p class="indent">Com arquitetura moderna e escalável, a plataforma Data Nordeste é mais do que um banco de dados: é uma ferramenta viva de inteligência territorial, criada para apoiar gestores, pesquisadores, empresários e cidadãos na construção de um Nordeste mais justo, sustentável e de alta resiliência econômica.</p>

<h2>1. Demografia</h2>

<p class="indent">Na plataforma DataNordeste, é possível acessar painéis de dados interativos, boletins e datastories sobre demografia. A apresentação em indicadores sintéticos, gráficos comparativos, séries temporais e mapa municipal facilita a visualização da dinâmica demográfica regional. Os dados foram extraídos do Censo Demográfico do Instituto Brasileiro de Geografia e Estatística (IBGE). Além disso, estão disponíveis boletins sobre a população negra, a população idosa, a população indígena, mulheres, juventude, migração e habitação, bem como um datastory sobre "Nordeste é feminino, mas isso aparece no poder?"</p>

<p class="indent">O município de {{ linha.nm_mun }} possui, de acordo com o Censo {{ linha.ano }}, população residente de {{ linha.pop_total }} pessoas. Desse total {{ linha.pop_mulher }} ({{ linha.pop_mulher_per }}) são do sexo feminino e {{ linha.pop_homem }} ({{ linha.pop_homem_per }}) do sexo masculino.</p>

<p class="indent">De acordo com o Censo Demográfico 2022, a população feminina no Brasil é composta por cerca de 104 milhões de mulheres (51,5% da população nacional), frente a 98 milhões de homens. As mulheres são maioria em todas as regiões do País. O Nordeste é a segunda região com maior número absoluto de mulheres, cerca de 28,2 milhões de mulheres. A primeira posição é ocupada pela região Sudeste, que concentra 43,9 milhões. Neste sentido, a plataforma Data Nordeste apresenta um Data Story dedicado a esta característica demográfica.</p>

<p class="indent">A taxa de crescimento populacional de {{ linha.nm_mun }} foi de {{ linha.cres_pop }} nos últimos censos do IBGE havendo uma predominância de população {{ linha.cor_raca_pri }}. Em todas as áreas de abrangência da plataforma DataNE, a população se autodeclara majoritariamente parda, seguida por branca, havendo aumento da cor ou raça indígena nos últimos dois censos e redução da cor ou raça Amarela.</p>

<p class="indent">No DataNE, o porte dos municípios é definido pela seguinte classificação: baixo porte (até 50 mil habitantes), médio porte (entre 50 mil e 100 mil habitantes) e grande porte (acima de 100 mil habitantes). Nesse contexto, {{ linha.nm_mun }} é um município de {{ linha.porte }} porte. O crescimento populacional de municípios de grande porte na região Nordeste ocorre, na maioria das vezes, pelo papel de polo regional que alguns deles desempenham. Quando há, entretanto, uma queda populacional, o IBGE aponta alguns motivos:</p>
<ul>
    <li>A transição demográfica do tamanho das famílias – menos nascimentos e envelhecimento da população</li>
    <li>A migração e a busca por oportunidades – êxodo para cidades médias e grandes, com fins de estudo e trabalho, uma vez que, em cidades muito pequenas, a economia muitas vezes depende de serviços prestados pelas prefeituras e de aposentadorias. A população mais jovem deve estar procurando oportunidades fora de sua cidade natal.</li>
    <li>O fenômeno do “Entorno” – pessoas podem estar deixando suas cidades para morar em cidades vizinhas com melhores oportunidades.</li>
</ul>
 </body>
</html>
{% endfor %}
"""

template = Template(TEMPLATE_STRING)
print(template.render(dados=linhas))
