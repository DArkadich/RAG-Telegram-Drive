from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import faiss
import json
from pathlib import Path

from loguru import logger
from langchain.schema import Document

# Импортируем наш типизированный конфиг
from config import config

class VectorStore(ABC):
    """Абстрактный базовый класс для векторных хранилищ."""

    @abstractmethod
    def add(self, documents: List[Document]):
        """Добавляет документы в хранилище."""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int) -> List[Tuple[Document, float]]:
        """Ищет k ближайших документов к данному эмбеддингу."""
        pass

    @abstractmethod
    def save(self):
        """Сохраняет состояние хранилища (индекс и метаданные)."""
        pass

    @abstractmethod
    def load(self):
        """Загружает состояние хранилища."""
        pass

class FaissVectorStore(VectorStore):
    """Реализация векторного хранилища на основе FAISS."""

    def __init__(self, 
                 index_path: str = config.env.FAISS_INDEX_PATH, 
                 metadata_path: str = config.env.METADATA_PATH,
                 embedding_dim: int = 1536): # Размер эмбеддингов для text-embedding-ada-002
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.embedding_dim = embedding_dim
        
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[int, Dict[str, Any]] = {}

        self.load()

    def add(self, documents: List[Document]):
        if not documents:
            logger.info("Нет документов для добавления в FAISS.")
            return

        embeddings = np.array([doc.metadata['embedding'] for doc in documents]).astype('float32')
        if self.index is None:
            logger.info(f"Создание нового FAISS-индекса с размерностью {self.embedding_dim}.")
            # Используем IndexFlatL2, так как он простой и не требует тренировки
            self.index = faiss.IndexFlatL2(self.embedding_dim)

        start_index = self.index.ntotal
        self.index.add(embeddings)
        logger.info(f"Добавлено {len(embeddings)} векторов в FAISS. Общий размер: {self.index.ntotal}.")

        for i, doc in enumerate(documents):
            # Сохраняем метаданные, но удаляем из них сам эмбеддинг, чтобы не дублировать
            doc_metadata = doc.metadata.copy()
            doc_metadata.pop('embedding', None)
            
            # Добавляем сам текст чанка для удобства
            doc_metadata['text'] = doc.page_content
            
            self.metadata[start_index + i] = doc_metadata
        
        self.save()

    def search(self, query_embedding: np.ndarray, k: int) -> List[Tuple[Document, float]]:
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Поиск в пустом или отсутствующем FAISS-индексе.")
            return []

        query_embedding = np.array(query_embedding).astype('float32').reshape(1, -1)
        
        # Используем k из настроек, если оно меньше количества векторов в индексе
        actual_k = min(k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, actual_k)

        results = []
        for i in range(actual_k):
            idx = indices[0][i]
            dist = distances[0][i]
            
            if idx in self.metadata:
                doc_meta = self.metadata[idx]
                doc = Document(
                    page_content=doc_meta.get('text', ''),
                    metadata={k: v for k, v in doc_meta.items() if k != 'text'}
                )
                results.append((doc, float(dist)))
            else:
                logger.warning(f"Метаданные для индекса {idx} не найдены.")
        
        logger.info(f"Найдено {len(results)} релевантных документов.")
        return results

    def save(self):
        if self.index is not None:
            logger.info(f"Сохранение FAISS-индекса по пути: {self.index_path}")
            faiss.write_index(self.index, str(self.index_path))
        
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"Сохранение метаданных по пути: {self.metadata_path}")

    def load(self):
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                logger.info(f"FAISS-индекс успешно загружен из {self.index_path}. Векторов: {self.index.ntotal}")
            except Exception as e:
                logger.error(f"Не удалось загрузить FAISS-индекс: {e}")
                self.index = None
        else:
            logger.warning(f"Файл FAISS-индекса не найден по пути {self.index_path}. Будет создан новый при добавлении данных.")

        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    # Ключи в JSON всегда строки, преобразуем их обратно в int
                    self.metadata = {int(k): v for k, v in json.load(f).items()}
                logger.info(f"Метаданные успешно загружены из {self.metadata_path}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Не удалось загрузить метаданные: {e}")
        else:
            logger.warning(f"Файл метаданных не найден по пути {self.metadata_path}.")


# Пример использования
if __name__ == '__main__':
    # Убедимся, что конфиг загружен
    if not config:
        raise RuntimeError("Конфигурация не была загружена. Невозможно запустить тест.")

    logger.info("--- Тестирование FaissVectorStore ---")
    
    # 1. Создаем экземпляр
    vector_store = FaissVectorStore()
    
    # 2. Создаем "фейковые" документы с эмбеддингами
    docs_to_add = [
        Document(
            page_content="Первый тестовый документ о кошках.",
            metadata={
                "source": "test.txt",
                "chunk_num": 1,
                "embedding": np.random.rand(1536).tolist() # Используем tolist для сериализации
            }
        ),
        Document(
            page_content="Второй документ, в котором говорится про собак.",
            metadata={
                "source": "test.txt",
                "chunk_num": 2,
                "embedding": np.random.rand(1536).tolist()
            }
        )
    ]

    # 3. Добавляем документы
    vector_store.add(docs_to_add)

    # 4. Сохраняем (происходит автоматически в `add`, но можно и вручную)
    vector_store.save()

    # 5. Создаем новый экземпляр, чтобы проверить загрузку
    logger.info("\n--- Перезагрузка хранилища ---")
    vector_store_loaded = FaissVectorStore()
    
    # 6. Делаем поисковый запрос
    query_emb = np.random.rand(1536)
    search_results = vector_store_loaded.search(query_emb, k=1)

    if search_results:
        doc, score = search_results[0]
        print(f"\nБлижайший найденный документ (Score: {score:.4f}):")
        print(f"  - Содержимое: {doc.page_content}")
        print(f"  - Метаданные: {doc.metadata}")
    else:
        print("\nНичего не найдено.")

    print("\nТестирование завершено.")
