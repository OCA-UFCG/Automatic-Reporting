# report-generator-demo

API em FastAPI para gerar um relatório HTML do **Data Nordeste** a partir do CSV `demografia.csv`.

A rota principal monta o HTML do município solicitado e também salva uma cópia em disco dentro de `output/`, para facilitar a visualização local.

## Requisitos

- Python 3.10+

## Instalação

Dentro da pasta `report-generator-demo`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Como executar a API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Depois abra no navegador:

- documentação interativa: `http://127.0.0.1:8000/docs`
- relatório: `http://127.0.0.1:8000/relatorio/Caruaru%20(PE)`

## O que a API faz

Quando você acessa a rota `/relatorio/{cidade}`:

1. lê o CSV `demografia.csv`;
2. filtra a cidade informada;
3. renderiza o HTML do relatório;
4. salva o arquivo em `output/`;
5. devolve o HTML no navegador.

## Onde fica o arquivo gerado

O arquivo é salvo em:

- `output/relatorio_<cidade>.html`

Exemplo:

- `output/relatorio_caruaru_pe.html`

## Formato da cidade

Use o nome igual ao do CSV. Exemplo:

- `Caruaru (PE)`
- `Recife (PE)`
- `Maceió (AL)`

Se houver espaços ou caracteres especiais, use URL encoding no navegador:

- `Caruaru%20(PE)`

## Arquivos importantes

- `main.py` — API FastAPI e template do relatório
- `demografia.csv` — base de dados usada no exemplo
- `requirements.txt` — dependências do projeto
- `output/` — HTMLs gerados pela API

## Observação

Se quiser, depois dá para separar o template em um arquivo `.html` próprio e também adicionar geração de PDF.
