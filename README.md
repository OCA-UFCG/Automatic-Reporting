# Automatic Reporting

Este repositório agora está focado no demo em [report-generator-demo](report-generator-demo), que gera relatórios HTML do **Data Nordeste** a partir do arquivo [demografia.csv](report-generator-demo/demografia.csv).

## O que o demo faz

- sobe uma API em FastAPI;
- recebe o nome de uma cidade na rota;
- filtra o CSV `demografia.csv`;
- monta o HTML do relatório;
- salva o HTML em [report-generator-demo/output](report-generator-demo/output).

## Estrutura principal

- [report-generator-demo/main.py](report-generator-demo/main.py) — API e template do relatório;
- [report-generator-demo/demografia.csv](report-generator-demo/demografia.csv) — base usada no demo;
- [report-generator-demo/requirements.txt](report-generator-demo/requirements.txt) — dependências;
- [report-generator-demo/output](report-generator-demo/output) — HTMLs gerados.

## Instalação

Dentro da pasta do demo:

```bash
cd report-generator-demo
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Como rodar a API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Como testar

Abra no navegador:

- documentação: `http://127.0.0.1:8000/docs`
- relatório: `http://127.0.0.1:8000/relatorio/Caruaru%20(PE)`

## Onde o HTML aparece

Depois que você acessar a rota, o arquivo fica salvo em:

- `report-generator-demo/output/relatorio_caruaru_pe.html`

## Observações

- O nome da cidade precisa existir no CSV;
- o endpoint compara ignorando maiúsculas/minúsculas e espaços;
- se quiser outro município, troque apenas a parte final da URL.
