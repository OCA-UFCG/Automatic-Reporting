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

## Baixar de uma GitHub Release

Crie uma release no GitHub do repositorio, anexe um `.zip` com as pastas `BR_Municipios_2025/` e `BR_UF_2025/`, e rode:

```bash
python scripts/download_map_shapes.py --url "https://github.com/OCA-UFCG/Automatic-Reporting/releases/tag/map-shapes-2025"
```

Se a release tiver mais de um asset, informe o nome do arquivo:

```bash
python scripts/download_map_shapes.py \
  --url "https://github.com/OCA-UFCG/Automatic-Reporting/releases/tag/map-shapes-2025" \
  --asset-name "map-shapes-2025.zip"
```

Tambem funciona com URL direta para o `.zip`:

```bash
python scripts/download_map_shapes.py --url "https://github.com/OCA-UFCG/Automatic-Reporting/releases/download/map-shapes-2025/map-shapes-2025.zip"
```
