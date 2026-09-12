# Plano — Painel Editorial (substituir a autoria em Google Docs)

Status: **Fases 0, 1 e 2 implementadas** (ver §10). Resultado de uma sessão de decisão
conduzida com Marcelo Delazari. Cada decisão abaixo foi tomada explicitamente; o que
ficou em aberto está na seção _Deixado para depois_.

O caminho Google Docs continua sendo o de produção: o painel só é usado quando
`FONTE_EDITORIAL` é ligado, por macrotema, e o padrão é `docs`.

---

## 1. O problema, medido

A prosa editorial vive hoje em um Google Doc por macrotema, com uma linguagem de
template ad-hoc interpretada por regex em `utils/render/placeholders.py`. Os números
do corpus real (extraídos de `output/docs_cache/`):

| Métrica | Valor |
| --- | --- |
| Texto editorial total | ~56 KB em 9 documentos |
| Condicionais reais | ~25 |
| Placeholders distintos | 94 (economia), 68 (demografia), 51, 42, 41… |
| Marcadores de bloco | 8 (`resumo_tema`, `descricao_tema`, `diagnostico_cidade`, `referencia`, `relatorio_geral`, `resumo_cidade`, `resumo_relatorio`, `apresentacao`) |
| Macrotemas cujo corpo é **um único bloco** | 8 de 8 — toda a prosa está dentro de `descricao_tema` |

O corpus é pequeno. Isso é a notícia boa do plano: **migrar é questão de dias.**

### 1.1 Por que o formato custa caro (evidência)

**a) O Doc dita o esquema do banco.** Commit `61b3aab`: _"reverte rename de
`n_estabel_maior1/2` — template usa grafia com 'ec'"_. Uma correção de digitação numa
coluna teve de ser desfeita porque o Doc tinha a grafia errada. A dependência está
invertida.

**b) As condicionais já custaram um ciclo de revert.** PR #83 → `df7c811 Revert` →
PR #84 → PR #85 (`fix/demografia-editorial-conditions-v2`). Mais `89d33f9` (vírgula
decimal no Gini), `4189534` (regex de namespace + operadores de faixa), `5742bdb`
(condição vazando para o conteúdo seguinte).

**c) O Python casa regex contra as frases do editor.**
`utils/render/placeholders.py:166-180` identifica parágrafos pelas palavras com que o
editor os começou:

```python
if re.match(r"^quanto à população (autodeclarad[ao]\s+)?quilombola", limpa.casefold()):
    bloco_ativo = bloco_populacoes_ativo
```

Reescrever "Quanto à população quilombola…" como "No que se refere à população
quilombola…" quebra o relatório em silêncio. Logo abaixo há um **parágrafo inteiro de
prosa escrito em Python** como fallback do caso "população em situação de rua": hoje o
texto editorial mora em dois lugares.

**d) As condicionais do Doc estão quebradas de cinco maneiras distintas.** Cada
item abaixo foi verificado executando o pipeline real contra os nove documentos
em cache, e cada um aparece nomeado em `output/contratos/<tema>.divergencias.md`:

| Defeito | O que acontece hoje | Onde |
| --- | --- | --- |
| **Comparação entre campos não existe** | `Para quando $sem_instr_2000 for igual a $sem_instr_2022:` — o parser só compara `$campo` com um número literal. A condição falha sempre e **o parágrafo não sai em município nenhum**. | Educação (2) |
| **Condicional inerte** | A linha em branco que a exportação do Docs põe depois da instrução reativa o bloco (`aguardando_fim_de_bloco_simples`) antes de ele chegar ao parágrafo. A condição não vale, e **as duas variantes mutuamente exclusivas saem juntas**. | Demografia (4), Economia (4) |
| **Condicional engole estrutura** | Sem linha em branco, a condição continua valendo sobre as linhas seguintes e leva junto títulos de caixa e legendas quando é falsa. | Desenv. Social (2) |
| **Operador ausente ou trocado** | `for negativo`, `for positivo`, `for 0%` não têm operador. E `for maior ou menor que 0%` (= "≠ 0") casa com a regex de `menor que 0`. | Demografia (4) |
| **Título perde o destaque** | Um título colado no parágrafo anterior, sem linha em branco, sai como `<p>` de texto corrido em vez de `<h2>`. | Saneamento, Hídrica, Desenv. Social (1 cada) |

