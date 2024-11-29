import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import threading
from queue import Queue

# Archivos para persistencia del estado
SCRAPED_DOMAINS_FILE = "files/scraped_domains.txt"
PENDING_DOMAINS_FILE = "files/pending_domains.txt"

# Leer o inicializar un archivo con datos
def load_list_from_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file.readlines() if line.strip())
    return set()

# Guardar un conjunto en un archivo
def save_list_to_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as file:
        for item in sorted(data):
            file.write(f"{item}\n")

# Crear una ruta de archivo segura
def safe_path(base_dir, url):
    parsed = urlparse(url)
    if not parsed.path or parsed.path == "/":
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

def crawl_domain(domain, scraped_domains, pending_domains, processing_domains, lock):
    base_url = f"https://{domain}"
    print(f"Rastreando el dominio: {domain}")
    visited = set()
    output_dir = os.path.join("files", domain)

    create_folder(output_dir)

    # Sesión de requests
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    session.headers.update(headers)

    def crawl(url):
        if url in visited:
            return
        visited.add(url)

        try:
            response = session.get(url, timeout=3)
            response.raise_for_status()

            # Obtener el tipo de contenido
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
                for tag in soup.find_all(["a", "img"]):
                    href = None
                    if tag.name == "a":
                        href = tag.get("href")
                    elif tag.name == "img":
                        href = tag.get("src")

                    if href:
                        new_url = urljoin(url, href)
                        parsed_new_url = urlparse(new_url)
                        new_domain = parsed_new_url.netloc

                        if new_url not in visited:
                            if new_domain == domain:
                                # Mismo dominio, continuar el crawl recursivamente
                                crawl(new_url)
                            else:
                                # Dominio externo
                                with lock:
                                    # Conjunto de palabras clave que se deben buscar en el dominio
                                    KEYWORDS = ["fuel", "petro", "verifone", "tank", "inge"]

                                    # Condicional mejorado
                                    if (any(keyword in new_domain for keyword in KEYWORDS)
                                            and new_domain not in scraped_domains
                                            and new_domain not in pending_domains
                                            and new_domain not in processing_domains):
                                        
                                        pending_domains.add(new_domain)
                                        save_list_to_file(PENDING_DOMAINS_FILE, pending_domains)
            else:
                # Si no es HTML, tratar como recurso
                resource_path = safe_path(output_dir, url)
                create_folder(os.path.dirname(resource_path))
                download_resource(session, url, resource_path)
        except Exception as e:
            print(f"Error al procesar {url}: {e}")

    # Indicar que vamos a procesar este dominio
    with lock:
        processing_domains.add(domain)
        if domain in pending_domains:
            pending_domains.remove(domain)
        save_list_to_file(PENDING_DOMAINS_FILE, pending_domains)
        save_list_to_file(SCRAPED_DOMAINS_FILE, scraped_domains.union(processing_domains))

    # Iniciar el crawl desde la base URL
    crawl(base_url)

    # Una vez completado, mover el dominio a scraped_domains
    with lock:
        processing_domains.remove(domain)
        scraped_domains.add(domain)
        save_list_to_file(SCRAPED_DOMAINS_FILE, scraped_domains)

    print(f"Rastreo completado para el dominio {domain}")

def worker(pending_domains_queue, scraped_domains, pending_domains, processing_domains, lock):
    while True:
        domain = None
        with lock:
            if not pending_domains_queue.empty():
                domain = pending_domains_queue.get()
            else:
                # Si no hay más pendientes y ningún dominio en procesamiento, terminamos
                if not processing_domains:
                    break

        if domain:
            crawl_domain(domain, scraped_domains, pending_domains, processing_domains, lock)
            pending_domains_queue.task_done()
        else:
            break

if __name__ == "__main__":
    # Crear carpeta base para los datos
    base_output_dir = os.path.abspath(os.path.join(".", "files"))
    create_folder(base_output_dir)

    # Bloqueo para manejo de concurrencia
    lock = threading.Lock()

    # Leer listas persistentes de dominios
    scraped_domains = load_list_from_file(SCRAPED_DOMAINS_FILE)
    pending_domains = load_list_from_file(PENDING_DOMAINS_FILE)
    processing_domains = set()

    # Agregar los dominios iniciales a la lista de pendientes si no están en scraped
    initial_urls = [
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
        "https://www.bakertilly.com"
    ]

    for url in initial_urls:
        domain = urlparse(url).netloc
        if domain not in scraped_domains and domain not in pending_domains:
            pending_domains.add(domain)

    # Guardar la lista actualizada de pendientes
    save_list_to_file(PENDING_DOMAINS_FILE, pending_domains)

    # Crear una cola para manejar dominios pendientes
    pending_domains_queue = Queue()

    # Agregar dominios pendientes a la cola
    with lock:
        for domain in pending_domains:
            pending_domains_queue.put(domain)

    # Crear y arrancar hilos
    num_initial_threads = len(initial_urls)
    threads = []
    for i in range(num_initial_threads):
        t = threading.Thread(target=worker, args=(pending_domains_queue, scraped_domains, pending_domains, processing_domains, lock))
        t.start()
        threads.append(t)

    # Esperar a que todos los dominios sean procesados
    pending_domains_queue.join()

    # Esperar a que todos los hilos terminen
    for t in threads:
        t.join()

    print("Crawling completado para todos los dominios.")