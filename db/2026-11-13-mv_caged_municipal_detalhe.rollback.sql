-- Desfaz mv_caged_municipal_detalhe.sql. Sem ela, buscar_caged_municipal segue com os
-- marcadores principais e o parágrafo de escolaridade/ocupações some pelas condições do Doc.
DROP MATERIALIZED VIEW IF EXISTS relatorios_auto.mv_caged_municipal_detalhe;
