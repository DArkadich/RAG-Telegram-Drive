from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from loguru import logger

from config import config

class TextSplitter:
    """
    Класс для разделения текста на чанки с использованием LangChain.
    """
    def __init__(self, 
                 chunk_size: int = config.app.rag.chunk_size, 
                 chunk_overlap: int = config.app.rag.chunk_overlap):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,
        )
        logger.info(
            f"Инициализирован TextSplitter: "
            f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}"
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Разделяет список документов LangChain на более мелкие чанки.

        Args:
            documents (List[Document]): Список документов для разделения.

        Returns:
            List[Document]: Плоский список чанков (тоже в виде документов).
        """
        if not documents:
            return []
            
        logger.info(f"Начинается разделение {len(documents)} документа(ов) на чанки...")
        chunked_docs = self.splitter.split_documents(documents)
        
        # Добавим номер чанка в метаданные для удобства
        # Группируем чанки по исходному файлу
        source_files = {doc.metadata.get('source', 'unknown'): [] for doc in chunked_docs}
        for doc in chunked_docs:
            source_files[doc.metadata.get('source', 'unknown')].append(doc)
            
        # Нумеруем чанки в рамках каждого файла
        for source in source_files:
            for i, doc in enumerate(source_files[source]):
                doc.metadata["chunk_number"] = i + 1

        logger.info(f"Разделение завершено. Получено {len(chunked_docs)} чанков.")
        return chunked_docs

# Пример использования
if __name__ == '__main__':
    if not config:
        raise RuntimeError("Конфигурация не была загружена.")

    logger.info("--- Тестирование TextSplitter ---")

    # 1. Создаем "фейковый" длинный документ
    with open("long_text_example.txt", "w", encoding="utf-8") as f:
        f.write("Это первое предложение. " * 100)
        f.write("\n\n") # Разделитель параграфов
        f.write("Это второе предложение, оно тоже очень длинное. " * 150)
        f.write("\n\n")
        f.write("А это третье, короткое.")

    with open("long_text_example.txt", "r", encoding="utf-8") as f:
        text_content = f.read()

    doc = Document(page_content=text_content, metadata={"source": "long_text_example.txt"})

    # 2. Инициализируем сплиттер
    text_splitter = TextSplitter(chunk_size=700, chunk_overlap=100)
    
    # 3. Разделяем документ
    chunks = text_splitter.split_documents([doc])

    print(f"\nДокумент был разделен на {len(chunks)} чанков.")
    
    if chunks:
        print("\n--- Пример первого чанка ---")
        print(f"Содержимое: '{chunks[0].page_content[:200]}...'")
        print(f"Метаданные: {chunks[0].metadata}")
        
        print("\n--- Пример второго чанка ---")
        print(f"Содержимое: '{chunks[1].page_content[:200]}...'")
        print(f"Метаданные: {chunks[1].metadata}")

        # Проверка overlap
        overlap_start = chunks[1].page_content[:100]
        print(f"\nНачало второго чанка (overlap): '{overlap_start}'")
        
        is_overlap_correct = chunks[0].page_content.endswith(overlap_start)
        print(f"Перекрытие совпадает с концом первого чанка: {is_overlap_correct}")

    import os
    os.remove("long_text_example.txt")

    logger.info("\nТестирование завершено.")
