# Используем официальный базовый образ Python.
# slim-buster - это легковесная версия Debian, что уменьшает размер итогового образа.
FROM python:3.10-slim-buster

# Устанавливаем рабочую директорию внутри контейнера.
# Все последующие команды будут выполняться относительно этого пути.
WORKDIR /app

# Устанавливаем Tesseract OCR и языковой пакет для русского языка.
# -y флаг автоматически отвечает "yes" на все запросы.
# --no-install-recommends предотвращает установку ненужных пакетов.
# В конце очищаем кэш apt, чтобы уменьшить размер образа.
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-rus --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Обновляем pip и устанавливаем зависимости.
# Копируем только requirements.txt сначала, чтобы воспользоваться кэшированием слоев Docker.
# Этот слой будет пересобираться только если requirements.txt изменится.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# Копируем все остальные файлы проекта в рабочую директорию.
# .gitignore и .dockerignore (который мы создадим) будут учитываться.
COPY . .

# Указываем команду для запуска приложения при старте контейнера.
CMD ["python", "telegram_bot.py"] 