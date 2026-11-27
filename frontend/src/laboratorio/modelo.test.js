// node --test 'frontend/src/laboratorio/*.test.js'  (test runner nativo do Node, sem dependência)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { AVISO_FIM_SOLTO, AVISO_FORA, AVISO_SEM_FIM, agruparEmBlocos, chaveDoRascunho, lerMarca,
  coladosNoMarcador, completarMarcas, juntarBlocos, novoBlocoDepois, renomearBloco, separarBloco, comNovoBloco, condicaoDoItem, exportar, lerDoc, prefixoDoDoc, trechoParaLer,
  avisosDaVersao, blocoAlterado, buscarOpcoes, doRascunho, htmlParaODocs, inserirColuna, paraRascunho, temEdicao, textoDoBloco } from './modelo.js'

const FIXTURES = new URL('../../../tests/fixtures/relatorio_congelado/docs/', import.meta.url)
const TEMAS = ['demografia', 'educacao', 'saude', 'economia-renda', 'hidraulica',
  'desenvolvimento-social', 'meio-ambiente', 'saneamento']

test('ida e volta: sem edição, exportar devolve o Doc idêntico', () => {
  for (const tema of TEMAS) {
    const doc = readFileSync(new URL(`${tema}.txt`, FIXTURES), 'utf-8')
    assert.equal(exportar(lerDoc(doc)), doc, tema)
  }
})

test('acha as versões dos Docs reais', () => {
  const doc = readFileSync(new URL('demografia.txt', FIXTURES), 'utf-8')
  const versoes = lerDoc(doc).filter((i) => i.tipo === 'versao')
  assert.ok(versoes.length > 20)
  assert.ok(versoes.every((v) => /^para|quando/i.test(v.condicao)))
})

test('versão leva a linha em branco e o parágrafo; texto fixo encerra o bloco', () => {
  const doc =
    'Intro.\n\nPara quando $a for igual a 1:\n\nUm.\n\nPara quando $a for igual a 2:\nDois.\n\nFixo.\n'
  const itens = lerDoc(doc)
  assert.deepEqual(itens.map((i) => i.tipo), ['texto', 'versao', 'texto', 'versao', 'texto'])
  assert.equal(itens[1].original, 'Para quando $a for igual a 1:\n\nUm.\n')
  assert.deepEqual(agruparEmBlocos(itens), [
    { tipo: 'texto', indice: 0 },
    { tipo: 'bloco', versoes: [1, 3], inicio: 1, fim: 3 },
    { tipo: 'texto', indice: 4 },
  ])
})

test('só o item editado muda na exportação', () => {
  const doc = 'Para quando $a for igual a 1:\nUm.\n\nFim.'
  const itens = lerDoc(doc)
  itens[0].editado = 'Para quando $a for igual a 1:\nUm só.\n'
  assert.equal(exportar(itens), 'Para quando $a for igual a 1:\nUm só.\n\nFim.')
})

test('"Para efeito de análise:" sem $campo não é condição', () => {
  assert.deepEqual(lerDoc('Para efeito de análise: nada.\n').map((i) => i.tipo), ['texto'])
})

test('versão que não testa nenhum $campo das anteriores começa outro bloco', () => {
  const doc =
    'Para quando $a for igual a 1:\nA1.\n\nPara quando $a for igual a 2:\nA2.\n\n' +
    'Para quando $b for igual a 1 e $a for igual a 2:\nB.\n\nPara quando $c for igual a 1:\nC.\n'
  const blocos = agruparEmBlocos(lerDoc(doc)).map((g) => g.versoes)
  assert.deepEqual(blocos, [[0, 2, 4], [6]])
})

