-- relatorios_auto.mv_comex_municipal_mensal + vw_perfil_economia lendo dela.
-- APLICADO no banco do beta (oca_db) em 2026-10-05; prod não. Rollback em
-- 2026-10-05-mv_comex_municipal_mensal.rollback.sql (definição da view lida do
-- beta em 05/10, antes desta mudança).
--
-- Por quê: vw_perfil_economia levava ~117 s por leitura, mesmo filtrando um
-- município. Ela lia eco_comercio_exterior.impexp_completa (view sobre
-- fato_comercio_exterior, 21 mi de linhas / 2,4 GB) 12 vezes e agregava os
-- ~2.000 municípios antes do filtro. O time de dados revisa colunas direto na
-- view (a mv_perfil_economia fixa as 135 colunas da criação), então cada teste
-- custava ~2 min no banco compartilhado.
--
-- O que muda:
-- 1. mv_comex_municipal_mensal: impexp_completa somada por município, ano,
--    mês, operação, país, seção e SH4 (~1,7 mi de linhas, ~460 MB). A view só
--    faz sum() sobre vl_fob/kg_liquido, então somar antes não muda resultado.
-- 2. Dois índices com as MESMAS expressões que a view usa nos filtros de
--    período (co_ano * 100 + btrim(co_mes)::int, e co_ano). Sem eles cada uma
--    das 12 partes ainda varria a matview inteira para usar só o último
--    mês/ano (~40 s); com eles, ~1,9 s. Se a view mudar essas expressões, o
--    índice deixa de casar e o tempo volta.
-- 3. vw_perfil_economia: os 12 FROM impexp_completa leem a matview, e
--    produtos_sh4_limpos deixa de repassar colunas que ninguém usa (id, sh4,
--    desc_uf, ...), que não existem na matview. Mesmas 135 colunas, mesma
--    ordem e tipo: CREATE OR REPLACE passa com mv_perfil_economia no lugar.
--    Conferido nos 2.074 municípios contra mv_perfil_economia: 0 diferenças.
--
-- Medido no beta (Campina Grande/PB): 117 s -> 1,9 s (1 cidade), 2,5 s (todos),
-- com jit = off (ALTER DATABASE oca_db SET jit = off, aplicado junto: com JIT
-- a compilação da consulta somava ~10 s).
--
-- Atualização: scripts/refresh_matviews.sh, ANTES de mv_perfil_economia (que
-- lê esta view). REFRESH sem CONCURRENTLY (não há chave única natural): bloqueia
-- leituras da vw_perfil_economia por alguns minutos às 04:00 UTC (a criação
-- no beta levou ~4 min com o banco em uso; ~1 min com ele parado).

CREATE MATERIALIZED VIEW relatorios_auto.mv_comex_municipal_mensal AS
SELECT co_mun,
       co_ano,
       co_mes,
       tipo_operacao,
       desc_pais_portugues,
       desc_secao,
       desc_sh4,
       sum(vl_fob) AS vl_fob,
       sum(kg_liquido) AS kg_liquido
FROM eco_comercio_exterior.impexp_completa
GROUP BY co_mun, co_ano, co_mes, tipo_operacao, desc_pais_portugues, desc_secao, desc_sh4;

CREATE INDEX idx_mv_comex_ano_mes
    ON relatorios_auto.mv_comex_municipal_mensal ((co_ano * 100 + btrim(co_mes::text)::integer));
CREATE INDEX idx_mv_comex_ano
    ON relatorios_auto.mv_comex_municipal_mensal (co_ano);
ANALYZE relatorios_auto.mv_comex_municipal_mensal;

