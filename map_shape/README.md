# Malhas cartograficas

Os arquivos de malha do IBGE nao ficam versionados porque o shapefile de municipios excede o limite de 100 MB do GitHub.

Para gerar os mapas do relatorio, baixe as malhas municipais e de UFs do IBGE, versao 2025, e mantenha esta estrutura:

```text
map_shape/
  BR_Municipios_2025/
    BR_Municipios_2025.shp
    BR_Municipios_2025.shx
    BR_Municipios_2025.dbf
    BR_Municipios_2025.prj
    BR_Municipios_2025.cpg
  BR_UF_2025/
    BR_UF_2025.shp
    BR_UF_2025.shx
    BR_UF_2025.dbf
    BR_UF_2025.prj
    BR_UF_2025.cpg
```

Fonte: IBGE, Malha Municipal Digital.