test('a editora corta e junta blocos por cima da regra automática', () => {
  const doc =
    'Para quando $a for igual a 1:\nA.\n\nPara quando $a for igual a 2 e $b for igual a 1:\nB.\n\n' +
    'Para quando $c for igual a 1:\nC.\n'
  const itens = lerDoc(doc)
  const blocos = (ajustes) => agruparEmBlocos(itens, ajustes).map((g) => g.versoes)
  assert.deepEqual(blocos(undefined), [[0, 2], [4]])
  assert.deepEqual(blocos({ cortes: new Set([2]), juncoes: new Set() }), [[0], [2], [4]])
  assert.deepEqual(blocos({ cortes: new Set(), juncoes: new Set([4]) }), [[0, 2, 4]])
})

test('a condição acompanha a edição da versão', () => {
  const itens = lerDoc('Para quando $a for igual a 1:\nA.\n')
  assert.equal(condicaoDoItem(itens[0]), 'Para quando $a for igual a 1:')
  itens[0].editado = 'Para quando $a for maior que 5:\nA.\n'
  assert.equal(condicaoDoItem(itens[0]), 'Para quando $a for maior que 5:')
  itens[0].editado = 'Sem condição.\n'
  assert.equal(condicaoDoItem(itens[0]), null)
})

test('prefixo do tema: o que o Doc mais usa, ou o slug', () => {
  assert.equal(prefixoDoDoc('ambiente.$a e ambiente.$b e meio-ambiente.$c', 'meio-ambiente'), 'ambiente')
  assert.equal(prefixoDoDoc('sem campo nenhum', 'meio-ambiente'), 'meio-ambiente')
})

test('trecho para ler sai sem o marcador do bloco do tema', () => {
  assert.equal(trechoParaLer('descricao_tema = “Para quando $x for 1, então:\nA.\n'), 'Para quando $x for 1, então:\nA.')
  assert.equal(trechoParaLer('\nFim do tema.”@@\n'), 'Fim do tema.')
})

test('os marcadores do tema ficam fora das versões', () => {
  for (const tema of TEMAS) {
    const versoes = lerDoc(readFileSync(new URL(`${tema}.txt`, FIXTURES), 'utf-8')).filter((i) => i.tipo === 'versao')
    for (const v of versoes) {
      assert.doesNotMatch(v.original, /descricao_tema|@@/, tema)
      assert.match(v.original, /^\s*Para/i, tema)
    }
  }
})

test('bloco: alterado só se algum item mudou, e o texto volta igual ao Doc', () => {
  const doc = readFileSync(new URL('demografia.txt', FIXTURES), 'utf-8')
  const itens = lerDoc(doc)
  const blocos = agruparEmBlocos(itens).filter((g) => g.tipo === 'bloco')
  for (const b of blocos) {
    assert.equal(blocoAlterado(itens, b), false)
    assert.ok(doc.includes(textoDoBloco(itens, b)))
  }
  const [b1, b2] = blocos
  itens[b2.versoes[0]].editado = ''
  assert.equal(blocoAlterado(itens, b1), false)
  assert.equal(blocoAlterado(itens, b2), true)
  assert.ok(!textoDoBloco(itens, b2).includes(itens[b2.versoes[0]].original.trim()))
  assert.equal(temEdicao(itens), true)
})

