import matplotlib.pyplot as plt
import pathlib

def gerar_grafico_sexo(cidade, OUTPUT_DIR: pathlib.PosixPath, safe_city: str):
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
