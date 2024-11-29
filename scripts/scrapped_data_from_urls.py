import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from tqdm import tqdm  # Para la barra de progreso

# Crear una ruta de archivo segura
def safe_path(base_dir, url):
    parsed = urlparse(url)
    if not parsed.path or parsed.path == '/':
        filename = "index.html"
    else:
        filename = parsed.path.strip("/")
        filename = filename.replace("/", "_")

        # Si no tiene extensión, tratarlo como un HTML
        if not os.path.splitext(filename)[1]:
            filename += ".html"
    return os.path.join(base_dir, filename)

# Crear una carpeta si no existe
def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Descargar un archivo o recurso
def download_resource(session, url, save_path):
    try:
        response = session.get(url, timeout=4, stream=True)
        response.raise_for_status()

        # Guardar el contenido en un archivo
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except Exception as e:
        print(f"Error al descargar {url}: {e}")
        return False

# Rastrear un sitio web
def crawl_website(base_url, output_dir):
    print(f"Rastreando el sitio: {base_url}")
    parsed_base = urlparse(base_url)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    visited = set()
    endpoints = []

    # Crear carpeta base para el sitio
    create_folder(output_dir)

    # Iniciar sesión de requests
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    session.headers.update(headers)

    # Función interna para el rastreo recursivo
    def crawl(url):
        if url in visited:
            return
        visited.add(url)
        endpoints.append(url)

        # Parsear URL y verificar dominio
        parsed_url = urlparse(url)
        if parsed_url.netloc != parsed_base.netloc:
            return  # Ignorar enlaces externos

        try:
            response = session.get(url, timeout=3)
            response.raise_for_status()

            # Obtener el contenido tipo
            content_type = response.headers.get("Content-Type", "").lower()

            # Si es HTML
            if "text/html" in content_type:
                html = response.text
                save_path = safe_path(output_dir, url)
                create_folder(os.path.dirname(save_path))
                with open(save_path, "w", encoding="utf-8") as file:
                    file.write(html)

                # Analizar HTML y buscar recursos
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup.find_all(["a", "img", "script", "link"]):
                    href = None
                    if tag.name == "a":
                        href = tag.get("href")
                    elif tag.name == "img":
                        href = tag.get("src")
                    elif tag.name == "script":
                        href = tag.get("src")
                    elif tag.name == "link":
                        href = tag.get("href")

                    if href:
                        new_url = urljoin(url, href)
                        if new_url not in visited:
                            # Si es un archivo (imagen u otro recurso)
                            if any(new_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".pdf", ".doc", ".docx", ".xlsx"]):
                                resource_path = safe_path(output_dir, new_url)
                                create_folder(os.path.dirname(resource_path))
                                download_resource(session, new_url, resource_path)
                            else:
                                # Si es otra página HTML, rastrearla
                                crawl(new_url)

            else:
                # Si no es HTML, tratar como recurso
                resource_path = safe_path(output_dir, url)
                create_folder(os.path.dirname(resource_path))
                download_resource(session, url, resource_path)
        except Exception as e:
            print(f"Error al procesar {url}: {e}")

    # Iniciar rastreo desde la URL base
    crawl(base_url)

    # Guardar endpoints
    endpoints_file = os.path.join(output_dir, "endpoints.txt")
    with open(endpoints_file, "w", encoding="utf-8") as f:
        for endpoint in endpoints:
            f.write(endpoint + "\n")
    print(f"Rastreo completado para {base_url}. Total de endpoints: {len(endpoints)}")
    print(f"Endpoints guardados en {endpoints_file}")

# Lista de sitios a rastrear
urls = [
    "https://www.spatco.com",
    "https://www.jfpetrogroup.com",
    "https://www.guardianfueltech.com",
    "https://www.mecoatlanta.com",
    "https://www.mckinneypetroleum.com",
    "https://www.barberequipco.com",
    "https://www.bkequip.com",
    "https://www.larsonco.com",
    "https://www.rstenstrom.com",
    "https://www.adamstankandlift.com",
    "https://www.wildcopes.com",
]

# Crear carpeta base para los datos
base_output_dir = os.path.abspath(os.path.join(".", "files"))
create_folder(base_output_dir)

# Rastrear cada URL
for url in urls:
    domain_name = urlparse(url).netloc.replace("www.", "")
    site_output_dir = os.path.join(base_output_dir, domain_name)
    crawl_website(url, site_output_dir)
    print(f"Datos guardados en {site_output_dir}\n")
    # time.sleep(5)  # Pausa entre sitios