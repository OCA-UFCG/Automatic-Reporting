-- relatorios_auto.ambiente: percentuais de aridez e de ASD na mesma base,
-- separador de milhar nas variações e "Área Marinha" fora da lista de biomas.
-- APLICADO no banco do beta (oca_db) em 2026-09-30; prod não (revisão de Meio
-- Ambiente, 30/09/2026). Rollback em
-- 2026-09-30-ambiente.rollback.sql (definição lida do beta em 30/09, antes
-- desta mudança).
--
-- Nenhuma coluna muda de nome, posição ou tipo, e a view não tem dependentes
-- (nem matview): CREATE OR REPLACE passa e o efeito é imediato. Validado
-- criando esta definição num schema à parte (ar_validacao) e comparando com a
-- atual nos 2.074 municípios: nenhum ano soma mais de 100% (classes + sem
-- dados), asd_per bate com a soma árida + semiárida + subúmida, nenhum
-- município passa a ter ou deixa de ter ASD (as condições do Doc em
-- asd_per_2021 = 0 / > 0 não mudam) e area_sem_dados* não muda em nenhum.
--
-- 1. Base comum dos percentuais (aridez_base_comum). asd_per era calculado
--    sobre a área classificada e as classes sobre a área do município, e as
--    duas saíam como "% do território municipal" no mesmo parágrafo: Icapuí
--    tinha 100% de ASD com 20% do território sem dado, Rio do Fogo 81,91% com
--    45,80% na única classe suscetível (115 municípios com diferença >= 1 p.p.).
--    Onde o polígono das classes é maior que o território (443 municípios), as
--    classes passavam de 100% (Lucrécia: 99,66% + 3,99%; 308 municípios). A
--    base agora é GREATEST(área do município, classificado 1991, classificado
--    2021), a mesma para classes, ranking, comparação, ASD e "área restante".
--    area_mun, area_diferenca* e aridez_fechamento* continuam contra a área
--    do município (são diagnóstico). area_sem_dados* segue NULL quando é zero,
--    senão o gráfico (plotting/meio_ambiente.py) ganharia uma barra
--    "Sem dados 0,00%".
--
-- 2. Variações dos textos de aridez com separador de milhar: "75874,02%" ->
--    "75.874,02%" (95 municípios com variação >= 1.000%).
--
-- 3. "Área Marinha" não é bioma: "inseridas nos biomas Área Marinha e
--    Caatinga" -> "inserida no bioma Caatinga, com parte em área marinha"
--    (164 municípios). A frase continua começando por "inserida(s) no(s)
--    bioma(s)", que é o que _PARTICIPIO_BIOMA (services/generation.py)
--    procura para concordar o particípio com n_uc.

