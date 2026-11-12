# Relatório por estado

Guia para quem vai implementar ou revisar um tema no relatório por estado. Ele
explica o fluxo de ponta a ponta, o passo a passo para colocar um tema novo no ar e
os tropeços que já custaram tempo. O fluxo municipal está em
[ARCHITECTURE.md](ARCHITECTURE.md); as regras de escrita do Doc estão em
[editorial/](editorial/).

Estado em 11/11/2026: **Demografia**, **Educação**, **Saúde**, **Economia e Renda**, **Infraestrutura e Saneamento**, **Segurança Hídrica** e **Meio Ambiente** têm Doc estadual de verdade.
Os outros temas têm Docs de rascunho. Um tema novo costuma precisar só do Doc e do
secret; no código, em geral só os ícones dos cards (`_ICONE_POR_CAMPO_DO_DOC` em
`utils/cover.py`).

## Em uma frase

O relatório de um estado é o mesmo produto do municipal (mesmo SSR, mesmo PDF, mesma
fila e cache), mas lê **uma linha da matview estadual** do tema e **um Doc estadual**
do tema, num handler separado para não arriscar o relatório municipal.

## Fluxo

```
Portal (recorte "Estado")
  │  GET /estados                    → os 9 estados do Nordeste
  │  GET /relatorio/Paraíba?macrotema=demografia
  ▼
main.py  /relatorio/{cidade}
  │  resolver_estado("Paraíba") acha o estado? → handler estadual
  │  senão                                     → handler municipal (de sempre)
  ▼
services/relatorio_estado.py  gerar_relatorio_estado_handler
  │  para cada tema pedido:
  │   1. docs_url(slug, "estado")       → <TEMA>_ESTADO_DOCS_URL (sem Doc: tema pulado)
  │   2. buscar_contexto_estado(slug)   → linha do estado na matview (sem linha: pulado)
  │   3. carregar_texto_do_docs(url)    → texto do Doc (cache em output/docs_cache/)
  │   4. separar_secoes_do_tema         → descricao_tema, Fontes, Conteúdos relacionados…
  │   5. placeholders + condicionais    → mesmo motor do municipal
  ▼
React SSR (report/) → HTML → WeasyPrint → PDF em output/
```

Nenhum tema com Doc e linha? O handler responde **503** em vez de gravar um PDF só
com a capa.

## As peças

| O quê | Onde |
| --- | --- |
| Lista dos estados (os 9 do NE; MG fica fora até entrar nas matviews) | `utils/data/estados.py` |
| Rota que separa estado de município | `main.py`, `/relatorio/{cidade}` e `/estados` |
| Handler estadual (capa, temas, cards) | `services/relatorio_estado.py` |
| Matview estadual de cada tema | `utils/queries/estado.py`, `MATVIEW_ESTADUAL_POR_MACROTEMA` |
| Nome da variável do Doc estadual | `services/macrotemas.py`, `docs_env` |
| Lista oficial das variáveis | `.env.example` |
| Atualização do cache dos Docs | `scripts/atualizar_docs.py` |
| Rótulo "Dados estaduais" e capa | `report/src/components/rotuloDaUnidade.js`, `cover/Cover.jsx`, `cover/capaTemConteudo.js` |

### Dados: a matview estadual

- Schema `auto_relatorios_est`, uma matview por tema (`est_demografia`,
  `est_educacao`…), mantidas pela equipe de dados.
- As colunas são as municipais com o prefixo `uf_`. As primeiras vêm da `est_geral`
  e servem para o texto: `uf_estado` ("Paraíba", é por ela que o código filtra),
  `uf_sigla_uf`, `uf_sujeito` ("A Paraíba"), `uf_de` ("da Paraíba"), `uf_em`
  ("na Paraíba").
- Ao contrário do municipal, **não há cálculo em Python**: tudo o que o Doc usa
  precisa vir pronto da matview, inclusive campos derivados como
  `uf_qtd_faixas_etarias_maior`. Se faltar coluna, o pedido vai para a equipe de dados.
