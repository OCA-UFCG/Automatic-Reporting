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

df = pd.read_csv('economy.csv')
linhas = df[df['cidade'] == args.city.lower()].to_dict('records')

template_string = """
{% for linha in dados %}
<html>
<head>
    <title>Relatório</title>
</head>
<body>
    <h1>Dados de {{ linha.cidade }}</h1>
    <p>
        A cidade <strong>{{ linha.cidade }}</strong> é de porte {{ linha.porte }},
        possui aproximadamente {{ linha.populacao }} mil habitantes e renda per capita de R$ {{ linha.renda_per_capita }} mil.
    </p>
</body>
</html>
{% endfor %}
"""

template = Template(template_string)
print(template.render(dados=linhas))
