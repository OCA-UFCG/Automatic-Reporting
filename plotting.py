import matplotlib.pyplot as plt
import pathlib

def gerar_grafico_sexo(cidade, OUTPUT_DIR: pathlib.Path, safe_city: str):
    mulheres = cidade["pop_mulher"]
    homens = cidade["pop_homem"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_sexo_{safe_city}.png"
    
    mylabels = ["Homem", "Mulher"]
    valores = [homens, mulheres]
    cores = ['#8fad35', '#c23b61']

    fig, ax = plt.subplots(figsize=(8, 3), facecolor='white')
    ax.set_facecolor('white')

    ax.barh(mylabels, valores, color=cores, height=0.6)

    max_val = max(valores)
    for i, v in enumerate(valores):
        txt = f'{v:,.0f}'.replace(',', '.')
        ax.text(v + (max_val * 0.02), i, txt, va='center', fontsize=12, color='#333')

    ax.set_xlim(0, max_val * 1.3)
    ax.set_xticks([]) 
    ax.tick_params(axis='y', left=False, labelsize=12)
    
    for spine in ax.spines.values():
        spine.set_visible(False)

    
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_file.name

def gerar_grafico_populacao_etaria_sexo(cidade, OUTPUT_DIR: pathlib.Path, safe_city: str):
    age_groups = [
        "0 a 9 anos", "10 a 19 anos", "20 a 29 anos", "30 a 39 anos",
        "40 a 49 anos", "50 a 59 anos", "60 a 69 anos", "70 a 79 anos", "80+ anos"
    ]
    
    mulheres = []
    homens = []
    for i in range(1, 10):
        mulheres.append(int(str(cidade[f"faixa{i}_mulher"]).replace('.', '')))
        homens.append(int(str(cidade[f"faixa{i}_homem"]).replace('.', '')))
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_populacao_etaria_sexo_{safe_city}.png"
    
    fig, ax = plt.subplots(figsize=(6, 5))
    
    cor_m, borda_m = '#c23b61', '#c23b61'
    cor_h, borda_h = '#8fad35', '#8fad35'

    ax.barh(age_groups, [-m for m in mulheres], color=cor_m, edgecolor=borda_m, height=0.85)
    ax.barh(age_groups, homens, color=cor_h, edgecolor=borda_h, height=0.85)

    max_val = max(max(mulheres), max(homens))
    limiar = max_val * 0.28

    for i, (m, h) in enumerate(zip(mulheres, homens)):
        m_txt = f'{m:,.0f}'.replace(',', '.')
        h_txt = f'{h:,.0f}'.replace(',', '.')
        
        if m > limiar:
            ax.text(-m / 2, i, m_txt, ha='center', va='center', 
                    fontsize=10, color='black', fontweight='normal')
        else:
            ax.text(-m - (max_val * 0.02), i, m_txt, ha='right', va='center', 
                    fontsize=10, color='#333333')

        if h > limiar:
            ax.text(h / 2, i, h_txt, ha='center', va='center', 
                    fontsize=10, color='black', fontweight='normal')
        else:
            ax.text(h + (max_val * 0.02), i, h_txt, ha='left', va='center', 
                    fontsize=10, color='#333333')
    
    
    ax.set_xlim(-max_val * 1.20, max_val * 1.20)
    
    ax.set_xticks([]) 
    ax.tick_params(axis='y', left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.05)

    plt.tight_layout()
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_file.name

def gerar_grafico_serie_temporal_mortalidade_infantil(cidade, OUTPUT_DIR, safe_city):
    anos = ["2010", "2020", "2021", "2022", "2023", "2024"]
    taxas = [float(cidade[str(ano)]) for ano in anos]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_mortalidade_infantil_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor('#f2f2f2')
    ax.set_facecolor('white')

    cor_barra = '#A51C24'
    barras = ax.bar(anos, taxas, color=cor_barra, width=0.7)

    for barra in barras:
        altura = barra.get_height()
        ax.text(
            barra.get_x() + barra.get_width() / 2, 
            altura - 1.5,           
            f'{altura:.2f}',        
            ha='center',
            va='center',
            color='white', 
            fontweight='bold', 
            fontsize=10
        )

    ax.set_yticks([0, 10, 20]) 
    ax.yaxis.grid(True, linestyle=':', color='#d3d3d3', linewidth=1.5)
    ax.set_axisbelow(True)      

    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)

    ax.tick_params(axis='both', which='both', length=0, labelsize=11)

    plt.title(
        'Série temporal da taxa de mortalidade infantil', 
        loc='left', 
        fontweight='bold', 
        fontsize=14, 
        pad=20
    )

    plt.tight_layout()
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_file.name

def gerar_grafico_estabelecimento_saude(cidade, OUTPUT_DIR, safe_city):
    anos = ["2010", "2020", "2021", "2022", "2023", "2024"]
    taxas = [int(cidade[str(ano)]) for ano in anos]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_estabelecimento_saude_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor('#f2f2f2')
    ax.set_facecolor('white')

    cor_barra = '#FC6B7B'
    barras = ax.bar(anos, taxas, color=cor_barra, width=0.7)

    offset_dinamico = max(taxas) * 0.05 if taxas else 10 

    for barra in barras:
        altura = barra.get_height()
        ax.text(
            barra.get_x() + barra.get_width() / 2, 
            altura + offset_dinamico,            
            f'{int(altura)}',
            ha='center',
            va='bottom',
            color='#444444',
            fontsize=11
        )

    ax.set_yticks([0, 500, 1000])
    
    ax.yaxis.grid(True, linestyle=':', color='#d3d3d3', linewidth=1.5)
    ax.set_axisbelow(True)      

    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)

    ax.tick_params(axis='both', which='both', length=0, labelsize=11, colors='#555555')

    ax.set_xlabel('Ano', fontsize=11, color='#555555', labelpad=10)

    plt.title(
        'Visão temporal do n° de tipo de estabelecimento de saúde', 
        loc='left', 
        fontweight='bold', 
        fontsize=14, 
        pad=20
    )

    plt.tight_layout()
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_file.name