- **Só o banco do gamma tem esse schema** (túnel na porta 5434). O banco do beta não tem.

### Texto: o Doc estadual

- Uma variável por tema: `DEMOGRAFIA_DOCS_URL` vira `DEMOGRAFIA_ESTADO_DOCS_URL`.
- Mesma linguagem do Doc municipal: `descricao_tema = “…”@@`, `Para quando … então:`,
  `*grafico_…`, `Síntese`, `#!Fontes`, `#!Conteúdos relacionados`.
- **Diferença importante: no Doc estadual, cada `Para quando … então:` vale só para a
  linha seguinte** (`isolar_paragrafo_de_cada_condicao`, em
  `utils/render/placeholders.py`). A linha depois dela já é texto sem condição. Para
  condicionar dois parágrafos, repita a condição antes de cada um. No municipal o
  bloco vai até a linha em branco; no estado não dá, porque o export não tem linhas
  em branco, e o parágrafo seguinte sumia junto com uma condição falsa.
- Os campos são escritos com o tema na frente e o prefixo `uf_`:
  `demografia.$uf_pop_total_2022`, `demografia.$uf_pop_mulher_per:2%`.
- **Panorama de indicadores** (cards do tema): antes de `descricao_tema`, cada card
  tem um rótulo, um valor e, se quiser, uma legenda "fonte • unidade". No município
  os cards vêm da `vw_indicadores`; no estado vêm do próprio Doc.

  ```
  Panorama de indicadores
  Domicílios com coleta de lixo
  infraestrutura.$uf_coleta_2022:2%
  IBGE Censo 2022 • coleta direta e em caçamba
  PIB
  R$ economia.$uf_pib_2023:2 economia.$uf_pib_unid_2023
  ```

  - O valor usa o mesmo formato do texto: `:2%` para percentual, `:2` para casas
    decimais, e pode ter moeda e unidade em volta (`R$ … bilhões`).
  - A legenda só é reconhecida com o `•`: o que vem antes vira a fonte do card, e o
    que vem depois, o rodapé. Sem o `•`, a linha é lida como rótulo do próximo card.
  - Card cujo campo não existe na matview some da capa, sem erro.

- Pode ser Google Doc nativo ou `.docx` no Drive: o export em texto dos dois é igual.

## Passo a passo: colocar um tema no ar por estado

1. **Confira as colunas da matview** no banco do gamma. É uma consulta ao catálogo,
   barata, que não varre a matview:

   ```sql
   SELECT a.attname
   FROM pg_attribute a
   JOIN pg_class t ON a.attrelid = t.oid
   JOIN pg_namespace n ON t.relnamespace = n.oid
   WHERE n.nspname = 'auto_relatorios_est' AND t.relname = 'est_educacao'
     AND a.attnum > 0 AND NOT a.attisdropped
   ORDER BY a.attnum;
   ```

2. **Confira os campos do Doc contra as colunas.** Exporte o Doc em texto
   (`https://docs.google.com/document/d/<ID>/export?format=txt`) e liste os campos:

   ```bash
   curl -sL "https://docs.google.com/document/d/<ID>/export?format=txt" \
     | grep -oE 'educacao\.\$[a-z0-9_]+' | sed 's/.*\$//' | sort -u
   ```

   Todo campo da lista precisa existir na matview. Os que faltarem vão para a equipe
   de dados ou viram correção no Doc.

3. **Configure o Doc localmente:** `<TEMA>_ESTADO_DOCS_URL` no `.env`. Atenção: o
   `config.py` carrega o `.env` com `override=True`, então uma variável exportada no
   terminal **não** vence a do `.env`.

