-- Materializa relatorios_auto.vw_indicadores: a view é uma agregação país-inteira
-- (~39k municípios, spill pra temp, ~14s por chamada). Materializada, a leitura
-- por município vira scan de ~15ms. Refresh noturno via scripts/refresh_matviews.sh.
-- Aplicar à mão na base (DDL de produção). Idempotente.

CREATE MATERIALIZED VIEW IF NOT EXISTS relatorios_auto.mv_indicadores AS
SELECT * FROM relatorios_auto.vw_indicadores
WITH DATA;

-- REFRESH ... CONCURRENTLY (usado pelo cron, não bloqueia leitura) EXIGE um índice
-- UNIQUE. cd_mun é uma linha por município na view (verificado: 2074 linhas, 2074
-- distintos, 0 nulos) — é a PK natural de mv_indicadores, diferente da chave
-- (nm_mun, sigla_uf) usada nas mv_perfil_* (indicadores não é view de perfil).
CREATE UNIQUE INDEX IF NOT EXISTS mv_indicadores_cd_mun_idx
    ON relatorios_auto.mv_indicadores (cd_mun);
