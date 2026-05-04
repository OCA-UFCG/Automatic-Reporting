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

    bars = ax.barh(mylabels, valores, color=cores, height=0.6)

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

def gerar_grafico_porte(df, OUTPUT_DIR: pathlib.Path, safe_city: str):
    df = df.copy()
    df['pop_total'] = df['pop_total'].astype(str).str.replace('.', '').astype(int)
    porte_counts = df.groupby('porte')['pop_total'].sum()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / "grafico_porte_{safe_city}.png"
    
    plt.figure(figsize=(8, 6))
    plt.pie(porte_counts, labels=porte_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title("População por porte do município (todos os municípios)")
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150)
    plt.close()
    return chart_file.name


def gerar_grafico_top_cidades(df, OUTPUT_DIR: pathlib.Path):
    df = df.copy()
    df['pop_total'] = df['pop_total'].astype(str).str.replace('.', '').astype(int)
    top_10 = df.nlargest(10, 'pop_total')[['nm_mun', 'pop_total']]
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / "grafico_top_cidades.png"
    
    plt.figure(figsize=(10, 6))
    plt.barh(top_10['nm_mun'], top_10['pop_total'])
    plt.xlabel("População total")
    plt.title("Top 10 municípios por população")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150)
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

    bars_m = ax.barh(age_groups, [-m for m in mulheres], color=cor_m, edgecolor=borda_m, height=0.85)
    bars_h = ax.barh(age_groups, homens, color=cor_h, edgecolor=borda_h, height=0.85)

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
