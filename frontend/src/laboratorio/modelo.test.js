// node --test 'frontend/src/laboratorio/*.test.js'  (test runner nativo do Node, sem dependência)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { agruparEmBlocos, condicaoDoItem, exportar, lerDoc } from './modelo.js'

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
