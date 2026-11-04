// node --test 'frontend/src/laboratorio/*.test.js'  (test runner nativo do Node, sem dependência)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { agruparEmBlocos, condicaoDoItem, exportar, lerDoc, prefixoDoDoc, trechoParaLer,
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
    { tipo: 'bloco', versoes: [1, 3] },
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
    assert.equal(blocoAlterado(itens, b.versoes), false)
    assert.ok(doc.includes(textoDoBloco(itens, b.versoes)))
  }
  const [b1, b2] = blocos
  itens[b2.versoes[0]].editado = ''
  assert.equal(blocoAlterado(itens, b1.versoes), false)
  assert.equal(blocoAlterado(itens, b2.versoes), true)
  assert.ok(!textoDoBloco(itens, b2.versoes).includes(itens[b2.versoes[0]].original.trim()))
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
  const copia = textoDoBloco(itens, versoes)
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