O padrão é o mesmo nos cinco: **o comportamento do relatório depende de espaços
em branco invisíveis e de frases exatas**, coisas que o editor não tem como ver
nem controlar. O primeiro item é o mais caro — foi introduzido por uma edição
legítima do Doc de Educação e apaga um parágrafo inteiro de todos os relatórios
do tema, sem erro nem aviso em lugar nenhum.

Há ainda um sexto caso, de natureza diferente: **prosa editorial escrita em
Python.** `utils/render/placeholders.py` decide por `re.match` na primeira frase
do parágrafo de população em situação de rua e emite, do próprio código, duas
versões alternativas do texto. Hoje o texto editorial mora em dois lugares.

---

## 2. Decisões tomadas

| # | Decisão | Escolha |
| --- | --- | --- |
| Escopo | O que o painel controla | **Relatório inteiro**: seções, ordem, gráficos, legendas, prosa |
| Formato | Contrato do documento | **Árvore de blocos tipados em JSON** |
| Regras | Granularidade | **Qualquer bloco** pode ter regra; seção é um bloco que contém outros e herda a regra |
| Regras | Composição | Lista de condições combinadas com **E** (sem OU, sem aninhamento) |
| Variáveis | Inserção no texto | **Chip tipado** vindo da lista lateral — nunca `$campo` digitado |
| Variáveis | Formatação | Padrão do manifesto, com override opcional por chip |
| Dados ausentes | Comportamento | Texto alternativo definido pelo operador; padrão = esconder o bloco |
| Template | Abrangência | **Global por macrotema** (sem override por município) |
| Autoridade | Campos e gráficos disponíveis | Endpoint **`/manifesto`** servido pelo FastAPI; o painel é burro |
| Armazenamento | Onde o conteúdo mora | **Postgres, schema separado, `jsonb`**, append-only |
| Entrega | Como o FastAPI lê | O painel **publica um artefato JSON versionado**; o FastAPI busca e cacheia |
| Preview | Fidelidade | **Renderização real** (reusa o SSR existente); modo rápido só depois |
| Auth | Modelo | Login simples, **sem papéis**; poucas pessoas, todas escrevem e publicam |
| Stack | Onde a tela mora | Novo workspace **`admin/`** neste repo, React, servido pelo próprio FastAPI |
| Piloto | Ordem | **Educação** para construir, **Demografia** para provar |
| Convivência | Isolamento | Flag por macrotema + cópia do Doc; nada existente é tocado |

Descartados com motivo: Contentful (a árvore ou vira grafo de entries com cascata de
publicação, ou vira um blob JSON — e aí o CMS é só storage caro; o SAP precisou de 503
linhas de encanamento em `contentfulManagement.ts` para conviver com a Management API);
markdown estendido (reinventa o parser que estamos eliminando); rich text WYSIWYG
(otimiza para prosa bonita quando o gargalo é acertar campo e condição); rota protegida
dentro do `data-nordeste-frontend` (põe login num portal que deliberadamente não tem).

---

## 3. Arquitetura

```
   ┌──────────────────────────┐        GET /manifesto
   │  admin/  (React, novo)   │◄────────────────────────┐
   │  - escolhe macrotema     │                         │
   │  - monta seções          │   POST /admin/publicar  │
   │  - arrasta variáveis     │────────────┐            │
   │  - define regras         │            │            │
   └──────────────────────────┘            ▼            │
                                ┌─────────────────────┐ │
                                │ Postgres            │ │
                                │ schema editorial_*  │ │
                                │ append-only, jsonb  │ │
                                └──────────┬──────────┘ │
                                           │ publica    │
                                           ▼            │
                                ┌─────────────────────┐ │
                                │ artefato JSON       │ │
                                │ versionado          │ │
                                └──────────┬──────────┘ │
                                           │            │
   ┌───────────────────────────────────────▼────────────┴──────┐
   │ utils/external/editorial.py   (ADAPTADOR — o seam)         │
   │   FONTE_EDITORIAL=docs    → caminho atual, intacto         │
   │   FONTE_EDITORIAL=painel  → lê o artefato, resolve regras  │
   └───────────────────────────────┬────────────────────────────┘
                                   ▼
        services/generation.py → renderer.py → SSR → WeasyPrint
                          (INALTERADOS na Fase 1)
```

