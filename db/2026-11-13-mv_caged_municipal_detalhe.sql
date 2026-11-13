-- relatorios_auto.mv_caged_municipal_detalhe: escolaridade e ocupações (CBO) do trimestre
-- de referência, uma linha por município. Complementa mv_caged_municipal (parágrafo de
-- escolaridade e ocupações do Doc de Economia e Renda, editoria 12/11/2026).
-- Decisões e razões: Documentacao-OCA data-nordeste/automatic-reporting/HANDOFF-CAGED-ECONOMIA.md
--
-- Por que matview separada: somar escolaridade e CBO à varredura de mv_caged_municipal
-- (grouping sets) passou de 15 min; uma segunda varredura só do trimestre leva ~4 min
-- (251 s, medido 13/11/2026). Separadas, cada REFRESH fica dentro do STMT_TIMEOUT_MS de
-- 10 min de scripts/refresh_matviews.sh, sem índice novo na tabela do time de dados.
--
-- O trimestre vem de mv_caged_municipal (mesmo trimestre do resto do texto, por
-- construção): o refresh desta precisa vir DEPOIS dela, e um DROP ... CASCADE nela leva
-- esta junto (são do mesmo recurso).
--
-- Ocupação sai com o código CBO (ocupacao_maior_saldoN_cbo): a base grava os títulos sem
-- acento ("Producao"); utils/queries/economia_caged.py troca pelo título oficial
-- (utils/data/cbo2002_ocupacao.csv) e usa este nome em minúsculas só quando o código
-- não está na lista oficial.

