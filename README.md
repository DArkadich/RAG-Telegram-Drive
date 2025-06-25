# RAG Telegram Drive Bot

Telegram бот с RAG (Retrieval Augmented Generation) системой, который отвечает на вопросы на основе документов из Google Drive.

## Основные возможности

- Интеграция с Google Drive для синхронизации документов
- Поддержка различных форматов файлов (PDF, DOCX)
- RAG система на основе FAISS для векторного поиска
- Telegram бот для удобного взаимодействия

## Настройка

### Переменные окружения

Создайте файл `.env` на основе `env.example` и заполните следующие переменные:

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-...

# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Google Drive Folder ID
GDRIVE_FOLDER_ID=your_gdrive_folder_id_here

# Path to Google Drive Service Account credentials
CREDENTIALS_FILE_PATH=./credentials.json

# Paths for storage
FAISS_INDEX_PATH=./vector_storage/index.faiss
METADATA_PATH=./vector_storage/metadata.json
LOG_FILE_PATH=./logs/rag_system.log
```

### Настройка прокси

Если вам нужно использовать прокси для подключения к OpenAI API, установите одну из следующих переменных окружения:

```bash
# Для HTTPS прокси
HTTPS_PROXY=http://proxy.example.com:8080

# Для HTTP прокси
HTTP_PROXY=http://proxy.example.com:8080

# Специальный прокси для OpenAI
OPENAI_PROXY=http://proxy.example.com:8080
```

## Статус деплоя
![Deploy Status](https://github.com/DArkadich/RAG-Telegram-Drive/actions/workflows/deploy.yml/badge.svg)





