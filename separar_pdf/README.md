# App para separar Hojas de PDF individualmente

### Pasos para generar el ejecutable
1. Clonar el repo
2. Activar el .venv `python -m venv venv`
3. Instalar las dependencias `pip install -r requirements.txt`
4. Instalar `pip install pyinstaller`
5. Generar el exe `pyinstaller --onefile --windowed --icon="separar_pdf/assets/pdf_icon.ico" --name "Separador_PDF" separar_pdf/main.py`