### 3.1 O seam exato

A fronteira já existe e é estreita:

- `utils/external/docs.py:294` — `carregar_texto_do_docs(link_ou_id) -> str` é o **único**
  ponto de entrada do texto.
- `services/generation.py:905-964` — a cadeia de `extrair_*(texto) -> (bloco, resto)`
  fatia esse texto nos 8 blocos do macrotema.
- `services/generation.py:534-636` — a mesma cadeia para os blocos do relatório geral/capa.

O adaptador novo (`utils/external/editorial.py`) expõe uma função com a mesma forma de
saída que essa cadeia produz hoje:

```python
def carregar_blocos_editoriais(macrotema_slug: str, contexto: dict) -> BlocosEditoriais:
    """Devolve os blocos já resolvidos (regras avaliadas, chips substituídos).

    Duas implementações atrás da flag FONTE_EDITORIAL: 'docs' delega para a
    cadeia extrair_* atual; 'painel' lê o artefato publicado.
    """
```

**Decisão de fase importante:** na Fase 1 o caminho novo emite **texto no mesmo formato
que o renderer já consome** — condicionais resolvidas, chips já substituídos por valores
formatados. Consequências:

- `renderer.py`, `GRAFICOS_AUTO_MARCADOR`, SSR e PDF ficam **intocados**.
- A paridade vira comparável byte a byte, que é o critério do Q7.
- `interpretar_blocos_condicionais` deixa de ser chamada no caminho novo — as ~180 linhas
  de máquina de estado (`bloco_populacoes_ativo`, `bloco_rua_ativo`, regex de Gini, regex
  de frase quilombola) só rodam no caminho Docs.

Só na Fase 3 os gráficos viram nós explícitos e a regex de legenda sai de cena.

---

## 4. O contrato

```jsonc
{
  "versao_contrato": 1,
  "macrotema": "educacao",
  "versao": 7,
  "publicado_em": "2026-09-11T14:02:00Z",
  "publicado_por": "marcelo.delazari@lsd.ufcg.edu.br",

  // Moldura: campos fixos, com papel no layout do PDF. O operador preenche, não cria.
  "moldura": {
    "resumo_tema":        { "blocos": [ /* … */ ] },
    "diagnostico_cidade": { "blocos": [ /* … */ ] },
    "referencias":        [ "IBGE, Censo 2022", "INEP, Censo Escolar 2023" ]
  },

  // Corpo: o operador cria, reordena e apaga à vontade.
  "corpo": { "blocos": [

    { "id": "s1", "tipo": "secao", "titulo": "Matrícula e rede", "regra": null,
      "blocos": [

        { "id": "p1", "tipo": "paragrafo", "regra": null,
          "conteudo": [
            { "t": "texto", "v": "Em " },
            { "t": "var", "campo": "educacao.ano_censo" },
            { "t": "texto", "v": ", o município registrou " },
            { "t": "var", "campo": "educacao.matriculas_total",
              "formato": { "decimais": 0, "milhar": true } },
            { "t": "texto", "v": " matrículas." }
          ] },

        { "id": "p2", "tipo": "paragrafo",
          "regra": {
            "condicoes": [
              { "campo": "educacao.matriculas_rede_federal", "op": "maior", "valor": 0 }
            ],
            "sem_dado": { "acao": "texto_alternativo",
                          "texto": "Não há registro de rede federal no município." }
          },
          "conteudo": [ /* … */ ] },

        { "id": "g1", "tipo": "grafico", "grafico": "grafico_matriculas_rede",
          "legenda": "Matrículas por rede de ensino" }
      ] }
  ] }
}
```

### 4.1 Operadores

Derivados de `_OPERADORES_EDITORIAIS` (`placeholders.py:21-32`), agora nomeados em vez
de frase livre:

`entre` (a, b) · `maior_igual` · `menor_igual` · `maior` · `menor` · `igual` ·
`diferente` · `existe` · `nao_existe`