test('avisos da versão', () => {
  const colunas = new Map([['x', {}]])
  const v = (texto) => avisosDaVersao({ tipo: 'versao', original: texto }, colunas)
  assert.deepEqual(v('Para quando $x for 1, então:\nTexto.\n'), [])
  assert.deepEqual(v('Para quando $x for 1, então: Texto na linha.\n'), [])
  assert.match(v('Para quando $x for 1, então:\n\n')[0], /^Esta versão só tem a condição/)
  assert.match(v('Texto qualquer\nmais')[0], /não é uma condição/)
  assert.match(v('Para quando demografia.$campo for igual a 0, então:\nT.\n')[0], /condição usa \$campo, que não existe/)
  // O texto embaixo da condição também (André, 03/11: o aviso só vinha da conferência, lá no topo).
  assert.deepEqual(v('Para quando $x for 1, então:\nValor $errado e tema.$outro.\n').map((a) => a.slice(0, 8)), ['$errado ', '$outro n'])
  assert.match(v('Para quando $x for 1, então: Na linha $errado.\n')[0], /^\$errado não existe/)
  // Apelido que o gerador resolve vem nas colunas (tipo "apelido"): não é aviso.
  assert.deepEqual(avisosDaVersao({ tipo: 'versao', original: 'Para quando $x for 1:\n$area.' }, new Map([['x', {}], ['area', { tipo: 'apelido' }]])), [])
  // Texto fixo: sai em todo município, então também avisa.
  assert.match(avisosDaVersao({ tipo: 'texto', original: 'Fixo com $errado.' }, colunas)[0], /^\$errado não existe/)
  assert.deepEqual(avisosDaVersao({ tipo: 'texto', original: 'Fixo $x.' }, null), [])
  assert.deepEqual(avisosDaVersao({ tipo: 'versao', original: 'Para quando $y for 1:\nT', editado: '' }, colunas), [])
})

test('rascunho: ida e volta, e formato desconhecido é ignorado', () => {
  const itens = lerDoc('Para quando $x for 1, então:\nA.\n')
  itens[0].editado = 'Para quando $x for 2, então:\nB.\n'
  const json = paraRascunho({ hash: 'h', itens, ajustes: { cortes: new Set([3]), juncoes: new Set() }, proximoId: 5 })
  const r = doRascunho(json)
  assert.equal(r.hash, 'h')
  assert.deepEqual(r.itens, itens)
  assert.ok(r.ajustes.cortes.has(3))
  assert.equal(doRascunho(json.replace('"formato":1', '"formato":0')), null)
  assert.equal(doRascunho('não é json'), null)
})

test('copiar o último bloco editado leva o ”@@ da linha do Doc', () => {
  const itens = lerDoc('descricao_tema = “Para quando $x for 1, então:\nA.\n\nPara quando $x for 2, então:\nB.”@@\n')
  const versoes = itens.flatMap((i, k) => (i.tipo === 'versao' ? [k] : []))
  itens[versoes[1]].editado = 'Para quando $x for 2, então:\nB editado.\n'
  const copia = textoDoBloco(itens, { inicio: versoes[0], fim: versoes.at(-1) })
  assert.ok(copia.startsWith('descricao_tema = “Para quando $x for 1'))
  assert.ok(copia.endsWith('B editado.\n”@@'))
})

test('inserirColuna põe o prefixo do Doc só quando o "$" veio solto', () => {
  // "em $esg|" → coluna escolhida, com o prefixo na frente
  assert.deepEqual(inserirColuna('em $esg fim', 4, 7, 'esgoto_rede_2022', 'infraestrutura'),
    { texto: 'em infraestrutura.$esgoto_rede_2022 fim', cursor: 35 })
  // já tinha prefixo (qualquer um): não duplica
  assert.equal(inserirColuna('em demografia.$', 15, 15, 'nm_mun', 'infraestrutura').texto, 'em demografia.$nm_mun')
  // "$" no começo do texto
  assert.equal(inserirColuna('$', 1, 1, 'nm_mun', 'saude').texto, 'saude.$nm_mun')
})

test('htmlParaODocs: cada $ num span, linhas (e as em branco) por <br>, texto escapado', () => {
  assert.equal(htmlParaODocs('a.$x <b>\n\nb.$y'),
    '<p style="margin:0">a.<span>$</span>x &lt;b&gt;<br><br>b.<span>$</span>y</p>')
})

