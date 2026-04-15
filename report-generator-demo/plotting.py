import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

df = pd.read_csv('demografia.csv', delimiter=";")
campina = df[df['nm_mun'] == 'Campina Grande (PB)']

y = np.array([campina['pop_mulher'].sum(), campina['pop_homem'].sum()])
mylabels = ["Mulher", "Homem"]

plt.pie(y, labels=mylabels)
plt.show()
