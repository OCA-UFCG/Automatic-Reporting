import matplotlib.pyplot as plt
import pathlib

def gerar_grafico_sexo(cidade, OUTPUT_DIR: pathlib.Path, safe_city: str):
    mulheres = int(str(cidade["pop_mulher"]).replace('.', ''))
    homens = int(str(cidade["pop_homem"]).replace('.', ''))
    
    mylabels = ["Mulheres", "Homens"]
    valores = [mulheres, homens]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_sexo_{safe_city}.png"

    plt.figure(figsize=(8, 5))
    plt.bar(mylabels, valores)
    
    nome_municipio = cidade['nm_mun']
    plt.title(f"População por sexo - {nome_municipio}")
    
    plt.ylabel("Número de habitantes")
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150)
    plt.close()

    return chart_file.name


def gerar_grafico_porte(df, OUTPUT_DIR: pathlib.Path, safe_city: str):
    df = df.copy()
    df['pop_total'] = df['pop_total'].astype(str).str.replace('.', '').astype(int)
    porte_counts = df.groupby('porte')['pop_total'].sum()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_porte_{safe_city}.png"
    
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