test('buscarOpcoes: sem acento e sem caixa, quem começa com o termo vem antes', () => {
  const cidades = ['Água Branca (AL)', 'Recife (PE)', 'Santa Rita (PB)', 'Riachão (MA)', 'Arapiraca (AL)']
  assert.deepEqual(buscarOpcoes(cidades, 'agua'), ['Água Branca (AL)'])
  assert.deepEqual(buscarOpcoes(cidades, 'ri'), ['Riachão (MA)', 'Santa Rita (PB)'])
  assert.deepEqual(buscarOpcoes(cidades, '(al)'), ['Água Branca (AL)', 'Arapiraca (AL)'])
  assert.equal(buscarOpcoes(cidades, '', 2).length, 2)
})

test('rascunho de estado não sobrescreve o municipal', () => {
  assert.equal(chaveDoRascunho('demografia'), 'laboratorio:rascunho:demografia')
  assert.equal(chaveDoRascunho('demografia', 'estado'), 'laboratorio:rascunho:demografia@estado')
})

test('novo bloco num Doc vazio monta o tema com os marcadores', () => {
  let n = 0
  const { id, itens } = comNovoBloco(lerDoc(''), 'demografia', () => n++)
  const texto = exportar(itens)
  assert.equal(texto, 'descricao_tema = “[bloco]\nPara quando demografia.$campo for igual a 0, então:\nTexto desta versão.\n[fimbloco]\n”@@\n')
  // Relido do Doc depois de colar, é o mesmo bloco.
  assert.deepEqual(lerDoc(texto).map((i) => i.tipo), ['texto', 'marca', 'versao', 'marca', 'texto'])
  assert.equal(agruparEmBlocos(itens).filter((g) => g.tipo === 'bloco').length, 1)
  assert.equal(itens.find((i) => i.id === id).tipo, 'versao')
})

test('Doc com texto não começa bloco pelo "+ começar"', () => {
  assert.equal(comNovoBloco(lerDoc('Só um texto.\n'), 'demografia', () => 0), null)
})

// --- Marcadores de bloco: [bloco: nome] … [fimbloco] (27/11/2026) ---

test('lerMarca: as grafias que o gerador aceita (_MARCADOR_BLOCO)', () => {
  assert.deepEqual(lerMarca('[bloco: Analfabetismo]\n'), { abre: true, nome: 'Analfabetismo' })
  assert.deepEqual(lerMarca('  [ Bloco ]  '), { abre: true, nome: '' })
  assert.deepEqual(lerMarca('\\[bloco: Escapado\\]'), { abre: true, nome: 'Escapado' })
  assert.deepEqual(lerMarca('descricao_tema = “[bloco: A]'), { abre: true, nome: 'A' })
  for (const fim of ['[fimbloco]', '[FimBloco]', '[fim bloco]', '[fim do bloco]', '\\[fimbloco\\]', '[fimbloco]”@@'])
    assert.deepEqual(lerMarca(fim), { abre: false }, fim)
  assert.equal(lerMarca('O [bloco] de texto continua.'), null)
})

const DOC_MARCADO =
  'descricao_tema = “[bloco: Analfabetismo]\nPara quando $a for igual a 1:\nUm.\n\nPara quando $b for igual a 2:\nDois.\n\nFixo dentro.\n[fimbloco]\n\nTítulo fora\n\n[bloco]\nPara quando $c for igual a 1:\nTrês.\n[fimbloco]”@@\n'

test('marcadores: ida e volta idêntica, e cada marcador é um item próprio', () => {
  const itens = lerDoc(DOC_MARCADO)
  assert.equal(exportar(itens), DOC_MARCADO)
  assert.deepEqual(itens.filter((i) => i.tipo === 'marca').map((i) => i.original), ['[bloco: Analfabetismo]\n', '[fimbloco]\n', '[bloco]\n', '[fimbloco]'])
  // O marcador colado no texto encerra a versão (o gerador lê a linha como em branco).
  const glued = lerDoc('Para quando $a for igual a 1:\nUm.\n[fimbloco]\nTítulo\n')
  assert.deepEqual(glued.map((i) => i.tipo), ['versao', 'marca', 'texto'])
})

