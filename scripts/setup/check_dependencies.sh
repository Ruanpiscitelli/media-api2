#!/bin/bash

echo "Verificando dependências..."

# Verificar Python e pip
python3 --version || { echo "Python3 não encontrado"; exit 1; }
pip3 --version || { echo "Pip3 não encontrado"; exit 1; }

# Verificar dependências do sistema
deps=(
    "libgl1-mesa-glx"
    "libglib2.0-0"
)

for dep in "${deps[@]}"; do
    dpkg -l | grep -q $dep || {
        echo "Instalando $dep..."
        apt-get install -y $dep
    }
done

# Verificar dependências Python
python3 -c "import cv2" || {
    echo "Instalando OpenCV..."
    pip install opencv-python-headless
}

echo "✅ Todas as dependências estão instaladas!" 