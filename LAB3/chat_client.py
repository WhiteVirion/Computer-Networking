import socket
import threading
from datetime import datetime


class ChatClient:
    def __init__(self):
        # Настройки сервера (по умолчанию)
        self.server_host = '127.0.0.1'
        self.server_port = 5555

        # Настройки клиента (вводятся пользователем)
        self.client_host = input("Введите IP этого клиента: ") or '127.0.0.1'
        self.client_port = self.get_port("Введите порт этого клиента: ", 5556)
        self.nickname = input("Введите ваш никнейм: ") or 'Guest'

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.history = []

    def get_port(self, prompt, default):
        """Получение и валидация порта"""
        while True:
            try:
                port = input(prompt) or default
                return int(port)
            except ValueError:
                print("Порт должен быть числом!")

    def connect(self):
        """Подключение к серверу"""
        try:
            # Привязываем клиентский сокет к указанному адресу
            self.client.bind((self.client_host, self.client_port))
            self.client.connect((self.server_host, self.server_port))
            self.running = True

            # Трехэтапное рукопожатие
            name_request = self.client.recv(1024)
            if name_request == b"NAME":
                self.client.send(self.nickname.encode('utf-8'))
                response = self.client.recv(1024)
                if response == b"OK":
                    print(f"Успешно подключено к серверу {self.server_host}:{self.server_port}")
                else:
                    print("Ошибка подключения")
                    return False
            else:
                print("Неверный протокол подключения")
                return False

            receive_thread = threading.Thread(target=self.receive)
            receive_thread.daemon = True
            receive_thread.start()

            return True
        except ConnectionRefusedError:
            print("Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
            return False
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    def receive(self):
        """Получение сообщений от сервера"""
        while self.running:
            try:
                message = self.client.recv(1024)
                if not message:
                    break

                msg_type = message[0]
                msg_len = message[1]
                content = message[2:2 + msg_len].decode('utf-8')

                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {content}"

                if msg_type == 1:  # Обычное сообщение
                    print(f"{content}")
                elif msg_type == 3:  # Пользователь подключился
                    print(f">>> {content} <<<")
                elif msg_type == 4:  # Пользователь отключился
                    print(f"<<< {content} >>>")

                self.history.append(log_entry)

                # Выводим приглашение только если пользователь не вводит сообщение
                if not self.waiting_for_input:
                    print("Ваше сообщение: ", end="", flush=True)

            except ConnectionResetError:
                break
            except Exception as e:
                print(f"\nОшибка получения сообщения: {e}")
                break

        print("\nСоединение с сервером разорвано")
        self.running = False

    def send(self, message):
        """Отправка сообщения на сервер"""
        try:
            self.client.send(message.encode('utf-8'))
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.history.append(f"[{timestamp}] Вы: {message}")
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

    def show_history(self):
        """Показать историю сообщений"""
        print("\n--- История чата ---")
        for entry in self.history:
            print(entry)
        print("--------------------\n")

    def disconnect(self):
        """Отключение от сервера"""
        self.running = False
        self.client.close()


def main():
    print("=== Настройка клиента чата ===")
    client = ChatClient()

    if not client.connect():
        return

    try:
        #print("Ваше сообщение: ", end="", flush=True)
        client.waiting_for_input = False

        while client.running:
            client.waiting_for_input = True
            message = input()
            client.waiting_for_input = False

            if message.lower() == '/exit':
                break
            elif message.lower() == '/history':
                client.show_history()
                #print("Ваше сообщение: ", end="", flush=True)
            elif message.lower() == '/help':
                print("\nДоступные команды:")
                print("/exit - выход из чата")
                print("/history - показать историю сообщений")
                print("/help - показать справку")
                #print("Ваше сообщение: ", end="", flush=True)
            else:
                client.send(message)
                #print("Ваше сообщение: ", end="", flush=True)

    except KeyboardInterrupt:
        print("\nЗавершение работы клиента...")
    finally:
        client.disconnect()
        print("Клиент завершен")


if __name__ == "__main__":
    main()