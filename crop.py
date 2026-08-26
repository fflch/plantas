import sys
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
import subprocess
import os
from pathlib import Path

def crop_svg_by_content(input_svg_path, output_svg_path, ignore_border_px=40, padding_percent=0.04):
    png_temp = output_svg_path + ".temp.png"
    
    os.makedirs(os.path.dirname(output_svg_path), exist_ok=True)

    subprocess.run([
        "inkscape", "--export-type=png",
        "--export-filename=" + png_temp,
        input_svg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(png_temp):
        print(f"Erro ao analisar: {input_svg_path}")
        return

    img = Image.open(png_temp).convert("RGBA")
    arr = np.array(img)
    img_h, img_w = arr.shape[:2]

    # 1. Ignora a marca d'água Autodesk nas bordas externas
    mask_arr = arr.copy()
    b = ignore_border_px
    mask_arr[:b, :, :] = 0          # Topo
    mask_arr[-b:, :, :] = 0         # Base
    mask_arr[:, :b, :] = 0          # Esquerda
    mask_arr[:, -b:, :] = 0         # Direita

    # 2. Localiza os limites do conteúdo da planta
    alpha = mask_arr[:, :, 3]
    rgb = mask_arr[:, :, :3]
    non_white = (rgb < 250).any(axis=2) & (alpha > 10)

    coords = np.argwhere(non_white)
    if coords.size == 0:
        os.remove(png_temp)
        print(f"Nenhum conteúdo detectado em: {input_svg_path}")
        return

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)

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

    scale_x = vw / img_w
    scale_y = vh / img_h

    # Coordenadas do conteúdo no sistema do SVG
    content_x = vx + (x_min * scale_x)
    content_y = vy + (y_min * scale_y)
    content_w = (x_max - x_min) * scale_x
    content_h = (y_max - y_min) * scale_y

    # 4. Calcula margens proporcionais (padding)
    margin_x = content_w * padding_percent
    margin_y = content_h * padding_percent

    new_vx = content_x - margin_x
    new_vy = content_y - margin_y
    new_vw = content_w + (margin_x * 2)
    new_vh = content_h + (margin_y * 2)

    # 5. Salva o novo viewBox
    root.set('viewBox', f"{new_vx:.2f} {new_vy:.2f} {new_vw:.2f} {new_vh:.2f}")
    root.attrib.pop('width', None)
    root.attrib.pop('height', None)

    tree.write(output_svg_path, encoding='utf-8', xml_declaration=True)
    print(f"Recortado com margem: {input_svg_path} -> {output_svg_path}")

def process_folder(input_folder="svg", output_folder="crops"):
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    if not input_path.exists():
        print(f"Pasta de entrada '{input_folder}' não encontrada.")
        return

    svg_files = list(input_path.rglob("*.svg"))
    
    if not svg_files:
        print(f"Nenhum arquivo .svg encontrado dentro de '{input_folder}/'.")
        return

    print(f"Encontrados {len(svg_files)} arquivos SVG para processar...")

    for file in svg_files:
        relative_path = file.relative_to(input_path)
        destination_file = output_path / relative_path

        crop_svg_by_content(str(file), str(destination_file))

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "svg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "crops"
    
    process_folder(src, dst)