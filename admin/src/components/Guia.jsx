import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Icone } from '../icones.jsx'

// O guia é a documentação da tela dentro da própria tela. Existe porque a
// ferramenta tem vocabulário próprio — bloco, contrato, regra, divergência — e
// nenhum desses termos aparece no Google Docs, que é de onde vem quem opera.
//
// Duas linguagens convivem aqui. O texto corrido é escrito para o operador: só
// fala de coisas que ele vê na tela e de decisões que ele toma. As notas
// marcadas como técnicas falam de arquivo, variável de ambiente e endpoint —
// úteis enquanto só o time de desenvolvimento tem acesso, e removíveis no
// primeiro dia em que alguém de fora entrar, sem que o resto perca sentido.
// Por isso são um bloco à parte e nunca uma oração no meio de um parágrafo.

function Dev({ children }) {
  return (
    <p className="guia-dev">
      <span className="guia-dev-selo">técnico</span>
      {children}
    </p>
  );
}

function Botao({ nome, onde, children }) {
  return (
    <div className="guia-botao">
      <div className="guia-botao-nome">
        <span className="guia-chip-botao">{nome}</span>
        {onde && <span className="guia-botao-onde">{onde}</span>}
      </div>
      <div className="guia-botao-texto">{children}</div>
    </div>
  );
}

