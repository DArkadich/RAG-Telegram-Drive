import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from loguru import logger

# --- Модели для настроек из settings.json ---

class RagSettings(BaseModel):
    chunk_size: int
    chunk_overlap: int
    top_k: int

class OpenAISettings(BaseModel):
    embedding_model: str
    generation_model: str

class DriveLoaderSettings(BaseModel):
    download_path: str

class AppSettings(BaseModel):
    rag: RagSettings
    openai: OpenAISettings
    drive_loader: DriveLoaderSettings

# --- Модель для настроек из .env ---

class EnvSettings(BaseSettings):
    OPENAI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    GDRIVE_FOLDER_ID: str
    CREDENTIALS_FILE_PATH: str
    FAISS_INDEX_PATH: str
    METADATA_PATH: str
    LOG_FILE_PATH: str

    # Указываем Pydantic, что нужно загружать переменные из .env файла
    # Имя файла по умолчанию .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class Config:
    def __init__(self, settings_path: str | Path = "settings.json"):
        self.env = EnvSettings()
        
        try:
            with open(settings_path, "r") as f:
                settings_json = json.load(f)
            self.app = AppSettings.model_validate(settings_json)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Не удалось загрузить файл настроек {settings_path}: {e}")
            raise
        
        # Создаем необходимые директории
        self._create_directories()

    def _create_directories(self):
        Path(self.app.drive_loader.download_path).mkdir(parents=True, exist_ok=True)
        Path(self.env.FAISS_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.env.LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
        logger.info("Все необходимые директории проверены и созданы.")


# Создаем единый экземпляр конфигурации, который будет использоваться во всем проекте
# Для этого нужно будет импортировать `config` из этого модуля
try:
    config = Config()
except Exception as e:
    logger.critical(f"Критическая ошибка при инициализации конфигурации: {e}")
    # В реальном приложении здесь может быть выход из программы
    config = None

# Пример использования (для тестирования)
if __name__ == "__main__":
    if config:
        print("--- Загруженные переменные окружения (.env) ---")
        print(f"OpenAI Key: ...{config.env.OPENAI_API_KEY[-4:]}")
        print(f"Telegram Token: ...{config.env.TELEGRAM_BOT_TOKEN[-4:]}")
        print(f"Gdrive Folder ID: {config.env.GDRIVE_FOLDER_ID}")
        print(f"Log File Path: {config.env.LOG_FILE_PATH}")

        print("\n--- Загруженные настройки приложения (settings.json) ---")
        print(f"Chunk Size: {config.app.rag.chunk_size}")
        print(f"Embedding Model: {config.app.openai.embedding_model}")
        print(f"Download Path: {config.app.drive_loader.download_path}")
    else:
        print("Не удалось загрузить конфигурацию.")
