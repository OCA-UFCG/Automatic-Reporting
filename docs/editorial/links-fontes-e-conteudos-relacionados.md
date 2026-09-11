# Links em "Fontes" e "Conteúdos relacionados"

Guia rápido para quem escreve/edita os Documentos Google Docs dos macrotemas.
Cobre só a caixa "Fontes"/"Conteúdos relacionados" que aparece no fim de cada
tema no relatório (o quadro cinza com o QR code "Continue explorando o tema").
Para os outros marcadores do Doc (`descricao_tema =`, `$placeholders`,
condicionais `Para quando ...:`), veja o Doc de referência de Demografia nesta
mesma pasta.

## O formato que funciona

Cada link — painel de dados ou boletim/narrativa — vai **numa linha só**, sem
quebra entre o nome e a URL:

```
[Painel: Nome do painel](URL)
[Narrativa de dados: Nome do boletim ou da narrativa](URL)
```

Exemplo real (Demografia, seção Fontes):

```
[Painel: Perfil Demográfico](https://datanordeste.sudene.gov.br/data-panel/populacao)
```

Isso vira o quadradinho colorido ("badge") com o nome e o link clicável. Uma
frase de introdução antes dos links (ex.: "Os dados deste relatório foram
extraídos dos seguintes painéis...") pode ficar como texto normal, numa linha
separada — só os *links* precisam do formato acima.

## Erros que já aconteceram (e por quê)

Cada um destes já apareceu em algum macrotema e quebrou o visual — ou fez o
conteúdo sumir do relatório sem deixar rastro. Seguindo o padrão certo, tudo
se reduz a "link e nome na mesma linha, dentro de colchetes, sem virar
hyperlink de verdade no Docs".

### 1. Nome numa linha, link na linha de baixo

```
Boletim Educação Básica
https://datanordeste.sudene.gov.br/boletim/5sPp0jQRba52vrjKhBfKgZ
```

Sem colchetes, isso não é reconhecido como link do painel/boletim. Vira dois
parágrafos soltos: o nome como texto comum, e a URL como link cru (o texto
visível do link fica sendo a URL inteira, feio e sem contexto).

**Correção:** juntar numa linha só —
`[Narrativa de dados: Boletim Educação Básica](URL)`.

### 2. `Nome = URL` sem o prefixo do macrotema

```
Habitação = https://datanordeste.sudene.gov.br/boletim/2uLi66i4yISOg9bjzuH6WG
```

Existe um formato ligado ao banco de dados (`saneamento."$campo" = URL`), mas
ele exige o prefixo do macrotema antes do nome (`saneamento.`, `demografia.`,
`economia.`, `hidraulica.`/`seg_hidrica.`, etc.). Sem esse prefixo, o sistema
não reconhece como link — pior, `Nome = URL` colide com um marcador interno
usado em outras partes do Doc, e a linha inteira **desaparece silenciosamente**
do relatório (nem aparece como texto quebrado).

**Correção:** ou usa o prefixo certo do tema, ou — mais simples — usa o
formato manual `[Narrativa de dados: Habitação](URL)`, que não depende de
banco nenhum.

### 3. Namespace errado (copiado de outro tema)

```
demografia."$nm_datastory1" = "Painel - Cisternas e outras tecnologias sociais
https://datanordeste.sudene.gov.br/data-panel/cisternas"
```

Isso apareceu no Doc de Segurança Hídrica com o prefixo `demografia.`, um
resíduo de copiar o template de outro macrotema sem trocar o prefixo. Cada Doc
só reconhece o prefixo do seu próprio tema.

**Correção:** confirmar que o prefixo bate com o tema do Doc, ou usar o
formato manual em colchetes, que não depende de prefixo nenhum.

### 4. A URL virou link clicável de verdade no Google Docs

O Google Docs "ajuda" convertendo automaticamente qualquer URL colada num link
azul sublinhado de verdade. Quando isso acontece dentro do padrão
`Nome = URL`, o texto exportado vira `Nome = [URL](URL)` (com colchetes
duplicados) em vez do link cru — e a linha para de ser reconhecida.

**Correção:** depois de colar a URL, clique nela e remova a formatação de
link (ou selecione o texto e use "Limpar formatação"). Ela deve ficar como
texto puro, sem sublinhado e sem cor de link. Isso vale tanto para o formato
`Nome = URL` quanto para o texto dentro dos colchetes/parênteses do formato
`[Rótulo: Nome](URL)` — o link real é só o `(URL)`; o `[Rótulo: Nome]` deve
ficar em texto puro, sem virar ele mesmo um hyperlink.

### 5. Marcador `hyperlink =` sem fechamento

```
hyperlink = "Painel - Nível de Instrução
https://datanordeste.sudene.gov.br/data-panel/niveldeinstrucao
```

`hyperlink =` é um marcador interno reconhecido pelo sistema (assim como
`referencia =`), não texto solto — e ele **precisa terminar com `@@`** em
algum lugar do texto. Sem o `@@`, o sistema entende que o bloco continua
indefinidamente e o conteúdo (nome do painel + link) some do relatório sem
deixar rastro. O mesmo apareceu no Doc de Meio Ambiente, com um agravante:
como os três links (um boletim e dois painéis) estavam no mesmo bloco sem
linha em branco entre eles, os três desapareceram juntos.

**Correção:** não usar `hyperlink =` pra isso — usar o formato manual
`[Painel: Nível de Instrução](URL)`.

### 6. Aspas, itálico e traço de lista sobrando

Coisas que não têm função nenhuma no sistema de marcação, mas aparecem por
causa de colar texto do Word/outro Doc, e ficam visíveis no relatório como
caractere solto:

- Aspas curvas (`" "`) envolvendo o parágrafo inteiro.
- Um `"n`, `”` ou aspas soltas coladas no fim de um link.
- Itálico ou negrito por cima do nome/link.
- Um `-` no início da linha antes de uma frase comum (isso ativa formatação
  de lista `<li>`, não é só estético).

**Correção:** ao colar, selecionar o trecho e limpar formatação
(negrito/itálico) e apagar aspas/caracteres soltos que não fazem parte do
texto.

## Checklist antes de publicar

1. Cada painel/boletim está em **uma linha só**, no formato
   `[Painel: Nome](URL)` ou `[Narrativa de dados: Nome](URL)`?
2. A URL dentro do `(...)` está como **texto puro** — sem virar link
   clicável, sem itálico/negrito por cima?
3. Não sobrou nenhum `Nome = URL` sem o prefixo certo do tema?
4. Não sobrou aspas curvas, `"n`, ou `-` de lista em volta do texto?
5. Se for usar `hyperlink =` ou `referencia =`, tem um `@@` fechando o bloco
   em algum lugar depois?

Na dúvida, comparar com o Doc de Demografia (`docs/editorial/demografia.md`
nesta pasta) — ele é a referência que já está correta e funcionando.
