-- Desfaz mv_caged_municipal.sql. Nada depende desta matview no banco; o relatório
-- (utils/queries) cai para "sem dado" se ela sumir (executar_query devolve None).
DROP MATERIALIZED VIEW IF EXISTS relatorios_auto.mv_caged_municipal;
