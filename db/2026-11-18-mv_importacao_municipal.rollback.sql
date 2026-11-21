-- Desfaz mv_importacao_municipal.sql. Nada depende desta matview no banco; o relatório
-- (utils/queries/economia_importacao.py) sai sem o bloco de importação se ela sumir
-- (executar_query devolve None). Tirar também de MATVIEWS no refresh_matviews.sh.
DROP MATERIALIZED VIEW IF EXISTS relatorios_auto.mv_importacao_municipal;
