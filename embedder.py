from typing import List
import openai
from loguru import logger
from config import config

class OpenAIEmbedder:
    """
    Класс для создания эмбеддингов с использованием OpenAI API.
    """
    def __init__(self, api_key: str = config.env.OPENAI_API_KEY, model: str = config.app.openai.embedding_model):
        if not api_key:
            raise ValueError("API-ключ OpenAI не найден. Проверьте .env файл.")
        # openai.api_key = api_key  # Для старых версий < 1.0
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Инициализирован OpenAIEmbedder с моделью: {self.model}")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов.

        Args:
            texts (List[str]): Список текстовых фрагментов (чанков).

        Returns:
            List[List[float]]: Список эмбеддингов.
        """
        if not texts:
            return []
        
        try:
            # Заменяем пустые строки на пробелы, т.к. API OpenAI не принимает пустые строки
            texts = [text.replace("\n", " ") for text in texts]
            response = self.client.embeddings.create(input=texts, model=self.model)
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Успешно создано {len(embeddings)} эмбеддингов.")
            return embeddings
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддингов через OpenAI API: {e}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для одного текста.

        Args:
            text (str): Текстовый фрагмент.

        Returns:
            List[float]: Эмбеддинг.
        """
        return self.get_embeddings([text])[0]

# Пример использования
if __name__ == '__main__':
    if not config:
        raise RuntimeError("Конфигурация не была загружена.")

    logger.info("--- Тестирование OpenAIEmbedder ---")
    
    # Убедитесь, что у вас есть .env файл с OPENAI_API_KEY
    try:
        embedder = OpenAIEmbedder()
        
        # 1. Тест с одним текстом
        text1 = "Привет, мир!"
        embedding1 = embedder.get_embedding(text1)
        print(f"Эмбеддинг для '{text1}':\n  - Размерность: {len(embedding1)}\n  - Фрагмент: {embedding1[:5]}...")

        # 2. Тест с несколькими текстами
        texts = ["Что такое RAG?", "Как работает FAISS?"]
        embeddings = embedder.get_embeddings(texts)
        print(f"\nЭмбеддинги для списка из {len(texts)} текстов:")
        for i, text in enumerate(texts):
            print(f"  - '{text}': размерность {len(embeddings[i])}")
            
    except (ValueError, openai.AuthenticationError) as e:
        logger.error(f"Ошибка инициализации или аутентификации: {e}")
        logger.warning("Пропустите этот тест, если у вас нет ключа OpenAI. Основная логика будет работать.")
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}")

    logger.info("\nТестирование завершено.")
