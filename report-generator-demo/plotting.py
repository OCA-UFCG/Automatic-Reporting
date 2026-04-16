import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def gerar_grafico_sexo(cidade: pandas.DataFrame, OUTPUT_DIR: pathlib.PosixPath, safe_city: str):
    mulheres = linha["pop_mulher"]
    homens = linha["pop_homem"]
    mylabels = ["Mulheres", "Homens"]
    valores = [mulheres, homens]

    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"grafico_sexo_{safe_city}.png"

    plt.figure(figsize=(8, 5))
    plt.bar(valores, labels=mylabels)
    plt.title(f"População por sexo - {linha['nm_mun']}")
    plt.ylabel("Número de habitantes")
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150)
    plt.close()

    return chart_file.name
