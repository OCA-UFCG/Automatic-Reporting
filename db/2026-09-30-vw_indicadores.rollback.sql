-- Rollback de 2026-09-30-vw_indicadores.sql: definição de
-- relatorios_auto.vw_indicadores lida do banco do beta em 30/09/2026
-- (pg_get_viewdef), antes da mudança.

CREATE OR REPLACE VIEW relatorios_auto.vw_indicadores AS
 SELECT COALESCE(nn.nm_mun::text, q.nm_mun) AS nm_mun,
    q.cd_mun,
    q.estado,
    q.sigla_uf,
    q.nm_area_municipio,
    q.valor_area_municipio,
    q.fonte_area_municipio,
    q.unid_area_municipio,
    q.nm_pop_residente,
    q.valor_pop_residente,
    q.fonte_pop_residente,
    q.unid_pop_residente,
    q.nm_pop_feminina,
    q.valor_pop_feminino,
    q.fonte_pop_feminino,
    q.unid_pop_feminino,
    q.nm_pop_masculina,
    q.valor_pop_masculina,
    q.fonte_pop_masculina,
    q.unid_pop_masculina,
    q.nm_pop_quilombola,
    q.valor_pop_quilombola,
    q.fonte_pop_quilombola,
    q.unid_pop_quilombola,
    q.nm_pop_indigena,
    q.valor_pop_indigena,
    q.fonte_pop_indigena,
    q.unid_pop_indigena,
    q.nm_pop_rua,
    q.valor_pop_rua,
    q.fonte_pop_rua,
    q.unid_pop_rua,
    q.nm_fundamental_incom,
    q.per_fundamental_incom,
    q.fonte_fundamental_incom,
    q.unid_fundamental_incom,
    q.nm_fundamental_com,
    q.per_fundamental_com,
    q.fonte_fundamental_com,
    q.unid_fundamental_com,
    q.nm_medio_com,
    q.per_medio_com,
    q.fonte_medio_com,
    q.unid_medio_com,
    q.nm_superior_com,
    q.per_superior_com,
    q.fonte_superior_com,
    q.unid_superior_com,
    q.nm_alfabetizada_quilombola,
    q.per_alfabetizada_quilombola,
    q.fonte_alfabetizada_quilombola,
    q.unid_alfabetizada_quilombola,
    q.nm_alfabetizada_indigena,
    q.per_alfabetizada_indigena,
    q.fonte_alfabetizada_indigena,
    q.unid_alfabetizada_indigena,
    q.nm_nascidos,
    q.valor_nascidos,
    q.fonte_nascidos,
    q.unid_nascidos,
    q.nm_mortalidade_infantil,
    q.valor_mortalidade_infantil,
    q.fonte_mortalidade_infantil,
    q.unid_mortalidade_infantil,
    q.nm_doses,
    q.valor_doses,
    q.fonte_doses,
    q.unid_doses,
    q.nm_estabelecimento,
    q.valor_estabelecimento,
    q.fonte_estabelecimento,
    q.unid_estabelecimento,
    q.nm_unidade_basica,
    q.valor_unidade_basica,
    q.fonte_unidade_basica,
    q.unid_unidade_basica,
    q.nm_clinica_centro_especialidade,
    q.valor_clinica_centro_especialidade,
    q.fonte_clinica_centro_especialidade,
    q.unid_clinica_centro_especialidade,
    q.nm_pib,
    q.valor_pib,
    q.fonte_pib,
    q.unid_pib,
    q.nm_pib_capita,
    q.valor_pib_capita,
    q.fonte_pib_capita,
    q.unid_pib_capita,
    q.nm_carga_tributaria,
    q.valor_carga_tributaria,
    q.fonte_carga_tributaria,
    q.unid_carga_tributaria,
    q.nm_exportacao,
    q.valor_exportacao,
    q.fonte_exportacao,
    q.unid_exportacao,
    q.nm_importacao,
    q.valor_importacao,
    q.fonte_importacao,
    q.unid_importacao,
    q.nm_balanca,
    q.valor_balanca,
    q.fonte_balanca,
    q.unid_balanca,
    q.nm_esgotamento,
    q.valor_esgotamento,
    q.fonte_esgotamento,
    q.unid_esgotamento,
    q.nm_banheiro,
    q.valor_banheiro,
    q.fonte_banheiro,
    q.unid_banheiro,
    q.nm_coleta_lixo,
    q.valor_coleta_lixo,
    q.fonte_coleta_lixo,
    q.unid_coleta_lixo,
    q.nm_renda_capita,
    q.valor_renda_capita,
    q.fonte_renda_capita,
    q.unid_renda_capita,
    q.nm_gini,
    q.valor_gini,
    q.fonte_gini,
    q.unid_gini,
    q.nm_idhm,
    q.valor_idhm,
    q.fonte_idhm,
    q.unid_idhm,
    q.nm_idhm_educacao,
    q.valor_idhm_educacao,
    q.fonte_idhm_educacao,
    q.unid_idhm_educacao,
    q.nm_idhm_longevidade,
    q.valor_idhm_longevidade,
    q.fonte_idhm_longevidade,
    q.unid_idhm_longevidade,
    q.nm_idhm_renda,
    q.valor_idhm_renda,
    q.fonte_idhm_renda,
    q.unid_idhm_renda,
    q.nm_cisternas,
    q.valor_cisternas,
    q.fonte_cisternas,
    q.unid_cisternas,
    q.nm_abastecimento_humano,
    q.valor_abastecimento_humano,
    q.fonte_abastecimento_humano,
    q.unid_abastecimento_humano,
    q.nm_irrigacao,
    q.valor_irrigacao,
    q.fonte_irrigacao,
    q.unid_irrigacao,
    q.nm_asd,
    q.valor_asd,
    q.fonte_asd,
    q.unid_asd,
    q."nm_asd_avanço",
    q."valor_asd_avanço",
    q."fonte_asd_avanço",
    q."unid_asd_avanço",
    q.nm_uc,
    q.valor_uc,
    q.fonte_uc,
    q.unid_uc,
    q.nm_uc_area,
    q.valor_uc_area,
    q.fonte_uc_area,
    q.unid_uc_area,
    q.nm_uc_pi,
    q.valor_uc_pi,
    q.fonte_uc_pi,
    q.unid_uc_pi,
    q.nm_uc_uso,
    q.valor_uc_uso,
    q.fonte_uc_uso,
    q.unid_uc_uso
   FROM ( WITH municipios_universo AS (
                 SELECT DISTINCT btrim(vw_pib.cd_mun::text)::integer AS cd_mun
                   FROM eco_pib.vw_pib
                  WHERE vw_pib.ano = 2023 AND vw_pib.cd_mun IS NOT NULL AND btrim(vw_pib.cd_mun::text) ~ '^[0-9]+$'::text
                ), municipios AS (
                 SELECT u.cd_mun,
                    max(c.nm_mun::text) AS nm_mun,
                    max(c.estado::text) AS estado,
                    max(c.sigla_uf::text) AS sigla_uf,
                    max(c.area) AS area_municipio
                   FROM municipios_universo u
                     LEFT JOIN carac_mun.caracteristicas_municipais c ON btrim(c.cd_mun::text) = u.cd_mun::text
                  GROUP BY u.cd_mun
                ), populacao_2022 AS (
                 SELECT view_demografia_2022.cd_mun,
                    sum(view_demografia_2022.populacao_total)::numeric AS populacao_residente,
                    sum(view_demografia_2022.mulher)::numeric AS populacao_feminina,
                    sum(view_demografia_2022.homem)::numeric AS populacao_masculina
                   FROM dem_demografia.view_demografia_2022
                  GROUP BY view_demografia_2022.cd_mun
                ), populacao_indigena_2022 AS (
                 SELECT vw_populacao_indigena_geral.cd_mun,
                    sum(vw_populacao_indigena_geral.pop_total_indigena) AS populacao_indigena
                   FROM dem_demografia_indigena.vw_populacao_indigena_geral
                  WHERE vw_populacao_indigena_geral.ano = 2022
                  GROUP BY vw_populacao_indigena_geral.cd_mun
                ), populacao_quilombola_2022 AS (
                 SELECT vw_demografia_quilombola_faixas_agrupadas.cd_mun,
                    max(vw_demografia_quilombola_faixas_agrupadas.populacao_total_quilombola)::numeric AS populacao_quilombola
                   FROM dem_demografia_quilombola.vw_demografia_quilombola_faixas_agrupadas
                  WHERE vw_demografia_quilombola_faixas_agrupadas.ano = 2022
                  GROUP BY vw_demografia_quilombola_faixas_agrupadas.cd_mun
                ), populacao_rua_2026 AS (
                 SELECT vw_pop.cd_mun,
                    max(vw_pop.numero_pessoas_situacao_rua_cadunico)::numeric AS populacao_rua
                   FROM dem_rua.vw_pop
                  WHERE vw_pop.ano = 2026
                  GROUP BY vw_pop.cd_mun
                ), instrucao_base AS (
                 SELECT niveis_instrucao_geral.cd_mun,
                    sum(niveis_instrucao_geral.sem_instrucao_fund_incomp) AS fundamental_incompleto,
                    sum(niveis_instrucao_geral.fund_comp_medio_incomp) AS fundamental_completo,
                    sum(niveis_instrucao_geral.medio_comp_superior_incomp) AS medio_completo,
                    sum(niveis_instrucao_geral.superior_completo) AS superior_completo
                   FROM edu_nivel_de_instrucao.niveis_instrucao_geral
                  WHERE niveis_instrucao_geral.ano = 2022
                  GROUP BY niveis_instrucao_geral.cd_mun
                ), instrucao_2022 AS (
                 SELECT instrucao_base.cd_mun,
                    round(100.0 * instrucao_base.fundamental_incompleto / NULLIF(instrucao_base.fundamental_incompleto + instrucao_base.fundamental_completo + instrucao_base.medio_completo + instrucao_base.superior_completo, 0::numeric), 2) AS per_fundamental_incompleto,
                    round(100.0 * instrucao_base.fundamental_completo / NULLIF(instrucao_base.fundamental_incompleto + instrucao_base.fundamental_completo + instrucao_base.medio_completo + instrucao_base.superior_completo, 0::numeric), 2) AS per_fundamental_completo,
                    round(100.0 * instrucao_base.medio_completo / NULLIF(instrucao_base.fundamental_incompleto + instrucao_base.fundamental_completo + instrucao_base.medio_completo + instrucao_base.superior_completo, 0::numeric), 2) AS per_medio_completo,
                    round(100.0 * instrucao_base.superior_completo / NULLIF(instrucao_base.fundamental_incompleto + instrucao_base.fundamental_completo + instrucao_base.medio_completo + instrucao_base.superior_completo, 0::numeric), 2) AS per_superior_completo
                   FROM instrucao_base
                ), alfabetizacao_quilombola_2022 AS (
                 SELECT vw_alfabetizacao_quilombola.cd_mun::integer AS cd_mun,
                    max(vw_alfabetizacao_quilombola.porcentagem_quilombolas_alfabetizados) AS per_alfabetizados_quilombolas
                   FROM edu_alfabetizacao_quilombola.vw_alfabetizacao_quilombola
                  WHERE vw_alfabetizacao_quilombola.ano = '2022'::text AND vw_alfabetizacao_quilombola.idade = 'Total'::text
                  GROUP BY vw_alfabetizacao_quilombola.cd_mun
                ), alfabetizacao_indigena_base AS (
                 SELECT vw_alfabetizacao_indigena.cd_mun::integer AS cd_mun,
                    max(vw_alfabetizacao_indigena.total_populacao_indigena_15_mais)::numeric AS total_indigenas,
                    max(vw_alfabetizacao_indigena.total_indigenas_alfabetizados_15_mais)::numeric AS alfabetizados_indigenas
                   FROM edu_alfabetizacao_indigena.vw_alfabetizacao_indigena
                  WHERE vw_alfabetizacao_indigena.ano = '2022'::text AND vw_alfabetizacao_indigena.idade = 'Total'::text
                  GROUP BY vw_alfabetizacao_indigena.cd_mun
                ), alfabetizacao_indigena_2022 AS (
                 SELECT alfabetizacao_indigena_base.cd_mun,
                    round(alfabetizacao_indigena_base.alfabetizados_indigenas / NULLIF(alfabetizacao_indigena_base.total_indigenas, 0::numeric) * 100::numeric, 2) AS per_alfabetizados_indigenas
                   FROM alfabetizacao_indigena_base
                ), mortalidade_2025 AS (
                 SELECT vw_mortalidade.cd_mun,
                    sum(vw_mortalidade.nascidos)::numeric AS nascidos,
                        CASE
                            WHEN sum(vw_mortalidade.nascidos) > 0 THEN round(sum(vw_mortalidade.obitos_infantis)::numeric / sum(vw_mortalidade.nascidos)::numeric * 1000::numeric, 2)
                            ELSE NULL::numeric
                        END AS mortalidade_infantil
                   FROM sau_mortalidade.vw_mortalidade
                  WHERE vw_mortalidade.ano = 2025
                  GROUP BY vw_mortalidade.cd_mun
                ), imunizacao_base AS (
                 SELECT DISTINCT vw_imunizacao_anual.cd_mun,
                    vw_imunizacao_anual.vacina,
                    vw_imunizacao_anual.categoria,
                    vw_imunizacao_anual.populacao,
                    vw_imunizacao_anual.doses_aplicadas,
                    vw_imunizacao_anual.cobertura_vacinal,
                    vw_imunizacao_anual.meta_cobertura
                   FROM sau_imunizacao.vw_imunizacao_anual
                  WHERE vw_imunizacao_anual.ano = 2025
                ), imunizacao_2025 AS (
                 SELECT imunizacao_base.cd_mun,
                    sum(imunizacao_base.doses_aplicadas) AS doses_aplicadas
                   FROM imunizacao_base
                  GROUP BY imunizacao_base.cd_mun
                ), estabelecimentos_dedup AS (
                 SELECT DISTINCT estabelecimento_saude_geral.cd_mun::integer AS cd_mun,
                    estabelecimento_saude_geral.ano,
                    estabelecimento_saude_geral.tipo_estab,
                    estabelecimento_saude_geral.cat_estabelecimento,
                    estabelecimento_saude_geral.total::numeric AS total
                   FROM sau_estabelecimento_de_saude.estabelecimento_saude_geral
                  WHERE estabelecimento_saude_geral.ano = 2025
                ), estabelecimentos_2025 AS (
                 SELECT estabelecimentos_dedup.cd_mun,
                    sum(estabelecimentos_dedup.total) AS total_estabelecimentos,
                    COALESCE(sum(estabelecimentos_dedup.total) FILTER (WHERE replace(replace(btrim(estabelecimentos_dedup.cat_estabelecimento), '/ '::text, '/'::text), ' /'::text, '/'::text) = 'Centro de saúde/Unidade básica'::text), 0::numeric) AS unidades_basicas,
                    COALESCE(sum(estabelecimentos_dedup.total) FILTER (WHERE btrim(estabelecimentos_dedup.cat_estabelecimento) = 'Clínica/ Centro de especialidade'::text), 0::numeric) AS clinicas_centro_especialidade
                   FROM estabelecimentos_dedup
                  GROUP BY estabelecimentos_dedup.cd_mun
                ), pib_2023 AS (
                 SELECT btrim(vw_pib.cd_mun::text)::integer AS cd_mun,
                    max(vw_pib.pib_total) AS pib_total,
                    max(vw_pib.pib_per_capita) AS pib_per_capita
                   FROM eco_pib.vw_pib
                  WHERE vw_pib.ano = 2023 AND vw_pib.cd_mun IS NOT NULL AND btrim(vw_pib.cd_mun::text) ~ '^[0-9]+$'::text
                  GROUP BY (btrim(vw_pib.cd_mun::text)::integer)
                ), receita_tributaria_2023 AS (
                 SELECT receita_tributaria_municipal.cd_mun::integer AS cd_mun,
                    max(receita_tributaria_municipal.receita_tributaria) AS receita_tributaria
                   FROM eco_pib.receita_tributaria_municipal
                  WHERE receita_tributaria_municipal.ano = 2023
                  GROUP BY receita_tributaria_municipal.cd_mun
                ), comercio_periodo AS (
                 SELECT impexp_completa.co_ano AS ano,
                    impexp_completa.co_mes::integer AS mes
                   FROM eco_comercio_exterior.impexp_completa
                  WHERE impexp_completa.co_ano IS NOT NULL AND btrim(impexp_completa.co_mes::text) ~ '^(0?[1-9]|1[0-2])$'::text AND impexp_completa.co_mun IS NOT NULL AND btrim(impexp_completa.co_mun::text) ~ '^[0-9]+$'::text
                  ORDER BY impexp_completa.co_ano DESC, (impexp_completa.co_mes::integer) DESC
                 LIMIT 1
                ), comercio_referencia AS (
                 SELECT comercio_periodo.ano,
                    comercio_periodo.mes,
                    ((('SECEX ('::text || (ARRAY['janeiro'::text, 'fevereiro'::text, 'março'::text, 'abril'::text, 'maio'::text, 'junho'::text, 'julho'::text, 'agosto'::text, 'setembro'::text, 'outubro'::text, 'novembro'::text, 'dezembro'::text])[comercio_periodo.mes]) || ' de '::text) || comercio_periodo.ano::text) || ')'::text AS fonte
                   FROM comercio_periodo
                ), comercio_recente AS (
                 SELECT btrim(impexp_completa.co_mun::text)::integer AS cd_mun,
                    COALESCE(sum(impexp_completa.vl_fob) FILTER (WHERE impexp_completa.tipo_operacao::text = 'Exportação'::text), 0::numeric) AS exportacao,
                    COALESCE(sum(impexp_completa.vl_fob) FILTER (WHERE impexp_completa.tipo_operacao::text = 'Importação'::text), 0::numeric) AS importacao,
                    COALESCE(sum(impexp_completa.vl_fob) FILTER (WHERE impexp_completa.tipo_operacao::text = 'Exportação'::text), 0::numeric) - COALESCE(sum(impexp_completa.vl_fob) FILTER (WHERE impexp_completa.tipo_operacao::text = 'Importação'::text), 0::numeric) AS balanca_comercial
                   FROM eco_comercio_exterior.impexp_completa
                  WHERE ((impexp_completa.co_ano, impexp_completa.co_mes::integer) = ( SELECT comercio_periodo.ano,
                            comercio_periodo.mes
                           FROM comercio_periodo)) AND impexp_completa.co_mun IS NOT NULL AND btrim(impexp_completa.co_mun::text) ~ '^[0-9]+$'::text
                  GROUP BY (btrim(impexp_completa.co_mun::text)::integer)
                ), infra_esgoto_2022 AS (
                 SELECT final_esgotamento_sanitario.cd_mun,
                    round(100.0 * max(final_esgotamento_sanitario.rede_geral_ou_pluvial)::numeric / NULLIF(max(final_esgotamento_sanitario.total)::numeric, 0::numeric), 2) AS per_esgotamento,
                    round(100.0 * max(final_esgotamento_sanitario.nao_tinham_banheiro_e_ou_sanitario)::numeric / NULLIF(max(final_esgotamento_sanitario.total)::numeric, 0::numeric), 2) AS per_sem_banheiro
                   FROM infra_esgotamento_sanitario.final_esgotamento_sanitario
                  WHERE final_esgotamento_sanitario.ano = 2022
                  GROUP BY final_esgotamento_sanitario.cd_mun
                ), infra_lixo_2022 AS (
                 SELECT destinacao_lixo.cd_mun::integer AS cd_mun,
                    round(100.0 * max(destinacao_lixo.coletado_por_servico_de_limpeza)::numeric / NULLIF(max(destinacao_lixo.total)::numeric, 0::numeric), 2) AS per_coleta_lixo
                   FROM infra_destino_lixo.destinacao_lixo
                  WHERE destinacao_lixo.ano = 2022
                  GROUP BY destinacao_lixo.cd_mun
                ), social_2010 AS (
                 SELECT vw_idhm.cd_mun,
                    max(vw_idhm.renda_per_capita) AS renda_per_capita,
                    max(vw_idhm.indice_gini) AS indice_gini,
                    max(vw_idhm.idhm) AS idhm,
                    max(vw_idhm.idhm_educacao) AS idhm_educacao,
                    max(vw_idhm.idhm_longevidade) AS idhm_longevidade,
                    max(vw_idhm.idhm_renda) AS idhm_renda
                   FROM des_idhm.vw_idhm
                  WHERE vw_idhm.ano = 2010
                  GROUP BY vw_idhm.cd_mun
                ), seguranca_hidrica_2025 AS (
                 SELECT seguranca_hidrica.cd_mun::integer AS cd_mun,
                    max(seguranca_hidrica.total_2025)::numeric AS total_cisternas,
                    max(seguranca_hidrica.primeira_agua_qtd)::numeric AS abastecimento_humano,
                    max(seguranca_hidrica.segunda_agua_qtd)::numeric AS irrigacao_dessedentacao
                   FROM relatorios_auto.seguranca_hidrica
                  GROUP BY seguranca_hidrica.cd_mun
                ), desertificacao_municipal AS (
                 SELECT vw_aridez.cd_mun,
                    sum(
                        CASE
                            WHEN vw_aridez.dn_uni::text = ANY (ARRAY['2'::text, '3'::text, '4'::text]) THEN vw_aridez.area_km2_classe
                            ELSE 0::numeric
                        END) AS area_suscetivel_desertificacao
                   FROM meio_aridez.vw_aridez
                  WHERE vw_aridez.ano_consolidacao = 2021
                  GROUP BY vw_aridez.cd_mun
                ), desertificacao_municipal_base AS (
                 SELECT vw_aridez.cd_mun,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_aridez.ano_consolidacao = 1991) > 0 THEN sum(
                            CASE
                                WHEN vw_aridez.ano_consolidacao = 1991 AND (vw_aridez.dn_uni::text = ANY (ARRAY['2'::text, '3'::text, '4'::text])) THEN vw_aridez.area_km2_classe
                                ELSE 0::numeric
                            END)
                            ELSE NULL::numeric
                        END AS area_1991,
                        CASE
                            WHEN count(*) FILTER (WHERE vw_aridez.ano_consolidacao = 2021) > 0 THEN sum(
                            CASE
                                WHEN vw_aridez.ano_consolidacao = 2021 AND (vw_aridez.dn_uni::text = ANY (ARRAY['2'::text, '3'::text, '4'::text])) THEN vw_aridez.area_km2_classe
                                ELSE 0::numeric
                            END)
                            ELSE NULL::numeric
                        END AS area_2021
                   FROM meio_aridez.vw_aridez
                  WHERE vw_aridez.ano_consolidacao = ANY (ARRAY[1991, 2021])
                  GROUP BY vw_aridez.cd_mun
                ), desertificacao_municipal_avanco AS (
                 SELECT desertificacao_municipal_base.cd_mun,
                        CASE
                            WHEN desertificacao_municipal_base.area_1991 IS NOT NULL AND desertificacao_municipal_base.area_2021 IS NOT NULL THEN desertificacao_municipal_base.area_2021 - desertificacao_municipal_base.area_1991
                            ELSE NULL::numeric
                        END AS avanco_asd
                   FROM desertificacao_municipal_base
                ), ucs AS (
                 SELECT btrim(vw_ucs.cd_mun)::integer AS cd_mun,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE)::numeric AS qtd_uc,
                    COALESCE(sum(vw_ucs.area_ha) FILTER (WHERE vw_ucs.possui_uc IS TRUE), 0::numeric) AS area_uc_ha,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE AND vw_ucs.grupo_manejo = 'Proteção Integral'::text)::numeric AS qtd_uc_protecao_integral,
                    count(*) FILTER (WHERE vw_ucs.possui_uc IS TRUE AND vw_ucs.grupo_manejo = 'Uso Sustentável'::text)::numeric AS qtd_uc_uso_sustentavel
                   FROM meio_ucs.vw_ucs
                  WHERE vw_ucs.sudene = 'Sim'::text AND vw_ucs.cd_mun IS NOT NULL AND btrim(vw_ucs.cd_mun) ~ '^[0-9]+$'::text
                  GROUP BY (btrim(vw_ucs.cd_mun)::integer)
                )
         SELECT m.nm_mun,
            m.cd_mun,
            m.estado,
            m.sigla_uf,
            'Área do município'::text AS nm_area_municipio,
            COALESCE(round(m.area_municipio, 3)::text, 'Não há dados'::text) AS valor_area_municipio,
            'IBGE'::text AS fonte_area_municipio,
            'Extensão territorial'::text AS unid_area_municipio,
            'População residente'::text AS nm_pop_residente,
            COALESCE(pop.populacao_residente::text, 'Não há dados'::text) AS valor_pop_residente,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_pop_residente,
            'Pessoas residentes'::text AS unid_pop_residente,
            'População feminina'::text AS nm_pop_feminina,
            COALESCE(pop.populacao_feminina::text, 'Não há dados'::text) AS valor_pop_feminino,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_pop_feminino,
            'Mulheres'::text AS unid_pop_feminino,
            'População masculina'::text AS nm_pop_masculina,
            COALESCE(pop.populacao_masculina::text, 'Não há dados'::text) AS valor_pop_masculina,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_pop_masculina,
            'Homens'::text AS unid_pop_masculina,
            'População quilombola'::text AS nm_pop_quilombola,
            COALESCE(pq.populacao_quilombola::text, 'Não há dados'::text) AS valor_pop_quilombola,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_pop_quilombola,
            'Quilombola(s)'::text AS unid_pop_quilombola,
            'População indígena'::text AS nm_pop_indigena,
            COALESCE(pi.populacao_indigena::text, 'Não há dados'::text) AS valor_pop_indigena,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_pop_indigena,
            'Indígena(s)'::text AS unid_pop_indigena,
            'População em situação de rua'::text AS nm_pop_rua,
            COALESCE(pr.populacao_rua::text, 'Não há dados'::text) AS valor_pop_rua,
            'SENARC (março de 2026)'::text AS fonte_pop_rua,
            'Pessoas em situação de rua'::text AS unid_pop_rua,
            'Fundamental incompleto ou sem instrução'::text AS nm_fundamental_incom,
            COALESCE(instr.per_fundamental_incompleto::text, 'Não há dados'::text) AS per_fundamental_incom,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_fundamental_incom,
            'Percentual da população'::text AS unid_fundamental_incom,
            'Fundamental completo'::text AS nm_fundamental_com,
            COALESCE(instr.per_fundamental_completo::text, 'Não há dados'::text) AS per_fundamental_com,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_fundamental_com,
            'Percentual da população'::text AS unid_fundamental_com,
            'Médio completo'::text AS nm_medio_com,
            COALESCE(instr.per_medio_completo::text, 'Não há dados'::text) AS per_medio_com,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_medio_com,
            'Percentual da população'::text AS unid_medio_com,
            'Superior completo'::text AS nm_superior_com,
            COALESCE(instr.per_superior_completo::text, 'Não há dados'::text) AS per_superior_com,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_superior_com,
            'Percentual da população'::text AS unid_superior_com,
            'População quilombola alfabetizada'::text AS nm_alfabetizada_quilombola,
            COALESCE(aq.per_alfabetizados_quilombolas::text, 'Não há dados'::text) AS per_alfabetizada_quilombola,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_alfabetizada_quilombola,
            'Percentual da população quilombola'::text AS unid_alfabetizada_quilombola,
            'População indígena alfabetizada'::text AS nm_alfabetizada_indigena,
            COALESCE(ai.per_alfabetizados_indigenas::text, 'Não há dados'::text) AS per_alfabetizada_indigena,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_alfabetizada_indigena,
            'Percentual da população indígena'::text AS unid_alfabetizada_indigena,
            'Nascidos vivos'::text AS nm_nascidos,
            COALESCE(mort.nascidos::text, 'Não há dados'::text) AS valor_nascidos,
            'DATASUS (2025)'::text AS fonte_nascidos,
            'Nascido(s) vivos'::text AS unid_nascidos,
            'Mortalidade infantil'::text AS nm_mortalidade_infantil,
            COALESCE(mort.mortalidade_infantil::text, 'Não há dados'::text) AS valor_mortalidade_infantil,
            'DATASUS (2025)'::text AS fonte_mortalidade_infantil,
            'Óbito(s) infantis por mil nascidos vivos'::text AS unid_mortalidade_infantil,
            'Doses aplicadas'::text AS nm_doses,
            COALESCE(imu.doses_aplicadas::text, 'Não há dados'::text) AS valor_doses,
            'MS/SVSA/DPNI (2025)'::text AS fonte_doses,
            'Doses'::text AS unid_doses,
            'Estabelecimentos de saúde'::text AS nm_estabelecimento,
            COALESCE(est.total_estabelecimentos::text, 'Não há dados'::text) AS valor_estabelecimento,
            'CNES (2025)'::text AS fonte_estabelecimento,
            'Unidade(s)'::text AS unid_estabelecimento,
            'Unidades Básicas de Saúde (UBS)'::text AS nm_unidade_basica,
            COALESCE(est.unidades_basicas::text, 'Não há dados'::text) AS valor_unidade_basica,
            'CNES (2025)'::text AS fonte_unidade_basica,
            'Unidade(s)'::text AS unid_unidade_basica,
            'Clínicas ou Centros de especialidade'::text AS nm_clinica_centro_especialidade,
            COALESCE(est.clinicas_centro_especialidade::text, 'Não há dados'::text) AS valor_clinica_centro_especialidade,
            'CNES (2025)'::text AS fonte_clinica_centro_especialidade,
            'Unidade(s)'::text AS unid_clinica_centro_especialidade,
            'PIB'::text AS nm_pib,
            COALESCE(pib.pib_total::text, 'Não há dados'::text) AS valor_pib,
            'IBGE (2025)'::text AS fonte_pib,
            'Reais'::text AS unid_pib,
            'PIB per capita'::text AS nm_pib_capita,
            COALESCE(pib.pib_per_capita::text, 'Não há dados'::text) AS valor_pib_capita,
            'IBGE (2025)'::text AS fonte_pib_capita,
            'Reais por habitante'::text AS unid_pib_capita,
            'Receita tributária municipal'::text AS nm_carga_tributaria,
            COALESCE(rt.receita_tributaria::text, 'Não há dados'::text) AS valor_carga_tributaria,
            'STN/FINBRA/SICONFI (2023)'::text AS fonte_carga_tributaria,
            'Reais'::text AS unid_carga_tributaria,
            'Exportações'::text AS nm_exportacao,
            COALESCE(com.exportacao::text, 'Não há dados'::text) AS valor_exportacao,
            COALESCE(com_ref.fonte, 'SECEX (sem período disponível)'::text) AS fonte_exportacao,
            'Dólar(s) FOB'::text AS unid_exportacao,
            'Importações'::text AS nm_importacao,
            COALESCE(com.importacao::text, 'Não há dados'::text) AS valor_importacao,
            COALESCE(com_ref.fonte, 'SECEX (sem período disponível)'::text) AS fonte_importacao,
            'Dólar(s) FOB'::text AS unid_importacao,
            'Balança comercial'::text AS nm_balanca,
            COALESCE(com.balanca_comercial::text, 'Não há dados'::text) AS valor_balanca,
            COALESCE(com_ref.fonte, 'SECEX (sem período disponível)'::text) AS fonte_balanca,
            'Dólar(s) FOB'::text AS unid_balanca,
            'Domicílios ligados à rede geral ou pluvial de esgotamento sanitário'::text AS nm_esgotamento,
            COALESCE(ie.per_esgotamento::text, 'Não há dados'::text) AS valor_esgotamento,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_esgotamento,
            'Percentual de domicílios'::text AS unid_esgotamento,
            'Domicílios sem banheiro e/ou sanitário'::text AS nm_banheiro,
            COALESCE(ie.per_sem_banheiro::text, 'Não há dados'::text) AS valor_banheiro,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_banheiro,
            'Percentual de domicílios'::text AS unid_banheiro,
            'Domicílios com lixo coletado por serviço de limpeza'::text AS nm_coleta_lixo,
            COALESCE(il.per_coleta_lixo::text, 'Não há dados'::text) AS valor_coleta_lixo,
            'Censo demográfico (IBGE, 2022)'::text AS fonte_coleta_lixo,
            'Percentual de domicílios'::text AS unid_coleta_lixo,
            'Renda per capita'::text AS nm_renda_capita,
            COALESCE(soc.renda_per_capita::text, 'Não há dados'::text) AS valor_renda_capita,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_renda_capita,
            'Reais por habitante'::text AS unid_renda_capita,
            'Índice de Gini'::text AS nm_gini,
            COALESCE(soc.indice_gini::text, 'Não há dados'::text) AS valor_gini,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_gini,
            'Índice'::text AS unid_gini,
            'IDHM'::text AS nm_idhm,
            COALESCE(soc.idhm::text, 'Não há dados'::text) AS valor_idhm,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_idhm,
            'Índice'::text AS unid_idhm,
            'IDHM Educação'::text AS nm_idhm_educacao,
            COALESCE(soc.idhm_educacao::text, 'Não há dados'::text) AS valor_idhm_educacao,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_idhm_educacao,
            'Índice'::text AS unid_idhm_educacao,
            'IDHM Longevidade'::text AS nm_idhm_longevidade,
            COALESCE(soc.idhm_longevidade::text, 'Não há dados'::text) AS valor_idhm_longevidade,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_idhm_longevidade,
            'Índice'::text AS unid_idhm_longevidade,
            'IDHM Renda'::text AS nm_idhm_renda,
            COALESCE(soc.idhm_renda::text, 'Não há dados'::text) AS valor_idhm_renda,
            'PNUD/ FJP/ Ipea (2010)'::text AS fonte_idhm_renda,
            'Índice'::text AS unid_idhm_renda,
            'Cisternas e tecnologias sociais de acesso à água'::text AS nm_cisternas,
            COALESCE(sh.total_cisternas::text, 'Não há dados'::text) AS valor_cisternas,
            'SESAN (2025)'::text AS fonte_cisternas,
            'Unidades'::text AS unid_cisternas,
            'Cisternas destinadas ao abastecimento humano (1ª água)'::text AS nm_abastecimento_humano,
            COALESCE(sh.abastecimento_humano::text, 'Não há dados'::text) AS valor_abastecimento_humano,
            'SESAN (2025)'::text AS fonte_abastecimento_humano,
            'Unidades'::text AS unid_abastecimento_humano,
            'Cisternas destinadas à irrigação e à dessedentação de animais (2ª água)'::text AS nm_irrigacao,
            COALESCE(sh.irrigacao_dessedentacao::text, 'Não há dados'::text) AS valor_irrigacao,
            'SESAN (2025)'::text AS fonte_irrigacao,
            'Unidades'::text AS unid_irrigacao,
            'Área suscetível à desertificação'::text AS nm_asd,
            COALESCE(round(dm.area_suscetivel_desertificacao, 2)::text, 'Não há dados'::text) AS valor_asd,
            'Xavier et al. (2020) e OCA'::text AS fonte_asd,
            'Extensão territorial'::text AS unid_asd,
            'Avanço da área suscetível à desertificação no município'::text AS "nm_asd_avanço",
            COALESCE(round(dma.avanco_asd, 2)::text, 'Não há dados'::text) AS "valor_asd_avanço",
            'Xavier et al. (2020) e OCA'::text AS "fonte_asd_avanço",
            'Diferença entre 1991 e 2021'::text AS "unid_asd_avanço",
            'Unidade(s)'::text AS nm_uc,
            COALESCE(uc.qtd_uc::text, 'Não há dados'::text) AS valor_uc,
            'CNUC (2025)'::text AS fonte_uc,
            'Quantidade de unidades de conservação'::text AS unid_uc,
            'Área das unidades de conservação'::text AS nm_uc_area,
            COALESCE(uc.area_uc_ha::text, 'Não há dados'::text) AS valor_uc_area,
            'CNUC (2025)'::text AS fonte_uc_area,
            'Extensão territorial'::text AS unid_uc_area,
            'Unidades de conservação de Proteção Integral'::text AS nm_uc_pi,
            COALESCE(uc.qtd_uc_protecao_integral::text, 'Não há dados'::text) AS valor_uc_pi,
            'CNUC (2025)'::text AS fonte_uc_pi,
            'Unidade(s)'::text AS unid_uc_pi,
            'Unidades de conservação de Uso Sustentável'::text AS nm_uc_uso,
            COALESCE(uc.qtd_uc_uso_sustentavel::text, 'Não há dados'::text) AS valor_uc_uso,
            'CNUC (2025)'::text AS fonte_uc_uso,
            'Unidade(s)'::text AS unid_uc_uso
           FROM municipios m
             LEFT JOIN populacao_2022 pop ON pop.cd_mun = m.cd_mun
             LEFT JOIN populacao_indigena_2022 pi ON pi.cd_mun = m.cd_mun
             LEFT JOIN populacao_quilombola_2022 pq ON pq.cd_mun = m.cd_mun
             LEFT JOIN populacao_rua_2026 pr ON pr.cd_mun = m.cd_mun
             LEFT JOIN instrucao_2022 instr ON instr.cd_mun = m.cd_mun
             LEFT JOIN alfabetizacao_quilombola_2022 aq ON aq.cd_mun = m.cd_mun
             LEFT JOIN alfabetizacao_indigena_2022 ai ON ai.cd_mun = m.cd_mun
             LEFT JOIN mortalidade_2025 mort ON mort.cd_mun = m.cd_mun
             LEFT JOIN imunizacao_2025 imu ON imu.cd_mun = m.cd_mun
             LEFT JOIN estabelecimentos_2025 est ON est.cd_mun = m.cd_mun
             LEFT JOIN pib_2023 pib ON pib.cd_mun = m.cd_mun
             LEFT JOIN receita_tributaria_2023 rt ON rt.cd_mun = m.cd_mun
             LEFT JOIN comercio_recente com ON com.cd_mun = m.cd_mun
             LEFT JOIN comercio_referencia com_ref ON true
             LEFT JOIN infra_esgoto_2022 ie ON ie.cd_mun = m.cd_mun
             LEFT JOIN infra_lixo_2022 il ON il.cd_mun = m.cd_mun
             LEFT JOIN social_2010 soc ON soc.cd_mun = m.cd_mun
             LEFT JOIN seguranca_hidrica_2025 sh ON sh.cd_mun = m.cd_mun
             LEFT JOIN desertificacao_municipal dm ON dm.cd_mun = m.cd_mun
             LEFT JOIN desertificacao_municipal_avanco dma ON dma.cd_mun = m.cd_mun
             LEFT JOIN ucs uc ON uc.cd_mun = m.cd_mun) q
     LEFT JOIN carac_mun.novos_nomes nn ON btrim(q.cd_mun::text) = btrim(nn.cd_mun::text);

REFRESH MATERIALIZED VIEW CONCURRENTLY relatorios_auto.mv_indicadores;
