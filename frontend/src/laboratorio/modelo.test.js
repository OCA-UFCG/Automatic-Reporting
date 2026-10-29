// node --test 'frontend/src/laboratorio/*.test.js'  (test runner nativo do Node, sem dependência)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { agruparEmBlocos, exportar, lerDoc } from './modelo.js'

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
