import socket
import threading
from urllib.parse import urlparse, urlunparse


class ProxyServer:
    def __init__(self, host='127.0.0.11', port=8888, blacklist=None):
        self.host = host
        self.port = port
        self.blacklist = blacklist or []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[*] Proxy server started on {self.host}:{self.port}")

            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"[*] New connection from {addr[0]}:{addr[1]}")
                    proxy_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,)
                    )
                    proxy_thread.start()
                except Exception as e:
                    print(f"[!] Accept error: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down proxy server")
        except Exception as e:
            print(f"[!] Server error: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket):
        try:
            request_data = client_socket.recv(4096)
            if not request_data:
                return

            # извлечение первой строки
            try:
                first_line = request_data.split(b'\n')[0].decode()
                parts = first_line.split()
                if len(parts) < 3:
                    return
                method, url, http_version = parts
            except:
                return


            if '://' not in url:
                print(f"[!] Invalid URL (no scheme): {url}")
                return

            try:
                parsed_url = urlparse(url)
                if not parsed_url.netloc:
                    print(f"[!] Invalid URL (no host): {url}")
                    return

                host = parsed_url.netloc.split(':')[0]
                port = parsed_url.port if parsed_url.port else 80
                clean_url = urlunparse((
                    parsed_url.scheme, #http
                    parsed_url.netloc, #live.legendy.by:8000
                    parsed_url.path,   #/legendyfm
                    parsed_url.params, #параметры пути, для старых url
                    parsed_url.query,  #строка запроса
                    ''  # удалить фрагмент
                ))
            except Exception as e:
                print(f"[!] URL parsing error: {e}")
                return

            # проверка на черный лист
            if host in self.blacklist:
                print(f"{clean_url} - 403 Forbidden")
                response = (
                    "HTTP/1.1 403 Forbidden\r\n"
                    "Content-Type: text/html\r\n\r\n"
                    "<html><body><h1>403 Forbidden</h1>"
                    "<p>Access to this site is blocked by proxy server.</p>"
                    "</body></html>\r\n"
                )
                client_socket.send(response.encode())
                return

            #коррекция запроса
            path = parsed_url.path if parsed_url.path else '/'
            if parsed_url.query:
                path += '?' + parsed_url.query

            modified_request = request_data.replace(
                f"{method} {url}".encode(),
                f"{method} {path}".encode(),
                1
            )

            # подключение к целевому серверу
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote_socket:
                    remote_socket.settimeout(10)
                    remote_socket.connect((host, port))
                    remote_socket.send(modified_request)

                    # получение заголовков ответа
                    response = b''
                    while True:
                        part = remote_socket.recv(4096)
                        if not part:
                            break
                        response += part
                        if b'\r\n\r\n' in response:  # заголовки получены
                            break

                    if not response:
                        print(f"{clean_url} - No Response")
                        return

                    # извлечение кода статутса и его вывод в консоль
                    status_line = response.split(b'\r\n')[0]
                    try:
                        status_parts = status_line.decode().split(' ', 2)
                        status_code = status_parts[1]
                        status_text = status_parts[2] if len(status_parts) > 2 else ''
                        print(f"{clean_url} - {status_code} {status_text}")
                    except:
                        print(f"{clean_url} - Unknown Status")

                    # прямой ответ клиенту
                    client_socket.send(response)


                    while True:
                        part = remote_socket.recv(4096)
                        if not part:
                            break
                        client_socket.send(part)

            except socket.timeout:
                print(f"{clean_url} - Connection Timeout")
            except ConnectionRefusedError:
                print(f"{clean_url} - Connection Refused")
            except Exception as e:
                print(f"{clean_url} - Connection Error: {str(e)}")

        except Exception as e:
            print(f"[!] Client handling error: {e}")
        finally:
            client_socket.close()


if __name__ == "__main__":
    #черный список
    BLACKLIST = [
        "example.com",
        "blockeddomain.com"
    ]

    try:
        proxy = ProxyServer(host='127.0.0.11', port=8888, blacklist=BLACKLIST)
        proxy.start()
    except Exception as e:
        print(f"[!] Fatal error: {e}")