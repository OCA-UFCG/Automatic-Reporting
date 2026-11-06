// O relatório de estado (services/relatorio_estado.py, 05/11/2026) manda
// cover.unidade = 'estado'; o municipal não manda nada e segue com o rótulo de sempre.
export function rotuloDaUnidade(cover) {
  return cover?.unidade === 'estado'
    ? 'Dados estaduais reunidos em uma única plataforma'
    : 'Dados municipais reunidos em uma única plataforma';
}
