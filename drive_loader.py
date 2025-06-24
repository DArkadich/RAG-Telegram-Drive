from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger
from config import config

class DriveLoader:
    """
    Класс для загрузки и обновления файлов из Google Drive.
    """

    def __init__(self):
        self.drive = self._authenticate()
        self.download_path = Path(config.app.drive_loader.download_path)
        self.download_path.mkdir(exist_ok=True)
        logger.info(f"Инициализирован DriveLoader. Файлы будут сохраняться в {self.download_path}")

    def _authenticate(self) -> GoogleDrive:
        """
        Аутентифицируется в Google Drive с помощью сервисного аккаунта.

        Для этого метода требуется файл `credentials.json`, полученный из 
        Google Cloud Console для вашего сервисного аккаунта.

        ШАГИ ДЛЯ НАСТРОЙКИ:
        1. Перейдите в Google Cloud Console: https://console.cloud.google.com/
        2. Создайте новый проект или выберите существующий.
        3. Включите API "Google Drive API".
        4. Перейдите в "Учетные данные" -> "Создать учетные данные" -> "Сервисный аккаунт".
        5. Дайте ему имя (например, "rag-telegram-bot-sa"), нажмите "Готово".
        6. Перейдите на вкладку "Ключи" для созданного аккаунта, нажмите "Добавить ключ" -> "Создать новый ключ".
        7. Выберите JSON и скачайте файл. Переименуйте его в `credentials.json` 
           и поместите в корень проекта (или укажите путь в .env).
        8. **ВАЖНО**: Откройте вашу папку на Google Drive, которую будет читать бот,
           и "поделитесь" ею (дайте права "Читатель" или "Редактор")
           с email-адресом вашего сервисного аккаунта (он выглядит как ...@...iam.gserviceaccount.com).
        """
        
        credentials_file = config.env.CREDENTIALS_FILE_PATH
        if not Path(credentials_file).exists():
            error_msg = (
                f"Файл учетных данных '{credentials_file}' не найден. "
                "Пожалуйста, следуйте инструкции в docstring метода `_authenticate`."
            )
            logger.critical(error_msg)
            raise FileNotFoundError(error_msg)

        # Собираем настройки для PyDrive2 в памяти, чтобы избежать проблем с форматом файла
        settings = {
            "client_config_backend": "service",
            "service_config": {
                "client_json_file_path": credentials_file,
            }
        }
        
        gauth = GoogleAuth(settings=settings)
        
        try:
            gauth.ServiceAuth()
            logger.success("Аутентификация в Google Drive через сервисный аккаунт прошла успешно.")
            return GoogleDrive(gauth)
        except Exception as e:
            logger.critical(f"Ошибка аутентификации в Google Drive: {e}")
            raise

    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Получает список файлов в указанной папке на Google Drive."""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            logger.info(f"Найдено {len(file_list)} файлов в папке Google Drive: {folder_id}")
            return file_list
        except Exception as e:
            logger.error(f"Не удалось получить список файлов из папки {folder_id}: {e}")
            return []

    def download_new_files(self, folder_id: str) -> List[Path]:
        """
        Скачивает новые файлы из папки Google Drive.
        "Новым" считается файл, которого нет в локальной директории загрузок.
        """
        online_files = self.list_files_in_folder(folder_id)
        if not online_files:
            return []

        downloaded_paths = []
        for file in online_files:
            local_path = self.download_path / file['title']
            if not local_path.exists():
                try:
                    logger.info(f"Скачивание нового файла: {file['title']}...")
                    file.GetContentFile(local_path)
                    downloaded_paths.append(local_path)
                    logger.success(f"Файл '{file['title']}' успешно скачан.")
                except Exception as e:
                    logger.error(f"Не удалось скачать файл {file['title']} (ID: {file['id']}): {e}")
            else:
                logger.info(f"Файл '{file['title']}' уже существует локально, пропуск.")
        
        logger.info(f"Завершено. Скачано {len(downloaded_paths)} новых файлов.")
        return downloaded_paths

# Пример использования
if __name__ == '__main__':
    if not config:
        raise RuntimeError("Конфигурация не загружена.")

    logger.info("--- Тестирование DriveLoader ---")
    try:
        loader = DriveLoader()
        
        folder_id = config.env.GDRIVE_FOLDER_ID
        if not folder_id or folder_id == 'your_gdrive_folder_id_here':
            print("\n!!! Пожалуйста, укажите GDRIVE_FOLDER_ID в вашем .env файле для теста.")
        else:
            print(f"\nЦелевая папка на Google Drive: {folder_id}")
            
            # 1. Получаем список файлов
            files = loader.list_files_in_folder(folder_id)
            if files:
                print(f"Найдено {len(files)} файлов онлайн:")
                for f in files[:5]: # Показываем первые 5
                    print(f"  - {f['title']} (ID: {f['id']})")
            else:
                print("В указанной папке не найдено файлов или произошла ошибка.")

            # 2. Скачиваем новые файлы
            print("\nПопытка скачать новые файлы...")
            newly_downloaded = loader.download_new_files(folder_id)

            if newly_downloaded:
                print(f"Скачано {len(newly_downloaded)} новых файлов:")
                for p in newly_downloaded:
                    print(f"  - {p.name}")
            else:
                print("Новых файлов для скачивания нет.")
    
    except (FileNotFoundError, Exception) as e:
        logger.error(f"Тестирование прервано из-за ошибки: {e}")

    logger.info("\nТестирование завершено.")
