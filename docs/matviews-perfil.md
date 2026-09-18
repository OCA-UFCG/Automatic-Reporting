# Materialized views das views de perfil pesadas

## Problema

O gerador lê **uma linha por município** de cada `relatorios_auto.vw_perfil_<tema>` a cada
relatório. Algumas dessas views são agregações caras, recalculadas do zero a cada leitura.
Medições no banco de produção (município Campina Grande/PB, `EXPLAIN ANALYZE`):

| Macrotema | View | Tempo de leitura |
|---|---|---|
| **economia-renda** | `vw_perfil_economia` | **> 30 s** 🔴 |
| **saúde** | `vw_perfil_saude_municipal` | **~11,6 s** 🔴 |
| educação | `vw_perfil_educacional_municipal` | ~2,6 s 🟡 |
| demografia | `vw_perfil_populacional_municipal` | ~0,5 s |
| meio-ambiente | `ambiente` | ~0,18 s |
| saneamento | `vw_perfil_infraestrutura_municipal` | < 0,1 s |
| hidráulica | `vw_seguranca_hidrica` | < 0,1 s |

A economia (>30s) chega a pendurar o worker único do uvicorn e a estourar o
`statement_timeout` (caindo no CSV). A causa é o desenho das views (agregações globais que
não são podadas pelo filtro de município) — não há edit em Python que as acelere.

## Solução: materializar as views lentas

Uma `MATERIALIZED VIEW` roda a consulta pesada **uma vez** e guarda o resultado em disco;
as leituras seguintes só leem a tabela pronta (~ms). Ela é um **snapshot**: precisa de um
`REFRESH` para atualizar. Como os dados por trás são anuais (mudam raramente), um refresh
diário/pós-carga é suficiente.

**Exemplo medido (economia):** build 93 s · 2074 linhas · ~2,8 MB (heap + índice único) ·
leitura por município **1,8 ms** (era > 30 s) — ganho de ~17.000×.

### Regra de decisão (o que materializar e o que NÃO)

Materialize uma view **apenas** quando a **leitura fria** for lenta a ponto de quebrar algo
(travar o worker, estourar timeout) **e** o dado for estável. O custo de uma matview não é
espaço (é ínfimo) — é **operacional**: cada uma vira um `REFRESH` para coordenar, um risco
de dado velho (staleness) e um objeto de schema a manter.

- ✅ **Materializar:** `vw_perfil_economia`, `vw_perfil_saude_municipal`.
- 🟡 **Opcional:** `vw_perfil_educacional_municipal` (2,6 s — tolerável).
- ❌ **Não materializar** as rápidas (< 0,5 s): trocar leitura fresca por leitura possivelmente
  velha, sem ganho perceptível. O cache de queries em memória (`utils/queries/base.py`) já
  torna instantâneas as **repetições** de qualquer view.

> **Transversal materializada (não é perfil):** `mv_indicadores` — snapshot de
> `relatorios_auto.vw_indicadores` (agregação país-inteira, ~39k municípios, ~14s
> por chamada; leitura por município cai a ~15ms materializada). Índice único em
> `cd_mun` — não `(nm_mun, sigla_uf)` como as `mv_perfil_*`, porque não é view de
> perfil. DDL em `db/2026-09-17-mv_indicadores.sql`; refresh no mesmo
> `scripts/refresh_matviews.sh` (array `MATVIEWS`). Consumida por
> `utils/queries/indicadores.py` (`buscar_indicadores_municipio`).
>
> Candidata separada (não é perfil): `eco_importacao.vw_importacao_completa` (~1,8 s) — a próxima
> mais lenta no relatório de economia, se um dia valer a pena apertar mais.

## Convenções

- **Nome:** `mv_perfil_<tema>` no schema `relatorios_auto` (ex.: `mv_perfil_economia`,
  `mv_perfil_saude_municipal`, `mv_perfil_educacional_municipal`).
- **Índice único obrigatório** em `(nm_mun, sigla_uf)` — é o que habilita
  `REFRESH ... CONCURRENTLY` (refresh sem bloquear as leituras).

## Estratégia de refresh

- **Diário, via cron na VM.** A VM roda em **UTC**, então **01:00 BRT = 04:00 UTC**:
  ```cron
  # Refresh das matviews de perfil — 04:00 UTC = 01:00 America/Sao_Paulo
  0 4 * * *  /caminho/para/Automatic-Reporting/scripts/refresh_matviews.sh
  ```
- **On-demand,** logo após uma carga de dados nova:
  ```bash
  scripts/refresh_matviews.sh
  ```
  O mesmo script serve aos dois usos. Ele faz `REFRESH ... CONCURRENTLY` de cada matview,
  com **lock** (não se sobrepõe a outra execução), **statement_timeout** de segurança e
  **log com timestamp** (`~/logs/refresh_matviews.log`, ou `/tmp` como fallback). Uma falha
  numa matview não aborta as demais.

## Como adicionar uma nova matview

1. **Criar e popular** (build pesado — faça com o banco calmo, monitorando memória):
   ```sql
   CREATE MATERIALIZED VIEW relatorios_auto.mv_perfil_<tema> AS
     SELECT * FROM relatorios_auto.vw_perfil_<tema>;
   ```
2. **Índice único** (habilita o CONCURRENTLY):
   ```sql
   CREATE UNIQUE INDEX ux_mv_perfil_<tema> ON relatorios_auto.mv_perfil_<tema> (nm_mun, sigla_uf);
   ```
   (confirme antes que `(nm_mun, sigla_uf)` é único na saída da view.)
3. **Adicionar o nome** ao array `MATVIEWS` em `scripts/refresh_matviews.sh`.
4. **Apontar o app** para a matview em `utils/queries/perfil_municipal.py`
   (`VIEW_POR_MACROTEMA`), trocando `vw_perfil_<tema>` por `mv_perfil_<tema>`.

## Ordem importa (para não servir dado vazio)

Crie a matview + índice **e** deixe o refresh configurado **antes** de apontar o app para ela.
Assim o app nunca lê uma matview ainda não populada/atualizada. O passo 4 (wiring) é o que de
fato entrega o ganho ao usuário — e é uma mudança de comportamento do app, então vai em PR
próprio.

## Tradeoff (staleness)

A matview mostra os números do **último refresh**. Entre refreshes, ela não reflete mudanças
na origem. Para dados anuais isso é irrelevante; se algum dia uma dessas fontes passar a mudar
com frequência, reavaliar o intervalo de refresh (ou voltar à view viva).
