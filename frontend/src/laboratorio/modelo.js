// Modelo do texto do tema no laboratório: o Doc vira uma lista de itens ("texto" ou
// "versao"), cada um com o trecho ORIGINAL do Doc. Exportar é concatenar os trechos,
// então o que ninguém editou volta idêntico ao Doc, caractere por caractere (spec,
// "Construir"). Quem decide o que o texto vira num município é o backend; aqui só se
// reconhece onde estão as versões, com as mesmas regras de linha do gerador
// (utils/render/placeholders.py: interpretar_blocos_condicionais).

// _normalizar_condicao_editorial
export function normalizarCondicao(linha) {
  return linha
    .trim()
    .replace(/\\([_=>()])/g, '$1')
    .replaceAll('**', '')
    .replaceAll(' ', ' ')
    .trim()
}

// "Para quando ...:" (ou "Para ...:") com pelo menos um $campo, e a variante do Gini.
const CONDICAO = /^para(?:\s+quando)?\s+(.+?):\s*(.*)$/i
const CAMPO = /(?:[A-Za-z_][\w-]*\.)?\$([A-Za-z_]\w*)/
const GINI =
  /^(?:para\s+)?quando\s+o\s+[íi]ndice\s+de\s+gini\s+for\s+(maior\s+(?:e|ou)\s+igual\s+a|menor\s+que)\s+(\d+(?:[.,]\d+)?)\s*:?\s*$/i
// Linhas de estrutura: título "#!" e marcador de gráfico. Encerram o parágrafo.
const ESTRUTURA = /^(?:#!|(?:%%|\*)\w+(?:\+\w+)*$)/

// O Doc abre e fecha o bloco do tema na própria linha de texto
// (descricao_tema = “Para quando ...); o backend corta isso antes de ler.
const semMarcadorDeBloco = (linha) =>
  linha.replace(/^\s*descricao_tema\s*=\s*[“"]?/, '').replace(/[”"]?\s*@@\s*$/, '')
const semFimDeLinha = (linha) => linha.replace(/\r$/, '')
const emBranco = (linha) => semFimDeLinha(linha).trim() === ''

// Devolve {inline} se a linha é uma condição; inline é o texto depois do ":".
function lerCondicao(linha) {
  const limpa = normalizarCondicao(semMarcadorDeBloco(semFimDeLinha(linha)))
  if (GINI.test(limpa)) return { inline: '' }
  const m = limpa.match(CONDICAO)
  if (m && CAMPO.test(m[1])) return { inline: m[2] }
  return null
}

export function lerDoc(texto) {
  // Cada linha leva o próprio "\n" (menos a última), para a concatenação ser exata.
  const linhas = texto.split('\n').map((l, i, todas) => (i < todas.length - 1 ? l + '\n' : l))
  const itens = []
  let texto_ = ''
  const fecharTexto = () => {
    if (texto_) itens.push({ tipo: 'texto', original: texto_ })
    texto_ = ''
  }

  let i = 0
  while (i < linhas.length) {
    const condicao = lerCondicao(linhas[i])
    if (!condicao) {
      texto_ += linhas[i]
      i++
      continue
    }
    fecharTexto()
    let trecho = linhas[i]
    i++
    if (!condicao.inline) {
      // A linha em branco entre a condição e o parágrafo pertence à versão.
      let j = i
      while (j < linhas.length && emBranco(linhas[j])) j++
      if (j < linhas.length && !lerCondicao(linhas[j]) && !ESTRUTURA.test(semFimDeLinha(linhas[j]).trim())) {
        trecho += linhas.slice(i, j).join('')
        i = j
        while (
          i < linhas.length &&
          !emBranco(linhas[i]) &&
          !lerCondicao(linhas[i]) &&
          !ESTRUTURA.test(semFimDeLinha(linhas[i]).trim())
        ) {
          trecho += linhas[i]
          i++
        }
      }
    }
    itens.push({
      tipo: 'versao',
      original: trecho,
      condicao: normalizarCondicao(semMarcadorDeBloco(semFimDeLinha(trecho.split('\n')[0]))),
    })
  }
  fecharTexto()
  return itens
}

export function exportar(itens) {
  return itens.map((item) => item.editado ?? item.original).join('')
}

// Os $campos que a condição testa (sem o prefixo do tema).
export function camposDaCondicao(condicao) {
  return new Set([...condicao.matchAll(new RegExp(CAMPO, 'g'))].map((m) => m[1]))
}

// Blocos são só leitura de tela (o gerador não tem esse conceito): versões seguidas,
// separadas no máximo por linhas em branco, até um texto fixo ou de estrutura. Dentro
// dessa sequência, uma versão que não testa nenhum $campo das anteriores começa outro
// bloco (ex.: demografia, faixa etária × diferença 0–9 / 60+). Dividir pelas versões
// que disparam juntas zeraria o "2+ versões" por construção, que é o alerta que importa.
export function agruparEmBlocos(itens) {
  const grupos = []
  let bloco = null
  itens.forEach((item, indice) => {
    if (item.tipo === 'versao') {
      const campos = camposDaCondicao(item.condicao)
      const compartilha = bloco && [...campos].some((c) => bloco.campos.has(c))
      if (!compartilha) {
        bloco = { tipo: 'bloco', versoes: [], campos: new Set() }
        grupos.push(bloco)
      }
      bloco.versoes.push(indice)
      campos.forEach((c) => bloco.campos.add(c))
    } else if (item.original.trim() === '' && bloco) {
      // linha em branco entre versões: continua o bloco
    } else {
      bloco = null
      if (item.original.trim()) grupos.push({ tipo: 'texto', indice })
    }
  })
  return grupos.map(({ campos: _campos, ...grupo }) => grupo)
}
