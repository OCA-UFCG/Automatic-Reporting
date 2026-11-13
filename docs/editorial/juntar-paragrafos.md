# Juntar dois parágrafos com condições diferentes

Cada parágrafo do Doc vira um parágrafo no relatório. Para o parágrafo seguinte
continuar o de cima, escreva `[junta com o próximo]` no fim do parágrafo **de cima**:

```
Para quando economia.$saldo_tri_atual for diferente de 0:
No segundo trimestre (...) O saldo foi de economia.$saldo_tri_atual. [junta com o próximo]

Para quando economia.$saldo_tri_atual for igual a 0 e (...):
No segundo trimestre (...) O saldo foi, portanto, nulo. [junta com o próximo]

No trimestre anterior (...), o saldo havia sido de economia.$saldo_tri_anterior.
```

Regras:

- **Marque todas as versões** do parágrafo de cima. A marca não aparece no relatório.
- Se nenhuma versão marcada sair, o parágrafo de baixo sai sozinho (não gruda no que
  veio antes).
- Só junta com o parágrafo **logo abaixo**. Se o de baixo não sair, o seguinte fica
  separado. Gráfico, título, legenda ou item de lista no meio também impedem a junção.
- Para juntar três, marque o primeiro e o segundo.
- Um parágrafo sem a marca se comporta como antes.

Código: `_MARCADOR_JUNTA` em `utils/render/placeholders.py`; testes em
`tests/test_junta_paragrafos.py`.
