-- Rollback de 2026-09-29-vw_perfil_desen_social_municipal.sql: definição de
-- relatorios_auto.vw_perfil_desen_social_municipal lida do banco do beta em
-- 29/09/2026 (pg_get_viewdef), antes da mudança.

CREATE OR REPLACE VIEW relatorios_auto.vw_perfil_desen_social_municipal AS
 WITH historico_idhm AS (
         SELECT vw_idhm.cd_mun,
            COALESCE(max(vw_idhm.nm_mun::text) FILTER (WHERE vw_idhm.ano = 2010), max(vw_idhm.nm_mun::text)) AS nm_mun,
            COALESCE(max(vw_idhm.uf::text) FILTER (WHERE vw_idhm.ano = 2010), max(vw_idhm.uf::text)) AS estado,
            COALESCE(max(vw_idhm.sigla_uf::text) FILTER (WHERE vw_idhm.ano = 2010), max(vw_idhm.sigla_uf::text)) AS sigla_uf,
            max(vw_idhm.idhm) FILTER (WHERE vw_idhm.ano = 1991) AS idhm_1991,
            max(vw_idhm.idhm) FILTER (WHERE vw_idhm.ano = 2000) AS idhm_2000,
            max(vw_idhm.idhm) FILTER (WHERE vw_idhm.ano = 2010) AS idhm_2010,
            max(vw_idhm.idhm_educacao) FILTER (WHERE vw_idhm.ano = 2010) AS idhm_educacao_2010,
            max(vw_idhm.idhm_longevidade) FILTER (WHERE vw_idhm.ano = 2010) AS idhm_longevidade_2010,
            max(vw_idhm.idhm_renda) FILTER (WHERE vw_idhm.ano = 2010) AS idhm_renda_2010,
            max(vw_idhm.indice_gini) FILTER (WHERE vw_idhm.ano = 1991) AS gini_1991,
            max(vw_idhm.indice_gini) FILTER (WHERE vw_idhm.ano = 2010) AS gini_2010,
            max(vw_idhm.renda_per_capita) FILTER (WHERE vw_idhm.ano = 2010) AS renda_2010
           FROM des_idhm.vw_idhm
          WHERE vw_idhm.ano = ANY (ARRAY[1991, 2000, 2010])
          GROUP BY vw_idhm.cd_mun
        ), bolsa_familia_2013 AS (
         SELECT "left"(pop.cd_mun::text, 6) AS cd_mun_6,
            max(pbf.beneficiarios_ate_2021::numeric) AS beneficiarios_2013,
            max(pop.pop_2013::numeric) AS populacao_2013
           FROM carac_mun.populacao_estimada pop
             LEFT JOIN des_bolsa_familia.pessoas_pbf pbf ON pbf.cd_mun::text = "left"(pop.cd_mun::text, 6) AND pbf.ano::text = '12/2013'::text
          GROUP BY ("left"(pop.cd_mun::text, 6))
        ), indicadores AS (
         SELECT h.cd_mun,
            h.nm_mun,
            h.estado,
            h.sigla_uf,
            h.idhm_1991,
            h.idhm_2000,
            h.idhm_2010,
            h.gini_1991,
            h.gini_2010,
            h.renda_2010,
            bf.beneficiarios_2013,
            bf.populacao_2013,
            componentes.componente1,
            componentes.valor_componente1,
            componentes.componente2,
            componentes.valor_componente2,
            componentes.componente3,
            componentes.valor_componente3
           FROM historico_idhm h
             LEFT JOIN bolsa_familia_2013 bf ON "left"(h.cd_mun::text, 6) = bf.cd_mun_6
             LEFT JOIN LATERAL ( SELECT max(ranking_componentes.nome_componente) FILTER (WHERE ranking_componentes.posicao = 1) AS componente1,
                    max(ranking_componentes.valor_componente) FILTER (WHERE ranking_componentes.posicao = 1) AS valor_componente1,
                    max(ranking_componentes.nome_componente) FILTER (WHERE ranking_componentes.posicao = 2) AS componente2,
                    max(ranking_componentes.valor_componente) FILTER (WHERE ranking_componentes.posicao = 2) AS valor_componente2,
                    max(ranking_componentes.nome_componente) FILTER (WHERE ranking_componentes.posicao = 3) AS componente3,
                    max(ranking_componentes.valor_componente) FILTER (WHERE ranking_componentes.posicao = 3) AS valor_componente3
                   FROM ( SELECT valores_componentes.nome_componente,
                            valores_componentes.valor_componente,
                            row_number() OVER (ORDER BY valores_componentes.valor_componente DESC NULLS LAST, valores_componentes.prioridade) AS posicao
                           FROM ( VALUES (1,'Educação'::text,h.idhm_educacao_2010), (2,'Longevidade'::text,h.idhm_longevidade_2010), (3,'Renda'::text,h.idhm_renda_2010)) valores_componentes(prioridade, nome_componente, valor_componente)
                          WHERE valores_componentes.valor_componente IS NOT NULL) ranking_componentes) componentes ON true
        )
 SELECT nm_mun,
    estado,
    sigla_uf,
    round(idhm_1991, 3) AS idhm_1991,
    round(idhm_2000, 3) AS idhm_2000,
    round(idhm_2010, 3) AS idhm_2010,
        CASE
            WHEN idhm_2010 IS NULL THEN 'sem dados'::text
            WHEN idhm_2010 < 0.50 THEN 'muito baixo'::text
            WHEN idhm_2010 < 0.60 THEN 'baixo'::text
            WHEN idhm_2010 < 0.70 THEN 'médio'::text
            WHEN idhm_2010 < 0.80 THEN 'alto'::text
            ELSE 'muito alto'::text
        END AS idhm_classe_2010,
    lower(componente1) AS nomesubindice1_2010,
    round(valor_componente1, 3) AS subindice1_2010,
    lower(componente2) AS nomesubindice2_2010,
    round(valor_componente2, 3) AS subindice2_2010,
    lower(componente3) AS nomesubindice3_2010,
    round(valor_componente3, 3) AS subindice3_2010,
        CASE
            WHEN idhm_1991 IS NULL OR idhm_2010 IS NULL THEN 'sem dados'::text
            WHEN idhm_2010 > idhm_1991 THEN 'crescimento'::text
            WHEN idhm_2010 < idhm_1991 THEN 'diminuição'::text
            ELSE 'sem alteração'::text
        END AS analise1_idhm,
    round((idhm_2010 - idhm_1991) / NULLIF(idhm_1991, 0::numeric) * 100::numeric, 2) AS var_idhm_per_1991_2010,
    round(gini_2010, 3) AS gini_2010,
    round(renda_2010, 2) AS renda_2010,
    round(beneficiarios_2013 / NULLIF(populacao_2013, 0::numeric) * 100::numeric, 2) AS bolsa_familia_per_2013,
        CASE
            WHEN idhm_1991 IS NULL OR idhm_2010 IS NULL OR gini_1991 IS NULL OR gini_2010 IS NULL THEN 'sem dados'::text
            WHEN idhm_2010 > idhm_1991 AND gini_2010 < gini_1991 THEN 'melhoria do desenvolvimento humano'::text
            WHEN idhm_2010 > idhm_1991 AND gini_2010 > gini_1991 THEN 'melhoria do IDHM com aumento da desigualdade de renda'::text
            WHEN idhm_2010 < idhm_1991 AND gini_2010 < gini_1991 THEN 'piora no desenvolvimento humano'::text
            WHEN idhm_2010 < idhm_1991 AND gini_2010 > gini_1991 THEN 'piora no desenvolvimento humano e na equidade'::text
            WHEN idhm_2010 = idhm_1991 AND gini_2010 < gini_1991 THEN 'melhoria na equidade'::text
            WHEN idhm_2010 = idhm_1991 AND gini_2010 > gini_1991 THEN 'piora na equidade'::text
            ELSE 'manutenção do desenvolvimento humano'::text
        END AS analise2_idhm,
        CASE
            WHEN gini_2010 IS NULL THEN ''::text
            WHEN gini_2010 >= 0.5 THEN 'índice de Gini'::text
            ELSE ''::text
        END AS analise_gini_2010,
    'Índice de Desenvolvimento Humano Municipal (IDHM)'::text AS nm_painel1,
    'https://datanordeste.sudene.gov.br/data-panel/idhm'::text AS link_painel1,
    'Explore Nordeste: Socioeconômico'::text AS nm_datastory1,
    'https://datanordeste.sudene.gov.br/data-stories/2072ff402a554914b16074fd440e2159'::text AS link_datastory1,
    'Emprego e Rendimento'::text AS nm_boletim1,
    'https://datanordeste.sudene.gov.br/boletim/4stpvtzkvFG1G5yZTNVz12'::text AS link_boletim1
   FROM indicadores;