CREATE MATERIALIZED VIEW IF NOT EXISTS relatorios_auto.mv_caged_municipal_detalhe AS
WITH r AS (
    SELECT
        ano_atual::int AS ano,
        CASE ultimo_mes_tri WHEN 'março' THEN 3 WHEN 'junho' THEN 6 WHEN 'setembro' THEN 9 ELSE 12 END
            AS ult_mes
    FROM relatorios_auto.mv_caged_municipal
    LIMIT 1
),
agg AS MATERIALIZED (
    -- ~2 mi de linhas do trimestre; o custo é a varredura, não o agrupamento.
    SELECT
        t.cd_mun_ibge::int AS cd_mun,
        CASE GROUPING(t.nm_instrucao, t.cd_cbo) WHEN 1 THEN 'instrucao' ELSE 'cbo' END AS conjunto,
        t.nm_instrucao,
        lpad(t.cd_cbo, 6, '0') AS cd_cbo,
        min(t.nm_cbo) AS nm_cbo,
        sum(t.cd_movi) AS saldo,
        count(*) AS mov
    FROM eco_caged.tb_caged_catalogo t
    JOIN r ON t.ano = r.ano AND t.co_mes BETWEEN r.ult_mes - 2 AND r.ult_mes
    GROUP BY GROUPING SETS ((t.cd_mun_ibge, t.nm_instrucao), (t.cd_mun_ibge, t.cd_cbo))
),
escolaridade AS (
    -- Rótulo da base -> como cabe em "trabalhadores com ___" no Doc.
    SELECT a.cd_mun, coalesce(e.frase, lower(a.nm_instrucao)) AS frase, a.saldo, a.mov,
        row_number() OVER (PARTITION BY a.cd_mun ORDER BY a.saldo DESC, a.mov DESC, e.frase) AS rk_max,
        row_number() OVER (PARTITION BY a.cd_mun ORDER BY a.saldo, a.mov DESC, e.frase) AS rk_min
    FROM agg a
    LEFT JOIN (VALUES
        ('Analfabeto', 'nenhuma escolaridade'),
        ('Até 5ª Incompleto', 'ensino fundamental incompleto (até o 5º ano)'),
        ('5ª Completo Fundamental', 'ensino fundamental incompleto (5º ano completo)'),
        ('6ª a 9ª Fundamental', 'ensino fundamental incompleto (do 6º ao 9º ano)'),
        ('Fundamental Completo', 'ensino fundamental completo'),
        ('Médio Incompleto', 'ensino médio incompleto'),
        ('Médio Completo', 'ensino médio completo'),
        ('Superior Incompleto', 'ensino superior incompleto'),
        ('Superior Completo', 'ensino superior completo'),
        ('Pós-Graduação completa', 'pós-graduação completa'),
        ('Mestrado', 'mestrado'),
        ('Doutorado', 'doutorado')
    ) e(rotulo, frase) ON e.rotulo = a.nm_instrucao
    WHERE a.conjunto = 'instrucao'
),
escolaridade_mun AS (
    -- Maior saldo só se positivo, maior redução só se negativa; postos em módulo
    -- ("redução de 12"). Empate: mais movimentação, depois nome.
    SELECT
        cd_mun,
        max(frase) FILTER (WHERE rk_max = 1 AND saldo > 0) AS escolaridade_maior_saldo,
        coalesce(max(saldo) FILTER (WHERE rk_max = 1 AND saldo > 0), 0) AS escolaridade_maior_saldo_postos,
        max(frase) FILTER (WHERE rk_min = 1 AND saldo < 0) AS escolaridade_menor_saldo,
        coalesce(-max(saldo) FILTER (WHERE rk_min = 1 AND saldo < 0), 0) AS escolaridade_menor_saldo_postos
    FROM escolaridade
    GROUP BY cd_mun
),
ocupacoes_mun AS (
    -- As 4 ocupações com maior saldo positivo, sem "Não Identificado" (999999).
    -- Empate (frequente na 4ª posição): mais movimentação, depois código.
    SELECT
        cd_mun,
        max(nome) FILTER (WHERE rk = 1) AS ocupacao_maior_saldo1,
        max(cd_cbo) FILTER (WHERE rk = 1) AS ocupacao_maior_saldo1_cbo,
        coalesce(max(saldo) FILTER (WHERE rk = 1), 0) AS ocupacao_maior_saldo1_valor,
        max(nome) FILTER (WHERE rk = 2) AS ocupacao_maior_saldo2,
        max(cd_cbo) FILTER (WHERE rk = 2) AS ocupacao_maior_saldo2_cbo,
        coalesce(max(saldo) FILTER (WHERE rk = 2), 0) AS ocupacao_maior_saldo2_valor,
        max(nome) FILTER (WHERE rk = 3) AS ocupacao_maior_saldo3,
        max(cd_cbo) FILTER (WHERE rk = 3) AS ocupacao_maior_saldo3_cbo,
        coalesce(max(saldo) FILTER (WHERE rk = 3), 0) AS ocupacao_maior_saldo3_valor,
        max(nome) FILTER (WHERE rk = 4) AS ocupacao_maior_saldo4,
        max(cd_cbo) FILTER (WHERE rk = 4) AS ocupacao_maior_saldo4_cbo,
        coalesce(max(saldo) FILTER (WHERE rk = 4), 0) AS ocupacao_maior_saldo4_valor
    FROM (
        SELECT cd_mun, cd_cbo, lower(nm_cbo) AS nome, saldo,
            row_number() OVER (PARTITION BY cd_mun ORDER BY saldo DESC, mov DESC, cd_cbo) AS rk
        FROM agg
        WHERE conjunto = 'cbo' AND cd_cbo <> '999999'
    ) o
    WHERE rk <= 4 AND saldo > 0
    GROUP BY cd_mun
)
SELECT
    b.cd_mun,
    m.nm_mun,
    m.sigla_uf,
    es.escolaridade_maior_saldo,
    coalesce(es.escolaridade_maior_saldo_postos, 0) AS escolaridade_maior_saldo_postos,
    es.escolaridade_menor_saldo,
    coalesce(es.escolaridade_menor_saldo_postos, 0) AS escolaridade_menor_saldo_postos,
    oc.ocupacao_maior_saldo1, oc.ocupacao_maior_saldo1_cbo,
    coalesce(oc.ocupacao_maior_saldo1_valor, 0) AS ocupacao_maior_saldo1_valor,
    oc.ocupacao_maior_saldo2, oc.ocupacao_maior_saldo2_cbo,
    coalesce(oc.ocupacao_maior_saldo2_valor, 0) AS ocupacao_maior_saldo2_valor,
    oc.ocupacao_maior_saldo3, oc.ocupacao_maior_saldo3_cbo,
    coalesce(oc.ocupacao_maior_saldo3_valor, 0) AS ocupacao_maior_saldo3_valor,
    oc.ocupacao_maior_saldo4, oc.ocupacao_maior_saldo4_cbo,
    coalesce(oc.ocupacao_maior_saldo4_valor, 0) AS ocupacao_maior_saldo4_valor
-- Mesmo universo e nomes de mv_caged_municipal (Censo 2022 + carac_mun.municipios).
FROM (SELECT DISTINCT cd_mun FROM dem_demografia.final_demografia WHERE ano = 2022) b
JOIN carac_mun.municipios m ON m.cd_mun = b.cd_mun::text
LEFT JOIN escolaridade_mun es ON es.cd_mun = b.cd_mun
LEFT JOIN ocupacoes_mun oc ON oc.cd_mun = b.cd_mun
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS mv_caged_municipal_detalhe_cd_mun_idx
    ON relatorios_auto.mv_caged_municipal_detalhe (cd_mun);
