// A capa só ganha página própria quando tem o que mostrar abaixo do título:
// Apresentação, Características Gerais, cards de métricas ou mapa. O relatório de
// estado (services/relatorio_estado.py) não tem nenhum deles por enquanto, e a capa
// saía como uma página só com o título. O modelo da equipe editorial (11/11/2026)
// começa o tema logo abaixo do título.
//
// Decide pelo conteúdo, e não por `unidade === 'estado'`: quando o Doc estadual
// trouxer o bloco resumo_cidade, a capa volta a ter página própria sozinha. As
// condições espelham o que Cover.jsx renderiza em ".cover-content"; se uma seção
// nova entrar lá, ela precisa entrar aqui também.
//
// Ex.: capaTemConteudo({ unidade: 'estado', metricas: [] }, false) === false
export function capaTemConteudo(cover, temMapasDoTema) {
  const temItens = lista => Array.isArray(lista) && lista.length > 0;
  // O título "Características Gerais" aparece sempre no municipal (Cover.jsx).
  const mostraCaracteristicas = cover.unidade !== 'estado' || temItens(cover.resumo_cidade_html);

  return (
    temItens(cover.relatorio_geral_html)
    || mostraCaracteristicas
    || temItens(cover.metricas)
    || Boolean(cover.mapa_principal)
    || temMapasDoTema
  );
}
