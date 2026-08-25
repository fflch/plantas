#!/bin/bash

# 1. Garante que a pasta de destino exista
mkdir -p svg

# 2. Busca todos os PDFs dentro de 'originais/' e subpastas (A0, A1, etc.)
find originais -type f -name "*.pdf" | while read -r pdf; do
    # Extrai o caminho relativo sem o trecho "originais/"
    rel_path="${pdf#originais/}"
    
    # Define o diretório de destino na pasta 'svg'
    target_dir="svg/$(dirname "$rel_path")"
    mkdir -p "$target_dir"
    
    # Define o nome do arquivo final substituindo .pdf por .svg
    target_svg="svg/${rel_path%.pdf}.svg"
    
    echo "Convertendo e recortando: $pdf -> $target_svg"
    
    # Executa o Inkscape convertendo para SVG e ajustando o recorte da página
    inkscape --export-area-drawing --export-margin=10 --export-filename="$target_svg" "$pdf"
done

echo "Conversão concluída!"