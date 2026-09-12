# CLAUDE.md — Painel Editorial

Guia do painel editorial para quem for continuar o desenvolvimento (pessoa ou agente).
O `CLAUDE.md` da raiz continua valendo: ele descreve o pipeline do relatório, e nada
aqui o substitui. Este arquivo cobre só o painel, que vive em dois lugares:

- `admin/` — a tela (React 18 + Vite), servida em `/painel`.
- `utils/editorial/`, `utils/external/editorial.py`, `services/admin.py` — o backend do
  painel, servido em `/admin/*` e `/manifesto`.

Companheiros, leia em vez de re-derivar:

- `docs/PLANO-PAINEL-EDITORIAL.md` — por que o painel existe, as decisões tomadas uma a
  uma, as fases e o que foi descartado com motivo. A referência de projeto.
- `docs/TESTAR-PAINEL-EDITORIAL.md` — o roteiro de teste manual, passo a passo, do túnel
  SSH até a publicação.
- `admin/src/components/Guia.jsx` — a documentação **do operador**, dentro da própria
  tela. Se a mudança altera o que a pessoa vê, o Guia é parte da mudança.

## O problema que o painel resolve

A prosa dos relatórios mora hoje num Google Doc por macrotema, com condicionais escritas
em português (`Para quando $campo for maior que 10:`) interpretadas por regex em
`utils/render/placeholders.py`. Isso quebra de maneiras que o editor não tem como ver: uma
linha em branco invisível desativa a condição, uma frase reescrita quebra um `re.match`, e
`for maior ou menor que 0%` é lido como `< 0`. O painel troca a frase livre por **dado**:
árvore de blocos tipados, variáveis como chips vindos do manifesto, condição como
formulário.

**Estado:** Fases 0, 1 e 2 implementadas. O Google Doc continua sendo o caminho de
produção — `FONTE_EDITORIAL` é `docs` por padrão, e a migração é um macrotema por vez.

## O caminho de uma edição, ponta a ponta

```
  navegador                      FastAPI                         disco
  ─────────                      ───────                         ─────
  Login ───────────────────► POST /admin/login ──► token HMAC (12 h)
  abre a tela ─────────────► GET /manifesto ─────► information_schema da
                                                   vw_perfil_<tema>  (ou CSV)
  escolhe o tema ──────────► GET /admin/contratos/<slug>
                                                 └► output/contratos/<slug>.json
  edita blocos ────────────► (só no estado do React; nada vai ao servidor)
  Prévia ──────────────────► POST /admin/contratos/<slug>/previa
                                 └► contrato_em_edicao(slug, contrato)
                                    └► gerar_relatorio_handler(...)  ← o relatório real
                                       └► output/relatorio_previa__<tema>__<cidade>.pdf
  Publicar ────────────────► PUT /admin/contratos/<slug>
                                 └► RepositorioDeContratos.publicar (versão +1,
                                    anterior arquivada em historico/)
```

A partir daí, quem lê o contrato publicado é o pipeline do relatório:
`services/generation.py` chama `carregar_texto_editorial`
(`utils/external/editorial.py`), que — conforme a fonte do macrotema — devolve o texto do
Google Doc **ou** renderiza o contrato. Tudo a jusante (renderer, SSR, WeasyPrint) recebe
exatamente o mesmo formato de texto e não sabe de onde ele veio. Esse é o *seam*, e é o que
torna a coisa reversível.

## Mapa dos arquivos

### Backend

| Arquivo | Papel |
| --- | --- |
| `utils/editorial/contrato.py` | A forma do contrato e `validar_contrato`, que devolve **todos** os erros de uma vez |
| `utils/editorial/regras.py` | Operadores nomeados, `avaliar_regra`, `ResultadoRegra` |
| `utils/editorial/render.py` | Contrato + contexto do município → o texto marcado que o pipeline consome |
| `utils/editorial/repositorio.py` | Armazenamento append-only e concorrência otimista |
| `utils/editorial/fontes.py` | A escolha de fonte feita pelo botão do painel (`_fontes.json`) |
| `utils/editorial/manifesto.py` | O payload do `GET /manifesto`: campos, gráficos, operadores, tipos |
| `utils/editorial/importador.py` | Google Doc → contrato, com relatório de divergências provadas |
| `utils/editorial/comparacao.py` | O que conta como "o mesmo texto" ao conferir a importação |
| `utils/external/editorial.py` | O adaptador: decide entre Doc e painel; `contrato_em_edicao` |
| `services/admin.py` | Autenticação, CRUD de contratos, importação, prévia, estado do banco |
| `main.py` | As rotas `/admin/*`, `/manifesto` e o mount de `/painel` |
| `scripts/importar_doc.py` | CLI do importador (`--do-cache`, `--baixar`, `--arquivo`, `--conferir`) |
| `scripts/conferir_paridade.py` | Compara o HTML dos dois caminhos, contexto a contexto |

