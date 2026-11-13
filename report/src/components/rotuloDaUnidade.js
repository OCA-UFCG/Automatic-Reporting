// O relatório de estado e o de área (services/relatorio_estado.py, 05/11 e 12/11/2026)
// mandam cover.unidade; o municipal não manda nada e segue com o rótulo de sempre.
const ROTULO_POR_UNIDADE = {
  estado: 'Dados estaduais reunidos em uma única plataforma',
  area: 'Dados das áreas de interesse reunidos em uma única plataforma',
};

export function rotuloDaUnidade(cover) {
  return ROTULO_POR_UNIDADE[cover?.unidade] ?? 'Dados municipais reunidos em uma única plataforma';
}

// Cartão "Monte seu relatório" no fim do PDF (D15/G6, 13/11/2026): o relatório de
// estado dizia "Escolha o município", o que não descreve o relatório que a pessoa
// tem nas mãos.
const ESCOLHA_POR_UNIDADE = {
  estado: 'Escolha o estado e gere um relatório como este.',
  area: 'Escolha a área de interesse e gere um relatório como este.',
};

export function escolhaDaUnidade(cover) {
  return ESCOLHA_POR_UNIDADE[cover?.unidade] ?? 'Escolha o município e gere um relatório como este.';
}
