-- Materializa relatorios_auto.mv_populacao_por_municipio_2010_2022: mesma
-- classe de problema já resolvida em mv_indicadores (2026-09-17) — agregação
-- país-inteira recalculada a cada relatório. APLICADO no banco do beta
-- (oca_db) em 2026-09-23.
--
-- utils/queries/demografia.py MEDIA_CRESCIMENTO_MESMO_PORTE reagregava
-- dem_demografia.final_demografia (74.568 linhas) inteira toda vez que um
-- relatório de demografia era gerado, só para comparar o crescimento do
-- município-alvo com o de todos os municípios do mesmo porte (<=50k, <=100k,
-- >100k habitantes). Medido: 59ms por chamada.
--
-- Com a query reescrita para ler da matview (mesmo commit): 6ms por chamada.
-- Nenhuma outra mudança de comportamento — os valores continuam vindo de
-- final_demografia, só passam a ser lidos de um snapshot em vez de
-- recalculados.
--
-- 2074 linhas (municípios cobertos pela plataforma), 112 kB de tabela + 64 kB
-- de índice.
--
-- REFRESH ... CONCURRENTLY (scripts/refresh_matviews.sh, já adicionada à
-- lista MATVIEWS) exige índice único — cd_mun é uma linha por município aqui,
-- mesma garantia já verificada em mv_indicadores.

CREATE MATERIALIZED VIEW IF NOT EXISTS relatorios_auto.mv_populacao_por_municipio_2010_2022 AS
SELECT
    cd_mun,
    SUM(populacao_total) FILTER (WHERE ano = 2010) AS pop_2010,
    SUM(populacao_total) FILTER (WHERE ano = 2022) AS pop_2022
FROM dem_demografia.final_demografia
WHERE ano IN (2010, 2022)
GROUP BY cd_mun
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS mv_populacao_por_municipio_2010_2022_cd_mun_idx
    ON relatorios_auto.mv_populacao_por_municipio_2010_2022 (cd_mun);