### Tela

| Arquivo | Papel |
| --- | --- |
| `admin/src/App.jsx` | Orquestra sessão, tema aberto, edição, prévia e publicação |
| `admin/src/api.js` | Cliente HTTP e a sessão no `localStorage` |
| `admin/src/contrato.js` | Manipulação da árvore — funções **puras** sobre uma cópia |
| `admin/src/components/ArvoreDeBlocos.jsx` | A árvore à esquerda: selecionar, mover, remover |
| `admin/src/components/EditorDeBloco.jsx` | O formulário do bloco selecionado |
| `admin/src/components/EditorDeTexto.jsx` | O editor com chips (`contentEditable` não controlado) |
| `admin/src/components/ConstrutorDeRegra.jsx` | Campo, comparação e valor em listas |
| `admin/src/components/PaletaDeVariaveis.jsx` | A lista do que existe, vinda do `/manifesto` |
| `admin/src/components/Previa.jsx` + `VisualizadorDePdf.jsx` | O PDF real, com pdf.js empacotado |
| `admin/src/components/SeletorDeFonte.jsx` | O botão Google Doc ↔ este painel |
| `admin/src/components/EstadoDaConexao.jsx` | Reconfere o túnel sem recarregar a página |
| `admin/src/components/Guia.jsx` | A documentação do operador dentro da tela |
| `admin/src/icones.jsx` | Símbolos copiados do `data-nordeste-frontend` |
| `admin/smoke.jsx` | Renderiza cada componente fora do navegador |

## O contrato

Um JSON por macrotema, em `output/contratos/<slug>.json`. Duas partes:

- **`moldura`** — slots de papel fixo no layout do PDF: `resumo_tema`, `resumo_cidade`,
  `diagnostico_cidade`, `relatorio_geral`, mais `fontes` e a lista `referencias`. O
  operador preenche; não cria nem reordena. Os nomes batem 1:1 com os marcadores que a
  cadeia `extrair_*` de `utils/external/docs.py` fatia hoje — é isso que permite ao
  adaptador emitir texto que o pipeline atual consome sem alteração.
- **`corpo`** — a árvore livre, que vira o `descricao_tema` do macrotema.

```jsonc
{ "id": "p2", "tipo": "paragrafo",
  "regra": {
    "condicoes": [{ "campo": "educacao.matriculas_rede_federal", "op": "maior", "valor": 0 }],
    "sem_dado": { "acao": "texto_alternativo", "texto": "Não há registro de rede federal." }
  },
  "conteudo": [
    { "t": "texto", "v": "O município registrou " },
    { "t": "var", "campo": "educacao.matriculas_total", "formato": { "decimais": 0 } },
    { "t": "texto", "v": " matrículas." }
  ] }
```

Tipos de bloco: `secao` e `caixa` (têm `titulo` e `blocos` filhos), `paragrafo`, `legenda`
e `nota` (têm `conteudo`), `lista` (tem `itens`, lista de listas de trechos) e `grafico`
(tem `grafico`, o nome registrado em `GRAFICOS_AUTO_MARCADOR`).

Operadores: `maior`, `menor`, `maior_igual`, `menor_igual`, `igual`, `diferente`, `entre`,
`existe`, `nao_existe`. As condições compõem sempre com **E** — sem OU e sem aninhamento,
por decisão de escopo. O `valor` pode ser um número, um texto ou **outro campo**
(`{"campo": "educacao.sem_instr_2022"}`), que é a capacidade que o parser dos Docs não tem
e que apagava um parágrafo inteiro de Educação em todo município.

`sem_dado.acao` decide o que acontece quando o campo não tem valor: `esconder` (padrão),
`mostrar` (segue avaliando as outras condições) ou `texto_alternativo`.

## Regras que não se devem amolecer