`existe`/`nao_existe` cobre o caso de `_CAMPOS_NULL_SENSIVEIS` (`centro_pop`, `n_uc`),
onde ausência de dado ≠ zero. E `diferente` resolve corretamente o
`maior ou menor que 0%` que hoje é lido como `< 0`.

### 4.2 Concorrência

Poucas pessoas, sem papéis (decidido), mas edição simultânea precisa ser segura:
**concorrência otimista** — cada salvamento carrega a `versao` que leu; se divergiu, o
painel recusa e mostra o que mudou. Sem lock, sem edição colaborativa ao vivo.

---

## 5. O manifesto

`GET /manifesto` — servido pelo FastAPI, é a única fonte de verdade sobre o que o
operador pode usar. Mata a classe de bug do `n_estabel_maior1`: renomear coluna passa a
quebrar a **validação no painel**, não o PDF em produção.

```jsonc
{
  "macrotemas": [
    { "slug": "educacao", "nome": "Educação", "cor": "#…", "secao": 2 }
  ],
  "campos": {
    "educacao": [
      { "campo": "matriculas_total", "rotulo": "Matrículas (total)",
        "tipo": "inteiro", "origem": "relatorios_auto.vw_perfil_educacao",
        "formato_padrao": { "decimais": 0, "milhar": true },
        "exemplo": 12347, "cobertura": 0.98 }
    ]
  },
  "graficos": {
    "educacao": [ { "nome": "grafico_matriculas_rede",
                    "rotulo": "Matrículas por rede",
                    "exige": ["matriculas_rede_municipal", "matriculas_rede_estadual"] } ]
  },
  "tipos_de_bloco": ["secao", "paragrafo", "lista", "grafico", "mapa", "nota"]
}
```

`cobertura` (fração de municípios com valor não-nulo) é o que permite ao painel avisar
"esta variável falta em 12% das cidades" **antes** de publicar.

---

## 6. Fases

Cada fase entrega algo verificável e nenhuma delas altera o caminho de produção até a 4.

### Fase 0 — Contrato e importador, sem UI
Definir o schema; escrever `scripts/importar_doc.py` que converte o `.txt` exportado
para o contrato; rodar contra **Demografia** (o pior caso: 16 condicionais, blocos
indígena/quilombola/rua). O importador **não replica bugs** — quando encontrar
`for negativo` / `for positivo` / `for 0%`, emite a regra correta e registra num relatório
de divergências.
- **Pronto quando:** Demografia converte com relatório de divergências revisado, e os
  casos que não couberem no modelo estiverem listados nominalmente.
- **Por que primeiro:** se o modelo não aguentar Demografia, descobre-se na semana 1.

### Fase 1 — Adaptador, flag e paridade
`utils/external/editorial.py` + `FONTE_EDITORIAL` por macrotema. Servir **Educação** a
partir do contrato importado.
- **Pronto quando:** o PDF de Educação gerado com `FONTE_EDITORIAL=painel` for
  equivalente ao gerado com `docs`, em ao menos 20 municípios de perfis distintos,
  com as diferenças justificadas uma a uma.

### Fase 2 — A tela
Workspace `admin/`: escolher macrotema → editar moldura e corpo → lista de variáveis do
manifesto → chips → construtor de regras → preview real → publicar. Auth simples.
- **Pronto quando:** um editor produzir uma alteração em Educação de ponta a ponta sem
  pedir ajuda a um dev. Esse é o critério do Q7, e é o único que importa.

### Fase 3 — Gráficos e seções como estrutura
Nós de gráfico explícitos; aposenta `GRAFICOS_AUTO_MARCADOR` no caminho novo. Seções
livres no corpo.

### Fase 4 — Migração e desligamento
Demais macrotemas, um a um, com a flag. Docs só é desligado quando o último migrar.

---

## 7. Como isto não atrapalha quem está nos Docs

Nos últimos 60 dias houve commit em **todos** os macrotemas (Rayane, André, Raína,
Marcelo). Não existe canto vazio — então o isolamento vem da estrutura, não da escolha
do tema:

**Criado (nada existente é tocado):** `admin/` · `utils/external/editorial.py` ·
`scripts/importar_doc.py` · schema novo no Postgres · rota `/manifesto` ·
`tests/test_editorial_*.py`

