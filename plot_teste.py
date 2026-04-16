from pathlib import Path
import matplotlib.pyplot as plt

def gerar_grafico_sexo(linha: dict, output_dir: Path, safe_city: str) -> str:
    mulheres = linha["pop_mulher"]
    homens = linha["pop_homem"]

    labels = ["Mulheres", "Homens"]
    valores = [mulheres, homens]

    chart_file = output_dir / f"grafico_sexo_{safe_city}.png"

    plt.figure(figsize=(8, 5))
    plt.bar(labels, valores)
    plt.title(f"População por sexo - {linha['nm_mun']}")
    plt.ylabel("Número de habitantes")
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150)
    plt.close()

    return chart_file.name