- **A variável de ambiente é a chave-mestra da fonte editorial.** `FONTE_EDITORIAL_<TEMA>`
  (ou a global `FONTE_EDITORIAL`) decide se o botão do painel tem efeito; só com ela em
  `painel` a escolha registrada em `output/contratos/_fontes.json` vale. Trocar a origem da
  prosa de um relatório público é decisão de operação, não de um clique na tela. A
  precedência está em `fonte_editorial()`, e há teste para ela em
  `tests/test_editorial_fontes.py`.
- **`utils/editorial/render.py` não resolve `$placeholder`.** Ele emite os marcadores e
  deixa `substituir_placeholders` formatar — é lá que moram pt-BR, aliases e percentuais
  derivados. Reimplementar aqui cria divergência entre o que o operador testa e o que sai
  no PDF.
- **Cada bloco da moldura é fechado com `@@`.** `extrair_bloco_marcado` casa de forma
  preguiçosa até `@@` ou até o fim do texto; sem o fechamento, o primeiro marcador engole
  todos os seguintes.
- **Variável sem valor esconde o trecho que depende dela**, e uma seção que perdeu todos os
  filhos perde também o título (`_sem_dado` e o ramo `secao`/`caixa` em `render.py`). Quem
  quiser o trecho mesmo sem o dado escreve a variante e a protege com `sem_dado` — é para
  isso que a ação existe. Um `$sol_predom` cru no relatório de um prefeito é pior do que a
  frase não existir.
- **A prévia é o relatório, não uma renderização paralela.** `previa_handler` chama
  `gerar_relatorio_handler`, o mesmo caminho que atende o portal, com
  `prefixo_artefato="previa__"`. Qualquer atalho aqui responde a uma pergunta diferente da
  que o editor está fazendo — foi assim que a prévia antiga passou a divergir sem ninguém
  notar. O prefixo também é o que impede a prévia de sobrescrever o PDF que o portal serve.
- **`contrato_em_edicao` é um `ContextVar`, não uma global.** O processo atende várias
  requisições ao mesmo tempo: a prévia de um editor não pode vazar para o relatório que
  outra pessoa está gerando no mesmo instante.
- **O manifesto lê `information_schema`, nunca a `vw_perfil_*`.** As views são agregações
  pesadas e listar colunas não pode custar um scan (mesma razão do guard de `SELECT *` no
  `CLAUDE.md` da raiz).
- **O manifesto degrada como o relatório degrada:** view → CSV → o que o contrato e o Doc
  em cache já usam. Cada lista carrega sua `origem` e seu `aviso`, porque o painel precisa
  abrir com o túnel fora do ar.
- **`validar_contrato` devolve todos os erros de uma vez**, em vez de levantar no primeiro:
  quem consome é a tela, que precisa mostrar tudo o que falta corrigir.
- **Publicar é append-only e otimista.** A versão anterior vai para
  `output/contratos/historico/<slug>/<versao>.json`, a nova é escrita num `.tmp` e
  renomeada, e uma publicação a partir de versão vencida vira 409 com quem publicou o quê.
- **Sem `PAINEL_SENHA` o painel não abre** (503). Falhar fechado é a escolha certa: o que se
  edita ali sai publicado. Não há papéis — quem entra, edita e publica; o nome serve só para
  preencher `publicado_por`.
- **O rótulo de um campo é o nome cru da coluna** (`pri_nivel_per`, não "Pri nivel per").
  Quem opera o painel conversa direto com quem mantém as views e precisa citar o
  identificador que a outra pessoa reconhece.

## Comandos

```bash
npm install
npm run build -w admin        # gera admin/dist; sem isso /painel responde 503
npm run dev -w admin          # Vite em :5174 (o CORS do main.py já libera essa porta)
npm run smoke -w admin        # renderiza cada componente fora do navegador

uvicorn main:app --reload --host 0.0.0.0 --port 8000   # a tela fica em /painel

python -m pytest tests/test_editorial_*.py tests/test_previa_*.py tests/test_admin_conexao.py -q
ruff check .

python scripts/importar_doc.py --macrotema demografia --do-cache --conferir
python scripts/conferir_paridade.py --macrotema educacao --detalhar
```

Para editar o `.env`, use um editor de verdade — **não** `echo >> .env`: se o arquivo não
terminar em quebra de linha, a variável nova gruda na última e as duas param de ser lidas.

### Validação antes de fechar uma mudança