4. **Gere o relatório localmente**, com o túnel do gamma de pé:

   ```bash
   npm run build -w report        # se mexeu em report/src
   .venv/bin/python scripts/atualizar_docs.py   # baixa a versão atual dos Docs
   uvicorn main:app --reload
   curl "http://localhost:8000/relatorio/Para%C3%ADba?macrotema=educacao"
   # PDF em output/relatorio_educacao__para_ba.pdf
   ```

   Depois de `npm run build -w report`, **reinicie o uvicorn**: o servidor node do
   SSR carrega o bundle uma vez, na subida.

5. **Revise o PDF** com a lista da seção seguinte, em mais de um estado. Os
   condicionais mudam de estado para estado.

6. **Configure o ambiente:** o Doc entra no secret `<TEMA>_ESTADO_DOCS_URL` do
   repositório no GitHub, que o `cd-gamma.yaml` passa ao container. Hoje **só o
   gamma** recebe as variáveis estaduais. Beta e prod não têm nenhuma, e o banco do
   beta não tem o schema `auto_relatorios_est`; lá o relatório de estado responde 503.

7. **Depois de editar o Doc**, o relatório só vê a mudança quando o cache for
   atualizado: pelo cron noturno ou rodando `scripts/atualizar_docs.py` à mão (no
   servidor, dentro do container).

## O que revisar no PDF

- **Nenhum `$campo` impresso cru.** Se aparecer, o campo não existe na matview ou
  está escrito diferente.
- **Parágrafos sumidos.** Um condicional que depende de um campo inexistente some
  sem erro.
- **Caixa de Fontes embolada** (tudo num parágrafo, com `#!Conteúdos relacionados`
  cru): o renderer só separa parágrafos onde há linha em branco. Ponha um parágrafo
  vazio entre os títulos e os blocos, e `*` só nos itens de lista, como no Doc
  municipal.
- **Linhas de instrução para quem programa** ("Implementação da síntese: …", "Usar o
  mesmo módulo…", "Exibir a Figura X… somente quando…") saem impressas, porque toda
  linha fora de uma condição é texto do relatório. Elas precisam sair do Doc. Uma
  instrução que cita "Figura X" ainda desalinha a numeração das figuras seguintes.
- **Menções a figuras.** Em tema sem gráficos estaduais, "(Figura X)" some, mas
  "conforme a Figura X" fica no texto. Nos temas com gráficos, a numeração começa
  na Figura 1 (o estado não tem o mapa de localização, que é a Figura 1 do municipal).

## O que ainda não existe no estado

- **Gráficos, fora de Demografia e Educação:** `services/graficos_estado.py` tem,
  por tema, um adaptador que monta a partir das colunas `uf_*` o dicionário que a
  função de `plotting/` já lê; o gráfico sai igual ao municipal. Estão lá
  (12/11/2026): Educação, sem diferença de dado (as 6 faixas de analfabetismo e os
  4 níveis de instrução são os do municipal), e Demografia: pirâmide com as 12 faixas da matview (D9), cor ou raça com os
  percentuais do texto e dinâmica populacional só com 2010 e 2022 (a matview não
  tem 2000). Para outro tema, acrescente a entrada em `GRAFICOS_ESTADO_POR_TEMA`
  com os mesmos placeholders do Doc. A área de interesse ainda não tem gráficos
  (colunas `area_*`).
- **Apresentação, Características Gerais, métricas e mapa da capa:** são municipais.
  Sem eles, o primeiro tema começa logo abaixo do título (`capaTemConteudo.js`); se
  o Doc estadual trouxer o bloco `resumo_cidade`, a capa volta a ter página própria.
- **Fonte e unidade nos cards do Panorama:** só aparecem quando o Doc traz a legenda "fonte • unidade" (Infraestrutura já traz; os outros temas ainda não).
- **CSV de fallback:** o estado só lê a matview.
- **Minas Gerais:** espera a equipe de dados incluí-lo nas matviews.

## Laboratório de Temas (gamma)

O TemaLab aceita `?unidade=estado` e confere o Doc estadual contra um snapshot da
matview, estado por estado (`services/laboratorio_snapshot.py`). É o jeito mais
rápido de ver todos os condicionais nos 9 estados sem gerar 9 PDFs.
