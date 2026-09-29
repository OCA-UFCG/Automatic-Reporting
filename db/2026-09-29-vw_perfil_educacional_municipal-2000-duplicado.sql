-- relatorios_auto.vw_perfil_educacional_municipal: 2000 contado uma vez só.
-- APLICADO no banco do beta (oca_db) em 2026-09-29, com refresh da matview;
-- prod não. Aplica-se DEPOIS de 2026-09-29-vw_perfil_educacional_municipal.sql
-- (esta definição parte daquela). Rollback: reaplicar aquele arquivo.
--
-- edu_nivel_de_instrucao.niveis_instrucao_geral traz 2000 em dois recortes
-- empilhados: um só por sexo (cor_ou_raca NULL, 20.660 linhas) e um só por cor
-- ou raça (sexo NULL, 61.980 linhas). Cada adulto aparece duas vezes. 2010 e
-- 2022 cruzam cor e sexo numa linha só, sem duplicação. A CTE
-- nivel_instrucao_2000 somava tudo: sem_instr_2000 e superior_2000 saíam em
-- dobro nos 2.066 municípios com Censo 2000. Açailândia/MA: 55.471 no lugar de
-- 27.738 (14.362 homens + 13.376 mulheres), e o texto dizia "redução de 51,70%"
-- quando foi de 3,41%. Com o dado certo, 1.159 municípios passam de "redução"
-- para "aumento" de adultos sem instrução (a população adulta cresceu) e 540
-- mudam avanço/retrocesso.
--
-- Fica o recorte por sexo: é o total publicado. O recorte por cor difere dele em
-- no máximo 10 pessoas (arredondamento da amostra), e o zero de superior em 2000
-- (221 municípios) é o mesmo nos dois.
--
-- Muda só valores, nenhum nome/posição/tipo de coluna: CREATE OR REPLACE passa
-- com a matview no lugar. Conferido com o SELECT abaixo contra a matview
-- anterior: 2.074 linhas, só colunas derivadas de 2000 mudam.

