// O relatório de estado e o de área (services/relatorio_estado.py, 05/11 e 12/11/2026)
// mandam cover.unidade; o municipal não manda nada e segue com o rótulo de sempre.
const ROTULO_POR_UNIDADE = {
  estado: 'Dados estaduais reunidos em uma única plataforma',
  area: 'Dados das áreas de interesse reunidos em uma única plataforma',
};

export function rotuloDaUnidade(cover) {
  return ROTULO_POR_UNIDADE[cover?.unidade] ?? 'Dados municipais reunidos em uma única plataforma';
}
