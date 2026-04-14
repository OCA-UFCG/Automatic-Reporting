# Automatic Reporting (MVP)

Geração de relatório **HTML simples** usando **Jinja2** a partir de um CSV local ou armazenado no Google Drive.

## Requisitos

- Python 3.10+

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Como usar

### 1) CSV local

```bash
python generate_report.py ./seu_arquivo.csv --title "Meu Relatório"
```

### 2) Google Drive (link público)

Você pode passar:

- URL de compartilhamento (`https://drive.google.com/file/d/<FILE_ID>/view?...`)
- URL com `id=`
- Apenas o `FILE_ID`

Exemplo:

```bash
python generate_report.py "https://drive.google.com/file/d/SEU_FILE_ID/view?usp=sharing" --title "Relatório Drive"
```

Saída padrão: `output/report.html`

### 3) Relatório narrativo por município (modelo Data Nordeste)

Use o template narrativo e informe a cidade:

```bash
python generate_report.py "https://drive.google.com/file/d/SEU_FILE_ID/view?usp=sharing" \
	--template templates/data_nordeste_report.html.j2 \
	--city "Recife" \
	--title "Data Nordeste – Relatório modelo" \
	--output output/recife.html
```

Se sua coluna de cidade tiver outro nome, use `--city-column`:

```bash
python generate_report.py "SEU_FILE_ID" --template templates/data_nordeste_report.html.j2 --city "Recife" --city-column "Município"
```

Você também pode forçar o ano exibido no texto com `--year "2022"`.

### 4) Exemplo com `demografia.csv` (seu arquivo)

```bash
python generate_report.py demografia.csv \
	--template templates/data_nordeste_report.html.j2 \
	--city "Recife (PE)" \
	--city-column "nm_mun" \
	--year-column "ano" \
	--title "Data Nordeste – Relatório modelo" \
	--output output/recife.html
```

Observação: o script detecta automaticamente delimitador `;` ou `,`.

### 5) Gerar PDF junto com o HTML (opcional)

Instale dependência opcional:

```bash
pip install weasyprint
```

Depois rode:

```bash
python generate_report.py demografia.csv \
	--template templates/data_nordeste_report.html.j2 \
	--city "Recife (PE)" \
	--city-column "nm_mun" \
	--year-column "ano" \
	--output output/recife.html \
	--pdf-output output/recife.pdf
```

#### Colunas esperadas para o texto de demografia

No CSV, use colunas com estes nomes (ou adapte o template):

- `city` (ou `cidade` / `municipio` / `município`)
- `year` (ou `ano`)
- `demografia.pop_total`
- `demografia.pop_mulher`
- `demografia.pop_mulher_per`
- `demografia.pop_homem`
- `demografia.pop_homem_per`
- `demografia.cres_pop`
- `demografia.cor_raca_pri`
- `demografia.porte`

## Observações

- O arquivo no Google Drive precisa estar compartilhado como **"Qualquer pessoa com o link"**.
- O template padrão está em `templates/report.html.j2`.
- Para customizar layout/campos, altere o template Jinja2.
