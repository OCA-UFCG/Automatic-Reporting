from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from jinja2 import Template

app = FastAPI()

TEMPLATE_STRING = """
{% for linha in dados %}
<html>
<head><title>Relatório</title></head>
<body>
    <h1>Dados de {{ linha.cidade }}</h1>
    <p>
        A cidade <strong>{{ linha.cidade }}</strong> é de porte {{ linha.porte }},
        possui aproximadamente {{ linha.populacao }} mil habitantes 
        e renda per capita de R$ {{ linha.renda_per_capita }} mil.
    </p>
</body>
</html>
{% endfor %}
"""

@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str):
    df = pd.read_csv("economy.csv")
    linhas = df[df["cidade"] == cidade.lower()].to_dict("records")

    if not linhas:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

    template = Template(TEMPLATE_STRING)
    return template.render(dados=linhas)
