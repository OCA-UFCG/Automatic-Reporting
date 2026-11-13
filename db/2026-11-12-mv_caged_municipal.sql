-- relatorios_auto.mv_caged_municipal: o trecho CAGED do relatório de Economia e Renda,
-- uma linha por município, os marcadores do Doc como colunas.
-- Decisões e razões: Documentacao-OCA data-nordeste/automatic-reporting/HANDOFF-CAGED-ECONOMIA.md
--
-- APLICADO no gamma (oca_db) em 2026-11-12 (310 s, 2.074 linhas) e incluído no
-- ~/scripts/refresh_matviews.sh de lá. Beta e prod: ainda não.
--
-- Fonte: eco_caged.tb_caged_catalogo (microdado, 1 linha por movimentação; cd_movi +1
-- admissão, -1 desligamento). Agregar a tabela leva minutos, por isso matview com refresh
-- noturno (scripts/refresh_matviews.sh), nunca view.
--
-- Trimestre de referência = último trimestre fechado nos dados, calculado aqui; nada de
-- ano fixo. Trimestres viram um índice contínuo (q = ano*4 + trimestre-1), então
-- "anterior" = q-1 (o anterior do 1º tri é o 4º do ano passado) e "mesmo tri do ano
-- anterior" = q-4.
--
-- Universo e nomes: municípios do Censo 2022 em dem_demografia.final_demografia (2.074,
-- o mesmo universo dos relatórios) com nome de carac_mun.municipios. O CAGED grava nomes
-- antigos (Açu, Arês) e o relatório casa por nm_mun + sigla_uf. Município sem
-- movimentação sai com zeros, não some. Sem dependência de outra matview: um DROP ...
-- CASCADE nelas não leva esta junto.
--
-- Colunas de ano saem como texto: inteiro passa pelo formatador do relatório e vira "2.026".