- `ruff check .` — sempre.
- `python -m pytest` — o painel tem 128 testes espalhados por `tests/test_editorial_*.py`,
  `tests/test_previa_*.py` e `tests/test_admin_conexao.py`; nenhum toca o banco. O CI **não**
  roda pytest, então rodar é o único gate.
- `npm run smoke -w admin` — depois de mexer em qualquer componente. Não substitui olhar a
  tela (não roda efeitos nem eventos), mas pega prop que virou `undefined` e tipo de bloco
  que ninguém tratou.
- `npm run build -w admin` — a API serve `admin/dist`, não o código-fonte. Sem o build, a
  tela que você abrir é a anterior.
- O uvicorn **sem `--reload`** importa os módulos uma única vez: depois de editar `.py`,
  confira com `ps -eo pid,lstart,cmd | grep uvicorn` em vez de supor que a mudança entrou.

## Receitas

**Um operador novo de regra.** `OPERADORES_BINARIOS` e `ROTULOS_OPERADORES` em
`utils/editorial/regras.py`; o manifesto passa a expô-lo com a aridade certa e o
`ConstrutorDeRegra` o mostra sem nenhuma alteração no front — a tela é burra de propósito.
Teste em `tests/test_editorial_regras.py`.

**Um tipo novo de bloco.** `TIPOS_DE_BLOCO` e a validação em `contrato.py`, o ramo
correspondente em `render.py`, `TIPOS_CRIAVEIS` e `blocoVazio` em `admin/src/contrato.js`,
o formulário em `EditorDeBloco.jsx`, a opção no `TrocadorDeTipo` (`App.jsx`) e um caso em
`smoke.jsx`.

**Um endpoint novo.** Handler em `services/admin.py`, rota em `main.py` com
`Depends(editor_autenticado)`, método em `admin/src/api.js`. Rota sem a dependência é rota
pública — o `/manifesto` é assim de propósito, porque só publica vocabulário.

**Trocar o armazenamento para Postgres.** Mexe em `RepositorioDeContratos` e em
`fontes.py`, e em mais nada: o adaptador, a tela e o pipeline conversam com a interface.
Quando for a hora, o schema é separado, como todo objeto que este time cria no banco do
Data Nordeste.

**Migrar um macrotema para o painel.** Importar do Doc → revisar as divergências → publicar
→ conferir a prévia em municípios de perfis diferentes → `FONTE_EDITORIAL_<TEMA>=painel` no
servidor → alternar o botão. `scripts/conferir_paridade.py` é o critério de aceite; o
relatório de divergências de cada tema está em `output/contratos/<slug>.divergencias.md`, e
toda divergência medida até aqui é o caminho novo mostrando o que o editor escreveu e o
antigo não mostrava.

## Vocabulário

Estes termos aparecem no código, na API e na tela, sempre com o mesmo sentido — vale
mantê-los em qualquer coisa nova:

**contrato** (o JSON de um macrotema) · **moldura** e **corpo** (as duas partes) ·
**bloco** (um nó da árvore) · **trecho** (`{t:"texto"}` ou `{t:"var"}`, o conteúdo de uma
linha) · **chip** (a variável na tela) · **regra** (as condições que decidem se o bloco
aparece) · **fonte editorial** (Google Doc ou painel) · **divergência** (um ponto em que o
contrato não reproduz o comportamento do Doc) · **manifesto** (o vocabulário que o servidor
publica) · **prévia** (o relatório gerado com o contrato ainda não publicado).

O texto da tela é escrito para o **operador**, não para quem desenvolve: ele fala do que a
pessoa vê e das decisões que ela toma. Nome de variável de ambiente, arquivo e endpoint
aparecem só nas notas técnicas, separadas de propósito para poderem sumir no primeiro dia
em que alguém de fora do time usar a ferramenta.

## O que ainda falta

- **Persistência no Postgres.** O artefato ainda vive em `output/contratos/`.
- **Desfazer pela tela.** O histórico é gravado e legível pela API
  (`GET /admin/contratos/{slug}/historico` e `.../versoes/{versao}`), mas não há botão.
- **Arrastar para reordenar.** Hoje é seta para cima e para baixo — funciona no teclado, mas
  é lento numa árvore grande.
- **Fase 3** — gráficos e seções como estrutura de verdade, aposentando a inserção por regex
  de legenda (`GRAFICOS_AUTO_MARCADOR`) no caminho novo.
- **Fase 4** — migrar os macrotemas restantes e desligar o caminho Google Docs.
