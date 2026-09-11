# Como colocar links em "Fontes" e "Conteúdos relacionados"

Guia rápido pra quem escreve os Documentos do Data Nordeste. Sem termos
técnicos — só o passo a passo de como escrever um link pra ele aparecer
certinho no relatório, como aquele quadradinho colorido com o nome do painel
ou do boletim.

## O jeito certo

Todo link — de painel ou de boletim/narrativa — precisa ficar **numa linha só**,
assim:

```
[Painel: Nome do painel](link aqui)
```

ou, pra boletins e narrativas de dados:

```
[Narrativa de dados: Nome do boletim](link aqui)
```

**Exemplo pronto, de Demografia (esse já está certo):**

```
[Painel: Perfil Demográfico](https://datanordeste.sudene.gov.br/data-panel/populacao)
```

Isso vira automaticamente o quadradinho colorido com o nome e o link. Uma
frase antes, tipo "Os dados deste relatório foram extraídos dos seguintes
painéis:", pode continuar como texto normal — só o link em si precisa seguir
esse formato, com colchetes e parênteses.

### Depois de colar o link, faz sempre isso:

Quando você cola uma URL no Google Docs, ele geralmente transforma ela num
link azul e sublinhado automaticamente. **Isso quebra o formato.** Depois de
colar, clique em cima do link e tire essa formatação (ou selecione o texto e
use "Limpar formatação"), deixando a URL como texto normal, sem cor e sem
sublinhado.

## Os erros que a gente já encontrou

Foi assim que percebemos o problema — comparando o que está em cada Documento
com o de Demografia, que funciona. Nenhum é "culpa" de ninguém, é só a mesma
pegadinha do Google Docs se repetindo — por isso esse guia.

### Educação

Tinha o nome do boletim numa linha e o link na linha debaixo, separados —
por exemplo "Boletim Educação Básica" numa linha e o link embaixo. Sem juntar
os dois numa linha só com colchetes, o link aparece cru (a URL inteira
como texto) e sem nome nenhum do lado.

**Como ficou depois de corrigir:**
```
[Narrativa de dados: Boletim Educação Básica](link)
```

### Economia e Renda

Aqui o texto já estava no formato certo (nome, sinal de igual, link), mas
os links tinham sido colados como **link de verdade** do Google Docs (aquele
azul sublinhado), em vez de texto puro. Isso é o suficiente pra quebrar —
mesmo com tudo escrito certo, aparecia o nome cru com aspas, sem virar o
quadradinho.

**Lição:** sempre tirar a formatação de link depois de colar a URL.

### Segurança Hídrica

Um dos links tinha sido copiado do Documento de outro tema (Demografia) e
não foi ajustado — o texto ainda falava "demografia" no meio, mesmo sendo
o Documento de Segurança Hídrica. Cada Documento só reconhece o nome do seu
próprio tema.

**Lição:** ao copiar um trecho de outro Documento como modelo, sempre revisar
se sobrou algum nome de tema errado.

### Desenvolvimento Social

Mesmo problema de Educação — nome e link em linhas separadas, sem colchetes.
Além disso, tinha aspas grandes ( " " ) envolvendo blocos inteiros de texto,
sobra de ter colado de outro lugar, sem nenhuma função — só aparecem soltas
no relatório.

### Saneamento

Também nome e link no formato "Nome = link", mas faltando informar de qual
tema é ("saneamento" antes do nome). Sem isso, o sistema nem reconhece o
link — e o texto some do relatório inteiro, sem deixar rastro nenhum
(nem aparece errado, simplesmente não aparece).

**Lição:** se não tiver certeza de como escrever esse formato com o nome do
tema, é mais seguro usar sempre o formato com colchetes:
`[Painel: Nome](link)` — ele funciona em qualquer Documento, sem precisar
saber o nome técnico do tema.

### Meio Ambiente

Os três links (um boletim e dois painéis) começavam com a palavra
"hyperlink =" antes do nome. Essa palavra é um comando especial que o sistema
reconhece, e ele exige um fechamento em algum lugar depois — que não estava
lá. Resultado: os três links sumiram inteiros do relatório, sem deixar
nem texto errado no lugar.

**Lição:** não usar "hyperlink =" pra escrever esses links — usar sempre o
formato com colchetes: `[Painel: Nome](link)` ou
`[Narrativa de dados: Nome](link)`.

## Checklist rápido antes de fechar o Documento

- [ ] Cada link está numa linha só, com colchetes: `[Painel: Nome](link)` ou
      `[Narrativa de dados: Nome](link)`?
- [ ] A URL não virou link azul/sublinhado de verdade? (clique nela e tire a
      formatação se tiver)
- [ ] Não tem negrito, itálico ou aspas em volta do nome/link?
- [ ] Não sobrou nome de outro tema, copiado sem querer?

Se bater dúvida, é só comparar com o Documento de Demografia — ele é o
exemplo que já está certo.
