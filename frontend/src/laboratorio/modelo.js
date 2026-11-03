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
    // Os marcadores do bloco do tema (descricao_tema = “ na 1ª versão, ”@@ na última)
    // ficam fora da versão, como texto: editar, remover ou trocar a condição não os
    // alcança. Sem eles, o backend não acha o texto do tema.
    const abertura = linhas[i].match(/^\s*descricao_tema\s*=\s*[“"]?/)?.[0] ?? ''
    texto_ += abertura
    fecharTexto()
    let trecho = linhas[i].slice(abertura.length)
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
    const fechamento = trecho.match(/[”"]?\s*@@\s*$/)?.[0] ?? ''
    trecho = trecho.slice(0, trecho.length - fechamento.length)
    itens.push({
      id: itens.length,
      tipo: 'versao',
      original: trecho,
      condicao: normalizarCondicao(semFimDeLinha(trecho.split('\n')[0])),
    })
    texto_ = fechamento
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
    } else if (trechoParaLer(textoDoItem(item)) === '' && bloco) {
      // linha em branco (ou o ”@@ do fim do tema) entre versões: continua o bloco
    } else {
      bloco = null
      // O "descricao_tema = “" sozinho, antes da 1ª versão, não vira cartão.
      if (trechoParaLer(textoDoItem(item))) grupos.push({ tipo: 'texto', indice })
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

// Troca o que se digitou depois do "$" (de `inicio` a `fim`) pela coluna escolhida e,
// se o "$" veio sem prefixo, põe o do Doc na frente: o gerador aceita "$campo" solto,
// mas o Doc escreve "tema.$campo" em tudo (André, 03/11). Devolve o texto e o cursor.
export function inserirColuna(texto, inicio, fim, nome, prefixo) {
  const antes = texto.slice(0, inicio - 1)
  const comPrefixo = /[A-Za-z_][\w-]*\.$/.test(antes) ? antes : `${antes}${prefixo}.`
  const novo = `${comPrefixo}$${nome}`
  return { texto: novo + texto.slice(fim), cursor: novo.length }
}

// HTML para colar no Google Docs. Colado como texto puro (ou HTML com o "$" junto do
// texto), o Docs vira todo "$…$" em equação, e o export em txt que o relatório lê
// perde o trecho inteiro. Cada "$" num <span> próprio escapa disso, e as linhas
// unidas por <br> voltam no export idênticas, linhas em branco inclusive (testado
// colando no Docs em 03/11; <p> vazio era descartado e a linha em branco fecha a versão).
export function htmlParaODocs(texto) {
  const esc = (l) => l.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return `<p style="margin:0">${texto.split('\n').map((l) => esc(l).replace(/\$/g, '<span>$</span>')).join('<br>')}</p>`
}

// Opções de uma caixa de busca (cidade, coluna): sem acento e sem caixa, primeiro as que
// começam com o termo, depois as que o contêm; no máximo `max`.
const semAcento = (t) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
export function buscarOpcoes(opcoes, termo, max = 50) {
  const t = semAcento(termo.trim())
  if (!t) return opcoes.slice(0, max)
  const comeca = []
  const contem = []
  for (const opcao of opcoes) {
    const n = semAcento(opcao)
    if (n.startsWith(t)) comeca.push(opcao)
    else if (n.includes(t)) contem.push(opcao)
  }
  return [...comeca, ...contem].slice(0, max)
}

// O trecho como o backend lê: sem o marcador do bloco do tema ("descricao_tema = “" /
// "”@@"), que fica no texto antes da 1ª versão e depois da última.
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

// --- Exportar e rascunho (5c-4) ---

const editado = (item) => item.editado !== undefined || item.original === ''
export const temEdicao = (itens) => itens.some(editado)

// Do 1º ao último item de um bloco (`versoes` são posições em `itens`): as linhas em
// branco entre as versões vão junto.
const itensDoBloco = (itens, versoes) => itens.slice(versoes[0], versoes.at(-1) + 1)

export const blocoAlterado = (itens, versoes) => itensDoBloco(itens, versoes).some(editado)

// O texto do bloco para colar no Doc por cima das mesmas linhas: o que não foi editado
// volta idêntico; só as pontas em branco saem. Linhas inteiras do Doc: na 1ª e na última
// versão do tema, o marcador (descricao_tema = “ / ”@@) está na mesma linha do texto, e
// colar sem ele apagaria o tema do relatório.
export function textoDoBloco(itens, versoes) {
  const antes = itens.slice(0, versoes[0]).map(textoDoItem).join('')
  const bloco = itensDoBloco(itens, versoes).map(textoDoItem).join('')
  const depois = itens.slice(versoes.at(-1) + 1).map(textoDoItem).join('')
  const comecoDaLinha = antes.slice(antes.lastIndexOf('\n') + 1)
  // Pelo original, que é o que está no Doc: editar a versão pode pôr uma quebra no fim
  // dela, mas no Doc a linha continua com o ”@@.
  const original = itensDoBloco(itens, versoes).map((i) => i.original).join('')
  const restoDaLinha = original.endsWith('\n') ? '' : depois.split('\n')[0]
  return (comecoDaLinha + bloco + restoDaLinha).trim()
}

// Avisos que a tela vê sozinha, antes de copiar. Os do gerador (campo cru, condição
// não entendida) vêm da conferência.
export function avisosDaVersao(item, colunas) {
  const texto = textoDoItem(item)
  if (item.tipo !== 'versao' || texto === '') return []
  const [primeira, ...resto] = texto.replace(/^\s*\n/, '').split('\n')
  const condicao = lerCondicao(semFimDeLinha(primeira))
  if (!condicao) return ['a 1ª linha não é uma condição: o gerador lê a versão como texto fixo']
  const avisos = []
  // Ex. real (economia, 01/11): condição seguida de um gráfico. O gerador não põe
  // gráfico, título nem outra condição sob a condição: eles saem sempre.
  if (!condicao.inline.trim() && !resto.join('').trim()) {
    avisos.push('Esta versão só tem a condição, sem texto embaixo. A condição só esconde texto: o gráfico ou título que vem depois sai em todas as cidades, mesmo onde ela não vale.')
  }
  // Coluna errada na condição não aparece como campo cru: vale como 0, e a versão
  // pode sair onde não devia. Pode ser apelido (_resolver_campo_com_alias).
  for (const campo of camposDaCondicao(primeira)) {
    if (colunas && !colunas.has(campo)) avisos.push(`a condição usa $${campo}, que não está nas colunas do tema`)
  }
  return avisos
}

// Rascunho no localStorage (spec, "Rascunho"): por tema, com o hash do Doc em que se
// baseou. `formato` muda se o lerDoc mudar o jeito de cortar o Doc: rascunho de outro
// formato é ignorado, em vez de restaurar itens que não batem mais.
const FORMATO_DO_RASCUNHO = 1
export const chaveDoRascunho = (slug) => `laboratorio:rascunho:${slug}`

export function paraRascunho({ hash, itens, ajustes, proximoId }) {
  return JSON.stringify({
    formato: FORMATO_DO_RASCUNHO,
    hash,
    salvo_em: new Date().toISOString(),
    proximoId,
    itens,
    ajustes: { cortes: [...ajustes.cortes], juncoes: [...ajustes.juncoes] },
  })
}

export function doRascunho(json) {
  try {
    const r = JSON.parse(json)
    if (r?.formato !== FORMATO_DO_RASCUNHO || !Array.isArray(r.itens)) return null
    return { ...r, ajustes: { cortes: new Set(r.ajustes.cortes), juncoes: new Set(r.ajustes.juncoes) } }
  } catch {
    return null
  }
}
