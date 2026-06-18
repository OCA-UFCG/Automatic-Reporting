#Namespaces
- docs_cache: Armazenará o texto dos relatórios do Google Docs. Nova regra: Ao invés de um TTL cego de 1 hora gerido manualmente, usaremos o diskcache com suporte a revalidação condicional (ETag), guardando o texto e a assinatura da última versão.
- geo_cache: Armazenará coordenadas e limites das cidades. Nova regra: Terá persistência em disco via diskcache, mas agora com um limite máximo de tamanho/itens (LRU) e um TTL longo (ex: 30 dias) para evitar que o arquivo cresça infinitamente com dados velhos.
- csv_cache: Armazenará os DataFrames Pandas processados. Nova regra: A chave de acesso não será apenas o nome do macrotema, mas sim um Hash baseado no caminho do arquivo e sua data de modificação (mtime). Assim, se o CSV for alterado no disco, o cache invalida automaticamente