// O total de municípios vem da própria lista que o painel carregou, e não
// escrito à mão: o número já ficou errado uma vez no texto do guia.
export function montarSecoes(totalDeCidades) {
  const quantos = totalDeCidades
    ? `${totalDeCidades.toLocaleString('pt-BR')} municípios`
    : 'todos os municípios da lista';
  return [
    {
      id: 'visao',
      titulo: 'Por onde começar',
      corpo: (
        <>
          <p>
            Este painel escreve o <strong>texto</strong> dos relatórios municipais — a
            prosa que hoje mora nos Google Docs. Os números, os gráficos e o mapa não
            são editados aqui: eles vêm do banco do Data Nordeste e entram sozinhos.
          </p>
          <p>
            Cada macrotema tem um texto próprio, e esse texto vale para{' '}
            <strong>{quantos} de uma vez</strong>. É essa a diferença que explica
            quase tudo nesta tela: você não escreve “Campina Grande tem 419 mil
            habitantes”, você escreve “<em>município</em> tem{' '}
            <em>população</em> habitantes” e o relatório preenche por município. Os pedaços em itálico aí
            são as <strong>variáveis</strong>.
          </p>
          <p>
            O texto é montado em <strong>blocos</strong>: um parágrafo é um bloco, uma
            lista é um bloco, um gráfico é um bloco. Cada bloco pode ter uma{' '}
            <strong>regra</strong> — “só apareça onde o dado existir” — e é isso que
            evita a frase sem sentido no município que não tem aquele indicador.
          </p>
          <p>
            Nada do que você faz aqui chega ao site enquanto você não apertar{' '}
            <span className="guia-chip-botao">Publicar</span>. E, mesmo publicado, o
            relatório de um tema só passa a usar este texto depois que o tema for
            virado para o painel — a etiqueta no cartão do tema diz em qual dos dois
            estados ele está.
          </p>
          <Dev>
            O texto de cada tema é um contrato JSON versionado em{' '}
            <code>output/editorial/&lt;slug&gt;.json</code>. Qual fonte vale em produção é
            decidido por <code>FONTE_EDITORIAL</code> (global) ou{' '}
            <code>FONTE_EDITORIAL_&lt;SLUG&gt;</code> (por tema), lidos em{' '}
            <code>utils/external/editorial.py</code>. Sem essa variável ligada, publicar
            aqui não altera o PDF que o portal serve.
          </Dev>
        </>
      ),
    },
    {
      id: 'passo-a-passo',
      titulo: 'Exemplo: do zero ao PDF',
      corpo: (
        <>
          <p>
            Um caminho completo, do jeito que ele acontece de verdade. O exemplo troca
            uma frase de <strong>Demografia</strong> e confere o resultado em Campina
            Grande. Leva uns dez minutos na primeira vez.
          </p>

          <ol className="guia-passos">
            <li>
              <h4>Confira o banco antes de tudo</h4>
              <p>
                No topo da tela, clique no selo de conexão. Se ele ficar verde, siga. Se
                ficar vermelho, o painel ainda funciona, mas com a lista de variáveis
                reduzida e a prévia incompleta — o próprio selo mostra o que fazer.
              </p>
            </li>
            <li>
              <h4>Abra o macrotema</h4>
              <p>
                Clique no cartão <strong>Demografia</strong>. Se ele disser “não
                importado”, o tema ainda está em branco aqui dentro: use{' '}
                <span className="guia-chip-botao">Baixar do Google Docs</span> para
                trazer o texto que existe hoje e começar de onde o Doc parou.
              </p>
            </li>
            <li>
              <h4>Ache o parágrafo</h4>
              <p>
                A coluna da esquerda é o índice do tema. Clique num parágrafo: ele abre
                no centro, pronto para editar.
              </p>
            </li>
            <li>
              <h4>Escreva, e insira a variável pela lista</h4>
              <p>
                Digite o texto normalmente. Onde entra um número que muda por município,{' '}
                <strong>clique primeiro no ponto do texto</strong> onde ele deve cair e
                depois clique na variável na coluna da direita. Ela entra como uma
                etiqueta cinza, que não dá para digitar errado.
              </p>
              <p className="guia-alerta">
                Se você clicar na variável sem ter clicado antes no texto, o painel avisa
                que não sabe onde colocá-la. É o erro mais comum aqui.
              </p>
            </li>
            <li>
              <h4>Proteja o parágrafo com uma regra</h4>
              <p>
                Ainda no bloco aberto, em <em>Quando este bloco aparece</em>, clique em{' '}
                <span className="guia-chip-botao">Só mostrar em certos municípios…</span>{' '}
                e monte a condição — por exemplo, a variável do parágrafo{' '}
                <em>maior que</em> 0. Sem isso, o município sem o dado recebe uma frase
                truncada.
              </p>
            </li>
            <li>
              <h4>Veja o relatório de verdade</h4>
              <p>
                Vá na aba <strong>Prévia</strong>, escreva{' '}
                <code>Campina Grande (PB)</code> e clique em{' '}
                <span className="guia-chip-botao">Gerar relatório</span>. O que aparece é
                o relatório inteiro, capa e gráficos inclusive, com o seu texto ainda não
                publicado no lugar do atual. Demora alguns segundos.
              </p>
            </li>
            <li>
              <h4>Confira as variáveis sem valor</h4>
              <p>
                Se a prévia abrir um aviso de variáveis sem valor, leia a lista: cada uma
                delas sai impressa como texto cru no PDF. Ou falta uma regra no bloco, ou
                a variável não existe para aquele município.
              </p>
            </li>
            <li>
              <h4>Repita em um município difícil</h4>
              <p>
                Gere de novo para uma cidade pequena. É onde os dados faltam, e é onde as
                regras que você acabou de escrever são testadas de verdade.
              </p>
            </li>
            <li>
              <h4>Publique</h4>
              <p>
                Clique em <span className="guia-chip-botao">Publicar</span>, na barra
              colorida do tema — ela fica visível de qualquer aba. Vira
                uma nova versão, com seu nome e a data. A versão anterior continua
                guardada.
              </p>
            </li>
          </ol>

          <Dev>
            A prévia chama <code>gerar_relatorio_handler</code> — o mesmo caminho do
            portal — com o contrato ainda não publicado injetado por{' '}
            <code>contrato_em_edicao</code>. Ela escreve em{' '}
            <code>output/previa__*</code>, prefixo que existe justamente para não
            sobrescrever o PDF de produção; o PDF em si não é gerado (
            <code>gerar_pdf=False</code>), só o HTML.
          </Dev>
        </>
      ),
    },
    {
      id: 'macrotemas',
      titulo: 'A tela de macrotemas',
      corpo: (
        <>
          <p>
            A primeira tela depois de entrar. Um cartão por macrotema, com duas
            etiquetas que valem a leitura antes de clicar.
          </p>
          <Botao nome="versão N / não importado" onde="etiqueta cinza ou verde">
            Diz se o tema já tem texto aqui dentro. “Não importado” significa que o
            painel nunca recebeu o conteúdo daquele Doc — é normal, e o primeiro passo é
            importar.
          </Botao>
          <Botao nome="no ar pelo painel / ainda pelo Doc" onde="etiqueta azul ou cinza">
            Diz de onde o site tira o texto <strong>hoje</strong>. Em “ainda pelo Doc”,
            tudo o que você publicar aqui fica guardado mas não muda o relatório que sai
            em produção. Virar essa chave é decisão de quem cuida do servidor.
          </Botao>
          <Dev>
            A chave é a variável <code>FONTE_EDITORIAL_&lt;SLUG&gt;=painel</code> no{' '}
            <code>.env</code>, com reinício da API. A tela também mostra o aviso em faixa
            amarela dentro do tema quando ele ainda está em <code>docs</code>.
          </Dev>
        </>
      ),
    },
    {
      id: 'barra',
      titulo: 'A barra do tema',
      corpo: (
        <>
          <p>A faixa colorida no topo, depois que você abre um macrotema.</p>
          <Botao nome="← macrotemas">
            Volta para a lista. Se houver alteração não publicada, pergunta antes.
          </Botao>
          <Botao nome="Editar / Prévia / Divergências" onde="abas">
            Trocam o que ocupa a tela. Trocar de aba não perde nada do que você escreveu.
          </Botao>
          <Botao nome="Importar do Doc (cópia local)">
            Converte o Google Doc do tema em blocos, usando a cópia que o servidor já
            tinha baixado antes. É rápido e não depende da internet, mas pode estar
            desatualizado se alguém mexeu no Doc hoje.
            <strong> Substitui tudo o que está aberto aqui</strong> — o painel confirma
            antes.
          </Botao>
          <Botao nome="Baixar do Google Docs">
            O mesmo, mas buscando o Doc agora, direto do Google. É o que você quer quando
            o Doc acabou de mudar. Também substitui tudo.
          </Botao>
          <Botao nome="Publicar">
            Grava o que está na tela como a nova versão oficial do tema, com seu nome e a
            data. Fica apagado enquanto não há nada novo para publicar.
          </Botao>
          <p className="guia-alerta">
            Importar é sempre destrutivo: joga fora o rascunho aberto e recomeça do Doc.
            Use no começo do trabalho, não no meio.
          </p>
          <Dev>
            A cópia local é o cache ETag em <code>output/docs_cache/</code> (
            <code>utils/external/docs.py</code>). Publicar usa optimistic locking: se
            outra pessoa publicou depois de você abrir, a API devolve 409 e o painel
            oferece recarregar a versão publicada em vez de sobrescrevê-la.
          </Dev>
        </>
      ),
    },
    {
      id: 'arvore',
      titulo: 'A coluna da esquerda: os blocos',
      corpo: (
        <>
          <p>
            O índice do tema. <strong>Corpo do tema</strong> é a seção do relatório —
            você cria, reordena e apaga à vontade. Abaixo dele vem a{' '}
            <strong>Moldura</strong>: lugares fixos do layout, como o resumo que vai para
            a capa e a caixa de fontes que fecha a seção. Esses existem sempre e não
            podem ser criados nem removidos — só preenchidos.
          </p>
          <Botao nome="+ bloco" onde="fim de cada grupo">
            Cria um parágrafo novo no fim daquele grupo. Depois de criado, dá para trocar
            o tipo dele no seletor do centro.
          </Botao>
          <Botao nome="+" onde="na linha de uma seção ou caixa">
            Cria um bloco <em>dentro</em> daquele, e não depois dele. Só aparece em
            blocos que aceitam filhos.
          </Botao>
          <Botao nome="↑ ↓">
            Sobem e descem o bloco entre os irmãos dele. Não atravessam para outro grupo.
          </Botao>
          <Botao nome="×">Apaga o bloco e tudo que está dentro dele. Pergunta antes.</Botao>
          <Botao nome="regra" onde="etiqueta na linha">
            Marca os blocos que têm condição — ou seja, que não aparecem em todo
            município. Bater o olho nessa coluna é a forma mais rápida de ver o que está
            desprotegido.
          </Botao>
        </>
      ),
    },
    {
      id: 'editor',
      titulo: 'O centro: o bloco aberto',
      corpo: (
        <>
          <Botao nome="Tipo" onde="seletor no topo">
            Troca o que o bloco é. <strong>Parágrafo</strong> é prosa;{' '}
            <strong>Seção</strong> e <strong>Caixa destacada</strong> agrupam outros
            blocos; <strong>Lista</strong> vira marcadores; <strong>Gráfico</strong>{' '}
            insere uma figura pronta; <strong>Legenda</strong> é a linha embaixo da
            figura; <strong>Nota</strong> é o texto miúdo de observação. Trocar o tipo
            mantém a regra, mas o conteúdo recomeça vazio.
          </Botao>
          <Botao nome="Texto" onde="a caixa de escrever">
            Uma linha de prosa. Enter não quebra linha de propósito — cada parágrafo é um
            bloco, e quebrar aqui sempre foi engano. Colar de Word ou Docs traz só o
            texto, sem formatação.
          </Botao>
          <Botao nome="etiqueta cinza" onde="dentro do texto">
            É uma variável. Some por inteiro com um Backspace, nunca pela metade — foi
            feita assim para que não exista variável com o nome errado.
          </Botao>
          <Botao nome="+ item / ×" onde="blocos do tipo Lista">
            Adicionam e removem marcadores. Cada item aceita variáveis, do mesmo jeito
            que um parágrafo.
          </Botao>
          <Botao nome="Gráfico" onde="blocos do tipo Gráfico">
            Escolhe qual figura entra. A lista é a dos gráficos que já existem para o
            tema — um gráfico novo é trabalho de programação, não de edição.
          </Botao>
        </>
      ),
    },
    {
      id: 'regras',
      titulo: 'Quando um bloco aparece',
      corpo: (
        <>
          <p>
            A parte que mais muda a qualidade do relatório. Sem regra, o bloco vai para
            {' '}{quantos}. Com regra, ele só vai para aqueles em que a frase faz
            sentido.
          </p>
          <Botao nome="Só mostrar em certos municípios…">
            Cria a primeira condição. Antes disso, o bloco aparece em todos.
          </Botao>
          <Botao nome="+ condição">
            Acrescenta outra exigência. Elas se somam: o bloco aparece quando{' '}
            <strong>todas</strong> forem verdadeiras.
          </Botao>
          <Botao nome="usar outro campo / usar número">
            Alterna entre comparar a variável com um número fixo (“maior que 0”) ou com
            outra variável (“maior que a média do estado”).
          </Botao>
          <Botao nome="mostrar sempre">
            Apaga a regra inteira de uma vez. Remover a última condição pelo × faz o
            mesmo.
          </Botao>
          <Botao nome="Quando o município não tiver o dado…">
            Decide o que acontece no caso mais chato: o dado nem existe para aquela
            cidade. <strong>Esconder</strong> tira o bloco;{' '}
            <strong>texto alternativo</strong> troca por uma frase que você escreve — é o
            lugar certo para “Não foram encontrados registros para este município”.
          </Botao>
          <Dev>
            As condições viram um objeto <code>regra</code> no contrato, avaliado em{' '}
            <code>utils/editorial/regras.py</code> contra o mesmo{' '}
            <code>contexto</code> que resolve os placeholders. A lista de operadores
            disponíveis vem do <code>/manifesto</code>, não está no front.
          </Dev>
        </>
      ),
    },
    {
      id: 'paleta',
      titulo: 'A coluna da direita: variáveis e gráficos',
      corpo: (
        <>
          <p>
            Tudo o que o relatório sabe preencher sozinho neste tema. Os nomes aparecem
            exatamente como estão no banco — <code>nm_mun</code>, e não “Nome do
            município”. É de propósito: quando você precisar perguntar de onde vem um
            número, é esse nome que quem cuida do banco reconhece.
          </p>
          <Botao nome="Variáveis / Gráficos" onde="abas da coluna">
            Trocam entre os valores que entram no texto e as figuras que entram como
            bloco.
          </Botao>
          <Botao nome="Buscar variável…">
            Filtra pelo nome. Com centenas de campos, é mais rápido que rolar.
          </Botao>
          <Botao nome="clique numa variável">
            Insere no ponto onde o cursor estava.{' '}
            <strong>Clique antes no texto</strong>, senão o painel não sabe onde colocar.
          </Botao>
          <Botao nome="clique num gráfico">
            Cria um bloco de gráfico logo depois do bloco selecionado.
          </Botao>
          <Botao nome="●" onde="bolinha ao lado do nome">
            Marca as variáveis que você já usou neste tema.
          </Botao>
          <p className="guia-alerta">
            Se a coluna mostrar um aviso e a lista parecer curta, é a conexão com o banco
            — veja abaixo. A lista reduzida vem da planilha CSV, e tem bem menos campos
            que a do banco.
          </p>
        </>
      ),
    },
    {
      id: 'previa',
      titulo: 'A prévia',
      corpo: (
        <>
          <p>
            Não é uma simulação: é o relatório sendo gerado pelo mesmo caminho que atende
            o site, com o seu texto ainda não publicado no lugar do atual. Capa,
            gráficos, mapa e diagramação são os mesmos que sairiam no PDF.
          </p>
          <Botao nome="Município">
            Escreva o nome com a sigla do estado, como{' '}
            <code>Campina Grande (PB)</code>. A lista completa autocompleta enquanto você
            digita; o painel avisa se o nome não estiver nela.
          </Botao>
          <Botao nome="Gerar relatório">
            Roda a geração de verdade — leva alguns segundos. Fica apagado enquanto não
            houver município escolhido, e a razão aparece escrita ao lado.
          </Botao>
          <Botao nome="N variável(is) sem valor neste município">
            A lista de variáveis que ficaram sem preenchimento. Cada uma sai impressa
            como texto cru no relatório final, então vale resolver todas: ou o bloco
            precisa de regra, ou a variável está errada para este tema.
          </Botao>
          <p>
            Gerar a prévia <strong>não</strong> publica nada e não toca no relatório que
            o site serve.
          </p>
        </>
      ),
    },
    {
      id: 'divergencias',
      titulo: 'Divergências',
      corpo: (
        <>
          <p>
            A aba só aparece depois de importar um Doc. Ela lista os pontos em que o
            contrato <strong>não</strong> reproduz exatamente o que o Google Doc fazia —
            uma condição que a importação não soube traduzir, uma formatação que se
            perdeu.
          </p>
          <p>
            Divergência não é erro: é a lista do que conferir antes de publicar. Cada
            item mostra o trecho, o que acontece hoje, o que passaria a acontecer e, onde
            existe, a prova.
          </p>
          <Dev>
            Geradas por <code>utils/editorial/importador.py</code>. A contagem por tema
            hoje vai de 2 (saúde, meio ambiente) a 5 (demografia). O script{' '}
            <code>scripts/conferir_paridade.py</code> compara os dois caminhos linha a
            linha fora do painel.
          </Dev>
        </>
      ),
    },
    {
      id: 'conexao',
      titulo: 'O selo de conexão',
      corpo: (
        <>
          <p>
            Fica no topo, ao lado do seu nome, e é o primeiro lugar para olhar quando
            alguma coisa parecer quebrada. O banco do Data Nordeste não roda nesta
            máquina: ele mora num servidor, e só chega até aqui por um túnel que alguém
            precisa deixar aberto.
          </p>
          <Botao nome="o próprio selo">
            Clique para testar a conexão na hora. Verde é banco respondendo; vermelho
            abre o motivo e o comando exato para abrir o túnel, com o host e a porta
            desta instalação já preenchidos.
          </Botao>
          <Botao nome="Copiar comando">
            Copia o comando do túnel. Ele roda num terminal à parte, pede a senha da
            chave e fica aberto enquanto você trabalha.
          </Botao>
          <Botao nome="Testar de novo">
            Depois de abrir o túnel, reconfere e recarrega a lista de variáveis{' '}
            <strong>sem recarregar a página</strong> — seu rascunho não se perde.
          </Botao>
          <p className="guia-alerta">
            Sem conexão o painel continua funcionando, mas a lista de variáveis cai para
            as poucas dezenas que vêm da planilha CSV, e a prévia sai com buracos. Não
            publique um tema inteiro nesse estado.
          </p>
          <Dev>
            Túnel SSH <code>5433 → 127.0.0.1:5432</code> para <code>ubuntu@10.5.8.5</code>,
            com VPN fora do escritório. O teste é{' '}
            <code>GET /admin/conexao</code>, que só abre e fecha uma conexão. Confira
            também por fora com <code>python3 -m utils.database</code>, que deve imprimir
            “Conexão bem-sucedida!”.
          </Dev>
        </>
      ),
    },
  ];
}