test('marcadores: o bloco vai do [bloco] ao [fimbloco], com o texto fixo de dentro, sem palpite', () => {
  const itens = lerDoc(DOC_MARCADO)
  const grupos = agruparEmBlocos(itens)
  assert.deepEqual(grupos.map((g) => g.tipo), ['bloco', 'texto', 'bloco'])
  const [b1, titulo, b2] = grupos
  // $a e $b não têm campo em comum: no palpite seriam dois blocos.
  assert.equal(b1.versoes.length, 2)
  assert.equal(b1.nome, 'Analfabetismo')
  assert.equal(itens[b1.membros.at(-1)].original.trim(), 'Fixo dentro.')
  assert.equal(textoQueSaiDe(itens, titulo.indice), 'Título fora')
  assert.equal(b2.nome, '')
  assert.ok(!b1.aviso && !b2.aviso)
  // Copiar leva os marcadores (e o descricao_tema / ”@@ da mesma linha).
  assert.ok(textoDoBloco(itens, b1).startsWith('descricao_tema = “[bloco: Analfabetismo]'))
  assert.ok(textoDoBloco(itens, b1).endsWith('Fixo dentro.\n[fimbloco]'))
  assert.ok(textoDoBloco(itens, b2).endsWith('[fimbloco]”@@'))
})

const textoQueSaiDe = (itens, i) => itens[i].original.trim()

test('marcadores: avisos de bloco sem fim, versão fora e [fimbloco] solto', () => {
  const doc = '[bloco: A]\nPara quando $a for igual a 1:\nUm.\n\n[bloco: B]\nPara quando $a for igual a 2:\nDois.\n[fimbloco]\n\nFixo.\n\nPara quando $a for igual a 3:\nTrês.\n\n[fimbloco]\n'
  const grupos = agruparEmBlocos(lerDoc(doc))
  assert.deepEqual(grupos.map((g) => g.aviso ?? null), [AVISO_SEM_FIM, null, null, AVISO_FORA, AVISO_FIM_SOLTO])
  const ultimo = agruparEmBlocos(lerDoc('[bloco]\nPara quando $a for igual a 1:\nUm.\n'))
  assert.equal(ultimo[0].aviso, AVISO_SEM_FIM)
})

test('Doc sem marcador continua com o palpite', () => {
  const itens = lerDoc('Para quando $a for igual a 1:\nUm.\n\nPara quando $b for igual a 1:\nDois.\n')
  assert.equal(agruparEmBlocos(itens).length, 2)
})

// --- Escrever os marcadores ---

const SEM_AJUSTES = { cortes: new Set(), juncoes: new Set() }
const contador = (itens) => {
  let n = Math.max(...itens.map((i) => i.id)) + 1
  return () => n++
}
const DOC_PALPITE =
  'descricao_tema = “Para quando $uf_pop for maior que 5:\nGrande.\n\nPara quando $uf_pop for menor ou igual a 5:\nPequeno.”@@\n\n#!Fontes\n'

test('+ novo bloco num Doc sem marcador: marca o palpite e põe o bloco novo depois', () => {
  const itens = lerDoc(DOC_PALPITE)
  const { id, itens: novos } = novoBlocoDepois(itens, SEM_AJUSTES, itens[1].id, 'demografia', contador(itens))
  assert.equal(exportar(novos),
    'descricao_tema = “[bloco]\nPara quando $uf_pop for maior que 5:\nGrande.\n\nPara quando $uf_pop for menor ou igual a 5:\nPequeno.\n[fimbloco]\n' +
    '[bloco]\nPara quando demografia.$campo for igual a 0, então:\nTexto desta versão.\n[fimbloco]\n”@@\n\n#!Fontes\n')
  assert.equal(novos.find((i) => i.id === id).tipo, 'versao')
  // Relido do Doc: os mesmos dois blocos, sem aviso.
  const blocos = agruparEmBlocos(lerDoc(exportar(novos))).filter((g) => g.tipo === 'bloco')
  assert.deepEqual(blocos.map((b) => [b.versoes.length, b.aviso ?? null]), [[2, null], [1, null]])
})

