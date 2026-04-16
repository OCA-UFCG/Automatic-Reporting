import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

df = pd.read_csv('demografia.csv', delimiter=";")
campina = df[df['nm_mun'] == 'Campina Grande (PB)']


y = np.array([campina['pop_mulher'].sum(), campina['pop_homem'].sum()])
mylabels = ["Mulher", "Homem"]

chart_file = output_dir / f"grafico_sexo_{safe_city}.png"

plt.pie(y, labels=mylabels)
plt.show()
