#!/bin/bash
awk -F',' '
   BEGIN {
       OFS=";"
   }
   NR > 1 {
       id_ibge = $1
       nm_mun = $2
       uf = $3
       gsub(/\r/, "", id_ibge)
       gsub(/\r/, "", nm_mun)
       gsub(/\r/, "", uf)
       gsub(/\x27/, "\x27\x27", nm_mun)
       printf "INSERT INTO charts (id_ibge, nm_mun, uf) VALUES (%s, \x27%s\x27, \x27%s\x27);\n", id_ibge, nm_mun, uf
   }' id_ibge_completo.csv > insert_municipios.sq
