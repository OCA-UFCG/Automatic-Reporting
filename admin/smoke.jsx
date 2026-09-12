/* Teste de fumaça dos componentes do painel: renderiza cada um fora do
   navegador (react-dom/server) com dados de exemplo e falha se algum quebrar.
   Não substitui olhar a tela — não roda efeitos nem eventos —, mas pega o que
   mais acontece ao mexer aqui: prop que virou undefined, componente renomeado,
   bloco de um tipo que ninguém tratou.

       npm run smoke -w admin
*/
import React from 'react'
import { renderToString } from 'react-dom/server'
import Login from './src/components/Login.jsx'
import SeletorDeTema from './src/components/SeletorDeTema.jsx'
import ArvoreDeBlocos from './src/components/ArvoreDeBlocos.jsx'
import EditorDeBloco from './src/components/EditorDeBloco.jsx'
import PaletaDeVariaveis from './src/components/PaletaDeVariaveis.jsx'
import ConstrutorDeRegra from './src/components/ConstrutorDeRegra.jsx'
import Previa from './src/components/Previa.jsx'
import Guia, { montarSecoes } from './src/components/Guia.jsx'
import { SpriteDeIcones } from './src/icones.jsx'

const manifesto = {
  operadores: [
    { op: 'maior', rotulo: 'é maior que', aridade: 1 },
    { op: 'entre', rotulo: 'está entre', aridade: 2 },
    { op: 'existe', rotulo: 'tem valor', aridade: 0 },
  ],
};
const campos = [
  { campo: 'matriculas', rotulo: 'Matrículas', tipo: 'inteiro', origem: 'view' },
  { campo: 'gini', rotulo: 'Gini', tipo: 'decimal', origem: 'view' },
];
const graficos = [{ nome: 'grafico_pib', rotulo: 'Pib' }];
const contrato = {
  moldura: { resumo_tema: { blocos: [] }, fontes: { blocos: [] }, referencias: [] },
  corpo: { blocos: [
    { id: 'p1', tipo: 'paragrafo', regra: null, conteudo: [{ t: 'texto', v: 'Olá ' }, { t: 'var', campo: 'matriculas' }] },
    { id: 's1', tipo: 'secao', titulo: 'Síntese', regra: { condicoes: [{ campo: 'gini', op: 'maior', valor: 0.5 }] },
      blocos: [{ id: 'p2', tipo: 'paragrafo', regra: null, conteudo: [{ t: 'texto', v: 'Dentro' }] }] },
    { id: 'g1', tipo: 'grafico', regra: null, grafico: 'grafico_pib' },
    { id: 'l1', tipo: 'lista', regra: null, itens: [[{ t: 'texto', v: 'IBGE' }]] },
  ] },
};

const nada = () => {};
const casos = {
  Login: <Login aoEntrar={nada} erro="" carregando={false} />,
  'Login com erro': <Login aoEntrar={nada} erro="Senha incorreta." carregando={false} />,
  SeletorDeTema: <SeletorDeTema carregando={false} aoEscolher={nada} temas={[
    { slug: 'educacao', nome: 'Educação', cor: '#FFD65A', fonte_editorial: 'docs', contrato: { versao: 3, publicado_por: 'Rayane' } },
    { slug: 'saude', nome: 'Saúde', cor: '#E5333F', fonte_editorial: 'painel', contrato: null },
  ]} />,
  ArvoreDeBlocos: <ArvoreDeBlocos contrato={contrato} selecionado="p1" aoSelecionar={nada} aoMover={nada} aoRemover={nada} aoAdicionar={nada} aoAdicionarFilho={nada} />,
  'EditorDeBloco (parágrafo)': <EditorDeBloco bloco={contrato.corpo.blocos[0]} aoMudar={nada} manifesto={manifesto} campos={campos} graficos={graficos} rotuloDe={(c) => c} registrarEditor={nada} />,
  'EditorDeBloco (seção com regra)': <EditorDeBloco bloco={contrato.corpo.blocos[1]} aoMudar={nada} manifesto={manifesto} campos={campos} graficos={graficos} rotuloDe={(c) => c} registrarEditor={nada} />,
  'EditorDeBloco (gráfico)': <EditorDeBloco bloco={contrato.corpo.blocos[2]} aoMudar={nada} manifesto={manifesto} campos={campos} graficos={graficos} rotuloDe={(c) => c} registrarEditor={nada} />,
  'EditorDeBloco (lista)': <EditorDeBloco bloco={contrato.corpo.blocos[3]} aoMudar={nada} manifesto={manifesto} campos={campos} graficos={graficos} rotuloDe={(c) => c} registrarEditor={nada} />,
  'EditorDeBloco (nada selecionado)': <EditorDeBloco bloco={null} aoMudar={nada} manifesto={manifesto} campos={campos} graficos={graficos} rotuloDe={(c) => c} registrarEditor={nada} />,
  'Regra entre-campos': <ConstrutorDeRegra manifesto={manifesto} campos={campos} aoMudar={nada}
    regra={{ condicoes: [{ campo: 'matriculas', op: 'maior', valor: { campo: 'gini' } }], sem_dado: { acao: 'texto_alternativo', texto: 'Sem dados.' } }} />,
  'Regra faixa': <ConstrutorDeRegra manifesto={manifesto} campos={campos} aoMudar={nada}
    regra={{ condicoes: [{ campo: 'gini', op: 'entre', valor: [0, 1] }] }} />,
  'Regra vazia': <ConstrutorDeRegra manifesto={manifesto} campos={campos} aoMudar={nada} regra={null} />,
  PaletaDeVariaveis: <PaletaDeVariaveis campos={campos} graficos={graficos} origem="cache" aviso="Banco fora" usados={new Set(['matriculas'])} aoInserir={nada} aoInserirGrafico={nada} />,
  SpriteDeIcones: <SpriteDeIcones />,
  Guia: <Guia aoFechar={nada} totalDeCidades={2074} />,
  'Guia sem a lista carregada': <Guia aoFechar={nada} totalDeCidades={0} />,
  // O guia só monta a seção aberta: sem isto, um erro da sétima seção em
  // diante só apareceria para quem clicasse nela.
  ...Object.fromEntries(
    montarSecoes(2074).map((s) => [`Guia § ${s.titulo}`, <div>{s.corpo}</div>])
  ),
  Previa: <Previa cidades={['Campina Grande (PB)']} cidade="Campina Grande (PB)" aoTrocarCidade={nada} aoGerar={nada} carregando={false} erro=""
    resultado={{ html: '<p>oi</p>', aviso: 'Sem banco', campos_nao_resolvidos: ['x', 'y'] }} />,
};

let falhas = 0;
for (const [nome, elemento] of Object.entries(casos)) {
  try {
    const html = renderToString(elemento);
    console.log(`  ✓  ${nome.padEnd(34)} ${String(html.length).padStart(6)} chars`);
  } catch (erro) {
    falhas += 1;
    console.log(`  ✗  ${nome}: ${erro.message}`);
  }
}
process.exit(falhas ? 1 : 0);