export default function Guia({ aoFechar, totalDeCidades }) {
  const secoes = useMemo(() => montarSecoes(totalDeCidades), [totalDeCidades]);
  const [secaoAtiva, setSecaoAtiva] = useState(secoes[0].id);
  const [mostrarDev, setMostrarDev] = useState(true);
  const caixa = useRef(null);

  // Esc fecha, e o foco entra na caixa para que a leitura por teclado comece
  // dentro do guia e não atrás dele.
  useEffect(() => {
    caixa.current?.focus();
    const aoTeclar = (evento) => { if (evento.key === 'Escape') aoFechar(); };
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aoFechar]);

  const secao = secoes.find((s) => s.id === secaoAtiva) || secoes[0];

  return (
    <div className="guia-fundo" role="presentation" onClick={aoFechar}>
      <div
        className={`guia${mostrarDev ? '' : ' sem-dev'}`}
        role="dialog"
        aria-modal="true"
        aria-label="Guia do painel"
        tabIndex={-1}
        ref={caixa}
        onClick={(evento) => evento.stopPropagation()}
      >
        <header className="guia-topo">
          <h2><Icone nome="info" className="icone-info" /> Guia do painel</h2>
          <label className="guia-alternador">
            <input
              type="checkbox"
              checked={mostrarDev}
              onChange={(e) => setMostrarDev(e.target.checked)}
            />
            Notas técnicas
          </label>
          <button type="button" className="icone" onClick={aoFechar} aria-label="Fechar o guia">×</button>
        </header>

        <div className="guia-corpo">
          <nav className="guia-indice" aria-label="Seções do guia">
            {secoes.map((item) => (
              <button
                type="button"
                key={item.id}
                className={item.id === secaoAtiva ? 'ativa' : ''}
                onClick={() => setSecaoAtiva(item.id)}
              >
                {item.titulo}
              </button>
            ))}
          </nav>

          <article className="guia-texto" key={secao.id}>
            <h3>{secao.titulo}</h3>
            {secao.corpo}
          </article>
        </div>
      </div>
    </div>
  );
}
