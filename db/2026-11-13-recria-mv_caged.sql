-- Recria as duas matviews do CAGED depois de mudar a definição de mv_caged_municipal
-- (2026-11-13: coalesce do acumulado na variação). CREATE ... IF NOT EXISTS não troca
-- uma matview existente, e mv_caged_municipal_detalhe depende dela (lê o trimestre),
-- então as duas caem e voltam juntas.
--
-- Rodar numa transação só (psql --single-transaction -f): se algo falhar, as antigas
-- continuam no ar. Enquanto roda (~10 min), leituras das duas ficam esperando o lock;
-- o relatório tem statement_timeout de 30 s e degrada para "sem dado".
--
--   psql --single-transaction -v ON_ERROR_STOP=1 \
--        -f db/2026-11-13-recria-mv_caged.sql \
--        -f db/2026-11-12-mv_caged_municipal.sql \
--        -f db/2026-11-13-mv_caged_municipal_detalhe.sql
DROP MATERIALIZED VIEW IF EXISTS relatorios_auto.mv_caged_municipal_detalhe;
DROP MATERIALIZED VIEW IF EXISTS relatorios_auto.mv_caged_municipal;
