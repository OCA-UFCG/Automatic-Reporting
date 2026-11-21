-- relatorios_auto.mv_importacao_municipal: linhas de importação do relatório de Economia
-- e Renda (utils/queries/economia_importacao.py), uma por município × mês × país × seção ×
-- produto (sh4), só do último ano com importação de cada município.
--
-- Ainda NÃO aplicado. Ao aplicar: incluir em MATVIEWS do scripts/refresh_matviews.sh
-- (e na cópia do script na VM), senão a matview fica parada no dia da criação.
--
-- Por que matview: a consulta direto na eco_comercio_exterior.impexp_completa, mesmo pelo
-- idx_fato_comex_co_mun_tipo_ano, lia dezenas de milhares de páginas espalhadas da fato
-- nos maiores importadores (todos os anos, para achar o último, e depois as linhas dele),
-- e com o cache do Postgres frio passava do statement_timeout. Aqui as linhas de cada
-- município ficam juntas (ORDER BY no fim) e a leitura é de poucas centenas de páginas.
--
-- Mesmo resultado da consulta antiga: processar_importacao só soma vl_fob e kg_liquido
-- por país, seção e produto, então somar antes não muda nada (conferido em 21 municípios,
-- incluindo Maceió, Recife, Camaçari e Belém (AL)). Também ficam aqui o replace de
-- "indútrias" e o nome corrigido do produto (dic_sh4_nome_corrigido), que antes eram
-- aplicados na consulta e no Python.
--
-- Dependência: impexp_completa. Um DROP ... CASCADE nela derruba esta matview junto; o
-- relatório então sai sem o bloco de importação (executar_query devolve None), sem erro.
--
-- Montagem: ~2 min e ~33 MB (2.074 municípios, ~97 mil linhas).

CREATE MATERIALIZED VIEW IF NOT EXISTS relatorios_auto.mv_importacao_municipal AS
WITH imp AS MATERIALIZED (
    SELECT
        co_mun,
        sg_uf_mun,
        desc_municipio,
        co_ano,
        co_mes,
        desc_mes,
        desc_pais_portugues,
        REPLACE(desc_secao, 'indútrias', 'indústrias') AS desc_secao,
        sh4,
        desc_sh4,
        kg_liquido,
        vl_fob
    FROM eco_comercio_exterior.impexp_completa
    WHERE tipo_operacao = 'Importação'
),
ultimo AS (
    SELECT co_mun, MAX(co_ano) AS co_ano
    FROM imp
    GROUP BY co_mun
)
SELECT
    i.co_mun,
    i.sg_uf_mun,
    i.desc_municipio,
    i.co_ano,
    i.co_mes,
    i.desc_mes,
    i.desc_pais_portugues,
    i.desc_secao,
    COALESCE(d.desc_corrigida, i.desc_sh4) AS desc_sh4,
    SUM(i.kg_liquido) AS kg_liquido,
    SUM(i.vl_fob) AS vl_fob
FROM imp i
JOIN ultimo u USING (co_mun, co_ano)
LEFT JOIN eco_comercio_exterior.dic_sh4_nome_corrigido d ON d.sh4::text = i.sh4::text
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
ORDER BY i.desc_municipio, i.sg_uf_mun, i.co_mes;

-- Leitura do relatório: nome + UF.
CREATE INDEX IF NOT EXISTS mv_importacao_municipal_nome_uf_idx
    ON relatorios_auto.mv_importacao_municipal (LOWER(desc_municipio), sg_uf_mun);

-- REFRESH ... CONCURRENTLY (scripts/refresh_matviews.sh) exige índice único. Há linhas com
-- país/seção/produto NULL (~14 mil no gamma); o índice as aceita e o refresh concorrente
-- também (compara a linha inteira). Conferir com um REFRESH ... CONCURRENTLY ao aplicar.
CREATE UNIQUE INDEX IF NOT EXISTS mv_importacao_municipal_chave_idx
    ON relatorios_auto.mv_importacao_municipal
    (co_mun, co_mes, desc_pais_portugues, desc_secao, desc_sh4);
