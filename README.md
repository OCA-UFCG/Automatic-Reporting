# report-generator-demo

Projeto com duas partes:

- **API em FastAPI** para gerar relatórios do Data Nordeste.
- **Frontend em React + Vite** para escolher macrotema e cidade e disparar o relatório.

## Estrutura

- `main.py` — API FastAPI
- `citys.txt` — lista de cidades usadas no frontend
- `demografia.csv` — base de dados do relatório
- `output/` — arquivos HTML/PDF e gráficos gerados
- `frontend/` — interface web

## Requisitos

- Python 3.10+
- Node.js 18+

## Instalação da API

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

Se quiser usar um Google Docs específico como texto-base do relatório:

```bash
export DATANE_DOCS_URL="https://docs.google.com/document/d/SEU_DOC_ID/edit"
```

Se essa variável não for definida, a API usa o documento padrão já configurado no `main.py`.

## Instalação do frontend

Dentro da pasta `report-generator-demo/frontend`:

```bash
yarn install
```

## Como executar o frontend

```bash
yarn dev
```

O frontend abre normalmente em `http://localhost:5173`.

Se quiser, também funciona:

```bash
yarn start
```

## Como usar

1. Rode a API.
2. Rode o frontend.
3. Abra o frontend no navegador.
4. Clique em **Gerar relatório**.
5. Escolha o macrotema e a cidade.
6. Clique em **Gerar relatório** novamente para abrir o relatório.

Por enquanto, o macrotema é apenas visual no formulário; a API recebe apenas a cidade.

## O que a API faz

Quando você acessa `/relatorio/{cidade}`:

1. lê o CSV `demografia.csv`;
2. procura a cidade informada, com ou sem UF;
3. busca o texto-base no Google Docs;
4. renderiza o HTML do relatório;
5. gera gráfico de população por sexo;
6. salva os arquivos em `output/`;
7. devolve o HTML no navegador.

## Exemplo de uso direto da API

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/relatorio/Caruaru%20(PE)`

## Arquivos importantes do frontend

- `frontend/src/App.jsx` — tela principal
- `frontend/src/styles.css` — estilos da interface
- `frontend/package.json` — scripts do frontend
