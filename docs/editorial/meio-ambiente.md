Esqueleto de condições editoriais para o macrotema Meio Ambiente, seguindo o mesmo mecanismo usado em `demografia.md` (ver `utils/render/placeholders.py::interpretar_blocos_condicionais`). O campo `$n_uc` vem da view `relatorios_auto.vw_perfil_ambiente_municipal` (coluna `n_uc`, bigint) — registrada em `VIEW_POR_MACROTEMA` (`utils/queries/perfil_municipal.py`). O namespace `meio-ambiente` (alias `ambiente`) já está registrado em `_ALIASES_NAMESPACE`.

**Para meio-ambiente.$n\_uc for igual a 0:**

O município não possui Unidades de Conservação (UC) em seu território. [texto de apoio/contexto]

**Para meio-ambiente.$n\_uc for igual a 1:**

O município possui 1 Unidade de Conservação (UC) em seu território. [texto no singular]

**Para meio-ambiente.$n\_uc maior que 1:**

O município possui meio-ambiente.$n\_uc Unidades de Conservação (UC) em seu território. [texto no plural]

---

Observações:

- Cada bloco `Para ... :` controla apenas o(s) parágrafo(s) imediatamente seguintes, até o próximo bloco `Para ...:` (ou até uma linha `Sequência do texto, sem condição:`/`Síntese`). A própria linha do bloco nunca aparece no relatório final.
- Operadores suportados: `igual a 0`, `igual a 1`, `maior que 1`, `diferente de 0`.
- `n_uc` nunca vem `NULL` na view (checado em produção: 0 municípios com `NULL`, sempre um número de 0 a N) — diferente de `demografia.$centro_pop`, que pode ser `NULL` quando não há dado. Mesmo assim, o parser exige que o valor não seja `None` para casar com `igual a 0` sempre que a condição referenciar um único campo — proteção genérica contra esse tipo de ambiguidade, útil caso outro campo do macrotema (não `n_uc`) venha a ter dado ausente.
- Para condições com mais de um campo (ex.: `$campo_a for igual a 0 e $campo_b for diferente de 0`), veja os exemplos em `demografia.md`.
