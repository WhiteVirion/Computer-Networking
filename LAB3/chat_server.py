import socket
import threading
from datetime import datetime


class ChatServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()

        self.clients = {}  #список клиентов
        self.nicknames = {} #их имена

        print(f"Сервер запущен на {self.host}:{self.port}")
        print("Ожидание подключений...")

    def broadcast(self, message, sender_addr=None):
        """Отправка сообщения всем подключенным клиентам"""
        for client_socket in self.clients.values():
            if client_socket.getpeername() != sender_addr:
                try:
                    client_socket.send(message)
                except:
                    self.remove_client(client_socket)

    def handle_client(self, client_socket, client_addr):
        """Обработка подключения клиента"""
        try:
            # Трехэтапное рукопожатие
            client_socket.send(b"NAME")
            nickname = client_socket.recv(1024).decode('utf-8')
            client_socket.send(b"OK")

            self.clients[client_addr] = client_socket
            self.nicknames[client_addr] = nickname

            join_msg = f"{nickname} ({client_addr[0]}) присоединился к чату!".encode('utf-8')
            self.broadcast(self.format_message(3, join_msg))
            print(f"{nickname} подключился с {client_addr}")

            while True:
                try:
                    message = client_socket.recv(1024)
                    if not message:
                        break

                    formatted_msg = self.format_message(1,
                                                        f"{nickname}: {message.decode('utf-8')}".encode('utf-8'))
                    self.broadcast(formatted_msg, client_addr)

                except ConnectionResetError:
                    break

        except Exception as e:
            print(f"Ошибка с клиентом {client_addr}: {e}")
        finally:
            self.remove_client(client_socket, client_addr)

    def format_message(self, msg_type, content):
        """Форматирование сообщения по протоколу"""
        msg_len = len(content)
        return bytes([msg_type, msg_len]) + content

    def remove_client(self, client_socket, client_addr=None):
        """Удаление клиента при отключении"""
        if not client_addr:
            client_addr = client_socket.getpeername()

        if client_addr in self.clients:
            nickname = self.nicknames.get(client_addr, 'Unknown')
            self.clients.pop(client_addr, None)
            self.nicknames.pop(client_addr, None)

            leave_msg = f"{nickname} ({client_addr[0]}) покинул чат.".encode('utf-8')
            self.broadcast(self.format_message(4, leave_msg))
            print(f"{nickname} отключился")

            client_socket.close()

    def start(self):
        """Запуск сервера"""
        try:
            while True:
                client_socket, client_addr = self.server.accept()
                print(f"Подключение с {client_addr}")

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_addr)
                )
                thread.start()

        except KeyboardInterrupt:
            print("\nОстановка сервера...")
        finally:
            for client in list(self.clients.values()):
                client.close()
            self.server.close()
            print("Сервер остановлен")


if __name__ == "__main__":
    server = ChatServer()  # Используем параметры по умолчанию
    server.start()