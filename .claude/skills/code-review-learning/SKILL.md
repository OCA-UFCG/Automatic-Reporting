---
name: code-review-learning
description: Revisa um PR, branch ou diff com foco em aprendizado — aponta problemas reais (nunca preferência de estilo), explica arquivo, função, causa e conceito por trás de cada um, avalia a cobertura de testes e fecha com resumo, problemas por prioridade, pontos positivos e conceitos aprendidos. Use quando pedirem revisão de PR, "revisa essa branch", "revisa meu diff", ou uma revisão que sirva para entender o código, não só aprovar.
---

# Code review com foco em aprendizado

O objetivo desta revisão é duplo: encontrar o que está errado **e** deixar quem
escreveu o código capaz de explicar e defender a correção. Uma revisão que só
lista defeitos falhou pela metade.

## 1. Levantar o alvo

Sem alvo informado, revise a branch atual contra a principal:

```bash
git fetch origin --quiet
git diff origin/main...HEAD --stat
git diff origin/main...HEAD
```

Se o usuário informar um número de PR, uma branch ou um caminho, revise aquilo.
Com `gh` disponível, `gh pr diff <n>` traz o diff e `gh pr view <n>` traz a
descrição e a discussão.

Leia os arquivos tocados por inteiro sempre que o hunk não bastar. A maioria dos
bugs reais mora no que o diff **não** mostra: o chamador que passa `None`, o
guard que existia acima, o teste que já cobria aquele caminho.

## 2. O que conta como problema

Reporte apenas o que tem consequência observável:

- **Correção** — condição invertida, off-by-one, `None`/vazio não tratado, chave
  de dicionário que não bate, unidade ou ano trocado, retorno ignorado.
- **Contrato quebrado** — a função passou a fazer algo que seu nome, assinatura
  ou chamadores não preveem; efeito colateral novo em função pura.
- **Guard afrouxado** — timeout, fallback, tratamento de erro ou validação que o
  diff removeu ou contornou. Se o projeto tem um `CLAUDE.md` ou doc de
  arquitetura, leia antes: os guards costumam estar escritos lá.
- **Concorrência, recurso e limite** — arquivo/conexão não fechados, consulta sem
  limite, laço que cresce com a entrada.
- **Segurança e dado sensível** — entrada não validada que chega a SQL, shell ou
  caminho de arquivo; credencial ou URL interna em código versionado.

Não reporte: preferência de nomenclatura, formatação, ordem de imports, gosto
sobre comprensão de lista versus laço, ou reescrita que não muda comportamento.
Se o projeto tem linter (`ruff`, `eslint`), o linter é a autoridade de estilo —
rode e cite o resultado dele em vez de opinar.

Antes de escrever um achado, valide-o: descreva uma entrada concreta e o que
acontece de errado com ela. Se não conseguir construir esse cenário, o achado é
suspeita, não problema — marque como tal ou descarte.

## 3. Como explicar cada achado

Cada problema recebe quatro camadas, nesta ordem:

1. **Onde** — `arquivo:linha`, e a função ou bloco.
2. **O quê** — uma frase com o defeito.
3. **Por quê** — o cenário concreto: entrada → comportamento errado.
4. **O conceito** — a ideia geral que o caso ilustra, em duas ou três frases:
   mutabilidade de argumento padrão, aliasing, encoding, precisão de ponto
   flutuante, invalidação de cache, ordem de avaliação, isolamento de
   transação. É essa camada que transforma um patch em conhecimento.

Formato de cada achado:

```
### [ALTA] utils/queries/saude.py:42 — buscar_cobertura_aps
Divide por `total_pop` sem checar zero.
Município sem população na view retorna `total_pop = 0` → ZeroDivisionError
sobe pela `executar_query` e derruba o relatório inteiro.
Conceito: guardas de pré-condição em fronteira de dados externos — o valor vem
de fora do processo, então a invariante ("população > 0") precisa ser verificada
aqui, não assumida.
```

### Perguntas antes da explicação

Quando o achado for uma **oportunidade real de aprendizado** — o autor
provavelmente não conhece o conceito, e o erro vai se repetir — abra com uma
pergunta antes de entregar a resposta:

> Em `buscar_cobertura_aps:42`, o que acontece quando a view devolve um
> município sem população? Repare no denominador.

Regras para isso não virar atrito:

- No máximo **duas ou três** perguntas na revisão inteira, nos achados mais
  formativos. O resto vem explicado direto.
- Uma pergunta por achado, nunca uma bateria.
- **Nunca sonegue a resposta.** A explicação completa vem logo abaixo da
  pergunta, no mesmo texto. A pergunta é um convite a pensar primeiro, não um
  teste a ser passado.
- Nada de perguntas retóricas ("será que isso é mesmo uma boa ideia?"). A
  pergunta aponta para um ponto específico do código.
- Se o usuário disser que está com pressa, que a produção está quebrada, ou
  pedir só a lista — entregue direto, sem perguntas.

## 4. Analisar os testes

Os testes são parte do diff, não um anexo. Verifique:

- **Existe teste?** Todo comportamento novo e todo bugfix precisam de um. Um
  bugfix sem teste de regressão significa que o bug pode voltar sem ninguém ver.
- **O teste falha sem o fix?** Um teste que passa nos dois lados do patch não
  testa o patch. Quando for barato, confirme: reverta o fix, rode o teste.
- **O que ele afirma?** Asserção sobre o valor esperado, não só "não lançou
  exceção" ou "retornou algo". `assert resultado` esconde quase todo bug.
- **Casos de borda** — vazio, zero, `None`, valor negativo, lista com um
  elemento, acentuação/encoding, o caminho de fallback.
- **Isolamento** — o teste depende de rede, banco, relógio ou ordem de execução?
  Isso é fragilidade que vai custar caro depois.
- **Testes que o diff deveria ter quebrado** e não quebrou: é sinal de cobertura
  falsa naquela área.

Rode a suíte e o linter do projeto e relate a saída real, inclusive quando
falhar. Não descreva um resultado que você não viu.

## 5. Formato do relatório final

Termine sempre com estas quatro seções, nesta ordem:

```markdown
## Resumo
Dois a quatro períodos: o que o PR faz, se está pronto para merge, e o bloqueio
principal se houver.

## Problemas por prioridade
### Alta — quebra em uso normal, perde dado ou abre risco de segurança
### Média — quebra em caso de borda, degrada desempenho ou dificulta manutenção
### Baixa — melhoria real de clareza ou robustez, sem consequência imediata
(cada item nas quatro camadas da seção 3; seção vazia se diz "nada nesta faixa")

## Pontos positivos
O que foi bem resolvido, com o mesmo nível de especificidade dos problemas:
arquivo, linha e por que a decisão foi boa. Isso não é cortesia — é o que
ensina qual padrão repetir.

## Conceitos aprendidos
Os conceitos que apareceram nos achados, um por linha, com uma frase cada e a
referência ao achado que o motivou. Se um conceito reaparece em vários pontos
do diff, diga isso: é o padrão mais útil da revisão.
```

Se nada relevante for encontrado, diga o que foi verificado e por que passou. Uma
revisão limpa é um resultado, não um fracasso — mas ela precisa mostrar o
trabalho para valer alguma coisa.