test('separar daqui, juntar de volta e dar nome', () => {
  const doc = 'Intro.\n\nPara quando $a for igual a 1:\nUm.\n\nPara quando $a for igual a 2:\nDois.\n\nPara quando $a for igual a 3:\nTrês.\n\nFixo.\n'
  const itens = lerDoc(doc)
  const novoId = contador(itens)
  const v2 = itens.filter((i) => i.tipo === 'versao')[1].id
  const separado = separarBloco(itens, SEM_AJUSTES, v2, novoId)
  assert.equal(exportar(separado),
    'Intro.\n\n[bloco]\nPara quando $a for igual a 1:\nUm.\n\n[fimbloco]\n[bloco]\nPara quando $a for igual a 2:\nDois.\n\nPara quando $a for igual a 3:\nTrês.\n[fimbloco]\n\nFixo.\n')
  assert.deepEqual(agruparEmBlocos(separado).filter((g) => g.tipo === 'bloco').map((b) => b.versoes.length), [1, 2])
  const junto = juntarBlocos(separado, SEM_AJUSTES, v2, novoId)
  assert.equal(exportar(junto), exportar(completarMarcas(itens, SEM_AJUSTES, contador(itens))))
  const nomeado = renomearBloco(junto, SEM_AJUSTES, v2, 'Faixa ] etária', novoId)
  assert.ok(exportar(nomeado).startsWith('Intro.\n\n[bloco: Faixa   etária]\nPara quando $a'))
  assert.equal(agruparEmBlocos(nomeado)[1].nome, 'Faixa   etária')
})

test('completarMarcas nos Docs reais: mesmos blocos do palpite, relidos do texto', () => {
  for (const tema of TEMAS) {
    const doc = readFileSync(new URL(`${tema}.txt`, FIXTURES), 'utf-8')
    const itens = lerDoc(doc)
    const condicoes = (its, grupos) => grupos.filter((g) => g.tipo === 'bloco').map((g) => g.versoes.map((k) => its[k].condicao))
    const completo = completarMarcas(itens, SEM_AJUSTES, contador(itens))
    const marcado = exportar(completo)
    const relidos = lerDoc(marcado)
    assert.equal(exportar(relidos), marcado, tema)
    const grupos = agruparEmBlocos(relidos)
    assert.deepEqual(condicoes(relidos, grupos), condicoes(itens, agruparEmBlocos(itens)), tema)
    assert.ok(grupos.every((g) => !g.aviso), tema)
    // Só os marcadores entraram: sem eles, o texto é o Doc de antes.
    assert.equal(exportar(completo.filter((i) => i.tipo !== 'marca')), doc, tema)
  }
})

test('texto colado no marcador depois de uma versão ganha aviso; com linha em branco, não', () => {
  const colado = lerDoc('[bloco]\nPara quando $a for igual a 1:\nUm.\n[fimbloco]\nTítulo\n')
  assert.deepEqual([...coladosNoMarcador(colado)].map((k) => colado[k].original), ['Título\n'])
  for (const doc of [
    '[bloco]\nPara quando $a for igual a 1:\nUm.\n[fimbloco]\n\nTítulo\n',
    '[bloco]\nPara quando $a for igual a 1:\nUm.\n[fimbloco]\n*grafico_x\n',
    'Fixo.\n[bloco]\nPara quando $a for igual a 1:\nUm.\n\n[fimbloco]\n',
    'descricao_tema = “[bloco]\nPara quando $a for igual a 1:\nUm.\n[fimbloco]\n”@@\n',
  ]) assert.equal(coladosNoMarcador(lerDoc(doc)).size, 0, doc)
})
