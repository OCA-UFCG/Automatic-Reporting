-- Três tabelas grandes sem índice nenhum em cd_mun, achadas investigando por
-- que graficos de saude/demografia ficavam lentos sob a nova geração
-- concorrente (feat/concorrencia-relatorios). APLICADO no banco do beta
-- (oca_db) em 2026-09-23.
--
-- Medido com EXPLAIN ANALYZE, cidade Maceió (AL), antes de qualquer índice:
--
--   utils/queries/saude.py ESTABELECIMENTOS_SAUDE_SERIE
--     estabelecimento_saude: 1,6M linhas, 310 MB, 0 índices -> Parallel Seq Scan
--     306ms por chamada (39.664 buffers lidos do disco a cada request).
--
--   utils/queries/demografia.py POPULACAO_MUNICIPIO_POR_ANO
--     final_demografia: 74.568 linhas, 13 MB, 0 índices -> Seq Scan, 57ms.
--     Bônus achado nesta investigação: a junção original comparava
--     `c.cd_mun = d.cd_mun::text` (cast no lado GRANDE) — nenhum índice em
--     cd_mun (int) resolve essa comparação por texto. Corrigido no mesmo commit
--     invertendo o cast pra `d.cd_mun = c.cd_mun::int` (mesmo padrão já usado
--     em saude.py), sem o que o índice abaixo ficaria morto.
--
--   utils/queries/saude.py PUBLICO_ETARIO_VACINAS (via vw_imunizacao_anual_*)
--     imunizacao_anual_final_base: 405.314 linhas, 29 MB, 0 índices -> 273ms.
--     Índice aqui ajuda parcialmente (273ms -> 163ms): a consulta atravessa 3
--     camadas de views empilhadas com uma junção aritmética
--     (`a.cd_mun / 10 = b.cd_mun`), que impede o planner de empurrar o filtro
--     de cidade pra dentro das views. Resolver de verdade exige reescrever a
--     cadeia de views, não um índice — registrado como pendência em
--     Documentacao-OCA/investigacao-indices-cd-mun-2026-09.md, não feito aqui
--     para não mexer em views de produção sem mapear todos os consumidores.
--
-- Resultado depois de aplicar (mesmas queries, cidade Maceió AL):
--   estabelecimento_saude: 306ms -> 10ms  (Bitmap Index Scan)
--   final_demografia:       57ms -> 3ms   (Bitmap Index Scan, com o fix do cast)
--   imunizacao (parcial):  273ms -> 163ms (ainda Seq Scan, ver nota acima)
--
-- Tamanho em disco (medido via pg_relation_size):
--   idx_estabelecimento_saude_cd_mun          11 MB
--   idx_final_demografia_cd_mun_ano           640 kB
--   idx_imunizacao_anual_final_base_cd_mun    2,7 MB
--   total: ~14 MB (disco do host tinha ~8,6 GB livres na aplicação)
--
-- CONCURRENTLY: não bloqueia escrita; requer conexão com statement_timeout=0,
-- e não pode rodar dentro de bloco de transação.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_estabelecimento_saude_cd_mun
    ON sau_estabelecimento_de_saude.estabelecimento_saude (cd_mun);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_final_demografia_cd_mun_ano
    ON dem_demografia.final_demografia (cd_mun, ano);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_imunizacao_anual_final_base_cd_mun
    ON sau_imunizacao.imunizacao_anual_final_base (cd_mun);

ANALYZE sau_estabelecimento_de_saude.estabelecimento_saude;
ANALYZE dem_demografia.final_demografia;
ANALYZE sau_imunizacao.imunizacao_anual_final_base;
