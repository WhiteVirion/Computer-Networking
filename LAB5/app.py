from flask import Flask, request, jsonify, send_file, make_response
import os
import shutil
from datetime import datetime
from pathlib import Path
import mimetypes

app = Flask(__name__)
# Использование абсолютного пути для хранилища
STORAGE_ROOT = os.path.abspath("./storage")  # Папка для хранения файлов

# Утилита для получения безопасного пути
def get_safe_path(path):
    # Нормализуем путь и убираем начальные слеши
    safe_path = os.path.normpath(os.path.join(STORAGE_ROOT, path.lstrip("/")))
    # Проверяем, что путь не выходит за пределы STORAGE_ROOT
    if not safe_path.startswith(os.path.abspath(STORAGE_ROOT)):
        raise ValueError("Access outside storage root is forbidden")
    return safe_path

# GET: Получение файла или списка файлов в каталоге
@app.route("/<path:path>", methods=["GET"])
def get_resource(path):
    try:
        safe_path = get_safe_path(path)
        if not os.path.exists(safe_path):
            return jsonify({"error": "Not found"}), 404

        if os.path.isfile(safe_path):
            # Отправляем файл с правильным Content-Type
            mime_type, _ = mimetypes.guess_type(safe_path)
            return send_file(safe_path, mimetype=mime_type or "application/octet-stream")
        elif os.path.isdir(safe_path):
            # Возвращаем список файлов и папок в формате JSON
            files = [
                {"name": f, "type": "directory" if os.path.isdir(os.path.join(safe_path, f)) else "file"}
                for f in os.listdir(safe_path)
            ]
            return jsonify(files), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# PUT: Загрузка файла или копирование (с заголовком X-Copy-From)
@app.route("/<path:path>", methods=["PUT"])
def upload_file(path):
    try:
        safe_path = get_safe_path(path)
        
        # Проверяем, является ли целевой путь директорией
        if os.path.isdir(safe_path):
            return jsonify({"error": "Cannot overwrite directory with file"}), 400
            
        # Создаем родительские директории, если их нет
        directory = os.path.dirname(safe_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Проверяем, есть ли заголовок для копирования
        copy_from = request.headers.get("X-Copy-From")
        if copy_from:
            source_path = get_safe_path(copy_from)
            if not os.path.isfile(source_path):
                return jsonify({"error": "Source file not found"}), 404
            shutil.copy2(source_path, safe_path)  # Копируем с сохранением метаданных
            return jsonify({"message": "File copied"}), 201

        # Обычная загрузка файла
        if not request.data:
            return jsonify({"error": "No file data provided"}), 400
        with open(safe_path, "wb") as f:
            f.write(request.get_data())
        return jsonify({"message": "File uploaded"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# HEAD: Получение метаданных файла (размер и дата изменения)
@app.route("/<path:path>", methods=["HEAD"])
def get_metadata(path):
    try:
        safe_path = get_safe_path(path)
        if not os.path.isfile(safe_path):
            return jsonify({"error": "Not found"}), 404

        stat = os.stat(safe_path)
        response = make_response()
        response.headers["Content-Length"] = stat.st_size
        response.headers["Last-Modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        response.headers["Content-Type"] = mimetypes.guess_type(safe_path)[0] or "application/octet-stream"
        return response
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# DELETE: Удаление файла или каталога
@app.route("/<path:path>", methods=["DELETE"])
def delete_resource(path):
    try:
        safe_path = get_safe_path(path)
        if not os.path.exists(safe_path):
            return jsonify({"error": "Not found"}), 404

        if os.path.isfile(safe_path):
            os.remove(safe_path)
        elif os.path.isdir(safe_path):
            shutil.rmtree(safe_path)
        return "", 204
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Обработка корневого пути для всех методов
@app.route("/", methods=["GET", "PUT", "HEAD", "DELETE"])
def root():
    if request.method == "GET":
        if not os.listdir(STORAGE_ROOT):
            return jsonify({"info": "Storage is empty"}), 200
        return get_resource("")
    elif request.method == "PUT":
        return upload_file("")
    elif request.method == "HEAD":
        return get_metadata("")
    elif request.method == "DELETE":
        return delete_resource("")

if __name__ == "__main__":
    # Создаём папку для хранения, если её нет
    os.makedirs(STORAGE_ROOT, exist_ok=True)
    host = "127.0.0.3"
    port = 8000
    print(f"Storage directory: {STORAGE_ROOT}")
    print(f"Starting server on http://{host}:{port}...")
    # Запускаем сервер, доступный в локальной сети
    app.run(host, port, debug=True)
