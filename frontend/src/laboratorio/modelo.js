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
    if (texto_) itens.push({ id: itens.length, tipo: 'texto', original: texto_ })
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
      id: itens.length,
      tipo: 'versao',
      original: trecho,
      condicao: normalizarCondicao(semMarcadorDeBloco(semFimDeLinha(trecho.split('\n')[0]))),
    })
  }
  fecharTexto()
  return itens
}

export function exportar(itens) {
  return itens.map(textoDoItem).join('')
}

export const textoDoItem = (item) => item.editado ?? item.original

// A condição de uma versão depois de editada (null se a 1ª linha deixou de ser condição).
export function condicaoDoItem(item) {
  const primeira = semFimDeLinha(textoDoItem(item).replace(/^\s*\n/, '').split('\n')[0])
  return lerCondicao(primeira) ? normalizarCondicao(semMarcadorDeBloco(primeira)) : null
}

// Os $campos de uma condição ou de um trecho inteiro (sem o prefixo do tema).
export function camposDaCondicao(condicao) {
  return new Set([...condicao.matchAll(new RegExp(CAMPO, 'g'))].map((m) => m[1]))
}

// Blocos são só leitura de tela (o gerador não tem esse conceito): versões seguidas,
// separadas no máximo por linhas em branco, até um texto fixo ou de estrutura. Dentro
// dessa sequência, uma versão que não testa nenhum $campo das anteriores começa outro
// bloco (ex.: demografia, faixa etária × diferença 0–9 / 60+). Dividir pelas versões
// que disparam juntas zeraria o "2+ versões" por construção, que é o alerta que importa.
//
// `ajustes` vem da editora: `cortes` (id de versão que começa bloco novo) e `juncoes`
// (id de versão que fica no bloco de cima), por cima da regra automática. Por id, e
// não pela posição: inserir uma versão desloca as posições.
export function agruparEmBlocos(itens, ajustes = { cortes: new Set(), juncoes: new Set() }) {
  const grupos = []
  let bloco = null
  itens.forEach((item, indice) => {
    if (item.tipo === 'versao') {
      // Versão removida ou sem condição agrupa pela condição original.
      const campos = camposDaCondicao(condicaoDoItem(item) ?? item.condicao ?? '')
      const compartilha = bloco && [...campos].some((c) => bloco.campos.has(c))
      const fica = bloco && !ajustes.cortes.has(item.id) && (compartilha || ajustes.juncoes.has(item.id))
      if (!fica) {
        bloco = { tipo: 'bloco', versoes: [], campos: new Set() }
        grupos.push(bloco)
      }
      bloco.versoes.push(indice)
      campos.forEach((c) => bloco.campos.add(c))
    } else if (textoDoItem(item).trim() === '' && bloco) {
      // linha em branco entre versões: continua o bloco
    } else {
      bloco = null
      if (textoDoItem(item).trim()) grupos.push({ tipo: 'texto', indice })
    }
  })
  return grupos.map(({ campos: _campos, ...grupo }) => grupo)
}

// O prefixo que o Doc já usa ("demografia.$campo"); o mais comum ganha. Sem nenhum,
// o slug inteiro, que o gerador aceita (_ALIASES_NAMESPACE).
export function prefixoDoDoc(texto, slug) {
  const contagem = new Map()
  for (const m of texto.matchAll(/([A-Za-z_][\w-]*)\.\$/g)) contagem.set(m[1], (contagem.get(m[1]) ?? 0) + 1)
  return [...contagem].sort((a, b) => b[1] - a[1])[0]?.[0] ?? slug
}

// O trecho como o backend lê: sem o marcador do bloco do tema, que a 1ª e a última
// versões do Doc carregam ("descricao_tema = “Para quando ..." / "...”@@").
export const trechoParaLer = (texto) => semMarcadorDeBloco(texto.trim())

// Os operadores que o gerador entende (utils/render/placeholders.py,
// _OPERADORES_EDITORIAIS e _CONDICAO_SEM_DADOS). Comparar coluna de texto com uma
// palavra não existe no gerador ("for igual a pequeno porte" nunca vale): coluna de
// texto só tem "sem dados".
export const OPERADORES = [
  { id: 'igual', rotulo: 'igual a', valores: 1, frase: (v) => `igual a ${v}` },
  { id: 'diferente', rotulo: 'diferente de', valores: 1, frase: (v) => `diferente de ${v}` },
  { id: 'maior', rotulo: 'maior que', valores: 1, frase: (v) => `maior que ${v}` },
  { id: 'menor', rotulo: 'menor que', valores: 1, frase: (v) => `menor que ${v}` },
  { id: 'maior_igual', rotulo: 'maior ou igual a', valores: 1, frase: (v) => `maior ou igual a ${v}` },
  { id: 'menor_igual', rotulo: 'menor ou igual a', valores: 1, frase: (v) => `menor ou igual a ${v}` },
  { id: 'entre', rotulo: 'entre … e …', valores: 2, frase: (v, w) => `entre ${v} e ${w}` },
  { id: 'sem_dados', rotulo: 'sem dados', valores: 0, texto: true, frase: () => 'sem dados' },
  { id: 'com_dados', rotulo: 'com dados (diferente de sem dados)', valores: 0, texto: true, frase: () => 'diferente de sem dados' },
]

// Número como o gerador lê no texto da condição (_NUMERO_EDITORIAL): sem sinal,
// vírgula ou ponto decimal. "-1" não casa e a regra nunca valeria.
export const numeroValido = (v) => /^\d+(?:[.,]\d+)?$/.test(v.trim())

export function fraseDaCondicao({ prefixo, coluna, operador, valor = '', valor2 = '' }) {
  const op = OPERADORES.find((o) => o.id === operador)
  return `Para quando ${prefixo}.$${coluna} for ${op.frase(valor.trim(), valor2.trim())}, então:`
}
