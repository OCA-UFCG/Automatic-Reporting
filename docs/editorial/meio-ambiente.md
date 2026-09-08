Guia rápido para quem escreve ou revisa o texto do Google Docs de **Meio Ambiente**. Não é preciso saber nada de programação para usar este guia — só seguir as regras e os exemplos abaixo.

## Como funciona, em resumo

O texto do Doc não é o relatório final. Ele é um **molde**: tem espaços em branco (chamados de "campos") que o sistema preenche automaticamente com os dados de cada cidade quando o relatório é gerado. É parecido com uma "mala direta" do Word.

Além disso, o texto pode ter **trechos que só aparecem em algumas cidades** — por exemplo, um parágrafo que só é exibido se a cidade não tiver nenhuma Unidade de Conservação, e outro parágrafo diferente para quando ela tiver várias. Isso é feito com uma linha de regra logo antes do parágrafo.

## Glossário: o que cada marcação significa

| O que você vê no Doc | O que significa |
|---|---|
| `ambiente.$nm_mun` | Um **campo** — vira o nome real da cidade quando o relatório é gerado. Qualquer coisa escrita como `ambiente.$alguma_coisa` é um campo, não deve ser editado (só usado como está). |
| `Para quando ambiente.$n_uc for igual a 0:` | Uma **regra**. Diz: "o parágrafo logo abaixo só aparece se a cidade tiver 0 UCs". Sempre termina com dois-pontos (`:`). |
| `descricao_tema = "` (no começo do texto) | Marca **onde o texto do tema começa**. Só existe **uma vez**, bem no início. |
| `"@@` (no final do texto) | Marca **onde o texto do tema termina**. Só existe **uma vez**, bem no final (depois da Síntese). Tudo que está entre essa marca e a de abertura é o que o sistema processa junto. |
| `Sequência do texto, sem condição:` | Diz "a partir daqui, o texto sempre aparece, não importa a cidade" — usado depois de uma regra, pra "desligar" a regra e voltar ao texto normal. |
| `Síntese` | Título de uma seção fixa que sempre aparece no fim do texto. |
| `hyperlink = "Nome do link` seguido de um endereço ou campo | Cria um link clicável no relatório. |

## As 5 regras de ouro

1. **Toda linha de regra (`Para quando ...`) termina com dois-pontos (`:`).**
   Sem o dois-pontos, o sistema não entende que é uma regra — e o parágrafo aparece **sempre**, pra qualquer cidade, mesmo quando não devia.

   - ❌ `Para quando for de 2 a 4 UC`
   - ✅ `Para quando ambiente.$n_uc for de 2 a 4:`

2. **Toda regra precisa citar um campo (algo com `$`).**
   Uma frase em português comum, mesmo com dois-pontos, não funciona como regra — precisa ter um `$campo` dentro dela.

   - ❌ `Para quando for apenas 1:`
   - ✅ `Para quando ambiente.$n_uc for igual a 1:`

3. **`descricao_tema = "` e `"@@` aparecem uma vez só cada, no começo e no fim de tudo.**
   Se você colocar mais de um desses no meio do texto, o sistema para de ler no primeiro `"@@` que encontrar — e o resto do texto (incluindo Fontes e Conteúdos Relacionados) desaparece do relatório. Se precisar de um parágrafo alternativo no meio do texto, use uma regra (`Para quando ...:`), nunca abra um novo `descricao_tema =`.

4. **Confira se o nome do campo está certo.**
   Se você escrever `$area_total` mas o campo certo é `$area_total_uc`, o sistema **não avisa erro nenhum** — ele simplesmente mostra `$area_total_uc` escrito literalmente no relatório, do jeito errado, sem virar um número. Sempre que copiar um campo de um parágrafo pra outro, confira se o nome é idêntico.

5. **Não repita informação que o campo já traz pronta.**
   Alguns campos já vêm com a frase inteira montada. Por exemplo, `$bioma` já é algo como *"inserida no bioma Cerrado"* — não escreva `"inserida no bioma ambiente.$bioma"`, porque aí a frase fica duplicada: *"inserida no bioma inserida no bioma Cerrado"*. O mesmo vale para `$analise_cond1`, que já vem como *"uma diminuição de"* — não escreva `$analise_cond1 de $var_aridez...`, porque o "de" fica duplicado.

## Erros que já encontramos neste texto (e como foram corrigidos)

- **Parágrafo repetido**: a regra "quando tiver 1 UC" aparecia duas vezes, uma copiada da outra com pequenos erros. → Mantida só uma versão, revisada.
- **Faltava o dois-pontos** em várias regras (UC de 2 a 4, UC 5 ou mais, condições de aridez) — por isso, mesmo sem querer, todos esses parágrafos apareciam juntos, pra qualquer cidade. → Corrigido, e cada regra agora só ativa o parágrafo certo.
- **"Unidade" no singular** onde deveria ser "Unidades" (quando são 2, 3 ou mais). → Corrigido para o plural.
- **Um dos painéis do rodapé (Fontes) não tinha link nenhum**, só o nome escrito. → Adicionado o campo do link.