**Alterado, e o mínimo:** `services/generation.py` (uma chamada passa pelo adaptador) ·
`config.py` (a flag) · `main.py` (registrar as rotas novas)

**Intocado:** `utils/render/placeholders.py` · `utils/render/renderer.py` ·
`utils/external/docs.py` · `utils/queries/**` · `plotting/**` · `report/**` · `frontend/**`

O Doc de Educação é **copiado**, não movido. Ninguém perde acesso a nada.

---

## 8. Riscos

| Risco | Mitigação |
| --- | --- |
| A paridade da Fase 1 falha porque o Doc tem bugs que o contrato corrige | O relatório de divergências da Fase 0 pré-declara cada diferença esperada — divergência prevista não é falha |
| O modelo de regras não cobre um caso editorial real | Fase 0 roda contra o pior caso antes de qualquer código de UI |
| Validar cobertura contra 1.800 municípios fica lento | Amostra estratificada (por porte e UF), não a base inteira |
| Dois editores salvam ao mesmo tempo | Concorrência otimista por `versao` (§4.2) |
| O painel vira mais um sistema para manter | O manifesto mantém o painel burro; toda evolução de dados continua acontecendo em Python |

---

## 9. Deixado para depois

- Texto específico por município (schema prevê, não se implementa).
- Comentários e sugestões, fluxo de aprovação, papéis — dispensados explicitamente.
- Trocar Postgres por Contentful: possível trocando só o adaptador, porque a entrega é
  um artefato JSON e não um acoplamento direto.
- Corrigir os operadores quebrados no caminho Docs (`negativo`, `positivo`, `0%`,
  `maior ou menor que`) — decisão do time, independente deste plano.

---

## 10. O que já está implementado

### Fase 0 — contrato e importador ✅

| Arquivo | Papel |
| --- | --- |
| `utils/editorial/contrato.py` | Forma do contrato e validação (devolve **todos** os erros de uma vez, porque quem consome é o painel) |
| `utils/editorial/regras.py` | Operadores nomeados, avaliação e validação de regra |
| `utils/editorial/render.py` | Contrato + contexto → o mesmo texto marcado que o pipeline já consome |
| `utils/editorial/importador.py` | Doc → contrato, com relatório de divergências |
| `utils/editorial/comparacao.py` | O que conta como "o mesmo texto" para este pipeline |
| `scripts/importar_doc.py` | CLI do importador, com `--conferir` |

Os **oito macrotemas** importam sem perder uma linha sequer do Doc. O único
acréscimo é em Demografia: os dois parágrafos que hoje moram no Python passam a
ser blocos do contrato.

### Fase 1 — adaptador, flag, manifesto e paridade ✅

| Arquivo | Papel |
| --- | --- |
| `utils/external/editorial.py` | O adaptador. `FONTE_EDITORIAL[_<TEMA>]` escolhe entre Doc e painel |
| `utils/editorial/manifesto.py` | `GET /manifesto` — campos, gráficos, operadores, tipos de bloco |
| `scripts/conferir_paridade.py` | Compara o **HTML** dos dois caminhos, contexto a contexto |
| `tests/test_editorial_*.py` | 61 testes, nenhum toca o banco |

Alterações fora do código novo, e só estas:

- `services/generation.py` — uma chamada (`carregar_texto_do_docs` → `carregar_texto_editorial`) e o guard de `docs_url`, que agora só vale no caminho Docs.
- `utils/render/placeholders.py` — **15 linhas aditivas**: um curto-circuito quando o contexto traz `_fonte_editorial = painel`. Não é otimização: a máquina de estado também reage ao *conteúdo* do parágrafo, e aplicá-la a um texto do painel reescreveria prosa que o operador escreveu.
- `config.py`, `.env.example`, `main.py` — a flag e a rota.

**Intocados**, como prometido: `utils/render/renderer.py`, `utils/external/docs.py`,
`utils/queries/**`, `plotting/**`, `report/**`, `frontend/**`.

### Paridade medida

`conferir_paridade.py` compara o HTML final — depois de condicionais, placeholders
e gráficos — sobre um contexto por ramo de regra:

