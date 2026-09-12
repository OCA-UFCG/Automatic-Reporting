# Como testar o painel editorial

Guia prático para conferir, com as próprias mãos, se o painel está fazendo o
que promete. Escrito para quem não acompanhou a implementação.

A ideia central, e a única que você precisa guardar: **a prévia do painel é o
relatório de verdade**. Ela roda o mesmo `gerar_relatorio_handler` que atende o
portal — mesma montagem de contexto, mesmos gráficos, mesma capa, mesmo SSR em
React. A única diferença é que a prosa do macrotema vem do contrato que você
está editando e ainda não publicou. Se o que você vê na prévia não for igual ao
que sai no PDF, é bug.

> **O que cada botão faz está dentro da própria tela.** O botão **Guia**, no
> topo do painel, abre a documentação de todos os controles, com um exemplo
> passo a passo do zero ao PDF. Este documento aqui responde a outra pergunta —
> como provar que o painel está correto —, e os dois não se substituem. O guia
> tem um interruptor de *notas técnicas*: ligado, ele cita arquivo e variável
> de ambiente; desligado, sobra o texto escrito para quem só opera.

---

## Passo 0 — Por que o túnel é obrigatório aqui e não no portal

Esta é a confusão mais fácil de cair, então vale entender antes de começar.

O portal beta (`beta-datanordeste.lsd.ufcg.edu.br/reports`) gera relatórios sem
túnel nenhum, e isso não contradiz nada: **ele roda dentro da VM `10.5.8.5`**, e
lá o PostgreSQL é local (`127.0.0.1:5432`). Não há rede no meio.

A sua máquina é outro host. Para ela, o banco só existe através do túnel SSH,
que cria uma porta local (`5433`) encaminhada para a `5432` da VM. Sem o túnel,
`DB_HOST=localhost DB_PORT=5433` não leva a lugar nenhum.

```
portal na VM:       aplicação ──> 127.0.0.1:5432  (banco, mesma máquina)
sua máquina:        aplicação ──> localhost:5433 ──[túnel SSH]──> 10.5.8.5:5432
```

Cuidado com um falso positivo: se você tiver um PostgreSQL instalado localmente,
ele escuta na `5432` e dá a impressão de que "o banco está no ar". É outro banco
— ele vai recusar as credenciais do Data Nordeste.

### Subir o ambiente

```bash
cd ~/Automatic-Reporting
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Num terminal dedicado, deixe o túnel aberto (fora do escritório, VPN antes):

```bash
ssh -o IdentityAgent=none -o IdentitiesOnly=yes -i ~/.ssh/<sua-chave> \
    -N -L 5433:127.0.0.1:5432 ubuntu@10.5.8.5