CREATE OR REPLACE VIEW relatorios_auto.vw_perfil_educacional_municipal AS
 WITH nivel_instrucao_2022 AS (
         SELECT n.cd_mun,
            max(regexp_replace(n.nm_mun::text, '\s*\([A-Z]{2}\)\s*$'::text, ''::text)) AS nm_mun,
            max(n.uf::text) AS estado,
            max(n.sigla_uf::text) AS sigla_uf,
            2022 AS ano,
            sum(COALESCE(n.sem_instrucao_fund_incomp, 0::bigint)) AS pop_fundamental_incompleto,
            sum(COALESCE(n.fund_comp_medio_incomp, 0::bigint)) AS pop_fundamental_completo,
            sum(COALESCE(n.medio_comp_superior_incomp, 0::bigint)) AS pop_medio_completo,
            sum(COALESCE(n.superior_completo, 0::bigint)) AS pop_superior_completo,
            sum(COALESCE(n.sem_instrucao_fund_incomp, 0::bigint) + COALESCE(n.fund_comp_medio_incomp, 0::bigint) + COALESCE(n.medio_comp_superior_incomp, 0::bigint) + COALESCE(n.superior_completo, 0::bigint)) AS pop_total_instrucao,
            sum(
                CASE
                    WHEN n.sexo::text = 'Mulheres'::text THEN COALESCE(n.superior_completo, 0::bigint)
                    ELSE 0::bigint
                END) AS mulher_superior_completo,
            sum(
                CASE
                    WHEN n.sexo::text = 'Homens'::text THEN COALESCE(n.superior_completo, 0::bigint)
                    ELSE 0::bigint
                END) AS homem_superior_completo
           FROM edu_nivel_de_instrucao.niveis_instrucao_geral n
          WHERE n.ano = 2022
          GROUP BY n.cd_mun
        ), nivel_unpivot AS (
         SELECT ni.cd_mun,
            v.classe,
            v.rotulo,
            v.per,
            v.pop
           FROM nivel_instrucao_2022 ni
             CROSS JOIN LATERAL ( VALUES ('Sem instrução ou fundamental incompleto'::text,'ensino fundamental incompleto ou sem instrução'::text,round(ni.pop_fundamental_incompleto / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2),ni.pop_fundamental_incompleto), ('Fundamental completo'::text,'ensino fundamental completo'::text,round(ni.pop_fundamental_completo / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2),ni.pop_fundamental_completo), ('Médio completo'::text,'ensino médio completo'::text,round(ni.pop_medio_completo / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2),ni.pop_medio_completo), ('Superior completo'::text,'ensino superior completo'::text,round(ni.pop_superior_completo / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2),ni.pop_superior_completo)) v(classe, rotulo, per, pop)
        ), nivel_rank AS (
         SELECT nivel_unpivot.cd_mun,
            nivel_unpivot.classe,
            nivel_unpivot.rotulo,
            nivel_unpivot.per,
            nivel_unpivot.pop,
            row_number() OVER (PARTITION BY nivel_unpivot.cd_mun ORDER BY nivel_unpivot.per DESC NULLS LAST, nivel_unpivot.classe) AS rn
           FROM nivel_unpivot
        ), nivel_pivot AS (
         SELECT nivel_rank.cd_mun,
            max(nivel_rank.rotulo) FILTER (WHERE nivel_rank.rn = 1) AS pri_nivel_classe,
            max(nivel_rank.per) FILTER (WHERE nivel_rank.rn = 1) AS pri_nivel_per,
            max(nivel_rank.pop) FILTER (WHERE nivel_rank.rn = 1) AS pri_nivel_pop,
            max(nivel_rank.rotulo) FILTER (WHERE nivel_rank.rn = 2) AS seg_nivel_classe,
            max(nivel_rank.per) FILTER (WHERE nivel_rank.rn = 2) AS seg_nivel_per,
            max(nivel_rank.pop) FILTER (WHERE nivel_rank.rn = 2) AS seg_nivel_pop,
            max(nivel_rank.rotulo) FILTER (WHERE nivel_rank.rn = 3) AS ter_nivel_classe,
            max(nivel_rank.per) FILTER (WHERE nivel_rank.rn = 3) AS ter_nivel_per,
            max(nivel_rank.pop) FILTER (WHERE nivel_rank.rn = 3) AS ter_nivel_pop,
            max(nivel_rank.rotulo) FILTER (WHERE nivel_rank.rn = 4) AS quar_nivel_classe,
            max(nivel_rank.per) FILTER (WHERE nivel_rank.rn = 4) AS quar_nivel_per,
            max(nivel_rank.pop) FILTER (WHERE nivel_rank.rn = 4) AS quar_nivel_pop
           FROM nivel_rank
          GROUP BY nivel_rank.cd_mun
        ), nivel_instrucao_2000 AS (
         SELECT n.cd_mun,
            sum(COALESCE(n.sem_instrucao_fund_incomp, 0::bigint)) AS pop_fundamental_incompleto_2000,
            sum(COALESCE(n.superior_completo, 0::bigint)) AS pop_superior_completo_2000
           FROM edu_nivel_de_instrucao.niveis_instrucao_geral n
          WHERE n.ano = 2000 AND n.sexo IS NOT NULL
          GROUP BY n.cd_mun
        ), alfabetizacao_2022 AS (
         SELECT a.cd_mun,
            sum(COALESCE(a.total, 0::bigint)) AS pop_total,
            sum(COALESCE(a.alfabetizadas, 0::bigint)) AS alfabetizadas
           FROM edu_analfabetismo.vw_analfabetismo a
          WHERE a.ano = 2022
          GROUP BY a.cd_mun
        ), analfabetismo_faixa_total AS (
         SELECT a.cd_mun,
            a.faixa_etaria AS faixa,
            round(sum(COALESCE(a.nao_alfabetizadas, 0::bigint)) / NULLIF(sum(COALESCE(a.total, 0::bigint)), 0::numeric) * 100::numeric, 2) AS taxa_total
           FROM edu_analfabetismo.vw_analfabetismo a
          WHERE a.ano = 2022
          GROUP BY a.cd_mun, a.faixa_etaria
        ), faixa_rank AS (
         SELECT analfabetismo_faixa_total.cd_mun,
            analfabetismo_faixa_total.faixa,
            row_number() OVER (PARTITION BY analfabetismo_faixa_total.cd_mun ORDER BY analfabetismo_faixa_total.taxa_total DESC NULLS LAST, analfabetismo_faixa_total.faixa) AS rn_desc,
            row_number() OVER (PARTITION BY analfabetismo_faixa_total.cd_mun ORDER BY analfabetismo_faixa_total.taxa_total, analfabetismo_faixa_total.faixa) AS rn_asc
           FROM analfabetismo_faixa_total
        ), faixa_maior_menor AS (
         SELECT faixa_rank.cd_mun,
            max(faixa_rank.faixa) FILTER (WHERE faixa_rank.rn_desc = 1) AS analf_faixa_maior,
            max(faixa_rank.faixa) FILTER (WHERE faixa_rank.rn_asc = 1) AS analf_faixa_menor
           FROM faixa_rank
          GROUP BY faixa_rank.cd_mun
        ), cor_faixa_unpivot AS (
         SELECT a.cd_mun,
            a.cor_ou_raca::text AS cor,
            a.faixa_etaria AS faixa,
            round(sum(COALESCE(a.nao_alfabetizadas, 0::bigint)) / NULLIF(sum(COALESCE(a.total, 0::bigint)), 0::numeric) * 100::numeric, 2) AS taxa
           FROM edu_analfabetismo.vw_analfabetismo a
          WHERE a.ano = 2022 AND a.cor_ou_raca::text <> 'Sem declaração'::text
          GROUP BY a.cd_mun, a.cor_ou_raca, a.faixa_etaria
        ), cor_na_faixa_maior AS (
         SELECT u.cd_mun,
            u.cor,
            u.taxa,
            row_number() OVER (PARTITION BY u.cd_mun ORDER BY u.taxa DESC NULLS LAST, u.cor) AS rn_desc,
            row_number() OVER (PARTITION BY u.cd_mun ORDER BY u.taxa, u.cor) AS rn_asc
           FROM cor_faixa_unpivot u
             JOIN faixa_maior_menor fm_1 ON fm_1.cd_mun = u.cd_mun AND fm_1.analf_faixa_maior = u.faixa
        ), cor_analf_pivot AS (
         SELECT cor_na_faixa_maior.cd_mun,
            max(cor_na_faixa_maior.cor) FILTER (WHERE cor_na_faixa_maior.rn_desc = 1) AS pri_cor_analf,
            max(cor_na_faixa_maior.taxa) FILTER (WHERE cor_na_faixa_maior.rn_desc = 1) AS pri_cor_analf_per,
            max(cor_na_faixa_maior.cor) FILTER (WHERE cor_na_faixa_maior.rn_desc = 2) AS seg_cor_analf,
            max(cor_na_faixa_maior.taxa) FILTER (WHERE cor_na_faixa_maior.rn_desc = 2) AS seg_cor_analf_per,
            max(cor_na_faixa_maior.cor) FILTER (WHERE cor_na_faixa_maior.rn_desc = 3) AS ter_cor_analf,
            max(cor_na_faixa_maior.taxa) FILTER (WHERE cor_na_faixa_maior.rn_desc = 3) AS ter_cor_analf_per,
            max(cor_na_faixa_maior.cor) FILTER (WHERE cor_na_faixa_maior.rn_asc = 1) AS ult_cor_analf,
            max(cor_na_faixa_maior.taxa) FILTER (WHERE cor_na_faixa_maior.rn_asc = 1) AS ult_cor_analf_per
           FROM cor_na_faixa_maior
          GROUP BY cor_na_faixa_maior.cd_mun
        ), indicadores AS (
         SELECT ni.cd_mun,
            ni.nm_mun,
            ni.estado,
            ni.sigla_uf,
            ni.ano,
            round(ni.pop_fundamental_completo / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2) AS fund_comp_per,
            round(ni.pop_superior_completo / NULLIF(ni.pop_total_instrucao, 0::numeric) * 100::numeric, 2) AS sup_comp_per,
            round(al.alfabetizadas / NULLIF(al.pop_total, 0::numeric) * 100::numeric, 2) AS alfabetizado_per,
            ni.pop_fundamental_incompleto AS sem_instr_2022_num,
            ni.mulher_superior_completo,
            ni.homem_superior_completo,
            n0.pop_fundamental_incompleto_2000 AS sem_instr_2000_num,
            n0.pop_superior_completo_2000 AS superior_2000_num,
            ni.pop_superior_completo AS superior_2022_num
           FROM nivel_instrucao_2022 ni
             LEFT JOIN alfabetizacao_2022 al ON al.cd_mun = ni.cd_mun
             LEFT JOIN nivel_instrucao_2000 n0 ON n0.cd_mun = ni.cd_mun
        )
 SELECT ind.nm_mun,
    ind.estado,
    ind.sigla_uf,
    ind.ano,
    np.pri_nivel_classe,
    np.pri_nivel_per,
    np.pri_nivel_pop,
    np.seg_nivel_classe,
    np.seg_nivel_per,
    np.seg_nivel_pop,
    np.ter_nivel_classe,
    np.ter_nivel_per,
    np.ter_nivel_pop,
    np.quar_nivel_classe,
    np.quar_nivel_per,
    np.quar_nivel_pop,
    ind.alfabetizado_per,
    COALESCE(
        CASE
            WHEN ind.sem_instr_2000_num IS NULL OR ind.sem_instr_2022_num IS NULL THEN NULL::text
            WHEN ind.sem_instr_2022_num < ind.sem_instr_2000_num THEN 'uma redução'::text
            WHEN ind.sem_instr_2022_num > ind.sem_instr_2000_num THEN 'um aumento'::text
            ELSE 'estável'::text
        END, 'sem dados'::text) AS tend_sem_instr,
    COALESCE(ind.sem_instr_2000_num::text, 'sem dados'::text) AS sem_instr_2000,
    ind.sem_instr_2022_num::text AS sem_instr_2022,
    COALESCE(
        CASE
            WHEN ind.superior_2000_num IS NULL OR ind.superior_2022_num IS NULL THEN NULL::text
            WHEN ind.superior_2022_num > ind.superior_2000_num THEN 'um aumento'::text
            WHEN ind.superior_2022_num < ind.superior_2000_num THEN 'uma diminuição'::text
            ELSE 'permaneceu estável'::text
        END, 'sem dados'::text) AS tend_nivel_sup,
    ind.fund_comp_per,
        CASE
            WHEN ind.fund_comp_per IS NULL THEN NULL::text
            WHEN ind.fund_comp_per >= 14::numeric THEN 'superior'::text
            ELSE 'inferior'::text
        END AS comp_fund_br,
    ind.sup_comp_per,
        CASE
            WHEN ind.sup_comp_per IS NULL THEN NULL::text
            WHEN ind.sup_comp_per >= 18.4 THEN 'superior'::text
            ELSE 'inferior'::text
        END AS comp_sup_br,
    (replace(to_char(ind.mulher_superior_completo, 'FM999,999,999,990'::text), ','::text, '.'::text) || ' '::text) ||
        CASE
            WHEN ind.mulher_superior_completo = 1::numeric THEN 'mulher'::text
            ELSE 'mulheres'::text
        END AS sup_comp_mulher,
    (replace(to_char(ind.homem_superior_completo, 'FM999,999,999,990'::text), ','::text, '.'::text) || ' '::text) ||
        CASE
            WHEN ind.homem_superior_completo = 1::numeric THEN 'homem'::text
            ELSE 'homens'::text
        END AS sup_comp_homem,
        CASE
            WHEN ind.alfabetizado_per IS NULL THEN NULL::text
            WHEN ind.alfabetizado_per >= 100::numeric THEN 'superior'::text
            ELSE 'inferior'::text
        END AS comp_alfab_pne,
    fm.analf_faixa_maior,
    lower(cp.pri_cor_analf) AS pri_cor_analf,
    cp.pri_cor_analf_per,
    lower(cp.seg_cor_analf) AS seg_cor_analf,
    lower(cp.ter_cor_analf) AS ter_cor_analf,
    floor(LEAST(cp.seg_cor_analf_per, cp.ter_cor_analf_per)) AS inter_cor_analf_per,
    lower(cp.ult_cor_analf) AS ult_cor_analf,
    cp.ult_cor_analf_per,
    COALESCE(round(abs(ind.sem_instr_2022_num - ind.sem_instr_2000_num) * 100.0 / NULLIF(ind.sem_instr_2000_num, 0::numeric), 2)::text, 'sem dados'::text) AS tend_sem_instr_per,
    COALESCE(round(abs(ind.superior_2022_num - ind.superior_2000_num) * 100.0 / NULLIF(ind.superior_2000_num, 0::numeric), 2)::text, 'sem dados'::text) AS tend_nivel_sup_per,
    abs(ind.fund_comp_per - 14::numeric) AS comp_fund_br_per,
        CASE
            WHEN ind.fund_comp_per IS NULL THEN NULL::text
            WHEN abs(ind.fund_comp_per - 14::numeric) >= 2::numeric THEN 'pontos percentuais'::text
            ELSE 'ponto percentual'::text
        END AS comp_fund_br_per_unid,
    abs(ind.sup_comp_per - 18.4) AS comp_sup_br_per,
        CASE
            WHEN ind.sup_comp_per IS NULL THEN NULL::text
            WHEN abs(ind.sup_comp_per - 18.4) >= 2::numeric THEN 'pontos percentuais'::text
            ELSE 'ponto percentual'::text
        END AS comp_sup_br_per_unid,
    abs(100::numeric - ind.alfabetizado_per) AS comp_alfab_pne_per,
        CASE
            WHEN ind.alfabetizado_per IS NULL THEN NULL::text
            WHEN abs(100::numeric - ind.alfabetizado_per) >= 2::numeric THEN 'pontos percentuais'::text
            ELSE 'ponto percentual'::text
        END AS comp_alfab_pne_per_unid,
    fm.analf_faixa_menor,
    COALESCE(round(abs(COALESCE(ind.sem_instr_2000_num, 0::numeric) - COALESCE(ind.sem_instr_2022_num, 0::numeric) + (COALESCE(ind.superior_2022_num, 0::numeric) - COALESCE(ind.superior_2000_num, 0::numeric))) * 100.0 / NULLIF(COALESCE(ind.sem_instr_2000_num, 0::numeric) + COALESCE(ind.superior_2000_num, 0::numeric), 0::numeric), 2)::text, 'sem dados'::text) AS sint_evolucao_per,
    COALESCE(
        CASE
            WHEN ind.sem_instr_2000_num IS NULL OR ind.superior_2000_num IS NULL THEN NULL::text
            WHEN (ind.sem_instr_2000_num - ind.sem_instr_2022_num + (ind.superior_2022_num - ind.superior_2000_num)) > 0::numeric THEN 'avanço'::text
            WHEN (ind.sem_instr_2000_num - ind.sem_instr_2022_num + (ind.superior_2022_num - ind.superior_2000_num)) < 0::numeric THEN 'retrocesso'::text
            ELSE 'estável'::text
        END, 'sem dados'::text) AS sint_evolucao,
    COALESCE(abs(ind.sem_instr_2022_num - ind.sem_instr_2000_num)::text, 'sem dados'::text) AS tend_sem_instr_abs,
    COALESCE(abs(ind.superior_2022_num - ind.superior_2000_num)::text, 'sem dados'::text) AS tend_nivel_sup_abs,
    COALESCE(abs(ind.superior_2022_num - ind.superior_2000_num)::text, 'sem dados'::text) AS tend_ens_sup,
    'Analfabetismo'::text AS nm_boletim1,
    'https://datanordeste.sudene.gov.br/boletim/421MHwS4czMWvBpHDhR6RJ'::text AS link_boletim1,
    'Educação básica'::text AS nm_boletim2,
    'https://datanordeste.sudene.gov.br/boletim/5sPp0jQRba52vrjKhBfKgZ'::text AS link_boletim2,
    'Nível de instrução'::text AS nm_painel1,
    'https://datanordeste.sudene.gov.br/data-panel/niveldeinstrucao'::text AS link_painel1,
    'Analfabetismo'::text AS nm_painel2,
    'https://datanordeste.sudene.gov.br/data-panel/analfabetismo'::text AS link_painel2,
    'Alfabetização da população quilombola'::text AS nm_painel3,
    'https://datanordeste.sudene.gov.br/data-panel/alfabetizacao_quilombola'::text AS link_painel3,
    'Alfabetização da população indígena'::text AS nm_painel4,
    'https://datanordeste.sudene.gov.br/data-panel/alfabetizacao_indigena'::text AS link_painel4,
    COALESCE(round((ind.sem_instr_2022_num - ind.sem_instr_2000_num) * 100.0 / NULLIF(ind.sem_instr_2000_num, 0::numeric), 2)::text, 'sem dados'::text) AS tend_sem_instr_per_dado,
    COALESCE(round((ind.superior_2022_num - ind.superior_2000_num) * 100.0 / NULLIF(ind.superior_2000_num, 0::numeric), 2)::text, 'sem dados'::text) AS tend_nivel_sup_per_dado,
    ind.fund_comp_per - 14::numeric AS comp_fund_br_per_dado,
    ind.sup_comp_per - 18.4 AS comp_sup_br_per_dado,
    100::numeric - ind.alfabetizado_per AS comp_alfab_pne_per_dado,
    COALESCE(round((COALESCE(ind.sem_instr_2000_num, 0::numeric) - COALESCE(ind.sem_instr_2022_num, 0::numeric) + (COALESCE(ind.superior_2022_num, 0::numeric) - COALESCE(ind.superior_2000_num, 0::numeric))) * 100.0 / NULLIF(COALESCE(ind.sem_instr_2000_num, 0::numeric) + COALESCE(ind.superior_2000_num, 0::numeric), 0::numeric), 2)::text, 'sem dados'::text) AS sint_evolucao_per_dado,
    COALESCE((ind.sem_instr_2022_num - ind.sem_instr_2000_num)::text, 'sem dados'::text) AS tend_sem_instr_abs_dado,
    COALESCE((ind.superior_2022_num - ind.superior_2000_num)::text, 'sem dados'::text) AS tend_nivel_sup_abs_dado,
    COALESCE((ind.superior_2022_num - ind.superior_2000_num)::text, 'sem dados'::text) AS tend_ens_sup_dado
   FROM indicadores ind
     LEFT JOIN nivel_pivot np ON np.cd_mun = ind.cd_mun
     LEFT JOIN faixa_maior_menor fm ON fm.cd_mun = ind.cd_mun
     LEFT JOIN cor_analf_pivot cp ON cp.cd_mun = ind.cd_mun;

REFRESH MATERIALIZED VIEW CONCURRENTLY relatorios_auto.mv_perfil_educacional_municipal;