| Macrotema | Contextos divergentes | Explicação |
| --- | --- | --- |
| Saúde, Meio Ambiente | **0** | paridade total |
| Saneamento, Hídrica | 1 | título que hoje perde o `<h2>` |
| Educação | 4 | a comparação entre campos que hoje apaga um parágrafo |
| Desenv. Social | 4 | condicional engolindo `#!Conteúdos relacionados` |
| Economia | 7 | 4 condicionais inertes |
| Demografia | 25 | 4 inertes + 4 operadores + a prosa vinda do Python |

Toda divergência é rastreável a um item nomeado no relatório do tema. **Nenhuma é
regressão**: em todas, o caminho novo mostra o que o editor escreveu e o caminho
atual não mostra.

### Fase 2 — a tela ✅

Workspace `admin/`, React 18 + Vite, nas mesmas convenções do `frontend/`.
Servida pelo próprio FastAPI em **`/painel`**; a API fica em `/admin/*`.

| Arquivo | Papel |
| --- | --- |
| `utils/editorial/repositorio.py` | Armazenamento append-only, com concorrência otimista por `versao` |
| `services/admin.py` | Autenticação, CRUD dos contratos, importação e prévia |
| `admin/src/App.jsx` | Orquestra sessão, tema, edição, publicação |
| `admin/src/contrato.js` | Manipulação da árvore (inserir, mover, remover), funções puras |
| `admin/src/components/EditorDeTexto.jsx` | O editor com **chips** — variáveis como objetos, nunca `$campo` digitado |
| `admin/src/components/ConstrutorDeRegra.jsx` | Campo, comparação e valor em listas; `Para quando ... :` vira dado |
| `admin/src/components/PaletaDeVariaveis.jsx` | A lista do que existe, vinda do `/manifesto` |
| `admin/src/components/Previa.jsx` | Renderização com o renderer real, e a lista de campos sem valor |
| `admin/smoke.jsx` | Renderiza cada componente fora do navegador (`npm run smoke -w admin`) |

O que a tela garante, e o Doc não garantia:

- **Variável errada deixa de existir.** O chip vem da lista do manifesto; não há
  como digitar `n_estabel_maior1` com a grafia errada.
- **Condição é formulário, não frase.** Some a classe inteira de defeito medida
  em §1.1 — não há linha em branco que desative uma regra, nem frase que o
  parser não entenda.
- **Comparar dois campos existe.** É o que o Doc de Educação pediu e não tinha.
- **A prévia diz o que vai faltar.** Lista os campos sem valor para o município
  escolhido — cada um é um placeholder que sairia cru no PDF.
- **Duas pessoas não se sobrescrevem.** Quem publica a partir de uma versão
  vencida recebe 409 com quem publicou o quê, e um botão para recarregar.
- **Nada se perde.** Toda publicação arquiva a versão anterior em
  `output/contratos/historico/`.

Autenticação: senha compartilhada em `PAINEL_SENHA`, sessão assinada por HMAC,
válida por 12 horas. Sem papéis, como decidido. Sem `PAINEL_SENHA` o painel
**não abre** — falha fechada, porque o que se edita ali sai publicado.

Para subir:

```bash
npm install && npm run build -w admin   # sem isto, /painel responde 503 explicando
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A tela fica em `http://localhost:8000/painel`. Edite o `.env` num editor para
acrescentar `PAINEL_SENHA` — **não** use `echo >> .env`: se o arquivo não
terminar em quebra de linha, a variável nova gruda na última e as duas param de
ser lidas.

### O que falta

- **Persistência no Postgres.** O artefato ainda vive em `output/contratos/`.
  O `RepositorioDeContratos` já isola o acesso: a troca para o schema próprio
  mexe só nessa classe. Ficou para depois de propósito — sem o túnel do banco
  no ar, escrever a versão SQL seria código não testado.
- **Desfazer pela tela.** O histórico é gravado e legível pela API
  (`GET /admin/contratos/{slug}/historico`), mas a tela ainda não oferece o
  botão de restaurar.
- **Arrastar para reordenar.** Hoje é seta para cima e para baixo — funciona em
  teclado e não depende de mouse, mas é mais lento numa árvore grande.
- **Fases 3 e 4** como descritas acima.
