import sys
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
import subprocess
import os
from pathlib import Path

def crop_svg_by_content(input_svg_path, output_svg_path, margin=10):
    # 1. Renderiza uma imagem temporária em PNG para achar a borda visual real
    png_temp = output_svg_path + ".temp.png"
    
    # Cria os diretórios pai caso não existam
    os.makedirs(os.path.dirname(output_svg_path), exist_ok=True)

    subprocess.run([
        "inkscape", "--export-type=png",
        "--export-filename=" + png_temp,
        input_svg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(png_temp):
        print(f"Erro ao analisar: {input_svg_path}")
        return

    # 2. Carrega a imagem e encontra os limites dos pixels desenhados
    img = Image.open(png_temp).convert("RGBA")
    arr = np.array(img)
    
    # Considera conteúdo tudo que não for transparente nem totalmente branco
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]
    non_white = (rgb < 250).any(axis=2) & (alpha > 10)

    coords = np.argwhere(non_white)
    if coords.size == 0:
        os.remove(png_temp)
        print(f"Nenhum conteúdo detectado em: {input_svg_path}")
        return

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)

    img_h, img_w = arr.shape[:2]
    os.remove(png_temp)

    # 3. Mapeia a proporção da imagem PNG para o viewBox original do SVG
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    tree = ET.parse(input_svg_path)
    root = tree.getroot()

    viewbox = root.get('viewBox')
    if viewbox:
        vx, vy, vw, vh = map(float, viewbox.split())
    else:
        vx, vy = 0.0, 0.0
        vw = float(root.get('width', img_w).replace('px', ''))
        vh = float(root.get('height', img_h).replace('px', ''))

    # Calcula as novas coordenadas no sistema SVG
    scale_x = vw / img_w
    scale_y = vh / img_h

    new_vx = vx + (x_min * scale_x) - margin
    new_vy = vy + (y_min * scale_y) - margin
    new_vw = ((x_max - x_min) * scale_x) + (margin * 2)
    new_vh = ((y_max - y_min) * scale_y) + (margin * 2)

    # 4. Grava o viewBox cortado cirurgicamente no arquivo de saída
    root.set('viewBox', f"{new_vx:.2f} {new_vy:.2f} {new_vw:.2f} {new_vh:.2f}")
    root.attrib.pop('width', None)
    root.attrib.pop('height', None)

    tree.write(output_svg_path, encoding='utf-8', xml_declaration=True)
    print(f"Recortado: {input_svg_path} -> {output_svg_path}")

def process_folder(input_folder="svg", output_folder="crops"):
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    if not input_path.exists():
        print(f"Pasta de entrada '{input_folder}' não encontrada.")
        return

    # Percorre todos os arquivos .svg na pasta svg/ e subpastas
    svg_files = list(input_path.rglob("*.svg"))
    
    if not svg_files:
        print(f"Nenhum arquivo .svg encontrado dentro de '{input_folder}/'.")
        return

    print(f"Encontrados {len(svg_files)} arquivos SVG para processar...")

    for file in svg_files:
        # Mantém a estrutura de subpastas (ex: svg/A0/planta.svg -> crops/A0/planta.svg)
        relative_path = file.relative_to(input_path)
        destination_file = output_path / relative_path

        crop_svg_by_content(str(file), str(destination_file))

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "svg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "crops"
    
    process_folder(src, dst)