CREATE OR REPLACE VIEW relatorios_auto.vw_perfil_economia AS
WITH municipios AS (
         SELECT DISTINCT btrim(vw_pib.cd_mun::text)::integer AS cd_mun,
            vw_pib.nm_mun::text AS nm_mun,
            vw_pib.uf::text AS estado,
            vw_pib.sigla_uf::text AS sigla_uf
           FROM eco_pib.vw_pib
          WHERE vw_pib.ano = 2023 AND vw_pib.cd_mun IS NOT NULL AND btrim(vw_pib.cd_mun::text) ~ '^[0-9]+$'::text
        ), pib_raw AS (
         SELECT btrim(vw_pib.cd_mun::text)::integer AS cd_mun,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2010) AS pib_2010_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2011) AS pib_2011_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2012) AS pib_2012_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2013) AS pib_2013_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2014) AS pib_2014_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2015) AS pib_2015_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2016) AS pib_2016_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2017) AS pib_2017_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2018) AS pib_2018_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2019) AS pib_2019_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2020) AS pib_2020_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2021) AS pib_2021_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2022) AS pib_2022_raw,
            max(vw_pib.pib_total) FILTER (WHERE vw_pib.ano = 2023) AS pib_2023_raw,
            max(vw_pib.pib_per_capita) FILTER (WHERE vw_pib.ano = 2023) AS pibcapita_2023_raw,
            max(vw_pib.atividade_maior_vab) FILTER (WHERE vw_pib.ano = 2021) AS ativ_participacao_pib,
            max(vw_pib.vab_setor_maior * 1000::numeric) FILTER (WHERE vw_pib.ano = 2021) AS ativ_valor_raw,
            max(vw_pib.vab_total * 1000::numeric) FILTER (WHERE vw_pib.ano = 2021) AS vab_total_2021_raw
           FROM eco_pib.vw_pib
          WHERE vw_pib.ano >= 2010 AND vw_pib.ano <= 2023 AND vw_pib.cd_mun IS NOT NULL AND btrim(vw_pib.cd_mun::text) ~ '^[0-9]+$'::text
          GROUP BY (btrim(vw_pib.cd_mun::text)::integer)
        ), pib_escala AS (
         SELECT p_1.cd_mun,
            p_1.pib_2010_raw,
            p_1.pib_2011_raw,
            p_1.pib_2012_raw,
            p_1.pib_2013_raw,
            p_1.pib_2014_raw,
            p_1.pib_2015_raw,
            p_1.pib_2016_raw,
            p_1.pib_2017_raw,
            p_1.pib_2018_raw,
            p_1.pib_2019_raw,
            p_1.pib_2020_raw,
            p_1.pib_2021_raw,
            p_1.pib_2022_raw,
            p_1.pib_2023_raw,
            p_1.pibcapita_2023_raw,
            p_1.ativ_participacao_pib,
            p_1.ativ_valor_raw,
            p_1.vab_total_2021_raw,
                CASE
                    WHEN g.max_pib >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint::numeric
                    WHEN g.max_pib >= 1000000000::numeric THEN 1000000000::numeric
                    WHEN g.max_pib >= 1000000::numeric THEN 1000000::numeric
                    WHEN g.max_pib >= 1000::numeric THEN 1000::numeric
                    ELSE 1::numeric
                END AS pib_divisor,
                CASE
                    WHEN g.max_pib >= '1000000000000'::bigint::numeric THEN 'trilhões'::text
                    WHEN g.max_pib >= 1000000000::numeric THEN 'bilhões'::text
                    WHEN g.max_pib >= 1000000::numeric THEN 'milhões'::text
                    WHEN g.max_pib >= 1000::numeric THEN 'mil'::text
                    ELSE ''::text
                END AS pib_unidade
           FROM pib_raw p_1
             LEFT JOIN LATERAL ( SELECT max(abs(x.valor)) AS max_pib
                   FROM ( VALUES (p_1.pib_2010_raw), (p_1.pib_2011_raw), (p_1.pib_2012_raw), (p_1.pib_2013_raw), (p_1.pib_2014_raw), (p_1.pib_2015_raw), (p_1.pib_2016_raw), (p_1.pib_2017_raw), (p_1.pib_2018_raw), (p_1.pib_2019_raw), (p_1.pib_2020_raw), (p_1.pib_2021_raw), (p_1.pib_2022_raw), (p_1.pib_2023_raw)) x(valor)
                  WHERE x.valor IS NOT NULL) g ON true
        ), setores_long AS (
         SELECT btrim(p_1.cd_mun::text)::integer AS cd_mun,
            s_1.setor,
            s_1.valor_vab * 1000::numeric AS valor_vab,
            s_1.ordem
           FROM eco_pib.vw_pib p_1
             CROSS JOIN LATERAL ( VALUES ('Agropecuária'::text,p_1.vab_agropecuaria,1), ('Indústria'::text,p_1.vab_industria,2), ('Serviços'::text,p_1.vab_servicos,3), ('Administração pública'::text,p_1.vab_adm_publica,4)) s_1(setor, valor_vab, ordem)
          WHERE p_1.ano = 2021 AND p_1.cd_mun IS NOT NULL AND btrim(p_1.cd_mun::text) ~ '^[0-9]+$'::text
        ), setores_ranking AS (
         SELECT setores_long.cd_mun,
            setores_long.setor,
            setores_long.valor_vab,
            setores_long.ordem,
            row_number() OVER (PARTITION BY setores_long.cd_mun ORDER BY setores_long.valor_vab DESC NULLS LAST, setores_long.ordem) AS posicao
           FROM setores_long
          WHERE setores_long.valor_vab IS NOT NULL
        ), setores AS (
         SELECT setores_ranking.cd_mun,
            max(setores_ranking.setor) FILTER (WHERE setores_ranking.posicao = 1) AS setor2021_maior1,
            max(setores_ranking.valor_vab) FILTER (WHERE setores_ranking.posicao = 1) AS valor_setor2021_maior1_raw,
            max(setores_ranking.setor) FILTER (WHERE setores_ranking.posicao = 2) AS setor2021_maior2,
            max(setores_ranking.valor_vab) FILTER (WHERE setores_ranking.posicao = 2) AS valor_setor2021_maior2_raw,
            max(setores_ranking.setor) FILTER (WHERE setores_ranking.posicao = 3) AS setor2021_maior3,
            max(setores_ranking.valor_vab) FILTER (WHERE setores_ranking.posicao = 3) AS valor_setor2021_maior3_raw,
            max(setores_ranking.setor) FILTER (WHERE setores_ranking.posicao = 4) AS setor2021_menor,
            max(setores_ranking.valor_vab) FILTER (WHERE setores_ranking.posicao = 4) AS valor_setor2021_menor_raw
           FROM setores_ranking
          GROUP BY setores_ranking.cd_mun
        ), ultimo_periodo AS (
         SELECT max(impexp_completa.co_ano * 100 + btrim(impexp_completa.co_mes::text)::integer) AS ano_mes
           FROM relatorios_auto.mv_comex_municipal_mensal impexp_completa
          WHERE impexp_completa.co_ano IS NOT NULL AND impexp_completa.co_mes IS NOT NULL AND btrim(impexp_completa.co_mes::text) ~ '^[0-9]+$'::text
        ), periodo_ultimo AS (
         SELECT ultimo_periodo.ano_mes,
            ultimo_periodo.ano_mes / 100 AS ano,
            ultimo_periodo.ano_mes % 100 AS mes
           FROM ultimo_periodo
        ), comercio_ultimo AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            COALESCE(sum(c.vl_fob) FILTER (WHERE c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS fob_importado_raw,
            COALESCE(sum(c.kg_liquido) FILTER (WHERE c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS kg_importado_raw,
            COALESCE(sum(c.vl_fob) FILTER (WHERE c.tipo_operacao::text = 'Exportação'::text), 0::numeric) AS fob_exportado_raw,
            COALESCE(sum(c.kg_liquido) FILTER (WHERE c.tipo_operacao::text = 'Exportação'::text), 0::numeric) AS kg_exportado_raw
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.co_ano IS NOT NULL AND c.co_mes IS NOT NULL AND btrim(c.co_mes::text) ~ '^[0-9]+$'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes
          GROUP BY (btrim(c.co_mun::text)::integer)
        ), paises_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            c.tipo_operacao::text AS tipo_operacao,
            btrim(c.desc_pais_portugues::text) AS pais,
            sum(c.vl_fob) AS valor_fob
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.co_ano IS NOT NULL AND c.co_mes IS NOT NULL AND btrim(c.co_mes::text) ~ '^[0-9]+$'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND (c.tipo_operacao::text = ANY (ARRAY['Importação'::character varying::text, 'Exportação'::character varying::text])) AND c.desc_pais_portugues IS NOT NULL AND btrim(c.desc_pais_portugues::text) <> ''::text
          GROUP BY (btrim(c.co_mun::text)::integer), c.tipo_operacao, (btrim(c.desc_pais_portugues::text))
        ), paises_ranking AS (
         SELECT paises_base.cd_mun,
            paises_base.tipo_operacao,
            paises_base.pais,
            paises_base.valor_fob,
            row_number() OVER (PARTITION BY paises_base.cd_mun, paises_base.tipo_operacao ORDER BY paises_base.valor_fob DESC, paises_base.pais) AS posicao
           FROM paises_base
          WHERE paises_base.valor_fob > 0::numeric
        ), paises AS (
         SELECT paises_ranking.cd_mun,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 1) AS pais_importado1,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 1) AS valor_pais_importado1_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 2) AS pais_importado2,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 2) AS valor_pais_importado2_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 3) AS pais_importado3,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 3) AS valor_pais_importado3_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 4) AS pais_importado4,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Importação'::text AND paises_ranking.posicao = 4) AS valor_pais_importado4_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 1) AS pais_exportacao1,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 1) AS valor_pais_exportacao1_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 2) AS pais_exportacao2,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 2) AS valor_pais_exportacao2_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 3) AS pais_exportacao3,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 3) AS valor_pais_exportacao3_raw,
            max(paises_ranking.pais) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 4) AS pais_exportacao4,
            max(paises_ranking.valor_fob) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao = 4) AS valor_pais_exportacao4_raw,
            array_agg(paises_ranking.pais ORDER BY paises_ranking.posicao) FILTER (WHERE paises_ranking.tipo_operacao = 'Exportação'::text AND paises_ranking.posicao >= 5 AND paises_ranking.posicao <= 10) AS paises_exportacao_restantes
           FROM paises_ranking
          GROUP BY paises_ranking.cd_mun
        ), secoes_importacao_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            btrim(c.desc_secao::text) AS secao,
            sum(c.vl_fob) AS valor_fob
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.tipo_operacao::text = 'Importação'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND NULLIF(btrim(c.desc_secao::text), ''::text) IS NOT NULL
          GROUP BY (btrim(c.co_mun::text)::integer), (btrim(c.desc_secao::text))
         HAVING sum(c.vl_fob) > 0::numeric
        ), secoes_importacao_rank AS (
         SELECT secoes_importacao_base.cd_mun,
            secoes_importacao_base.secao,
            secoes_importacao_base.valor_fob,
            row_number() OVER (PARTITION BY secoes_importacao_base.cd_mun ORDER BY secoes_importacao_base.valor_fob DESC, secoes_importacao_base.secao) AS posicao
           FROM secoes_importacao_base
        ), secoes_importacao AS (
         SELECT secoes_importacao_rank.cd_mun,
            max(secoes_importacao_rank.secao) FILTER (WHERE secoes_importacao_rank.posicao = 1) AS secao_importado1,
            max(secoes_importacao_rank.valor_fob) FILTER (WHERE secoes_importacao_rank.posicao = 1) AS valor_secao_importado1_raw,
            max(secoes_importacao_rank.secao) FILTER (WHERE secoes_importacao_rank.posicao = 2) AS secao_importado2,
            max(secoes_importacao_rank.valor_fob) FILTER (WHERE secoes_importacao_rank.posicao = 2) AS valor_secao_importado2_raw
           FROM secoes_importacao_rank
          GROUP BY secoes_importacao_rank.cd_mun
        ), secoes_exportacao_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            btrim(c.desc_secao::text) AS secao,
            sum(c.vl_fob) AS valor_fob
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.tipo_operacao::text = 'Exportação'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND NULLIF(btrim(c.desc_secao::text), ''::text) IS NOT NULL
          GROUP BY (btrim(c.co_mun::text)::integer), (btrim(c.desc_secao::text))
         HAVING sum(c.vl_fob) > 0::numeric
        ), secoes_exportacao AS (
         SELECT DISTINCT ON (secoes_exportacao_base.cd_mun) secoes_exportacao_base.cd_mun,
            secoes_exportacao_base.secao AS secao_exportacao1,
            secoes_exportacao_base.valor_fob AS valor_exportacao_secao1_raw
           FROM secoes_exportacao_base
          ORDER BY secoes_exportacao_base.cd_mun, secoes_exportacao_base.valor_fob DESC, secoes_exportacao_base.secao
        ), produtos_sh4_limpos AS (
         SELECT c.tipo_operacao,
            c.co_ano,
            c.co_mes,
            c.co_mun,
            c.kg_liquido,
            c.vl_fob,
            c.desc_pais_portugues,
            c.desc_sh4,
            c.desc_secao,
                CASE
                    WHEN (length(c.desc_sh4::text) - length(replace(c.desc_sh4::text, '('::text, ''::text))) > (length(c.desc_sh4::text) - length(replace(c.desc_sh4::text, ')'::text, ''::text))) THEN btrim(c.desc_sh4::text) || ')'::text
                    WHEN (length(c.desc_sh4::text) - length(replace(c.desc_sh4::text, ')'::text, ''::text))) > (length(c.desc_sh4::text) - length(replace(c.desc_sh4::text, '('::text, ''::text))) THEN regexp_replace(btrim(c.desc_sh4::text), '\)$'::text, ''::text)
                    ELSE btrim(c.desc_sh4::text)
                END AS desc_sh4_corrigida
           FROM relatorios_auto.mv_comex_municipal_mensal c
        ), produto_importacao_valor_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            c.desc_sh4_corrigida AS produto,
            sum(c.vl_fob) AS valor_fob
           FROM produtos_sh4_limpos c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.tipo_operacao::text = 'Importação'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND NULLIF(c.desc_sh4_corrigida, ''::text) IS NOT NULL
          GROUP BY (btrim(c.co_mun::text)::integer), c.desc_sh4_corrigida
         HAVING sum(c.vl_fob) > 0::numeric
        ), produto_importacao_valor_rank AS (
         SELECT produto_importacao_valor_base.cd_mun,
            produto_importacao_valor_base.produto,
            produto_importacao_valor_base.valor_fob,
            row_number() OVER (PARTITION BY produto_importacao_valor_base.cd_mun ORDER BY produto_importacao_valor_base.valor_fob DESC, produto_importacao_valor_base.produto) AS posicao
           FROM produto_importacao_valor_base
        ), produto_importacao_valor AS (
         SELECT produto_importacao_valor_rank.cd_mun,
            max(produto_importacao_valor_rank.produto) FILTER (WHERE produto_importacao_valor_rank.posicao = 1) AS produto_importado1,
            max(produto_importacao_valor_rank.valor_fob) FILTER (WHERE produto_importacao_valor_rank.posicao = 1) AS valor_produto_importado1_raw,
            max(produto_importacao_valor_rank.produto) FILTER (WHERE produto_importacao_valor_rank.posicao = 2) AS produto_importado2,
            max(produto_importacao_valor_rank.valor_fob) FILTER (WHERE produto_importacao_valor_rank.posicao = 2) AS valor_produto_importado2_raw
           FROM produto_importacao_valor_rank
          GROUP BY produto_importacao_valor_rank.cd_mun
        ), produto_importacao_kg_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            btrim(c.desc_sh4::text) AS produto,
            sum(c.kg_liquido) AS kg
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.tipo_operacao::text = 'Importação'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND NULLIF(btrim(c.desc_sh4::text), ''::text) IS NOT NULL
          GROUP BY (btrim(c.co_mun::text)::integer), (btrim(c.desc_sh4::text))
         HAVING sum(c.kg_liquido) > 0::numeric
        ), produto_importacao_kg_rank AS (
         SELECT produto_importacao_kg_base.cd_mun,
            produto_importacao_kg_base.produto,
            produto_importacao_kg_base.kg,
            row_number() OVER (PARTITION BY produto_importacao_kg_base.cd_mun ORDER BY produto_importacao_kg_base.kg DESC, produto_importacao_kg_base.produto) AS posicao
           FROM produto_importacao_kg_base
        ), produto_importacao_kg AS (
         SELECT produto_importacao_kg_rank.cd_mun,
            max(produto_importacao_kg_rank.produto) FILTER (WHERE produto_importacao_kg_rank.posicao = 1) AS produto_importado_kg1,
            max(produto_importacao_kg_rank.kg) FILTER (WHERE produto_importacao_kg_rank.posicao = 1) AS kg_importado_produto1_raw,
            max(produto_importacao_kg_rank.produto) FILTER (WHERE produto_importacao_kg_rank.posicao = 2) AS produto_importado_kg2,
            max(produto_importacao_kg_rank.kg) FILTER (WHERE produto_importacao_kg_rank.posicao = 2) AS kg_importado_produto2_raw
           FROM produto_importacao_kg_rank
          GROUP BY produto_importacao_kg_rank.cd_mun
        ), produto_exportacao_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            btrim(c.desc_sh4::text) AS produto,
            sum(c.vl_fob) AS valor_fob
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_periodo u
          WHERE c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND c.tipo_operacao::text = 'Exportação'::text AND (c.co_ano * 100 + btrim(c.co_mes::text)::integer) = u.ano_mes AND NULLIF(btrim(c.desc_sh4::text), ''::text) IS NOT NULL
          GROUP BY (btrim(c.co_mun::text)::integer), (btrim(c.desc_sh4::text))
         HAVING sum(c.vl_fob) > 0::numeric
        ), produto_exportacao AS (
         SELECT DISTINCT ON (produto_exportacao_base.cd_mun) produto_exportacao_base.cd_mun,
            produto_exportacao_base.produto AS produto_exportado1,
            produto_exportacao_base.valor_fob AS valor_exportacao_produto1_raw
           FROM produto_exportacao_base
          ORDER BY produto_exportacao_base.cd_mun, produto_exportacao_base.valor_fob DESC, produto_exportacao_base.produto
        ), ultimo_junho AS (
         SELECT max(impexp_completa.co_ano) AS ano
           FROM relatorios_auto.mv_comex_municipal_mensal impexp_completa
          WHERE btrim(impexp_completa.co_mes::text)::integer = 6
        ), importacao_janjun_base AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 1) AS fob_jan,
            sum(c.kg_liquido) FILTER (WHERE btrim(c.co_mes::text)::integer = 1) AS kg_jan,
            sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 6) AS fob_jun,
            sum(c.kg_liquido) FILTER (WHERE btrim(c.co_mes::text)::integer = 6) AS kg_jun
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_junho u
          WHERE c.tipo_operacao::text = 'Importação'::text AND c.co_ano = u.ano AND (btrim(c.co_mes::text)::integer = ANY (ARRAY[1, 6])) AND c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text
          GROUP BY (btrim(c.co_mun::text)::integer)
        ), importacao_janjun AS (
         SELECT importacao_janjun_base.cd_mun,
                CASE
                    WHEN importacao_janjun_base.kg_jan IS NOT NULL AND importacao_janjun_base.kg_jan <> 0::numeric THEN importacao_janjun_base.fob_jan / importacao_janjun_base.kg_jan
                    ELSE NULL::numeric
                END AS valormedio_importado_jan_raw,
                CASE
                    WHEN importacao_janjun_base.kg_jun IS NOT NULL AND importacao_janjun_base.kg_jun <> 0::numeric THEN importacao_janjun_base.fob_jun / importacao_janjun_base.kg_jun
                    ELSE NULL::numeric
                END AS valormedio_importado_jun_raw
           FROM importacao_janjun_base
        ), balanca_semestre AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 1 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 1 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_jan,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 2 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 2 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_fev,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 3 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 3 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_mar,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 4 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 4 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_abr,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 5 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 5 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_mai,
            COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 6 AND c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE btrim(c.co_mes::text)::integer = 6 AND c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca_jun,
            COALESCE(sum(c.vl_fob) FILTER (WHERE c.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(c.vl_fob) FILTER (WHERE c.tipo_operacao::text = 'Importação'::text), 0::numeric) AS valor_balanca6meses_raw
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN ultimo_junho u
          WHERE c.co_ano = u.ano AND btrim(c.co_mes::text)::integer >= 1 AND btrim(c.co_mes::text)::integer <= 6 AND c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text
          GROUP BY (btrim(c.co_mun::text)::integer)
        ), balanca_mensal AS (
         SELECT btrim(c.co_mun::text)::integer AS cd_mun,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 1) AS valor_balanca_jan,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 2) AS valor_balanca_fev,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 3) AS valor_balanca_mar,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 4) AS valor_balanca_abr,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 5) AS valor_balanca_mai,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 6) AS valor_balanca_jun,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 7) AS valor_balanca_jul,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 8) AS valor_balanca_ago,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 9) AS valor_balanca_set,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 10) AS valor_balanca_out,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 11) AS valor_balanca_nov,
            sum(
                CASE
                    WHEN c.tipo_operacao::text = 'Exportação'::text THEN c.vl_fob
                    ELSE - c.vl_fob
                END) FILTER (WHERE btrim(c.co_mes::text)::integer = 12) AS valor_balanca_dez
           FROM relatorios_auto.mv_comex_municipal_mensal c
             CROSS JOIN periodo_ultimo u
          WHERE c.co_ano = u.ano AND c.co_mun IS NOT NULL AND btrim(c.co_mun::text) ~ '^[0-9]+$'::text AND
                CASE
                    WHEN btrim(c.co_mes::text) ~ '^[0-9]+$'::text THEN btrim(c.co_mes::text)::integer >= 1 AND btrim(c.co_mes::text)::integer <= u.mes
                    ELSE false
                END AND (c.tipo_operacao::text = ANY (ARRAY['Exportação'::text, 'Importação'::text]))
          GROUP BY (btrim(c.co_mun::text)::integer)
        )
 SELECT m.nm_mun,
    m.estado,
    m.sigla_uf,
    round(p.pib_2010_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2010,
        CASE
            WHEN abs(round(p.pib_2010_raw / NULLIF(p.pib_divisor, 0::numeric), 2)) < 2::numeric THEN
            CASE p.pib_unidade
                WHEN 'trilhões'::text THEN 'trilhão'::text
                WHEN 'bilhões'::text THEN 'bilhão'::text
                WHEN 'milhões'::text THEN 'milhão'::text
                ELSE p.pib_unidade
            END
            ELSE p.pib_unidade
        END AS pib_unid_2010,
    round(p.pib_2011_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2011,
    round(p.pib_2012_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2012,
    round(p.pib_2013_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2013,
    round(p.pib_2014_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2014,
    round(p.pib_2015_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2015,
    round(p.pib_2016_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2016,
    round(p.pib_2017_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2017,
    round(p.pib_2018_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2018,
    round(p.pib_2019_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2019,
    round(p.pib_2020_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2020,
    round(p.pib_2021_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2021,
    round(p.pib_2022_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2022,
    round(p.pib_2023_raw / NULLIF(p.pib_divisor, 0::numeric), 2) AS pib_2023,
        CASE
            WHEN abs(round(p.pib_2023_raw / NULLIF(p.pib_divisor, 0::numeric), 2)) < 2::numeric THEN
            CASE p.pib_unidade
                WHEN 'trilhões'::text THEN 'trilhão'::text
                WHEN 'bilhões'::text THEN 'bilhão'::text
                WHEN 'milhões'::text THEN 'milhão'::text
                ELSE p.pib_unidade
            END
            ELSE p.pib_unidade
        END AS pib_unid_2023,
    round(p.pibcapita_2023_raw /
        CASE
            WHEN abs(p.pibcapita_2023_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(p.pibcapita_2023_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(p.pibcapita_2023_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(p.pibcapita_2023_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS pibcapita_2023,
        CASE
            WHEN abs(p.pibcapita_2023_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(p.pibcapita_2023_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(p.pibcapita_2023_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(p.pibcapita_2023_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(p.pibcapita_2023_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(p.pibcapita_2023_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(p.pibcapita_2023_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS pibcapita_unid_2023,
        CASE
            WHEN p.pib_2010_raw IS NULL OR p.pib_2023_raw IS NULL THEN 'Não há dados'::text
            WHEN p.pib_2023_raw > p.pib_2010_raw THEN 'um crescimento'::text
            WHEN p.pib_2023_raw < p.pib_2010_raw THEN 'uma diminuição'::text
            ELSE 'uma estabilidade'::text
        END AS analise1_pib,
        CASE
            WHEN p.pib_2010_raw IS NULL OR p.pib_2023_raw IS NULL OR p.pib_2010_raw = 0::numeric THEN NULL::numeric
            ELSE abs(round((p.pib_2023_raw - p.pib_2010_raw) / p.pib_2010_raw * 100::numeric, 2))
        END AS pib_per_2010_2023,
    abs(round((p.pib_2023_raw - p.pib_2010_raw) /
        CASE
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2)) AS diferenca_pib_2010_2023,
        CASE
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(p.pib_2023_raw - p.pib_2010_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(p.pib_2023_raw - p.pib_2010_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(p.pib_2023_raw - p.pib_2010_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(p.pib_2023_raw - p.pib_2010_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS diferenca_pib_2010_2023unid,
        CASE
            WHEN s.setor2021_maior1 = 'Serviços'::text THEN 'de Serviços'::text
            WHEN s.setor2021_maior1 IS NOT NULL THEN 'da '::text || s.setor2021_maior1
            ELSE NULL::text
        END AS setor2021_maior1,
    round(s.valor_setor2021_maior1_raw /
        CASE
            WHEN abs(s.valor_setor2021_maior1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_setor2021_maior1,
        CASE
            WHEN abs(s.valor_setor2021_maior1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(s.valor_setor2021_maior1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS setor2021_maior1unid,
        CASE
            WHEN s.setor2021_maior2 = 'Serviços'::text THEN 'de Serviços'::text
            WHEN s.setor2021_maior2 IS NOT NULL THEN 'da '::text || s.setor2021_maior2
            ELSE NULL::text
        END AS setor2021_maior2,
    round(s.valor_setor2021_maior2_raw /
        CASE
            WHEN abs(s.valor_setor2021_maior2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_setor2021_maior2,
        CASE
            WHEN abs(s.valor_setor2021_maior2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(s.valor_setor2021_maior2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS setor2021_maior2unid,
        CASE
            WHEN s.setor2021_maior3 = 'Serviços'::text THEN 'de Serviços'::text
            WHEN s.setor2021_maior3 IS NOT NULL THEN 'da '::text || s.setor2021_maior3
            ELSE NULL::text
        END AS setor2021_maior3,
    round(s.valor_setor2021_maior3_raw /
        CASE
            WHEN abs(s.valor_setor2021_maior3_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_setor2021_maior3,
        CASE
            WHEN abs(s.valor_setor2021_maior3_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior3_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior3_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_maior3_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(s.valor_setor2021_maior3_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS setor2021_maior3unid,
    s.setor2021_menor,
    round(s.valor_setor2021_menor_raw /
        CASE
            WHEN abs(s.valor_setor2021_menor_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_setor2021_menor,
        CASE
            WHEN abs(s.valor_setor2021_menor_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_menor_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_menor_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(s.valor_setor2021_menor_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(s.valor_setor2021_menor_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS setor2021_menor_unid,
    (
        CASE pu.mes
            WHEN 1 THEN 'janeiro'::text
            WHEN 2 THEN 'fevereiro'::text
            WHEN 3 THEN 'março'::text
            WHEN 4 THEN 'abril'::text
            WHEN 5 THEN 'maio'::text
            WHEN 6 THEN 'junho'::text
            WHEN 7 THEN 'julho'::text
            WHEN 8 THEN 'agosto'::text
            WHEN 9 THEN 'setembro'::text
            WHEN 10 THEN 'outubro'::text
            WHEN 11 THEN 'novembro'::text
            WHEN 12 THEN 'dezembro'::text
            ELSE NULL::text
        END || ' de '::text) || pu.ano::text AS ultimo_mes_ano,
    round(com.fob_importado_raw /
        CASE
            WHEN abs(com.fob_importado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.fob_importado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.fob_importado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.fob_importado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS fob_importado_ultimo,
    p.ativ_participacao_pib,
        CASE
            WHEN p.ativ_valor_raw IS NULL OR p.vab_total_2021_raw IS NULL OR p.vab_total_2021_raw = 0::numeric THEN NULL::numeric
            ELSE round(p.ativ_valor_raw / p.vab_total_2021_raw * 100::numeric, 2)
        END AS ativ_participacao_pibper,
        CASE
            WHEN abs(com.fob_importado_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(com.fob_importado_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(com.fob_importado_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_importado_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(com.fob_importado_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_importado_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(com.fob_importado_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS fob_importado_ultimo_unid,
    round(com.kg_importado_raw /
        CASE
            WHEN abs(com.kg_importado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.kg_importado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.kg_importado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.kg_importado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS kg_importado_ultimo,
        CASE
            WHEN abs(com.kg_importado_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(com.kg_importado_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(com.kg_importado_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(com.kg_importado_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(com.kg_importado_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(com.kg_importado_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(com.kg_importado_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS kg_importado_ultimo_unid,
    pais.pais_importado1,
    round(pais.valor_pais_importado1_raw /
        CASE
            WHEN abs(pais.valor_pais_importado1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_importado1,
        CASE
            WHEN abs(pais.valor_pais_importado1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_importado1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_importado_unid1,
    pais.pais_importado2,
    round(pais.valor_pais_importado2_raw /
        CASE
            WHEN abs(pais.valor_pais_importado2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_importado2,
        CASE
            WHEN abs(pais.valor_pais_importado2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_importado2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_importado_unid2,
    pais.pais_importado3,
    round(pais.valor_pais_importado3_raw /
        CASE
            WHEN abs(pais.valor_pais_importado3_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_importado3,
        CASE
            WHEN abs(pais.valor_pais_importado3_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado3_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado3_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado3_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_importado3_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_importado_unid3,
    pais.pais_importado4,
    round(pais.valor_pais_importado4_raw /
        CASE
            WHEN abs(pais.valor_pais_importado4_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_importado4,
        CASE
            WHEN abs(pais.valor_pais_importado4_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado4_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado4_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_importado4_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_importado4_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_importado_unid4,
    replace(lower(si.secao_importado1), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS secao_importado1,
    round(si.valor_secao_importado1_raw /
        CASE
            WHEN abs(si.valor_secao_importado1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(si.valor_secao_importado1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(si.valor_secao_importado1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(si.valor_secao_importado1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_secao_importado1,
        CASE
            WHEN abs(si.valor_secao_importado1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(si.valor_secao_importado1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(si.valor_secao_importado1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(si.valor_secao_importado1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_secao_importado_unid1,
    replace(lower(si.secao_importado2), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS secao_importado2,
    round(si.valor_secao_importado2_raw /
        CASE
            WHEN abs(si.valor_secao_importado2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(si.valor_secao_importado2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(si.valor_secao_importado2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(si.valor_secao_importado2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_secao_importado2,
        CASE
            WHEN abs(si.valor_secao_importado2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(si.valor_secao_importado2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(si.valor_secao_importado2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(si.valor_secao_importado2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(si.valor_secao_importado2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_secao_importado_unid2,
    replace(replace(
        CASE
            WHEN strpos(lower(piv.produto_importado1), ' (por exemplo:'::text) > 0 AND "right"(regexp_replace(lower(piv.produto_importado1), '[[:space:]]+$'::text, ''::text), 1) <> ')'::text THEN regexp_replace(lower(piv.produto_importado1), '[[:space:]]+$'::text, ''::text) || ')'::text
            ELSE lower(piv.produto_importado1)
        END, 'protecção'::text, 'proteção'::text), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS produto_importado1,
    round(piv.valor_produto_importado1_raw /
        CASE
            WHEN abs(piv.valor_produto_importado1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_produto_importado1,
        CASE
            WHEN abs(piv.valor_produto_importado1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(piv.valor_produto_importado1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_produto_importadounid1,
    replace(replace(
        CASE
            WHEN strpos(lower(piv.produto_importado2), ' (por exemplo:'::text) > 0 AND "right"(regexp_replace(lower(piv.produto_importado2), '[[:space:]]+$'::text, ''::text), 1) <> ')'::text THEN regexp_replace(lower(piv.produto_importado2), '[[:space:]]+$'::text, ''::text) || ')'::text
            ELSE lower(piv.produto_importado2)
        END, 'protecção'::text, 'proteção'::text), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS produto_importado2,
    round(piv.valor_produto_importado2_raw /
        CASE
            WHEN abs(piv.valor_produto_importado2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_produto_importado2,
        CASE
            WHEN abs(piv.valor_produto_importado2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(piv.valor_produto_importado2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(piv.valor_produto_importado2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_produto_importadounid2,
    round(pik.kg_importado_produto1_raw /
        CASE
            WHEN abs(pik.kg_importado_produto1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS kg_importado_produto1,
        CASE
            WHEN abs(pik.kg_importado_produto1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pik.kg_importado_produto1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS kg_importado_produtounid1,
    replace(lower(pik.produto_importado_kg1), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS produto_importado_kg1,
    round(pik.kg_importado_produto2_raw /
        CASE
            WHEN abs(pik.kg_importado_produto2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS kg_importado_produto2,
        CASE
            WHEN abs(pik.kg_importado_produto2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pik.kg_importado_produto2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pik.kg_importado_produto2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS kg_importado_produtounid2,
    replace(lower(pik.produto_importado_kg2), 'indútrias alimentares'::text, 'indústrias alimentares'::text) AS produto_importado_kg2,
        CASE
            WHEN piv.produto_importado1 IS NULL OR pik.produto_importado_kg1 IS NULL THEN 'Não há dados'::text
            WHEN piv.produto_importado1 = pik.produto_importado_kg1 AND NOT piv.produto_importado2 IS DISTINCT FROM pik.produto_importado_kg2 THEN 'se concentrou nesses grupos:'::text
            WHEN piv.produto_importado1 = pik.produto_importado_kg1 OR piv.produto_importado1 = pik.produto_importado_kg2 OR piv.produto_importado2 = pik.produto_importado_kg1 OR piv.produto_importado2 = pik.produto_importado_kg2 THEN 'se concentrou parcialmente nesses grupos:'::text
            ELSE 'se concentrou em grupos distintos, sendo eles:'::text
        END AS analise_produto,
    round(ij.valormedio_importado_jan_raw /
        CASE
            WHEN abs(ij.valormedio_importado_jan_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valormedio_importado_jan,
        CASE
            WHEN abs(ij.valormedio_importado_jan_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jan_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jan_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jan_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(ij.valormedio_importado_jan_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valormedio_importado_janunid,
    round(ij.valormedio_importado_jun_raw /
        CASE
            WHEN abs(ij.valormedio_importado_jun_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valormedio_importado_jun,
        CASE
            WHEN abs(ij.valormedio_importado_jun_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jun_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jun_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(ij.valormedio_importado_jun_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(ij.valormedio_importado_jun_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valormedio_importado_jununid,
    uj.ano AS ultimo_junho,
        CASE
            WHEN ij.valormedio_importado_jan_raw IS NULL OR ij.valormedio_importado_jun_raw IS NULL THEN 'Não há dados'::text
            WHEN ij.valormedio_importado_jun_raw > ij.valormedio_importado_jan_raw THEN 'aumento'::text
            WHEN ij.valormedio_importado_jun_raw < ij.valormedio_importado_jan_raw THEN 'diminuição'::text
            ELSE 'manutenção'::text
        END AS analise_importado_janjun,
    round(com.fob_exportado_raw /
        CASE
            WHEN abs(com.fob_exportado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.fob_exportado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.fob_exportado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.fob_exportado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS fob_exportado_ultimo,
        CASE
            WHEN abs(com.fob_exportado_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(com.fob_exportado_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(com.fob_exportado_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(com.fob_exportado_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS fob_exportado_ultimo_unid,
    round(com.kg_exportado_raw /
        CASE
            WHEN abs(com.kg_exportado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.kg_exportado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.kg_exportado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.kg_exportado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS kg_exportado,
        CASE
            WHEN abs(com.kg_exportado_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(com.kg_exportado_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(com.kg_exportado_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(com.kg_exportado_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(com.kg_exportado_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(com.kg_exportado_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(com.kg_exportado_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS kg_exportado_unid,
    regexp_replace(se.secao_exportacao1, '(\mindú)(trias alimentares\M)'::text, '\1s\2'::text, 'gi'::text) AS secao_exportacao1,
    round(se.valor_exportacao_secao1_raw /
        CASE
            WHEN abs(se.valor_exportacao_secao1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_exportacao_secao1,
        CASE
            WHEN abs(se.valor_exportacao_secao1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(se.valor_exportacao_secao1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(se.valor_exportacao_secao1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(se.valor_exportacao_secao1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(se.valor_exportacao_secao1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_exportacao_secao1unid,
    regexp_replace(pe.produto_exportado1, '(\mindú)(trias alimentares\M)'::text, '\1s\2'::text, 'gi'::text) AS produto_exportado1,
    round(pe.valor_exportacao_produto1_raw /
        CASE
            WHEN abs(pe.valor_exportacao_produto1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_exportacao_produto1,
        CASE
            WHEN abs(pe.valor_exportacao_produto1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pe.valor_exportacao_produto1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pe.valor_exportacao_produto1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pe.valor_exportacao_produto1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pe.valor_exportacao_produto1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_exportacao_produto1unid,
    pais.pais_exportacao1,
    round(pais.valor_pais_exportacao1_raw /
        CASE
            WHEN abs(pais.valor_pais_exportacao1_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_exportacao1,
        CASE
            WHEN abs(pais.valor_pais_exportacao1_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao1_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao1_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao1_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao1_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_exportacaounid1,
    pais.pais_exportacao2,
    round(pais.valor_pais_exportacao2_raw /
        CASE
            WHEN abs(pais.valor_pais_exportacao2_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_exportacao2,
        CASE
            WHEN abs(pais.valor_pais_exportacao2_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao2_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao2_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao2_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao2_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_exportacaounid2,
    pais.pais_exportacao3,
    round(pais.valor_pais_exportacao3_raw /
        CASE
            WHEN abs(pais.valor_pais_exportacao3_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_exportacao3,
        CASE
            WHEN abs(pais.valor_pais_exportacao3_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao3_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao3_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao3_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao3_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_exportacaounid3,
    pais.pais_exportacao4,
    round(pais.valor_pais_exportacao4_raw /
        CASE
            WHEN abs(pais.valor_pais_exportacao4_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_pais_exportacao4,
        CASE
            WHEN abs(pais.valor_pais_exportacao4_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao4_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao4_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(pais.valor_pais_exportacao4_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(pais.valor_pais_exportacao4_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_pais_exportacaounid4,
        CASE
            WHEN pais.paises_exportacao_restantes IS NULL THEN NULL::text
            WHEN cardinality(pais.paises_exportacao_restantes) = 1 THEN pais.paises_exportacao_restantes[1]
            ELSE (array_to_string(pais.paises_exportacao_restantes[1:cardinality(pais.paises_exportacao_restantes) - 1], ', '::text) || ' e '::text) || pais.paises_exportacao_restantes[cardinality(pais.paises_exportacao_restantes)]
        END AS pais_exportacao6destino,
        CASE
            WHEN com.cd_mun IS NULL THEN 'Não há dados'::text
            WHEN (com.fob_exportado_raw - com.fob_importado_raw) > 0::numeric THEN 'superávit'::text
            WHEN (com.fob_exportado_raw - com.fob_importado_raw) < 0::numeric THEN 'déficit'::text
            ELSE 'saldo zero'::text
        END AS analise_balanca1,
    round((com.fob_exportado_raw - com.fob_importado_raw) /
        CASE
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_balanca1,
        CASE
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw - com.fob_importado_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw - com.fob_importado_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(com.fob_exportado_raw - com.fob_importado_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_balanca1unid,
    round(bs.valor_balanca6meses_raw /
        CASE
            WHEN abs(bs.valor_balanca6meses_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2) AS valor_balanca6meses,
        CASE
            WHEN abs(bs.valor_balanca6meses_raw) >= '1000000000000'::bigint::numeric THEN
            CASE
                WHEN round(abs(bs.valor_balanca6meses_raw) / '1000000000000'::bigint::numeric, 2) >= 2::numeric THEN 'trilhões'::text
                ELSE 'trilhão'::text
            END
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000000000::numeric THEN
            CASE
                WHEN round(abs(bs.valor_balanca6meses_raw) / 1000000000::numeric, 2) >= 2::numeric THEN 'bilhões'::text
                ELSE 'bilhão'::text
            END
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000000::numeric THEN
            CASE
                WHEN round(abs(bs.valor_balanca6meses_raw) / 1000000::numeric, 2) >= 2::numeric THEN 'milhões'::text
                ELSE 'milhão'::text
            END
            WHEN abs(bs.valor_balanca6meses_raw) >= 1000::numeric THEN 'mil'::text
            ELSE ''::text
        END AS valor_balanca6mesesunid,
    round(bm.valor_balanca_jan, 2) AS valor_balanca_jan,
    round(bm.valor_balanca_fev, 2) AS valor_balanca_fev,
    round(bm.valor_balanca_mar, 2) AS valor_balanca_mar,
    round(bm.valor_balanca_abr, 2) AS valor_balanca_abr,
    round(bm.valor_balanca_mai, 2) AS valor_balanca_mai,
    round(bm.valor_balanca_jun, 2) AS valor_balanca_jun,
        CASE
            WHEN bs.valor_balanca6meses_raw IS NULL THEN 'Não há dados'::text
            WHEN bs.valor_balanca6meses_raw > 0::numeric THEN 'positivo'::text
            WHEN bs.valor_balanca6meses_raw < 0::numeric THEN 'negativo'::text
            ELSE 'zero'::text
        END AS analise_balanca2,
    'Emprego e Renda'::text AS boletim1,
    'https://datanordeste.sudene.gov.br/boletim/4stpvtzkvFG1G5yZTNVz12'::text AS boletim1_link,
    'Emprego (2004 a 2015)'::text AS boletim2,
    'https://datanordeste.sudene.gov.br/boletim/43EWIrip3GP1CFmpxwkYyC'::text AS boletim2_link,
    'Importação vs Exportação'::text AS painel1,
    'https://datanordeste.sudene.gov.br/data-panel/importacao_exportacao'::text AS painel1_link,
    'Produto Interno Bruto'::text AS painel2,
    'https://datanordeste.sudene.gov.br/data-panel/pib'::text AS painel2_link,
    'Exportação'::text AS painel3,
    'https://datanordeste.sudene.gov.br/data-panel/exportacao'::text AS painel3_link,
    'Importação'::text AS painel4,
    'https://datanordeste.sudene.gov.br/data-panel/importacao'::text AS painel4_link,
    round(bm.valor_balanca_jul, 2) AS valor_balanca_jul,
    round(bm.valor_balanca_ago, 2) AS valor_balanca_ago,
    round(bm.valor_balanca_set, 2) AS valor_balanca_set,
    round(bm.valor_balanca_out, 2) AS valor_balanca_out,
    round(bm.valor_balanca_nov, 2) AS valor_balanca_nov,
    round(bm.valor_balanca_dez, 2) AS valor_balanca_dez,
    abs(round((com.fob_exportado_raw - com.fob_importado_raw) /
        CASE
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= '1000000000000'::bigint::numeric THEN '1000000000000'::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000000::numeric THEN 1000000000::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000000::numeric THEN 1000000::bigint
            WHEN abs(com.fob_exportado_raw - com.fob_importado_raw) >= 1000::numeric THEN 1000::bigint
            ELSE 1::bigint
        END::numeric, 2)) AS valor_balanca1_abs
   FROM municipios m
     LEFT JOIN pib_escala p ON p.cd_mun = m.cd_mun
     LEFT JOIN setores s ON s.cd_mun = m.cd_mun
     LEFT JOIN comercio_ultimo com ON com.cd_mun = m.cd_mun
     LEFT JOIN paises pais ON pais.cd_mun = m.cd_mun
     LEFT JOIN secoes_importacao si ON si.cd_mun = m.cd_mun
     LEFT JOIN secoes_exportacao se ON se.cd_mun = m.cd_mun
     LEFT JOIN produto_importacao_valor piv ON piv.cd_mun = m.cd_mun
     LEFT JOIN produto_importacao_kg pik ON pik.cd_mun = m.cd_mun
     LEFT JOIN produto_exportacao pe ON pe.cd_mun = m.cd_mun
     LEFT JOIN importacao_janjun ij ON ij.cd_mun = m.cd_mun
     LEFT JOIN balanca_semestre bs ON bs.cd_mun = m.cd_mun
     LEFT JOIN balanca_mensal bm ON bm.cd_mun = m.cd_mun
     CROSS JOIN periodo_ultimo pu
     CROSS JOIN ultimo_junho uj;

ALTER DATABASE oca_db SET jit = off;
