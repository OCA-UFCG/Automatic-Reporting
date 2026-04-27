# Sistema de Configuração Centralizado

## Visão Geral

A aplicação usa **UMA ÚNICA URL** apontando para um documento Google Docs central que armazena **TODAS** as configurações em formato `CHAVE=VALOR`.

Não há URLs hardcoded, não há múltiplos .env files. Tudo vem do documento central.

## Como Funciona

### 1. **Única URL de Configuração**

Edite `.env` ou `main.py` para definir:

```env
CONFIG_DOC_ID=12o-W-VtSl9ytbF6CD9S14ACJL63XsmYJnmZValPqKKA
```

Ou no código:
```python
CONFIG_DOC_ID = os.getenv("CONFIG_DOC_ID", "12o-W-VtSl9ytbF6CD9S14ACJL63XsmYJnmZValPqKKA")
```

### 2. **Documento Central (Google Docs)**

O documento deve estar **publicamente acessível** (Qualquer pessoa com o link - Leitor) e ter o seguinte formato:

```
DEMOGRAFIA_CSV_URL=https://drive.google.com/file/d/1zH6Yri2EdchUUjoTDtXgdHrmo6SVBfBG/view
DEFAULT_DOCS_URL=https://docs.google.com/document/d/1WA3LcQAWIKFYu6MmuF4RSrGFSdYvbpnn/edit?userstoinvite=lucianna.mrf@gmail.com&sharingaction=manageaccess&role=writer

EDUCACAO_CSV_URL=https://drive.google.com/file/d/SEU_ID_AQUI/view
EDUCACAO_DOCS_URL=https://docs.google.com/document/d/SEU_ID_AQUI/edit

# Comentários começam com #
# Linhas em branco são ignoradas
```

### 3. **Inicialização da Aplicação**

Na inicialização:
1. ✓ Conecta ao documento central (Google Docs export URL)
2. ✓ Lê o conteúdo em plain text
3. ✓ Parse cada linha `CHAVE=VALOR`
4. ✓ Armazena em memória no dicionário `CONFIG`
5. ✗ Se falhar aqui, a aplicação não inicia (erro crítico)

### 4. **Uso Durante Execução**

Toda a aplicação acessa `CONFIG["CHAVE"]`:

```python
# Ao gerar relatório
csv_url = CONFIG["DEMOGRAFIA_CSV_URL"]
docs_url = CONFIG["DEFAULT_DOCS_URL"]

# Se a chave não existir, erro 503 Service Unavailable
```

## APIs

### `GET /config`

Retorna a configuração carregada (para debug):

```json
{
  "config_doc_url": "https://docs.google.com/document/d/12o-W-VtSl9ytbF6CD9S14ACJL63XsmYJnmZValPqKKA/export?format=txt",
  "config_loaded": true,
  "config_keys": ["DEMOGRAFIA_CSV_URL", "DEFAULT_DOCS_URL"],
  "config_values": {
    "DEMOGRAFIA_CSV_URL": "https://drive.google.com/...",
    "DEFAULT_DOCS_URL": "https://docs.google.com/..."
  }
}
```

## Troubleshooting

### "ERRO CRÍTICO: Não foi possível carregar a configuração central"

Verifique:
1. **Documento público?** Acesse o link direto no navegador. Deve estar acessível sem login.
2. **Formato correto?** Cada linha: `CHAVE=VALOR`
3. **Internet?** Teste: `curl -I https://docs.google.com/document/d/SEU_ID/export?format=txt`
4. **Timeout?** O Google Docs pode ser lento. Timeout está em 20s.

### "Configuração XXX_URL não encontrada"

A chave não existe no documento central. Adicione ao Google Docs:

```
MINHA_CHAVE=https://exemplo.com/meu-arquivo.csv
```

## Exemplo Completo

**Documento Google Docs (URL: `https://docs.google.com/document/d/12o-W-VtSl9ytbF6CD9S14ACJL63XsmYJnmZValPqKKA`)**

```
# Configurações de Demografia
DEMOGRAFIA_CSV_URL=https://drive.google.com/file/d/1zH6Yri2EdchUUjoTDtXgdHrmo6SVBfBG/view
DEFAULT_DOCS_URL=https://docs.google.com/document/d/1WA3LcQAWIKFYu6MmuF4RSrGFSdYvbpnn/edit

# Futuras configurações
EDUCACAO_CSV_URL=https://drive.google.com/file/d/ABC123/view
EDUCACAO_DOCS_URL=https://docs.google.com/document/d/DEF456/edit
```

**Código Python:**

```python
# Carrega tudo na inicialização
CONFIG = carregar_config_central()

# Usa em qualquer lugar
csv_url = CONFIG["DEMOGRAFIA_CSV_URL"]
docs_url = CONFIG["DEFAULT_DOCS_URL"]
```

## Benefícios

✓ **Única fonte de verdade** - Um documento, todas as configs  
✓ **Sem deploy** - Muda URL no Google Docs, aplicação já usa  
✓ **Escalável** - Novos macrotemas? Apenas adicione linhas ao documento  
✓ **Seguro** - Futuramente, pode ser um secret no GitHub Actions  
✓ **Sem hardcoding** - Nenhuma URL no código ou .env