## Sobre a Síntese e municípios sem alguns dados

Alguns municípios têm menos dados do que outros (por exemplo, Fernando de Noronha não tem informação de clima/aridez, provavelmente por ser uma ilha). Pra esses casos, o texto tem uma versão alternativa da Síntese e do parágrafo de aridez, que aparece só quando o dado não existe. Se você for editar essas partes, mantenha as duas versões (com dado / sem dado) — não apague nenhuma, mesmo que pareça repetitivo.

## Texto de referência (já revisado e testado)

```
descricao_tema = "As condições ambientais de um município podem indicar vulnerabilidades que demandam a atenção do poder público e influenciam o planejamento e as possibilidades de desenvolvimento local. Conhecê-las permite identificar áreas que demandam ações de conservação, proteção ou adaptação e considerar as características ambientais na elaboração de projetos e políticas públicas.

Para quando meio-ambiente.$n_uc for igual a 0:

Nesse sentido, é oportuno mencionar, que em ambiente.$nm_mun (ambiente.$sigla_uf), não há registro de Unidade de Conservação (UC).

Para quando meio-ambiente.$n_uc for igual a 1:

Em ambiente.$nm_mun (ambiente.$sigla_uf), está registrada ambiente.$n_uc Unidade de Conservação (UC), ambiente.$nome_uc, com área de ambiente.$area_total_uc hectares, ambiente.$bioma. Criada em ambiente.$ano_criacao_uc1, a unidade pertence à esfera ambiente.$esfera_1uc, está enquadrada na categoria ambiente.$categoria_uc1 e integra o grupo de ambiente.$grupo_uc1.

Para quando meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_us for igual a 0:

Em ambiente.$nm_mun (ambiente.$sigla_uf), há ambiente.$n_uc Unidades de Conservação (UC), totalizando ambiente.$area_total_uc hectares de área protegida, ambiente.$bioma. As UCs presentes no município são: ambiente.$nome_uc. Todas as unidades estão enquadradas no grupo de Proteção Integral.

Para quando meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_pi for igual a 0:

Em ambiente.$nm_mun (ambiente.$sigla_uf), há ambiente.$n_uc Unidades de Conservação (UC), totalizando ambiente.$area_total_uc hectares de área protegida, ambiente.$bioma. As UCs presentes no município são: ambiente.$nome_uc. Todas as unidades estão enquadradas no grupo de Uso sustentável.

Para quando meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_pi for diferente de 0 e meio-ambiente.$n_protecao_us for diferente de 0:

Em ambiente.$nm_mun (ambiente.$sigla_uf), há ambiente.$n_uc Unidades de Conservação (UC), totalizando ambiente.$area_total_uc hectares de área protegida, ambiente.$bioma. As UCs presentes no município são: ambiente.$nome_uc. Desse total, ambiente.$n_protecao_pi unidades estão enquadradas no grupo de Proteção Integral, enquanto ambiente.$n_protecao_us unidades pertencem ao grupo de Uso Sustentável.

Para quando meio-ambiente.$n_uc for maior ou igual a 5:

Em ambiente.$nm_mun (ambiente.$sigla_uf), há ambiente.$n_uc Unidades de Conservação (UC), totalizando ambiente.$area_total_uc hectares, ambiente.$bioma. Desse total, ambiente.$n_protecao_pi unidades estão enquadradas no grupo de Proteção Integral, enquanto ambiente.$n_protecao_us unidades pertencem ao grupo de Uso Sustentável. As UCs presentes no município são: ambiente.$nome_uc.

Para quando meio-ambiente.$aridez_cond1_area1991 for igual a 0:

Não há classificação de aridez disponível para ambiente.$nm_mun (ambiente.$sigla_uf) na fonte de dados consultada.

Para quando meio-ambiente.$aridez_cond3_area1991 for diferente de 0:

Entre 1991 e 2021, o clima de ambiente.$nm_mun (ambiente.$sigla_uf) apresentou mudanças na distribuição de suas classes de aridez. Em 1991, o território municipal, de  ambiente.$area_mun km², distribuía-se em ambiente.$aridez_cond1_area1991 km² (ambiente.$aridez_cond1_areaper1991 %) sob condição ambiente.$aridez_cond1_1991, ambiente.$aridez_cond2_area1991 km² (ambiente.$aridez_cond2_areaper1991 %) sob condição ambiente.$aridez_cond2_1991 e ambiente.$aridez_cond3_area1991 km² (ambiente.$aridez_cond3_areaper1991 %) sob condição ambiente.$aridez_cond3_1991. Em 2021, a condição predominante (ambiente.$aridez_cond1_1991) passou a ocupar ambiente.$aridez_cond1_area2021 km² (ambiente.$aridez_cond1_areaper2021 %), ambiente.$analise_cond1 ambiente.$var_aridez_cond1_1991_2021 pontos percentuais. O avanço da condição de aridez sobre áreas anteriormente classificadas como mais úmidas indica um processo de aridização do território, tendência observada em diversos municípios do Semiárido brasileiro e associada ao aumento do risco de degradação da terra.

Para quando meio-ambiente.$aridez_cond2_area1991 for diferente de 0 e meio-ambiente.$aridez_cond3_area1991 for igual a 0:

Entre 1991 e 2021, o clima de ambiente.$nm_mun (ambiente.$sigla_uf) apresentou mudanças na distribuição de suas classes de aridez. Em 1991, o território municipal, de  ambiente.$area_mun km², distribuía-se em ambiente.$aridez_cond1_area1991 km² (ambiente.$aridez_cond1_areaper1991 %) sob condição ambiente.$aridez_cond1_1991 e ambiente.$aridez_cond2_area1991 km² (ambiente.$aridez_cond2_areaper1991 %) sob condição ambiente.$aridez_cond2_1991. Em 2021, a condição predominante (ambiente.$aridez_cond1_1991) passou a ocupar ambiente.$aridez_cond1_area2021 km² (ambiente.$aridez_cond1_areaper2021 %), ambiente.$analise_cond1 ambiente.$var_aridez_cond1_1991_2021 pontos percentuais. O avanço da condição de aridez sobre áreas anteriormente classificadas como mais úmidas indica um processo de aridização do território, tendência observada em diversos municípios do Semiárido brasileiro e associada ao aumento do risco de degradação da terra.

Para quando meio-ambiente.$aridez_cond1_area1991 for diferente de 0 e meio-ambiente.$aridez_cond2_area1991 for igual a 0:

Entre 1991 e 2021, o clima de ambiente.$nm_mun (ambiente.$sigla_uf) apresentou mudanças na distribuição de suas classes de aridez. Em 1991, o território municipal, de  ambiente.$area_mun km², distribuía-se em ambiente.$aridez_cond1_area1991 km² (ambiente.$aridez_cond1_areaper1991 %) sob condição ambiente.$aridez_cond1_1991. Em 2021, a condição ambiente.$aridez_cond1_1991 passou a ocupar ambiente.$aridez_cond1_area2021 km² (ambiente.$aridez_cond1_areaper2021 %), ambiente.$analise_cond1 ambiente.$var_aridez_cond1_1991_2021 pontos percentuais. O avanço da condição de aridez sobre áreas anteriormente classificadas como mais úmidas indica um processo de aridização do território, tendência observada em diversos municípios do Semiárido brasileiro e associada ao aumento do risco de degradação da terra.

Para quando meio-ambiente.$aridez_cond1_area1991 for diferente de 0:

Em 2021, ambiente.$asd_per_2021 % do território municipal (ambiente.$asd_2021 km²) permanecia inserido em área suscetível à desertificação, extensão ambiente.$analise_asd_per1991_2021 à registrada em 1991. O avanço ou a permanência da totalidade do território nessa condição ao longo de três décadas evidencia que a suscetibilidade à desertificação é uma característica estrutural do município, que deve ser considerada no planejamento territorial, na gestão dos recursos hídricos e nas ações de prevenção da degradação da terra.

Figura X - Classificação das condições de aridez em ambiente.$nm_mun (ambiente.$sigla_uf) para o ano de 2021.

Síntese

Para quando meio-ambiente.$aridez_cond1_area1991 for igual a 0:

Os dados ambientais de ambiente.$nm_mun (ambiente.$sigla_uf) indicam elementos relevantes para o planejamento local. O município conta com ambiente.$n_uc Unidade(s) de Conservação registrada(s). Não há dados de aridez ou desertificação disponíveis para o município na fonte de dados consultada.

Para quando meio-ambiente.$aridez_cond1_area1991 for diferente de 0:

Os dados ambientais de ambiente.$nm_mun (ambiente.$sigla_uf) indicam elementos relevantes para o planejamento local. O município conta com ambiente.$n_uc Unidade(s) de Conservação registrada(s) e, em 2021, tinha ambiente.$asd_per_2021 % do seu território inserido em área suscetível à desertificação, extensão ambiente.$analise_asd_per1991_2021 à registrada em 1991. No mesmo período, as condições de aridez ambiente.$analise_aridez, com avanço da condição ambiente.$aridez_cond1_1991 de ambiente.$aridez_cond1_areaper1991 % para ambiente.$aridez_cond1_areaper2021 % da área municipal."@@


#!Conteúdos relacionados

Para saber mais sobre este tema, consulte os seguintes conteúdos do Data Nordeste:

hyperlink = "Boletim de Desertificação
ambiente.$boletim1_link"@@


#!Fontes

Os dados deste relatório foram extraídos dos seguintes painéis do Data Nordeste:

hyperlink = "Painel de Unidades de Conservação
ambiente.$painel2_link"@@

hyperlink = "Painel de Índice de Aridez
ambiente.$painel1_link"@@

As informações desses painéis têm origem nas seguintes instituições:

Ministério do Meio Ambiente e Mudança do Clima. Cadastro Nacional de Unidades de Conservação (CNUC)

Observatório da Caatinga e Desertificação (OCA) da Universidade Federal de Campina Grande (UFCG)
```