```

O comando não devolve o prompt — é assim mesmo, ele fica segurando o túnel.

**Confirme antes de seguir.** Este é o teste de fumaça:

```bash
python3 -m utils.database
# esperado: Conexão bem-sucedida!
```

Só depois:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Passo 1 — O teste mais rápido: o banco está sendo usado?

Com a API no ar, num outro terminal:

```bash
curl -s localhost:8000/manifesto | python3 -m json.tool | head -30
```

Procure o campo `origem` de cada macrotema:

| `origem` | Significado |
|---|---|
| `banco` | Lendo as colunas da view. É o estado bom. |
| `csv` | Sem conexão — caiu para a planilha. **Abra o túnel.** |
| `cache` | Nem banco nem planilha; só os campos que o contrato já usa. |

Um jeito de ver os oito de uma vez:

```bash
curl -s localhost:8000/manifesto | python3 -c "
import json,sys
for slug, i in json.load(sys.stdin)['campos'].items():
    print(f\"{slug:24s} {i['origem']:6s} {len(i['campos'])} campos\")"
```

Com o túnel aberto, demografia deve mostrar por volta de **104** campos. Se
mostrar **19**, você está lendo o CSV: o túnel caiu.

---

## Passo 2 — Abrir o painel

```bash
npm install
npm run build -w admin
```

Abra <http://localhost:8000/painel/> e entre com a senha de `PAINEL_SENHA`
(no seu `.env`).

> Se der **503** dizendo que a tela não foi construída, faltou o
> `npm run build -w admin`. Se der **404**, você digitou `/painel` sem a barra
> final em uma versão antiga — hoje há um redirecionamento.

Você verá os oito macrotemas. Cada card diz se já tem contrato publicado e se o
relatório daquele tema sai hoje do **Doc** ou do **painel**.

---

## Passo 3 — O teste que importa: a prévia bate com o relatório?

Esta é a verificação central. Faça nesta ordem.

**3.1 — Gere o relatório pelo caminho normal**, o mesmo que o portal usa:

```bash
curl -s "localhost:8000/relatorio/Campina%20Grande%20(PB)?macrotema=demografia" \
  -o /tmp/relatorio-oficial.html
```

Abra `/tmp/relatorio-oficial.html` no navegador, ou o PDF que ele escreveu em
`output/relatorio_demografia__campina_grande_pb_.pdf`.

**3.2 — Gere a prévia pelo painel**: entre em Demografia, aba **Prévia**,
digite `Campina Grande (PB)`, clique em **Gerar relatório**.

> O botão fica travado enquanto não houver município digitado — ele diz o
> motivo ao lado. Se avisar que o município está fora da lista, confira a
> grafia e o `(UF)`; o nome precisa bater com o que `GET /cities` devolve.

**3.3 — Compare.** Aqui vale uma ressalva importante, e ela não é uma desculpa:
os dois **não** são idênticos hoje, e não deveriam ser.

A capa, os gráficos e a estrutura têm que bater exatamente. O texto vai diferir
em alguns pontos — e cada ponto tem nome e prova. O relatório oficial de um tema
que ainda está em `docs` lê o Google Doc, cujo interpretador tem defeitos
conhecidos: condicionais que não disparam, comparação entre dois campos que ele
não sabe fazer, título que perde o destaque. O painel mostra o que o autor
escreveu; o Doc, em alguns trechos, não.

Cada tema tem seu relatório de divergências listando exatamente quais trechos
devem diferir e por quê:

```bash
cat output/contratos/demografia.divergencias.md
```

Medido em Campina Grande (PB), demografia: **7 linhas de texto diferentes**,
todas rastreáveis às 5 divergências documentadas. Os 3 gráficos e a capa são
iguais. Um exemplo concreto do que você vai ver:

- O painel mostra o parágrafo sobre **pessoas em situação de rua**; o relatório
  oficial não. Esse texto vivia dentro do `placeholders.py`, em Python, e não no
  Doc — a importação o trouxe para o contrato, onde um editor consegue mexer.
- O painel mostra o parágrafo de **distribuição por faixa etária**; o oficial o
  engole junto com uma condicional que não dispara.

**A regra prática:** se a diferença está no relatório de divergências daquele
tema, está certo. Se aparecer uma diferença que não está lá, aí sim é bug —
me chame.

Se quiser ver o caso sem nenhuma ressalva, use **Saúde** ou **Meio Ambiente**:
são os dois temas com menos divergências, e neles a comparação sai muito mais
limpa.

Um jeito de comparar os dois lado a lado, só o texto visível:

```bash
for f in oficial previa; do
  python3 -c "
import re
h = open('/tmp/$f.html', encoding='utf-8').read()
h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
print('\n'.join(l.strip() for l in re.sub(r'<[^>]+>', '\n', h).splitlines() if l.strip()))
" > /tmp/$f.txt
done
diff /tmp/oficial.txt /tmp/previa.txt
```

**3.4 — Agora edite e veja a diferença.** Volte para **Editar**, mude uma frase
de um parágrafo, volte para **Prévia** e gere de novo. Sua alteração tem que
aparecer — **sem publicar nada**. É esse o ponto do painel: ver o efeito antes
de valer.

### Por que isso não estraga o relatório publicado

A prévia grava os arquivos com prefixo `previa__`:

```bash
ls output/ | grep campina_grande
# relatorio_demografia__campina_grande_pb_.pdf          <- o que o portal serve
# relatorio_previa__demografia__campina_grande_pb_.html <- a sua prévia
```

São arquivos diferentes de propósito. Sem esse prefixo, uma prévia sobrescreveria
o PDF que o portal entrega ao público, e prosa não aprovada iria ao ar pela porta
dos fundos. Há teste automatizado travando isso.

---

## Passo 4 — Ler os avisos da prévia

A prévia devolve três sinais. Vale saber o que cada um quer dizer.

**"Variáveis sem valor neste município"** — cada nome listado sai impresso como
texto cru (`$pop_total_2022`) no relatório. Ou o campo não existe para aquela
cidade, e o bloco precisa de uma regra que o esconda, ou o nome está errado.
Com o túnel aberto, demografia em Campina Grande deve dar **zero**.

**"Sem conexão com o banco…"** — caiu para a planilha CSV. A ação é abrir o
túnel.

**"O banco respondeu, mas não tem 'X' na view…"** — o túnel está bem; aquela
cidade não está na view do macrotema. Isso é assunto de quem mantém os dados,
não seu.

A diferença entre os dois últimos importa: eles pedem ações opostas.

---

## Passo 5 — Publicar, e o que publicar ainda não faz

Ao publicar, a versão sobe (v2, v3…) e a anterior vai para
`output/contratos/historico/<tema>/`. Nada é sobrescrito.

**Publicar não muda o relatório de produção.** Cada macrotema tem uma chave que
decide de onde a prosa vem. Enquanto ela disser `docs`, o relatório continua
lendo o Google Doc, e o painel é um rascunho paralelo. Para ligar um tema:

```bash
FONTE_EDITORIAL_DEMOGRAFIA=painel uvicorn main:app --reload
```

Isso é de propósito: dá para importar, editar e conferir os oito temas sem
atrapalhar quem ainda trabalha nos Docs. A faixa amarela no topo do painel
lembra disso o tempo todo.

Se você mudou de ideia, basta tirar a variável e reiniciar — o Doc volta a
mandar. O contrato publicado continua guardado.

---

## Passo 6 — Rodar os testes automatizados

```bash
python -m pytest -q      # a suíte inteira, sem precisar de banco
ruff check .             # o lint, que é o portão da CI
npm run smoke -w admin   # renderiza os componentes da tela fora do navegador
```

Atenção: **a CI não roda o `pytest`**. Ela só roda o `ruff`, constrói os bundles
e faz um health-check. Rodar a suíte localmente é o único portão real.

Os arquivos que cobrem este trabalho, se você quiser ler o que eles garantem:

| Arquivo | O que trava |
|---|---|
| `tests/test_previa_contexto.py` | a prévia monta o mesmo contexto do relatório |
| `tests/test_previa_e_relatorio.py` | a prévia passa pelo handler real e não toca os artefatos de produção |
| `tests/test_editorial_regras.py` | os operadores de regra (`maior_igual`, `entre`, campo-vs-campo…) |
| `tests/test_editorial_render.py` | o contrato vira o texto marcado que o pipeline já entendia |
| `tests/test_editorial_importador.py` | importar um Doc não perde linha |
| `tests/test_editorial_admin.py` | sessão, senha, conflito de versão |

---

## Passo 7 — Conferir a importação de um Doc

Ao importar um macrotema, o painel também produz um **relatório de
divergências**: trechos em que o Doc de hoje se comporta de um jeito que o autor
provavelmente não quis.

```bash
python scripts/importar_doc.py --macrotema educacao --do-cache
cat output/contratos/educacao.divergencias.md
```

Cada divergência vem com a linha do Doc e a prova do que foi observado. Elas não
são opinião: são comportamentos verificados do parser atual. A mais séria hoje é
em Educação — uma comparação entre dois campos que o parser não sabe fazer, e
por isso um parágrafo inteiro não aparece em município nenhum.

---

## Quando algo der errado

| Sintoma | Causa provável |
|---|---|
| Tela de variáveis com 19 campos | túnel caiu; confira com `python3 -m utils.database` |
| `$campo` cru no meio do texto | aquele campo não existe para o município; veja o Passo 4 |
| `/painel` dá 503 | falta `npm run build -w admin` |
| Botão "Gerar relatório" travado | município vazio ou fora da lista de `GET /cities` |
| Botão "Publicar" cinza | nada foi alterado desde a última publicação |
| Editei um `.py` e nada mudou | o uvicorn subiu sem `--reload`; reinicie |
| Editei algo em `report/src` e nada mudou | falta `npm run build -w report` |

Uma dica que economiza tempo: `ps -eo pid,lstart,cmd | grep uvicorn` mostra a
hora em que o servidor subiu. Se for anterior à sua edição e não tiver
`--reload`, o processo não viu a mudança.
