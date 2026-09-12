// Manipulação da árvore do contrato. Tudo aqui é função pura sobre uma cópia:
// os contratos são pequenos (dezenas de blocos), então clonar inteiro a cada
// edição é mais barato do que qualquer bug de mutação compartilhada.

export const SLOTS_MOLDURA = [
  { chave: 'resumo_tema', nome: 'Resumo do tema', ajuda: 'Uma frase, aparece no topo da seção.' },
  { chave: 'resumo_cidade', nome: 'Resumo da cidade', ajuda: 'Vai para a capa do relatório.' },
  { chave: 'diagnostico_cidade', nome: 'Diagnóstico da cidade', ajuda: 'Vai para a capa do relatório.' },
  { chave: 'relatorio_geral', nome: 'Apresentação', ajuda: 'Abre o relatório completo.' },
  { chave: 'fontes', nome: 'Fontes e conteúdos', ajuda: 'A caixa que fecha a seção do tema.' },
];

export const TIPOS_CRIAVEIS = [
  { tipo: 'paragrafo', nome: 'Parágrafo', icone: '¶' },
  { tipo: 'secao', nome: 'Seção', icone: '§' },
  { tipo: 'lista', nome: 'Lista', icone: '•' },
  { tipo: 'grafico', nome: 'Gráfico', icone: '▦' },
  { tipo: 'legenda', nome: 'Legenda de figura', icone: '⌯' },
  { tipo: 'caixa', nome: 'Caixa destacada', icone: '▤' },
  { tipo: 'nota', nome: 'Nota', icone: '✎' },
];

const TEM_FILHOS = new Set(['secao', 'caixa']);
const TEM_CONTEUDO = new Set(['paragrafo', 'legenda', 'nota']);

export const temFilhos = (bloco) => TEM_FILHOS.has(bloco?.tipo);
export const temConteudo = (bloco) => TEM_CONTEUDO.has(bloco?.tipo);

export function clonar(valor) {
  return JSON.parse(JSON.stringify(valor));
}

function todasAsListas(contrato) {
  const listas = [];
  const visitar = (blocos) => {
    listas.push(blocos);
    blocos.forEach((bloco) => {
      if (Array.isArray(bloco.blocos)) visitar(bloco.blocos);
    });
  };
  SLOTS_MOLDURA.forEach(({ chave }) => {
    const slot = contrato.moldura?.[chave];
    if (slot?.blocos) visitar(slot.blocos);
  });
  if (contrato.corpo?.blocos) visitar(contrato.corpo.blocos);
  return listas;
}

export function todosOsBlocos(contrato) {
  return todasAsListas(contrato).flat();
}

export function novoId(contrato, tipo) {
  const usados = new Set(todosOsBlocos(contrato).map((b) => b.id));
  const prefixo = tipo.slice(0, 3);
  let n = usados.size + 1;
  while (usados.has(`${prefixo}-${n}`)) n += 1;
  return `${prefixo}-${n}`;
}

export function blocoVazio(contrato, tipo) {
  const base = { id: novoId(contrato, tipo), tipo, regra: null };
  if (TEM_FILHOS.has(tipo)) return { ...base, titulo: '', blocos: [] };
  if (tipo === 'lista') return { ...base, itens: [[{ t: 'texto', v: '' }]] };
  if (tipo === 'grafico') return { ...base, grafico: '' };
  return { ...base, conteudo: [{ t: 'texto', v: '' }] };
}

function localizar(contrato, id) {
  for (const lista of todasAsListas(contrato)) {
    const indice = lista.findIndex((bloco) => bloco.id === id);
    if (indice >= 0) return { lista, indice };
  }
  return null;
}

export function encontrarBloco(contrato, id) {
  const local = localizar(contrato, id);
  return local ? local.lista[local.indice] : null;
}

export function atualizarBloco(contrato, id, mudancas) {
  const copia = clonar(contrato);
  const local = localizar(copia, id);
  if (!local) return contrato;
  local.lista[local.indice] = { ...local.lista[local.indice], ...mudancas };
  return copia;
}

export function removerBloco(contrato, id) {
  const copia = clonar(contrato);
  const local = localizar(copia, id);
  if (!local) return contrato;
  local.lista.splice(local.indice, 1);
  return copia;
}

export function moverBloco(contrato, id, passo) {
  const copia = clonar(contrato);
  const local = localizar(copia, id);
  if (!local) return contrato;
  const destino = local.indice + passo;
  // Mover só reordena entre irmãos: tirar um bloco de dentro de uma seção por
  // engano, só apertando a seta, seria fácil demais.
  if (destino < 0 || destino >= local.lista.length) return contrato;
  const [bloco] = local.lista.splice(local.indice, 1);
  local.lista.splice(destino, 0, bloco);
  return copia;
}

export function inserirBloco(contrato, { slot, paiId, depoisDe }, bloco) {
  const copia = clonar(contrato);
  let lista;
  if (paiId) {
    const pai = localizar(copia, paiId);
    if (!pai) return contrato;
    const alvo = pai.lista[pai.indice];
    alvo.blocos = alvo.blocos || [];
    lista = alvo.blocos;
  } else if (slot === 'corpo') {
    lista = copia.corpo.blocos;
  } else {
    copia.moldura[slot] = copia.moldura[slot] || { blocos: [] };
    lista = copia.moldura[slot].blocos;
  }

  const indice = depoisDe ? lista.findIndex((b) => b.id === depoisDe) + 1 : lista.length;
  lista.splice(indice >= 0 ? indice : lista.length, 0, bloco);
  return copia;
}

// -- conteúdo em linha ----------------------------------------------------

export function trechosParaTextoVisivel(conteudo = []) {
  return conteudo
    .map((trecho) => (trecho.t === 'texto' ? trecho.v : `«${trecho.campo}»`))
    .join('');
}

export function resumoDoBloco(bloco) {
  if (temFilhos(bloco)) return bloco.titulo || '(sem título)';
  if (bloco.tipo === 'grafico') return bloco.grafico || '(gráfico não escolhido)';
  if (bloco.tipo === 'lista') {
    const primeiro = trechosParaTextoVisivel(bloco.itens?.[0] || []);
    const n = bloco.itens?.length || 0;
    return primeiro ? `${primeiro}${n > 1 ? ` (+${n - 1})` : ''}` : '(lista vazia)';
  }
  return trechosParaTextoVisivel(bloco.conteudo) || '(vazio)';
}

export function contarRegras(contrato) {
  return todosOsBlocos(contrato).filter((bloco) => bloco.regra).length;
}

export function camposUsados(contrato) {
  const campos = new Set();
  const daLista = (conteudo = []) =>
    conteudo.forEach((t) => {
      if (t.t === 'var') campos.add(t.campo.split('.').pop());
    });
  todosOsBlocos(contrato).forEach((bloco) => {
    daLista(bloco.conteudo);
    (bloco.itens || []).forEach(daLista);
    (bloco.regra?.condicoes || []).forEach((c) => {
      campos.add(c.campo.split('.').pop());
      if (c.valor && typeof c.valor === 'object' && c.valor.campo) {
        campos.add(c.valor.campo.split('.').pop());
      }
    });
  });
  return campos;
}