CREATE OR REPLACE VIEW relatorios_auto.ambiente AS
 SELECT COALESCE(nn.nm_mun::text, q.nm_mun) AS nm_mun,
    q.estado,
    q.sigla_uf,
    q.ano,
    q.n_uc,
    q.nome_uc,
    q.area_total_uc,
    q.bioma,
    q.ano_criacao_uc1,
    q.esfera_1uc,
    q.categoria_uc1,
    q.grupo_uc1,
    q.n_protecao_pi,
    q.n_protecao_us,
    q.area_mun,
    q.area_semiarida1991,
    q.area_subumida1991,
    q.area_arida1991,
    q.area_umida1991,
    q.area_semiarida2021,
    q.area_subumida2021,
    q.area_arida2021,
    q.area_umida2021,
    q.area_semiarida1991_per,
    q.area_subumida1991_per,
    q.area_arida1991_per,
    q.area_umida1991_per,
    q.area_semiarida2021_per,
    q.area_subumida2021_per,
    q.area_arida2021_per,
    q.area_umida2021_per,
    q.aridez_cond1_1991,
    q.aridez_cond2_1991,
    q.aridez_cond3_1991,
    q.aridez_cond4_1991,
    q.aridez_cond1_area1991,
    q.aridez_cond2_area1991,
    q.aridez_cond3_area1991,
    q.aridez_cond4_area1991,
    q.aridez_cond1_areaper1991,
    q.aridez_cond2_areaper1991,
    q.aridez_cond3_areaper1991,
    q.aridez_cond4_areaper1991,
    q.aridez_cond1_2021,
    q.aridez_cond2_2021,
    q.aridez_cond3_2021,
    q.aridez_cond4_2021,
    q.aridez_cond1_area2021,
    q.aridez_cond2_area2021,
    q.aridez_cond3_area2021,
    q.aridez_cond4_area2021,
    q.aridez_cond1_areaper2021,
    q.aridez_cond2_areaper2021,
    q.aridez_cond3_areaper2021,
    q.aridez_cond4_areaper2021,
    q.aridez_comp_cond1_area2021,
    q.aridez_comp_cond2_area2021,
    q.aridez_comp_cond3_area2021,
    q.aridez_comp_cond4_area2021,
    q.aridez_comp_cond1_areaper2021,
    q.aridez_comp_cond2_areaper2021,
    q.aridez_comp_cond3_areaper2021,
    q.aridez_comp_cond4_areaper2021,
    q.var_aridez_cond1_1991_2021,
    q.var_aridez_cond2_1991_2021,
    q.var_aridez_cond3_1991_2021,
    q.var_aridez_cond4_1991_2021,
    q.analise_cond1,
    q.analise_cond2,
    q.analise_cond3,
    q.analise_cond4,
    q.aridez_texto_condicao1991,
    q.aridez_texto_condicao2021,
    q.asd_2021,
    q.asd_per_2021,
    q.asd_1991,
    q.asd_per_1991,
    q.analise_asd_per1991_2021,
    q.analise_aridez,
    q.painel1,
    q.painel1_link,
    q.painel2,
    q.painel2_link,
    q.boletim1,
    q.boletim1_link,
    q.cd_mun,
    q.area_mun_origem1991,
    q.area_classificada1991,
    q.area_diferenca1991,
    q.area_sem_dados1991,
    q.area_sem_dados1991_per,
    q.area_total_aridez1991,
    q.aridez_fechamento1991,
    q.area_mun_origem2021,
    q.area_classificada2021,
    q.area_diferenca2021,
    q.area_sem_dados2021,
    q.area_sem_dados2021_per,
    q.area_total_aridez2021,
    q.aridez_fechamento2021
   FROM ( WITH municipios_universo AS (
                 SELECT DISTINCT btrim(vw_pib.cd_mun::text)::integer AS cd_mun
                   FROM eco_pib.vw_pib
                  WHERE vw_pib.ano = 2023 AND vw_pib.cd_mun IS NOT NULL AND btrim(vw_pib.cd_mun::text) ~ '^[0-9]+$'::text
                ), municipios AS (
                 SELECT u.cd_mun,
                    max(c.nm_mun::text) AS nm_mun,
                    max(c.estado::text) AS estado,
                    max(c.sigla_uf::text) AS sigla_uf
                   FROM municipios_universo u
                     LEFT JOIN carac_mun.caracteristicas_municipais c ON btrim(c.cd_mun::text) = u.cd_mun::text
                  GROUP BY u.cd_mun
                ), aridez_1991_base AS (
                 SELECT vw_aridez.cd_mun,
                    max(vw_aridez.area_km2_territorio) AS area_mun,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '2'::text), 0::numeric) AS area_arida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '3'::text), 0::numeric) AS area_semiarida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '4'::text), 0::numeric) AS area_subumida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '5'::text), 0::numeric) AS area_umida
                   FROM meio_aridez.vw_aridez
                  WHERE vw_aridez.ano_consolidacao = 1991
                  GROUP BY vw_aridez.cd_mun
                ), aridez_2021_base AS (
                 SELECT vw_aridez.cd_mun,
                    max(vw_aridez.area_km2_territorio) AS area_mun,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '2'::text), 0::numeric) AS area_arida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '3'::text), 0::numeric) AS area_semiarida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '4'::text), 0::numeric) AS area_subumida,
                    COALESCE(sum(vw_aridez.area_km2_classe) FILTER (WHERE vw_aridez.dn_uni::text = '5'::text), 0::numeric) AS area_umida
                   FROM meio_aridez.vw_aridez
                  WHERE vw_aridez.ano_consolidacao = 2021
                  GROUP BY vw_aridez.cd_mun
                ), aridez_base_comum AS (
                 SELECT COALESCE(b21.cd_mun, b91.cd_mun) AS cd_mun,
                    GREATEST(COALESCE(b21.area_mun, b91.area_mun), b91.area_arida + b91.area_semiarida + b91.area_subumida + b91.area_umida, b21.area_arida + b21.area_semiarida + b21.area_subumida + b21.area_umida) AS area_base
                   FROM aridez_1991_base b91
                     FULL JOIN aridez_2021_base b21 ON b21.cd_mun = b91.cd_mun
                ), aridez_1991 AS (
                 SELECT a.cd_mun,
                    a.area_mun,
                    c.area_base,
                    a.area_arida,
                    a.area_semiarida,
                    a.area_subumida,
                    a.area_umida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_semiarida / c.area_base * 100::numeric, 2)))
                        END AS per_semiarida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_subumida / c.area_base * 100::numeric, 2)))
                        END AS per_subumida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_arida / c.area_base * 100::numeric, 2)))
                        END AS per_arida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_umida / c.area_base * 100::numeric, 2)))
                        END AS per_umida,
                    a.area_arida + a.area_semiarida + a.area_subumida AS asd,
                        CASE
                            WHEN (a.area_arida + a.area_semiarida + a.area_subumida + a.area_umida) = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, round((a.area_arida + a.area_semiarida + a.area_subumida) / NULLIF(c.area_base, 0::numeric) * 100::numeric, 2))
                        END AS asd_per
                   FROM aridez_1991_base a
                     JOIN aridez_base_comum c ON c.cd_mun = a.cd_mun
                ), aridez_2021 AS (
                 SELECT a.cd_mun,
                    a.area_mun,
                    c.area_base,
                    a.area_arida,
                    a.area_semiarida,
                    a.area_subumida,
                    a.area_umida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_semiarida / c.area_base * 100::numeric, 2)))
                        END AS per_semiarida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_subumida / c.area_base * 100::numeric, 2)))
                        END AS per_subumida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_arida / c.area_base * 100::numeric, 2)))
                        END AS per_arida,
                        CASE
                            WHEN c.area_base IS NULL OR c.area_base = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(a.area_umida / c.area_base * 100::numeric, 2)))
                        END AS per_umida,
                    a.area_arida + a.area_semiarida + a.area_subumida AS asd,
                        CASE
                            WHEN (a.area_arida + a.area_semiarida + a.area_subumida + a.area_umida) = 0::numeric THEN NULL::numeric
                            ELSE LEAST(100::numeric, round((a.area_arida + a.area_semiarida + a.area_subumida) / NULLIF(c.area_base, 0::numeric) * 100::numeric, 2))
                        END AS asd_per
                   FROM aridez_2021_base a
                     JOIN aridez_base_comum c ON c.cd_mun = a.cd_mun
                ), aridez_1991_unpivot AS (
                 SELECT a.cd_mun,
                    a.area_base AS area_mun,
                    v.classe,
                    v.area
                   FROM aridez_1991 a
                     CROSS JOIN LATERAL ( VALUES ('Árida'::text,a.area_arida), ('Semiárida'::text,a.area_semiarida), ('Subúmida seca'::text,a.area_subumida), ('Úmida'::text,a.area_umida)) v(classe, area)
                ), aridez_1991_ranked AS (
                 SELECT aridez_1991_unpivot.cd_mun,
                    aridez_1991_unpivot.area_mun,
                    aridez_1991_unpivot.classe,
                    aridez_1991_unpivot.area,
                    row_number() OVER (PARTITION BY aridez_1991_unpivot.cd_mun ORDER BY aridez_1991_unpivot.area DESC, aridez_1991_unpivot.classe) AS rn
                   FROM aridez_1991_unpivot
                  WHERE aridez_1991_unpivot.area > 0::numeric
                ), aridez_1991_pivot AS (
                 SELECT aridez_1991_ranked.cd_mun,
                    max(aridez_1991_ranked.classe) FILTER (WHERE aridez_1991_ranked.rn = 1) AS aridez_cond1_1991,
                    max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 1) AS aridez_cond1_area1991,
                        CASE
                            WHEN max(aridez_1991_ranked.area_mun) IS NULL OR max(aridez_1991_ranked.area_mun) = 0::numeric OR max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 1) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 1) / max(aridez_1991_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond1_areaper1991,
                    max(aridez_1991_ranked.classe) FILTER (WHERE aridez_1991_ranked.rn = 2) AS aridez_cond2_1991,
                    max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 2) AS aridez_cond2_area1991,
                        CASE
                            WHEN max(aridez_1991_ranked.area_mun) IS NULL OR max(aridez_1991_ranked.area_mun) = 0::numeric OR max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 2) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 2) / max(aridez_1991_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond2_areaper1991,
                    max(aridez_1991_ranked.classe) FILTER (WHERE aridez_1991_ranked.rn = 3) AS aridez_cond3_1991,
                    max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 3) AS aridez_cond3_area1991,
                        CASE
                            WHEN max(aridez_1991_ranked.area_mun) IS NULL OR max(aridez_1991_ranked.area_mun) = 0::numeric OR max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 3) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 3) / max(aridez_1991_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond3_areaper1991,
                    max(aridez_1991_ranked.classe) FILTER (WHERE aridez_1991_ranked.rn = 4) AS aridez_cond4_1991,
                    max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 4) AS aridez_cond4_area1991,
                        CASE
                            WHEN max(aridez_1991_ranked.area_mun) IS NULL OR max(aridez_1991_ranked.area_mun) = 0::numeric OR max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 4) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_1991_ranked.area) FILTER (WHERE aridez_1991_ranked.rn = 4) / max(aridez_1991_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond4_areaper1991
                   FROM aridez_1991_ranked
                  GROUP BY aridez_1991_ranked.cd_mun
                ), aridez_2021_unpivot AS (
                 SELECT a.cd_mun,
                    a.area_base AS area_mun,
                    v.classe,
                    v.area
                   FROM aridez_2021 a
                     CROSS JOIN LATERAL ( VALUES ('Árida'::text,a.area_arida), ('Semiárida'::text,a.area_semiarida), ('Subúmida seca'::text,a.area_subumida), ('Úmida'::text,a.area_umida)) v(classe, area)
                ), aridez_2021_ranked AS (
                 SELECT aridez_2021_unpivot.cd_mun,
                    aridez_2021_unpivot.area_mun,
                    aridez_2021_unpivot.classe,
                    aridez_2021_unpivot.area,
                    row_number() OVER (PARTITION BY aridez_2021_unpivot.cd_mun ORDER BY aridez_2021_unpivot.area DESC, aridez_2021_unpivot.classe) AS rn
                   FROM aridez_2021_unpivot
                  WHERE aridez_2021_unpivot.area > 0::numeric
                ), aridez_2021_pivot AS (
                 SELECT aridez_2021_ranked.cd_mun,
                    max(aridez_2021_ranked.classe) FILTER (WHERE aridez_2021_ranked.rn = 1) AS aridez_cond1_2021,
                    max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 1) AS aridez_cond1_area2021,
                        CASE
                            WHEN max(aridez_2021_ranked.area_mun) IS NULL OR max(aridez_2021_ranked.area_mun) = 0::numeric OR max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 1) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 1) / max(aridez_2021_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond1_areaper2021,
                    max(aridez_2021_ranked.classe) FILTER (WHERE aridez_2021_ranked.rn = 2) AS aridez_cond2_2021,
                    max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 2) AS aridez_cond2_area2021,
                        CASE
                            WHEN max(aridez_2021_ranked.area_mun) IS NULL OR max(aridez_2021_ranked.area_mun) = 0::numeric OR max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 2) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 2) / max(aridez_2021_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond2_areaper2021,
                    max(aridez_2021_ranked.classe) FILTER (WHERE aridez_2021_ranked.rn = 3) AS aridez_cond3_2021,
                    max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 3) AS aridez_cond3_area2021,
                        CASE
                            WHEN max(aridez_2021_ranked.area_mun) IS NULL OR max(aridez_2021_ranked.area_mun) = 0::numeric OR max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 3) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 3) / max(aridez_2021_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond3_areaper2021,
                    max(aridez_2021_ranked.classe) FILTER (WHERE aridez_2021_ranked.rn = 4) AS aridez_cond4_2021,
                    max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 4) AS aridez_cond4_area2021,
                        CASE
                            WHEN max(aridez_2021_ranked.area_mun) IS NULL OR max(aridez_2021_ranked.area_mun) = 0::numeric OR max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 4) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(aridez_2021_ranked.area) FILTER (WHERE aridez_2021_ranked.rn = 4) / max(aridez_2021_ranked.area_mun) * 100::numeric, 2)))
                        END AS aridez_cond4_areaper2021
                   FROM aridez_2021_ranked
                  GROUP BY aridez_2021_ranked.cd_mun
                ), aridez_texto_comparacao AS (
                 SELECT p.cd_mun,
                    max(
                        CASE
                            WHEN u.classe = p.aridez_cond1_1991 THEN u.area
                            ELSE NULL::numeric
                        END) AS aridez_comp_cond1_area2021,
                        CASE
                            WHEN max(u.area_mun) IS NULL OR max(u.area_mun) = 0::numeric OR max(
                            CASE
                                WHEN u.classe = p.aridez_cond1_1991 THEN u.area
                                ELSE NULL::numeric
                            END) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(
                            CASE
                                WHEN u.classe = p.aridez_cond1_1991 THEN u.area
                                ELSE NULL::numeric
                            END) / max(u.area_mun) * 100::numeric, 2)))
                        END AS aridez_comp_cond1_areaper2021,
                    max(
                        CASE
                            WHEN u.classe = p.aridez_cond2_1991 THEN u.area
                            ELSE NULL::numeric
                        END) AS aridez_comp_cond2_area2021,
                        CASE
                            WHEN max(u.area_mun) IS NULL OR max(u.area_mun) = 0::numeric OR max(
                            CASE
                                WHEN u.classe = p.aridez_cond2_1991 THEN u.area
                                ELSE NULL::numeric
                            END) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(
                            CASE
                                WHEN u.classe = p.aridez_cond2_1991 THEN u.area
                                ELSE NULL::numeric
                            END) / max(u.area_mun) * 100::numeric, 2)))
                        END AS aridez_comp_cond2_areaper2021,
                    max(
                        CASE
                            WHEN u.classe = p.aridez_cond3_1991 THEN u.area
                            ELSE NULL::numeric
                        END) AS aridez_comp_cond3_area2021,
                        CASE
                            WHEN max(u.area_mun) IS NULL OR max(u.area_mun) = 0::numeric OR max(
                            CASE
                                WHEN u.classe = p.aridez_cond3_1991 THEN u.area
                                ELSE NULL::numeric
                            END) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(
                            CASE
                                WHEN u.classe = p.aridez_cond3_1991 THEN u.area
                                ELSE NULL::numeric
                            END) / max(u.area_mun) * 100::numeric, 2)))
                        END AS aridez_comp_cond3_areaper2021,
                    max(
                        CASE
                            WHEN u.classe = p.aridez_cond4_1991 THEN u.area
                            ELSE NULL::numeric
                        END) AS aridez_comp_cond4_area2021,
                        CASE
                            WHEN max(u.area_mun) IS NULL OR max(u.area_mun) = 0::numeric OR max(
                            CASE
                                WHEN u.classe = p.aridez_cond4_1991 THEN u.area
                                ELSE NULL::numeric
                            END) IS NULL THEN NULL::numeric
                            ELSE LEAST(100::numeric, GREATEST(0::numeric, round(max(
                            CASE
                                WHEN u.classe = p.aridez_cond4_1991 THEN u.area
                                ELSE NULL::numeric
                            END) / max(u.area_mun) * 100::numeric, 2)))
                        END AS aridez_comp_cond4_areaper2021
                   FROM aridez_1991_pivot p
                     LEFT JOIN aridez_2021_unpivot u ON u.cd_mun = p.cd_mun
                  GROUP BY p.cd_mun
                ), aridez_fechamento_base AS (
                 SELECT m_1.cd_mun,
                    COALESCE(a2021_1.area_mun, a1991_1.area_mun) AS area_mun,
                    c_1.area_base,
                    a1991_1.area_mun AS area_mun_origem1991,
                    a1991_1.area_arida + a1991_1.area_semiarida + a1991_1.area_subumida + a1991_1.area_umida AS area_classificada1991,
                    COALESCE(a2021_1.area_mun, a1991_1.area_mun) - (a1991_1.area_arida + a1991_1.area_semiarida + a1991_1.area_subumida + a1991_1.area_umida) AS area_diferenca1991,
                    a2021_1.area_mun AS area_mun_origem2021,
                    a2021_1.area_arida + a2021_1.area_semiarida + a2021_1.area_subumida + a2021_1.area_umida AS area_classificada2021,
                    COALESCE(a2021_1.area_mun, a1991_1.area_mun) - (a2021_1.area_arida + a2021_1.area_semiarida + a2021_1.area_subumida + a2021_1.area_umida) AS area_diferenca2021
                   FROM municipios m_1
                     LEFT JOIN aridez_1991 a1991_1 ON a1991_1.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_2021 a2021_1 ON a2021_1.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_base_comum c_1 ON c_1.cd_mun = m_1.cd_mun
                ), aridez_fechamento AS (
                 SELECT f_1.cd_mun,
                    f_1.area_mun,
                    f_1.area_base,
                    f_1.area_mun_origem1991,
                    f_1.area_classificada1991,
                    f_1.area_diferenca1991,
                    f_1.area_mun_origem2021,
                    f_1.area_classificada2021,
                    f_1.area_diferenca2021,
                        CASE
                            WHEN f_1.area_classificada1991 IS NULL THEN NULL::numeric
                            ELSE NULLIF(GREATEST(0::numeric, f_1.area_base - f_1.area_classificada1991), 0::numeric)
                        END AS area_sem_dados1991,
                        CASE
                            WHEN f_1.area_classificada2021 IS NULL THEN NULL::numeric
                            ELSE NULLIF(GREATEST(0::numeric, f_1.area_base - f_1.area_classificada2021), 0::numeric)
                        END AS area_sem_dados2021
                   FROM aridez_fechamento_base f_1
                ), aridez_narrativa_classes AS (
                 SELECT r.cd_mun,
                    1991 AS ano,
                    r.classe,
                    r.area,
                    r.rn,
                    lead(r.area, 1, 0::numeric) OVER (PARTITION BY r.cd_mun ORDER BY r.rn) AS proxima_area,
                    f_1.area_base AS area_mun,
                    NULL::numeric AS area1991
                   FROM aridez_1991_ranked r
                     JOIN aridez_fechamento f_1 ON f_1.cd_mun = r.cd_mun
                UNION ALL
                 SELECT r.cd_mun,
                    2021 AS ano,
                    r.classe,
                    r.area,
                    r.rn,
                    lead(r.area, 1, 0::numeric) OVER (PARTITION BY r.cd_mun ORDER BY r.rn) AS proxima_area,
                    f_1.area_base AS area_mun,
                    a.area AS area1991
                   FROM aridez_2021_ranked r
                     JOIN aridez_fechamento f_1 ON f_1.cd_mun = r.cd_mun
                     LEFT JOIN aridez_1991_unpivot a ON a.cd_mun = r.cd_mun AND a.classe = r.classe
                ), aridez_narrativa_trechos AS (
                 SELECT n.cd_mun,
                    n.ano,
                    n.classe,
                    n.area,
                    n.rn,
                    n.proxima_area,
                    n.area_mun,
                    n.area1991,
                    (((
                        CASE
                            WHEN n.rn = 1 AND n.area > n.proxima_area THEN ('predominava a condição '::text || lower(n.classe)) || ', que abrangia '::text
                            WHEN n.rn = 1 THEN ('não havia uma condição predominante única, pois as maiores áreas estavam empatadas. A condição '::text || lower(n.classe)) || ' ocupava '::text
                            ELSE ('A condição '::text || lower(n.classe)) || ' ocupava '::text
                        END || translate(to_char(round(n.area, 2), 'FM999,999,999,999,990.00'::text), ',.'::text, '.,'::text)) || ' km²'::text) ||
                        CASE
                            WHEN n.area_mun > 0::numeric THEN (' ('::text ||
                            CASE
                                WHEN n.area > 0::numeric AND (n.area / NULLIF(n.area_mun, 0::numeric) * 100::numeric) < 0.01 THEN 'menos de 0,01'::text
                                WHEN n.area < n.area_mun AND round(n.area / NULLIF(n.area_mun, 0::numeric) * 100::numeric, 2) = 100::numeric THEN 'aproximadamente 100'::text
                                ELSE replace(replace(round(LEAST(100::numeric, GREATEST(0::numeric, n.area / NULLIF(n.area_mun, 0::numeric) * 100::numeric)), 2)::text, '.'::text, ','::text), '100,00'::text, '100'::text)
                            END) ||
                            CASE
                                WHEN n.rn = 1 THEN '% do território municipal)'::text
                                ELSE '%)'::text
                            END
                            ELSE ''::text
                        END) ||
                        CASE
                            WHEN n.ano = 1991 THEN ''::text
                            WHEN n.area1991 IS NULL THEN ', sem dados de 1991 para comparação'::text
                            WHEN n.area1991 = 0::numeric THEN ', sem área registrada nessa condição em 1991'::text
                            WHEN n.area = n.area1991 THEN ', mantendo a mesma área registrada em 1991'::text
                            WHEN n.area > n.area1991 THEN (', representando um aumento de '::text || translate(to_char(round((n.area - n.area1991) / NULLIF(n.area1991, 0::numeric) * 100::numeric, 2), 'FM999,999,999,999,990.00'::text), ',.'::text, '.,'::text)) || '% em relação a 1991'::text
                            ELSE (', representando uma diminuição de '::text || translate(to_char(round((n.area1991 - n.area) / NULLIF(n.area1991, 0::numeric) * 100::numeric, 2), 'FM999,999,999,999,990.00'::text), ',.'::text, '.,'::text)) || '% em relação a 1991'::text
                        END AS trecho
                   FROM aridez_narrativa_classes n
                ), aridez_narrativa_lista AS (
                 SELECT aridez_narrativa_trechos.cd_mun,
                    aridez_narrativa_trechos.ano,
                    max(aridez_narrativa_trechos.trecho) FILTER (WHERE aridez_narrativa_trechos.rn = 1) AS primeiro,
                    string_agg(aridez_narrativa_trechos.trecho, '. '::text ORDER BY aridez_narrativa_trechos.rn) FILTER (WHERE aridez_narrativa_trechos.rn > 1) AS demais,
                    count(*) AS quantidade_classes
                   FROM aridez_narrativa_trechos
                  GROUP BY aridez_narrativa_trechos.cd_mun, aridez_narrativa_trechos.ano
                ), aridez_desaparecidas AS (
                 SELECT a.cd_mun,
                    string_agg(('A condição '::text || lower(a.classe)) || ' deixou de apresentar área registrada em 2021, uma diminuição de 100,00% em relação a 1991'::text, '. '::text ORDER BY a.area DESC, a.classe) AS descricao
                   FROM aridez_1991_unpivot a
                     JOIN aridez_2021_unpivot b ON b.cd_mun = a.cd_mun AND b.classe = a.classe
                  WHERE a.area > 0::numeric AND b.area = 0::numeric
                  GROUP BY a.cd_mun
                ), aridez_predominancia AS (
                 SELECT m_1.cd_mun,
                    a1991_1.cd_mun IS NOT NULL AS tem_dados1991,
                    a2021_1.cd_mun IS NOT NULL AS tem_dados2021,
                    p1991.aridez_cond1_1991 AS classe1991,
                    p2021.aridez_cond1_2021 AS classe2021,
                    COALESCE(p1991.aridez_cond1_area1991 > COALESCE(p1991.aridez_cond2_area1991, 0::numeric), false) AS predomina1991,
                    COALESCE(p2021.aridez_cond1_area2021 > COALESCE(p2021.aridez_cond2_area2021, 0::numeric), false) AS predomina2021
                   FROM municipios m_1
                     LEFT JOIN aridez_1991 a1991_1 ON a1991_1.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_2021 a2021_1 ON a2021_1.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_1991_pivot p1991 ON p1991.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_2021_pivot p2021 ON p2021.cd_mun = m_1.cd_mun
                ), aridez_conclusao_predominancia AS (
                 SELECT aridez_predominancia.cd_mun,
                        CASE
                            WHEN NOT aridez_predominancia.tem_dados2021 OR NOT aridez_predominancia.tem_dados1991 THEN NULL::text
                            WHEN aridez_predominancia.predomina1991 AND aridez_predominancia.predomina2021 AND aridez_predominancia.classe1991 = aridez_predominancia.classe2021 THEN 'Assim, a condição predominante permaneceu a mesma entre 1991 e 2021.'::text
                            WHEN aridez_predominancia.predomina1991 AND aridez_predominancia.predomina2021 THEN ((('Assim, a condição predominante mudou de '::text || lower(aridez_predominancia.classe1991)) || ', em 1991, para '::text) || lower(aridez_predominancia.classe2021)) || ', em 2021.'::text
                            WHEN aridez_predominancia.predomina2021 AND aridez_predominancia.classe1991 IS NOT NULL THEN ('Assim, a condição '::text || lower(aridez_predominancia.classe2021)) || ' passou a predominar em 2021, enquanto em 1991 havia empate entre as classes de maior área.'::text
                            WHEN aridez_predominancia.predomina2021 THEN 'Em 1991, não havia área registrada nas quatro classes para comparar a predominância.'::text
                            WHEN aridez_predominancia.predomina1991 AND aridez_predominancia.classe2021 IS NOT NULL THEN ('A condição '::text || lower(aridez_predominancia.classe1991)) || ', predominante em 1991, deixou de predominar isoladamente, pois em 2021 houve empate entre as classes de maior área.'::text
                            WHEN aridez_predominancia.predomina1991 THEN ('Em 1991, predominava a condição '::text || lower(aridez_predominancia.classe1991)) || ', mas em 2021 não havia área registrada nas quatro classes para comparar a predominância.'::text
                            WHEN aridez_predominancia.classe1991 IS NOT NULL AND aridez_predominancia.classe2021 IS NOT NULL THEN 'Não houve uma condição predominante única em nenhum dos dois anos.'::text
                            ELSE NULL::text
                        END AS descricao
                   FROM aridez_predominancia
                ), aridez_mudancas_ranking AS (
                 SELECT m_1.cd_mun,
                    string_agg(
                        CASE
                            WHEN NOT v.atual IS DISTINCT FROM v.anterior THEN NULL::text
                            WHEN v.anterior IS NULL OR v.atual IS NULL THEN NULL::text
                            ELSE ((((v.rotulo || ' mudou de '::text) || lower(v.anterior)) || ', em 1991, para '::text) || lower(v.atual)) || ', em 2021.'::text
                        END, ' '::text ORDER BY v.posicao) AS descricao
                   FROM municipios m_1
                     JOIN aridez_1991 a1991_1 ON a1991_1.cd_mun = m_1.cd_mun
                     JOIN aridez_2021 a2021_1 ON a2021_1.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_1991_pivot p1991 ON p1991.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_2021_pivot p2021 ON p2021.cd_mun = m_1.cd_mun
                     CROSS JOIN LATERAL ( VALUES (2,'A segunda condição de maior área'::text,p1991.aridez_cond2_1991,p2021.aridez_cond2_2021), (3,'A terceira condição de maior área'::text,p1991.aridez_cond3_1991,p2021.aridez_cond3_2021), (4,'A quarta condição de maior área'::text,p1991.aridez_cond4_1991,p2021.aridez_cond4_2021)) v(posicao, rotulo, anterior, atual)
                  GROUP BY m_1.cd_mun
                ), aridez_empates_ranking AS (
                 SELECT DISTINCT aridez_narrativa_classes.cd_mun
                   FROM aridez_narrativa_classes
                  WHERE aridez_narrativa_classes.area = aridez_narrativa_classes.proxima_area
                ), aridez_narrativa_anos AS (
                 SELECT f_1.cd_mun,
                    f_1.area_base AS area_mun,
                    v.ano,
                    v.area_classificada,
                    v.area_sem_dados,
                    v.area_diferenca
                   FROM aridez_fechamento f_1
                     CROSS JOIN LATERAL ( VALUES (1991,f_1.area_classificada1991,f_1.area_sem_dados1991,f_1.area_diferenca1991), (2021,f_1.area_classificada2021,f_1.area_sem_dados2021,f_1.area_diferenca2021)) v(ano, area_classificada, area_sem_dados, area_diferenca)
                ), aridez_narrativa_final AS (
                 SELECT f_1.cd_mun,
                    f_1.ano,
                        CASE
                            WHEN f_1.area_classificada IS NULL THEN NULL::text
                            ELSE (((((('Em '::text || f_1.ano::text) || ', '::text) || COALESCE(l.primeiro, 'não havia área registrada nas quatro classes de aridez'::text)) ||
                            CASE
                                WHEN l.demais IS NOT NULL THEN '. '::text || l.demais
                                ELSE ''::text
                            END) ||
                            CASE
                                WHEN f_1.area_sem_dados > 0::numeric THEN ((('. A área restante, de '::text || translate(to_char(round(f_1.area_sem_dados, 2), 'FM999,999,999,999,990.00'::text), ',.'::text, '.,'::text)) || ' km²'::text) ||
                                CASE
                                    WHEN f_1.area_mun > 0::numeric THEN (' ('::text ||
                                    CASE
WHEN (f_1.area_sem_dados / NULLIF(f_1.area_mun, 0::numeric) * 100::numeric) < 0.01 THEN 'menos de 0,01'::text
WHEN f_1.area_sem_dados < f_1.area_mun AND round(f_1.area_sem_dados / NULLIF(f_1.area_mun, 0::numeric) * 100::numeric, 2) = 100::numeric THEN 'aproximadamente 100'::text
ELSE replace(replace(round(LEAST(100::numeric, GREATEST(0::numeric, f_1.area_sem_dados / NULLIF(f_1.area_mun, 0::numeric) * 100::numeric)), 2)::text, '.'::text, ','::text), '100,00'::text, '100'::text)
                                    END) || '%)'::text
                                    ELSE ''::text
                                END) || ', não apresentava dados sobre a classificação de aridez'::text
                                ELSE ''::text
                            END) || '.'::text) ||
                            CASE
                                WHEN f_1.ano = 2021 THEN (
                                CASE
                                    WHEN d.descricao IS NOT NULL THEN (' '::text || d.descricao) || '.'::text
                                    ELSE ''::text
                                END ||
                                CASE
                                    WHEN p.descricao IS NOT NULL THEN ' '::text || p.descricao
                                    ELSE ''::text
                                END) ||
                                CASE
                                    WHEN r.descricao IS NOT NULL THEN (
                                    CASE
WHEN e.cd_mun IS NOT NULL THEN ' As posições empatadas em área seguem a ordenação por nome da classe.'::text
ELSE ''::text
                                    END || ' '::text) || r.descricao
                                    ELSE ''::text
                                END
                                ELSE ''::text
                            END
                        END AS texto
                   FROM aridez_narrativa_anos f_1
                     LEFT JOIN aridez_narrativa_lista l ON l.cd_mun = f_1.cd_mun AND l.ano = f_1.ano
                     LEFT JOIN aridez_desaparecidas d ON d.cd_mun = f_1.cd_mun
                     LEFT JOIN aridez_conclusao_predominancia p ON p.cd_mun = f_1.cd_mun
                     LEFT JOIN aridez_mudancas_ranking r ON r.cd_mun = f_1.cd_mun
                     LEFT JOIN aridez_empates_ranking e ON e.cd_mun = f_1.cd_mun
                ), aridez_textos AS (
                 SELECT aridez_narrativa_final.cd_mun,
                    max(aridez_narrativa_final.texto) FILTER (WHERE aridez_narrativa_final.ano = 1991) AS aridez_texto_condicao1991,
                    max(aridez_narrativa_final.texto) FILTER (WHERE aridez_narrativa_final.ano = 2021) AS aridez_texto_condicao2021
                   FROM aridez_narrativa_final
                  GROUP BY aridez_narrativa_final.cd_mun
                ), aridez_integrada AS (
                 SELECT m_1.cd_mun,
                    p1991.aridez_cond1_1991,
                    p1991.aridez_cond2_1991,
                    p1991.aridez_cond3_1991,
                    p1991.aridez_cond4_1991,
                    p1991.aridez_cond1_area1991,
                    p1991.aridez_cond2_area1991,
                    p1991.aridez_cond3_area1991,
                    p1991.aridez_cond4_area1991,
                    p1991.aridez_cond1_areaper1991,
                    p1991.aridez_cond2_areaper1991,
                    p1991.aridez_cond3_areaper1991,
                    p1991.aridez_cond4_areaper1991,
                    p2021.aridez_cond1_2021,
                    p2021.aridez_cond2_2021,
                    p2021.aridez_cond3_2021,
                    p2021.aridez_cond4_2021,
                    p2021.aridez_cond1_area2021,
                    p2021.aridez_cond2_area2021,
                    p2021.aridez_cond3_area2021,
                    p2021.aridez_cond4_area2021,
                    p2021.aridez_cond1_areaper2021,
                    p2021.aridez_cond2_areaper2021,
                    p2021.aridez_cond3_areaper2021,
                    p2021.aridez_cond4_areaper2021,
                    tc.aridez_comp_cond1_area2021,
                    tc.aridez_comp_cond2_area2021,
                    tc.aridez_comp_cond3_area2021,
                    tc.aridez_comp_cond4_area2021,
                    tc.aridez_comp_cond1_areaper2021,
                    tc.aridez_comp_cond2_areaper2021,
                    tc.aridez_comp_cond3_areaper2021,
                    tc.aridez_comp_cond4_areaper2021,
                    txt.aridez_texto_condicao1991,
                    txt.aridez_texto_condicao2021
                   FROM municipios m_1
                     LEFT JOIN aridez_1991_pivot p1991 ON p1991.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_2021_pivot p2021 ON p2021.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_texto_comparacao tc ON tc.cd_mun = m_1.cd_mun
                     LEFT JOIN aridez_textos txt ON txt.cd_mun = m_1.cd_mun
                ), ucs_bioma AS (
                 SELECT t.cd_mun,
                    COALESCE(array_agg(t.biome ORDER BY t.biome) FILTER (WHERE t.biome <> 'Área Marinha'::text), '{}'::text[]) AS biomas_arr,
                    bool_or(t.biome = 'Área Marinha'::text) AS tem_area_marinha
                   FROM ( SELECT DISTINCT vw_ucs.cd_mun::integer AS cd_mun,
                                CASE
                                    WHEN lower(btrim(b.biome)) = 'área marinha'::text THEN 'Área Marinha'::text
                                    ELSE btrim(b.biome)
                                END AS biome
                           FROM meio_ucs.vw_ucs
                             CROSS JOIN LATERAL regexp_split_to_table(vw_ucs.biomas, '[-;,]'::text) b(biome)
                          WHERE vw_ucs.possui_uc IS TRUE AND vw_ucs.biomas IS NOT NULL AND vw_ucs.cd_mun ~ '^\d+$'::text AND btrim(b.biome) <> ''::text) t
                  GROUP BY t.cd_mun
                ), ucs_agg AS (
                 SELECT vw_ucs.cd_mun::integer AS cd_mun,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE) AS n_uc,
                    sum(vw_ucs.area_ha) FILTER (WHERE vw_ucs.possui_uc IS TRUE) AS area_total_uc,
                    array_agg(DISTINCT vw_ucs.nm_uc ORDER BY vw_ucs.nm_uc) FILTER (WHERE vw_ucs.possui_uc IS TRUE) AS nome_uc_arr,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE AND vw_ucs.grupo_manejo = 'Proteção Integral'::text) AS n_protecao_pi,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE AND vw_ucs.grupo_manejo = 'Uso Sustentável'::text) AS n_protecao_us,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE) = 1 THEN max(vw_ucs.ano_uc) FILTER (WHERE vw_ucs.possui_uc IS TRUE)
                            ELSE NULL::text
                        END AS ano_criacao_uc1,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE) = 1 THEN max(vw_ucs.esfera) FILTER (WHERE vw_ucs.possui_uc IS TRUE)
                            ELSE NULL::text
                        END AS esfera_1uc,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE) = 1 THEN max(vw_ucs.cat_manejo) FILTER (WHERE vw_ucs.possui_uc IS TRUE)
                            ELSE NULL::text
                        END AS categoria_uc1,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE) = 1 THEN max(vw_ucs.grupo_manejo) FILTER (WHERE vw_ucs.possui_uc IS TRUE)
                            ELSE NULL::text
                        END AS grupo_uc1
                   FROM meio_ucs.vw_ucs
                  WHERE vw_ucs.cd_mun ~ '^\d+$'::text
                  GROUP BY vw_ucs.cd_mun
                )
         SELECT m.nm_mun,
            m.estado,
            m.sigla_uf,
            2021 AS ano,
            COALESCE(ucs.n_uc, 0::bigint) AS n_uc,
                CASE
                    WHEN ucs.nome_uc_arr IS NULL OR cardinality(ucs.nome_uc_arr) = 0 THEN NULL::text
                    WHEN cardinality(ucs.nome_uc_arr) = 1 THEN ucs.nome_uc_arr[1]
                    ELSE (array_to_string(ucs.nome_uc_arr[1:cardinality(ucs.nome_uc_arr) - 1], ', '::text) || ' e '::text) || ucs.nome_uc_arr[cardinality(ucs.nome_uc_arr)]
                END AS nome_uc,
            COALESCE(ucs.area_total_uc, 0::numeric) AS area_total_uc,
                CASE
                    WHEN bio.cd_mun IS NULL THEN NULL::text
                    WHEN cardinality(bio.biomas_arr) = 0 THEN
                    CASE
                        WHEN bio.tem_area_marinha THEN 'inserida em área marinha'::text
                        ELSE NULL::text
                    END
                    ELSE
                    CASE
                        WHEN cardinality(bio.biomas_arr) = 1 THEN 'inserida no bioma '::text || bio.biomas_arr[1]
                        ELSE (('inseridas nos biomas '::text || array_to_string(bio.biomas_arr[1:cardinality(bio.biomas_arr) - 1], ', '::text)) || ' e '::text) || bio.biomas_arr[cardinality(bio.biomas_arr)]
                    END ||
                    CASE
                        WHEN bio.tem_area_marinha THEN ', com parte em área marinha'::text
                        ELSE ''::text
                    END
                END AS bioma,
            ucs.ano_criacao_uc1,
            ucs.esfera_1uc,
            ucs.categoria_uc1,
            ucs.grupo_uc1,
            COALESCE(ucs.n_protecao_pi, 0::bigint) AS n_protecao_pi,
            COALESCE(ucs.n_protecao_us, 0::bigint) AS n_protecao_us,
            COALESCE(a2021.area_mun, a1991.area_mun) AS area_mun,
            a1991.area_semiarida AS area_semiarida1991,
            a1991.area_subumida AS area_subumida1991,
            a1991.area_arida AS area_arida1991,
            a1991.area_umida AS area_umida1991,
            a2021.area_semiarida AS area_semiarida2021,
            a2021.area_subumida AS area_subumida2021,
            a2021.area_arida AS area_arida2021,
            a2021.area_umida AS area_umida2021,
            a1991.per_semiarida AS area_semiarida1991_per,
            a1991.per_subumida AS area_subumida1991_per,
            a1991.per_arida AS area_arida1991_per,
            a1991.per_umida AS area_umida1991_per,
            a2021.per_semiarida AS area_semiarida2021_per,
            a2021.per_subumida AS area_subumida2021_per,
            a2021.per_arida AS area_arida2021_per,
            a2021.per_umida AS area_umida2021_per,
            ar.aridez_cond1_1991,
            ar.aridez_cond2_1991,
            ar.aridez_cond3_1991,
            ar.aridez_cond4_1991,
            ar.aridez_cond1_area1991,
            ar.aridez_cond2_area1991,
            ar.aridez_cond3_area1991,
            ar.aridez_cond4_area1991,
            ar.aridez_cond1_areaper1991,
            ar.aridez_cond2_areaper1991,
            ar.aridez_cond3_areaper1991,
            ar.aridez_cond4_areaper1991,
            ar.aridez_cond1_2021,
            ar.aridez_cond2_2021,
            ar.aridez_cond3_2021,
            ar.aridez_cond4_2021,
            ar.aridez_cond1_area2021,
            ar.aridez_cond2_area2021,
            ar.aridez_cond3_area2021,
            ar.aridez_cond4_area2021,
            ar.aridez_cond1_areaper2021,
            ar.aridez_cond2_areaper2021,
            ar.aridez_cond3_areaper2021,
            ar.aridez_cond4_areaper2021,
            ar.aridez_comp_cond1_area2021,
            ar.aridez_comp_cond2_area2021,
            ar.aridez_comp_cond3_area2021,
            ar.aridez_comp_cond4_area2021,
            ar.aridez_comp_cond1_areaper2021,
            ar.aridez_comp_cond2_areaper2021,
            ar.aridez_comp_cond3_areaper2021,
            ar.aridez_comp_cond4_areaper2021,
            round((ar.aridez_comp_cond1_area2021 - ar.aridez_cond1_area1991) / NULLIF(ar.aridez_cond1_area1991, 0::numeric) * 100::numeric, 2) AS var_aridez_cond1_1991_2021,
            round((ar.aridez_comp_cond2_area2021 - ar.aridez_cond2_area1991) / NULLIF(ar.aridez_cond2_area1991, 0::numeric) * 100::numeric, 2) AS var_aridez_cond2_1991_2021,
            round((ar.aridez_comp_cond3_area2021 - ar.aridez_cond3_area1991) / NULLIF(ar.aridez_cond3_area1991, 0::numeric) * 100::numeric, 2) AS var_aridez_cond3_1991_2021,
            round((ar.aridez_comp_cond4_area2021 - ar.aridez_cond4_area1991) / NULLIF(ar.aridez_cond4_area1991, 0::numeric) * 100::numeric, 2) AS var_aridez_cond4_1991_2021,
                CASE
                    WHEN ar.aridez_cond1_area1991 IS NULL OR ar.aridez_comp_cond1_area2021 IS NULL THEN NULL::text
                    WHEN ar.aridez_comp_cond1_area2021 > ar.aridez_cond1_area1991 THEN 'um aumento de'::text
                    WHEN ar.aridez_comp_cond1_area2021 < ar.aridez_cond1_area1991 THEN 'uma diminuição de'::text
                    ELSE 'manteve em'::text
                END AS analise_cond1,
                CASE
                    WHEN ar.aridez_cond2_area1991 IS NULL OR ar.aridez_comp_cond2_area2021 IS NULL THEN NULL::text
                    WHEN ar.aridez_comp_cond2_area2021 > ar.aridez_cond2_area1991 THEN 'um aumento de'::text
                    WHEN ar.aridez_comp_cond2_area2021 < ar.aridez_cond2_area1991 THEN 'uma diminuição de'::text
                    ELSE 'manteve em'::text
                END AS analise_cond2,
                CASE
                    WHEN ar.aridez_cond3_area1991 IS NULL OR ar.aridez_comp_cond3_area2021 IS NULL THEN NULL::text
                    WHEN ar.aridez_comp_cond3_area2021 > ar.aridez_cond3_area1991 THEN 'um aumento de'::text
                    WHEN ar.aridez_comp_cond3_area2021 < ar.aridez_cond3_area1991 THEN 'uma diminuição de'::text
                    ELSE 'manteve em'::text
                END AS analise_cond3,
                CASE
                    WHEN ar.aridez_cond4_area1991 IS NULL OR ar.aridez_comp_cond4_area2021 IS NULL THEN NULL::text
                    WHEN ar.aridez_comp_cond4_area2021 > ar.aridez_cond4_area1991 THEN 'um aumento de'::text
                    WHEN ar.aridez_comp_cond4_area2021 < ar.aridez_cond4_area1991 THEN 'uma diminuição de'::text
                    ELSE 'manteve em'::text
                END AS analise_cond4,
            ar.aridez_texto_condicao1991,
            ar.aridez_texto_condicao2021,
                CASE
                    WHEN a2021.cd_mun IS NULL THEN NULL::numeric
                    ELSE a2021.asd
                END AS asd_2021,
                CASE
                    WHEN a2021.cd_mun IS NULL THEN NULL::numeric
                    ELSE a2021.asd_per
                END AS asd_per_2021,
                CASE
                    WHEN a1991.cd_mun IS NULL THEN NULL::numeric
                    ELSE a1991.asd
                END AS asd_1991,
                CASE
                    WHEN a1991.cd_mun IS NULL THEN NULL::numeric
                    ELSE a1991.asd_per
                END AS asd_per_1991,
                CASE
                    WHEN a1991.asd_per IS NULL OR a2021.asd_per IS NULL THEN NULL::text
                    WHEN a2021.asd_per = a1991.asd_per THEN 'idêntica'::text
                    ELSE 'diferente'::text
                END AS analise_asd_per1991_2021,
                CASE
                    WHEN a1991.cd_mun IS NULL OR a2021.cd_mun IS NULL THEN NULL::text
                    WHEN a2021.area_semiarida < a1991.area_semiarida THEN 'melhoraram'::text
                    WHEN a2021.area_semiarida > a1991.area_semiarida THEN 'intensificaram'::text
                    ELSE 'mantiveram'::text
                END AS analise_aridez,
            'Índice de Aridez'::text AS painel1,
            'https://datanordeste.sudene.gov.br/data-panel/aridez'::text AS painel1_link,
            'Unidades de Conservação'::text AS painel2,
            'https://datanordeste.sudene.gov.br/data-panel/unidades_conservacao'::text AS painel2_link,
            'Desertificação'::text AS boletim1,
            'https://datanordeste.sudene.gov.br/boletim/7tbxR9sivkEzXGk7b5t8vu'::text AS boletim1_link,
            m.cd_mun,
            f.area_mun_origem1991,
            f.area_classificada1991,
            f.area_diferenca1991,
            f.area_sem_dados1991,
            round(f.area_sem_dados1991 / NULLIF(f.area_base, 0::numeric) * 100::numeric, 2) AS area_sem_dados1991_per,
            f.area_classificada1991 + f.area_sem_dados1991 AS area_total_aridez1991,
                CASE
                    WHEN f.area_classificada1991 IS NULL OR f.area_mun IS NULL THEN 'sem dados para fechamento'::text
                    WHEN f.area_diferenca1991 < 0::numeric THEN 'área classificada excede a área municipal'::text
                    ELSE 'fechamento consistente'::text
                END AS aridez_fechamento1991,
            f.area_mun_origem2021,
            f.area_classificada2021,
            f.area_diferenca2021,
            f.area_sem_dados2021,
            round(f.area_sem_dados2021 / NULLIF(f.area_base, 0::numeric) * 100::numeric, 2) AS area_sem_dados2021_per,
            f.area_classificada2021 + f.area_sem_dados2021 AS area_total_aridez2021,
                CASE
                    WHEN f.area_classificada2021 IS NULL OR f.area_mun IS NULL THEN 'sem dados para fechamento'::text
                    WHEN f.area_diferenca2021 < 0::numeric THEN 'área classificada excede a área municipal'::text
                    ELSE 'fechamento consistente'::text
                END AS aridez_fechamento2021
           FROM municipios m
             LEFT JOIN aridez_2021 a2021 ON a2021.cd_mun = m.cd_mun
             LEFT JOIN aridez_1991 a1991 ON a1991.cd_mun = m.cd_mun
             LEFT JOIN ucs_agg ucs ON ucs.cd_mun = m.cd_mun
             LEFT JOIN ucs_bioma bio ON bio.cd_mun = m.cd_mun
             LEFT JOIN aridez_fechamento f ON f.cd_mun = m.cd_mun
             LEFT JOIN aridez_integrada ar ON ar.cd_mun = m.cd_mun) q
     LEFT JOIN carac_mun.novos_nomes nn ON btrim(q.cd_mun::text) = btrim(nn.cd_mun::text);