CREATE MATERIALIZED VIEW IF NOT EXISTS relatorios_auto.mv_caged_municipal AS
WITH agg AS MATERIALIZED (
    -- ponytail: agrega a tabela inteira toda noite; com anos de histórico, um índice em
    -- tb_caged_catalogo(ano) e um WHERE ano >= max(ano)-1 aqui deixam o custo constante.
    SELECT
        cd_mun_ibge::int AS cd_mun,
        ano,
        co_mes,
        ano * 4 + (co_mes - 1) / 3 AS q,
        CASE nm_setores WHEN 'Industria' THEN 'indústria' ELSE lower(nm_setores) END AS setor,
        nm_secao,
        nm_sexo,
        nm_faixa_etaria,
        count(*) FILTER (WHERE cd_movi = 1) AS adm,
        count(*) FILTER (WHERE cd_movi = -1) AS des
    FROM eco_caged.tb_caged_catalogo
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
),
ref AS (
    -- Último mês com dado; o trimestre dele só conta se fechou (mês 3, 6, 9 ou 12).
    SELECT
        CASE WHEN mes >= 3 THEN ano ELSE ano - 1 END AS ano_ref,
        CASE WHEN mes >= 3 THEN mes / 3 ELSE 4 END AS tri_ref
    FROM (SELECT ano, max(co_mes) AS mes FROM agg WHERE ano = (SELECT max(ano) FROM agg) GROUP BY ano) u
),
r AS (
    SELECT ano_ref, tri_ref, ano_ref * 4 + tri_ref - 1 AS cur, 3 * tri_ref AS ult_mes FROM ref
),
base AS (
    SELECT f.cd_mun, m.nm_mun, m.sigla_uf, f.pop_2022
    FROM (
        SELECT cd_mun, sum(populacao_total) AS pop_2022
        FROM dem_demografia.final_demografia
        WHERE ano = 2022
        GROUP BY cd_mun
    ) f
    JOIN carac_mun.municipios m ON m.cd_mun = f.cd_mun::text
),
mun AS (
    SELECT
        a.cd_mun,
        sum(a.adm) FILTER (WHERE a.q = r.cur) AS adm_tri,
        sum(a.des) FILTER (WHERE a.q = r.cur) AS des_tri,
        sum(a.adm) FILTER (WHERE a.q = r.cur - 1) AS adm_ant,
        sum(a.des) FILTER (WHERE a.q = r.cur - 1) AS des_ant,
        sum(a.adm - a.des) FILTER (WHERE a.q = r.cur - 4) AS saldo_yoy,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes <= r.ult_mes) AS acum,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes <= r.ult_mes) AS acum_ant,
        sum(a.adm - a.des) FILTER (WHERE a.q = r.cur AND a.nm_sexo = 'Mulher') AS saldo_mulheres,
        sum(a.adm - a.des) FILTER (WHERE a.q = r.cur AND a.nm_sexo = 'Homem') AS saldo_homens,
        -- Série da Figura X3: janeiro até o fim do trimestre de referência, nos dois anos.
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 1) AS m01_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 2) AS m02_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 3) AS m03_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 4) AS m04_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 5) AS m05_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 6) AS m06_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 7) AS m07_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 8) AS m08_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 9) AS m09_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 10) AS m10_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 11) AS m11_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref - 1 AND a.co_mes = 12) AS m12_ant,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 1) AS m01,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 2) AS m02,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 3) AS m03,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 4) AS m04,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 5) AS m05,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 6) AS m06,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 7) AS m07,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 8) AS m08,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 9) AS m09,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 10) AS m10,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 11) AS m11,
        sum(a.adm - a.des) FILTER (WHERE a.ano = r.ano_ref AND a.co_mes = 12) AS m12
    FROM agg a CROSS JOIN r
    WHERE a.q BETWEEN r.cur - 4 AND r.cur OR a.ano = r.ano_ref - 1
    GROUP BY a.cd_mun
),
setores AS (
    SELECT
        a.cd_mun, a.setor,
        sum(a.adm) AS adm, sum(a.des) AS des, sum(a.adm - a.des) AS saldo,
        row_number() OVER w_saldo AS rk_saldo,
        row_number() OVER w_mov AS rk_mov
    FROM agg a CROSS JOIN r
    WHERE a.q = r.cur
    GROUP BY a.cd_mun, a.setor
    WINDOW
        w_saldo AS (PARTITION BY a.cd_mun ORDER BY sum(a.adm - a.des) DESC, sum(a.adm + a.des) DESC, a.setor),
        w_mov AS (PARTITION BY a.cd_mun ORDER BY sum(a.adm + a.des) DESC, sum(a.adm - a.des) DESC, a.setor)
),
setores_mun AS (
    SELECT
        cd_mun,
        -- "serviços (+1.010), construção (+338) e agricultura (-53)": ordem por saldo; o
        -- regexp troca a última vírgula por " e" (nenhum item tem vírgula).
        regexp_replace(
            string_agg(
                setor || ' (' || CASE WHEN saldo > 0 THEN '+' WHEN saldo < 0 THEN '-' ELSE '' END
                    || replace(to_char(abs(saldo), 'FM999,999,990'), ',', '.') || ')',
                ', ' ORDER BY rk_saldo),
            ', ([^,]*)$', ' e \1') AS setores_saldo_lista,
        max(setor) FILTER (WHERE rk_mov = 1) AS setor_maior_movimentacao,
        max(adm) FILTER (WHERE rk_mov = 1) AS setor_maior_movimentacao_admissoes,
        max(des) FILTER (WHERE rk_mov = 1) AS setor_maior_movimentacao_desligamentos,
        max(saldo) FILTER (WHERE rk_mov = 1) AS setor_maior_movimentacao_saldo,
        (max(setor) FILTER (WHERE rk_mov = 1) = max(setor) FILTER (WHERE rk_saldo = 1))::int
            AS setor_maior_mov_e_maior_saldo
    FROM setores
    GROUP BY cd_mun
),
secoes AS (
    SELECT DISTINCT ON (a.cd_mun)
        a.cd_mun,
        replace(lower(a.nm_secao), 'aqüicultura', 'aquicultura') AS secao_maior_saldo,
        sum(a.adm - a.des) AS secao_maior_saldo_postos
    FROM agg a CROSS JOIN r
    WHERE a.q = r.cur AND a.nm_secao <> 'Não identificado'
    GROUP BY a.cd_mun, a.nm_secao
    ORDER BY a.cd_mun, sum(a.adm - a.des) DESC, sum(a.adm + a.des) DESC, a.nm_secao
),
faixas AS (
    SELECT
        cd_mun,
        regexp_replace(
            string_agg(
                faixa || ' (' || CASE WHEN saldo > 0 THEN '+' ELSE '-' END
                    || replace(to_char(abs(saldo), 'FM999,999,990'), ',', '.') || ')',
                -- Empate de saldo: da faixa mais nova para a mais velha ("até 17" primeiro).
                ', ' ORDER BY saldo DESC, CASE WHEN faixa LIKE 'até%' THEN '0' ELSE faixa END),
            ', ([^,]*)$', ' e \1') AS faixas_saldo_lista
    FROM (
        SELECT
            a.cd_mun,
            CASE WHEN a.nm_faixa_etaria LIKE 'Até%' THEN 'até' || substr(a.nm_faixa_etaria, 4)
                 ELSE a.nm_faixa_etaria END AS faixa,
            sum(a.adm - a.des) AS saldo
        FROM agg a CROSS JOIN r
        WHERE a.q = r.cur AND a.nm_faixa_etaria <> 'Desconhecidos'
        GROUP BY 1, 2
    ) f
    WHERE saldo <> 0
    GROUP BY cd_mun
),
nomes AS (
    SELECT * FROM (VALUES
        (1, 'primeiro', 'março'), (2, 'segundo', 'junho'),
        (3, 'terceiro', 'setembro'), (4, 'quarto', 'dezembro')
    ) v(tri, ordinal, ultimo_mes)
),
linhas AS (
    SELECT
        b.cd_mun,
        b.nm_mun,
        b.sigla_uf,
        nt.ordinal AS tri_atual1,
        r.ano_ref::text AS ano_atual,
        na.ordinal AS tri_anterior1,
        (CASE WHEN r.tri_ref = 1 THEN r.ano_ref - 1 ELSE r.ano_ref END)::text AS ano_tri_anterior,
        (r.ano_ref - 1)::text AS ano_anterior,
        nt.ultimo_mes AS ultimo_mes_tri,
        coalesce(m.adm_tri, 0) AS admissao_tri_atual,
        coalesce(m.des_tri, 0) AS desligamento_tri_atual,
        coalesce(m.adm_tri - m.des_tri, 0) AS saldo_tri_atual,
        coalesce(m.adm_tri + m.des_tri, 0) AS movimentacoes_tri_atual,
        coalesce(m.adm_ant, 0) AS admissao_tri_anterior,
        coalesce(m.des_ant, 0) AS desligamento_tri_anterior,
        coalesce(m.adm_ant - m.des_ant, 0) AS saldo_tri_anterior,
        coalesce(m.saldo_yoy, 0) AS saldo_tri_ano_anterior,
        coalesce(m.acum, 0) AS saldo_acumulado_ano_atual,
        coalesce(m.acum_ant, 0) AS saldo_acumulado_ano_anterior,
        -- Só com base positiva: com base negativa ou zero o percentual inverte o sentido
        -- ou divide por zero (decisão C). O Doc só usa esta coluna sob essa condição.
        CASE WHEN m.acum_ant > 0 THEN round((m.acum - m.acum_ant) * 100.0 / m.acum_ant, 1) END
            AS variacao_acumulado_per,
        s.setores_saldo_lista,
        sc.secao_maior_saldo,
        coalesce(sc.secao_maior_saldo_postos, 0) AS secao_maior_saldo_postos,
        s.setor_maior_movimentacao,
        s.setor_maior_movimentacao_admissoes,
        s.setor_maior_movimentacao_desligamentos,
        s.setor_maior_movimentacao_saldo,
        coalesce(s.setor_maior_mov_e_maior_saldo, 0) AS setor_maior_mov_e_maior_saldo,
        coalesce(m.saldo_mulheres, 0) AS saldo_mulheres,
        coalesce(m.saldo_homens, 0) AS saldo_homens,
        f.faixas_saldo_lista,
        b.pop_2022,
        round(coalesce(m.adm_tri - m.des_tri, 0) * 1000.0 / nullif(b.pop_2022, 0), 1) AS saldo_por_mil_hab,
        round(sum(coalesce(m.adm_tri - m.des_tri, 0)) OVER () * 1000.0 / sum(b.pop_2022) OVER (), 1)
            AS saldo_por_mil_hab_sudene,
        m.m01_ant AS saldo_mes01_ano_anterior, m.m02_ant AS saldo_mes02_ano_anterior,
        m.m03_ant AS saldo_mes03_ano_anterior, m.m04_ant AS saldo_mes04_ano_anterior,
        m.m05_ant AS saldo_mes05_ano_anterior, m.m06_ant AS saldo_mes06_ano_anterior,
        m.m07_ant AS saldo_mes07_ano_anterior, m.m08_ant AS saldo_mes08_ano_anterior,
        m.m09_ant AS saldo_mes09_ano_anterior, m.m10_ant AS saldo_mes10_ano_anterior,
        m.m11_ant AS saldo_mes11_ano_anterior, m.m12_ant AS saldo_mes12_ano_anterior,
        -- Ano atual só até o fim do trimestre de referência: meses depois dele ainda não
        -- fecham trimestre e ficam fora do texto e do gráfico.
        CASE WHEN r.ult_mes >= 1 THEN m.m01 END AS saldo_mes01_ano_atual,
        CASE WHEN r.ult_mes >= 2 THEN m.m02 END AS saldo_mes02_ano_atual,
        CASE WHEN r.ult_mes >= 3 THEN m.m03 END AS saldo_mes03_ano_atual,
        CASE WHEN r.ult_mes >= 4 THEN m.m04 END AS saldo_mes04_ano_atual,
        CASE WHEN r.ult_mes >= 5 THEN m.m05 END AS saldo_mes05_ano_atual,
        CASE WHEN r.ult_mes >= 6 THEN m.m06 END AS saldo_mes06_ano_atual,
        CASE WHEN r.ult_mes >= 7 THEN m.m07 END AS saldo_mes07_ano_atual,
        CASE WHEN r.ult_mes >= 8 THEN m.m08 END AS saldo_mes08_ano_atual,
        CASE WHEN r.ult_mes >= 9 THEN m.m09 END AS saldo_mes09_ano_atual,
        CASE WHEN r.ult_mes >= 10 THEN m.m10 END AS saldo_mes10_ano_atual,
        CASE WHEN r.ult_mes >= 11 THEN m.m11 END AS saldo_mes11_ano_atual,
        CASE WHEN r.ult_mes >= 12 THEN m.m12 END AS saldo_mes12_ano_atual
    FROM base b
    CROSS JOIN r
    JOIN nomes nt ON nt.tri = r.tri_ref
    JOIN nomes na ON na.tri = CASE WHEN r.tri_ref = 1 THEN 4 ELSE r.tri_ref - 1 END
    LEFT JOIN mun m ON m.cd_mun = b.cd_mun
    LEFT JOIN setores_mun s ON s.cd_mun = b.cd_mun
    LEFT JOIN secoes sc ON sc.cd_mun = b.cd_mun
    LEFT JOIN faixas f ON f.cd_mun = b.cd_mun
)
SELECT
    *,
    CASE WHEN saldo_tri_atual > 0 THEN 'positivo' WHEN saldo_tri_atual < 0 THEN 'negativo' ELSE 'nulo' END
        AS analise_saldo_tri_atual,
    CASE WHEN saldo_tri_anterior > 0 THEN 'positivo' WHEN saldo_tri_anterior < 0 THEN 'negativo' ELSE 'nulo' END
        AS analise_saldo_tri_anterior,
    CASE WHEN saldo_tri_ano_anterior > 0 THEN 'positivo' WHEN saldo_tri_ano_anterior < 0 THEN 'negativo' ELSE 'nulo' END
        AS analise_saldo_tri_ano_anterior
FROM linhas
WITH DATA;

-- REFRESH ... CONCURRENTLY (scripts/refresh_matviews.sh) exige índice único; cd_mun é
-- uma linha por município (universo do Censo 2022).
CREATE UNIQUE INDEX IF NOT EXISTS mv_caged_municipal_cd_mun_idx
    ON relatorios_auto.mv_caged_municipal (cd_mun);
