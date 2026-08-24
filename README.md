# Automatic Reporting

Aplicação para gerar relatórios municipais em HTML e PDF. A API FastAPI combina
dados de planilhas, PostgreSQL e Google Docs; o relatório é renderizado com React
SSR e convertido para PDF pelo WeasyPrint.

## Requisitos

- Python 3.10 ou superior
- Node.js 18 ou superior
- PostgreSQL com acesso às bases do Data Nordeste

> O PostgreSQL passou a ser obrigatório para gerar os relatórios. Este
> repositório não contém dump, migrations ou dados de exemplo capazes de montar
> essa base do zero. Para testar a geração completa, solicite à equipe as
> credenciais da instância de desenvolvimento/homologação.

## Configuração

Crie o arquivo local de configuração:

```bash
cp .env.example .env
```

Preencha no `.env` as fontes CSV, os documentos e a conexão com o banco. Não
adicione esse arquivo ao Git.

```dotenv
DEMOGRAFIA_CSV_URL=https://docs.google.com/spreadsheets/d/ID/edit#gid=0
EDUCACAO_CSV_URL=https://docs.google.com/spreadsheets/d/ID/edit#gid=0
SAUDE_CSV_URL=https://docs.google.com/spreadsheets/d/ID/edit#gid=0

CARACTERISTICAS_DOCS_URL=https://docs.google.com/document/d/ID/edit
DEMOGRAFIA_DOCS_URL=https://docs.google.com/document/d/ID/edit
EDUCACAO_DOCS_URL=https://docs.google.com/document/d/ID/edit
SAUDE_DOCS_URL=https://docs.google.com/document/d/ID/edit

DB_HOST=host-do-postgres
DB_DATABASE=nome-do-banco
DB_USER=usuario
DB_PASSWORD=senha
DB_PORT=5432
```

As demais variáveis disponíveis estão documentadas em `.env.example`. Planilhas
e documentos do Google precisam estar acessíveis para leitura pela aplicação.

### Banco de dados esperado

A aplicação consulta atualmente estes schemas:

- `carac_mun`
- `dem_demografia`
- `dem_demografia_indigena`
- `dem_demografia_quilombola`
- `dem_rua`
- `edu_analfabetismo`
- `sau_imunizacao`

O usuário configurado em `DB_USER` precisa de permissão `SELECT` nesses schemas.
Não é necessário conceder permissão de escrita.

Para validar as credenciais antes de subir a aplicação:

```bash
source .venv/bin/activate
python -m utils.database
```

O resultado esperado começa com:

```text
Conexão bem-sucedida!
```

Se a aplicação estiver em Docker e o PostgreSQL estiver na máquina host, não use
`localhost` em `DB_HOST`: dentro do container, `localhost` aponta para o próprio
container. Use um hostname acessível pela rede Docker ou
`host.docker.internal`, quando disponível no sistema operacional.

## Execução local

Instale as dependências:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

npm install
npm run build -w report
```

Inicie a API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

O FastAPI inicia o servidor React SSR automaticamente. Em outro terminal, rode
o frontend em modo de desenvolvimento:

```bash
npm run dev -w frontend
```

- Frontend: `http://localhost:5173`
- Swagger da API: `http://localhost:8000/docs`

Um relatório também pode ser gerado diretamente pela API:

```text
http://localhost:8000/relatorio/Canapi%20(AL)?macrotema=demografia
```

Os PDFs, HTMLs, mapas e gráficos gerados ficam em `output/`.

## Execução com Docker

Com o `.env` preenchido:

```bash
docker compose up --build
```

A aplicação fica disponível em `http://localhost:8000`. O Compose lê o `.env` e
repassa as credenciais do PostgreSQL ao container. A pasta `output/` é montada
como volume para preservar os relatórios.

Também é possível executar a imagem diretamente:

```bash
docker build -t automatic-reporting .
docker run --rm \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/output:/app/output" \
  automatic-reporting
```

## Testes

Com o ambiente virtual ativo:

```bash
pytest -q
```

Os testes unitários de renderização não precisam acessar o PostgreSQL. A geração
de um relatório real e os testes manuais das queries precisam das variáveis
`DB_*` e de conectividade com a instância configurada.

## Estrutura principal

- `main.py` — rotas FastAPI
- `services/generation.py` — orquestra a geração do relatório
- `utils/queries/` — consultas PostgreSQL por macrotema
- `utils/render/` — placeholders, condições editoriais e HTML
- `utils/external/docs.py` — leitura e limpeza dos Google Docs
- `plotting/` — geração dos gráficos
- `report/` — componentes React usados no PDF
- `frontend/` — interface de seleção e listagem
- `output/` — artefatos gerados

Para detalhes do fluxo interno, consulte [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
