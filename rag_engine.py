import openai
from typing import List, Tuple
from langchain.schema import Document
from loguru import logger

from config import config
from drive_loader import DriveLoader
from text_extractor import TextExtractor
from text_splitter import TextSplitter
from embedder import OpenAIEmbedder
from vector_store import FaissVectorStore

class RagEngine:
    """
    Класс, координирующий весь RAG-пайплайн.
    """
    def __init__(self):
        logger.info("Инициализация RagEngine...")
        # Инициализация всех компонентов
        self.drive_loader = DriveLoader()
        self.text_extractor = TextExtractor()
        self.text_splitter = TextSplitter()
        self.embedder = OpenAIEmbedder()
        self.vector_store = FaissVectorStore()
        
        # Настройка клиента OpenAI для генерации ответов
        self.openai_client = openai.OpenAI(api_key=config.env.OPENAI_API_KEY)
        self.generation_model = config.app.openai.generation_model

        # Проверяем, пуста ли база знаний при старте
        if self.vector_store.index is None or self.vector_store.index.ntotal == 0:
            logger.warning("База знаний пуста. Запускаю первоначальную синхронизацию...")
            self.sync_knowledge_base()

        logger.info("RagEngine успешно инициализирован.")

    def sync_knowledge_base(self):
        """
        Полный цикл обновления базы знаний с рекурсивным обходом папок.
        """
        logger.info("--- Начало полной синхронизации базы знаний ---")
        
        folders_to_scan = [config.env.GDRIVE_FOLDER_ID]
        processed_folders = set()
        all_new_chunks = []

        while folders_to_scan:
            folder_id = folders_to_scan.pop(0)
            if folder_id in processed_folders:
                continue
            
            logger.info(f"Сканирование папки Google Drive: {folder_id}")
            processed_folders.add(folder_id)

            # 1. Скачивание
            new_files = self.drive_loader.download_new_files(folder_id)
            if not new_files:
                logger.info(f"В папке {folder_id} новых файлов для обработки нет.")
                continue

            # 2. Извлечение текста и ссылок
            extracted_docs = []
            for file_path in new_files:
                doc, new_links = self.text_extractor.extract_from_file(file_path)
                if doc:
                    extracted_docs.append(doc)
                if new_links:
                    for link_id in new_links:
                        if link_id not in processed_folders and link_id not in folders_to_scan:
                            folders_to_scan.append(link_id)
            
            if not extracted_docs:
                logger.info("Не удалось извлечь текст из скачанных файлов в этой папке.")
                continue

            # 3. Разделение на чанки
            chunks = self.text_splitter.split_documents(extracted_docs)
            if chunks:
                all_new_chunks.extend(chunks)

        if not all_new_chunks:
            logger.info("Нового контента для добавления в базу не найдено.")
            logger.info("--- Синхронизация базы знаний завершена (без изменений) ---")
            return

        # 4. Создание эмбеддингов для всех собранных чанков
        logger.info(f"Создание эмбеддингов для {len(all_new_chunks)} новых чанков...")
        texts_to_embed = [chunk.page_content for chunk in all_new_chunks]
        try:
            embeddings = self.embedder.get_embeddings(texts_to_embed)
            # Добавляем эмбеддинги в метаданные каждого чанка
            for i, chunk in enumerate(all_new_chunks):
                chunk.metadata["embedding"] = embeddings[i]
        except Exception as e:
            logger.error(f"Не удалось создать эмбеддинги: {e}")
            return
            
        # 5. Добавление в векторное хранилище
        self.vector_store.add(all_new_chunks)
        
        logger.info("--- Синхронизация базы знаний успешно завершена ---")

    def _build_prompt(self, question: str, context_chunks: List[Document]) -> str:
        """Формирует промпт для LLM."""
        context = "\n\n---\n\n".join([chunk.page_content for chunk in context_chunks])
        
        prompt_template = """
Используй следующий контекст, чтобы ответить на вопрос в конце.
Если ты не знаешь ответа на основе предоставленного контекста, просто скажи, что не знаешь. Не пытайся выдумать ответ.
Отвечай кратко и по существу, если не попросят иного.

Контекст:
{context}

Вопрос: {question}
Ответ:
"""
        return prompt_template.format(context=context, question=question)

    def answer_query(self, question: str) -> str:
        """
        Выполняет RAG-пайплайн для ответа на вопрос пользователя.
        """
        logger.info(f"Получен новый вопрос: '{question}'")
        
        # 1. Создание эмбеддинга для вопроса
        try:
            query_embedding = self.embedder.get_embedding(question)
        except Exception as e:
            logger.error(f"Не удалось создать эмбеддинг для вопроса: {e}")
            return "Ошибка: не удалось обработать ваш вопрос."

        # 2. Поиск релевантных чанков в базе
        k = config.app.rag.top_k
        search_results = self.vector_store.search(query_embedding, k=k)
        
        if not search_results:
            logger.warning("Релевантных документов в базе не найдено.")
            return "К сожалению, в моей базе знаний нет информации по вашему вопросу."
            
        relevant_chunks = [doc for doc, score in search_results]

        # 3. Построение промпта
        prompt = self._build_prompt(question, relevant_chunks)
        logger.debug(f"Сформированный промпт для LLM:\n{prompt}")

        # 4. Генерация ответа
        try:
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "Ты — полезный ассистент, который отвечает на вопросы на основе предоставленного контекста."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            answer = response.choices[0].message.content
            logger.info(f"Получен ответ от LLM: '{answer}'")
            return answer
        except Exception as e:
            logger.error(f"Ошибка при вызове API OpenAI для генерации ответа: {e}")
            return "Ошибка: не удалось получить ответ от языковой модели."

# Пример использования
if __name__ == '__main__':
    if not config:
        raise RuntimeError("Конфигурация не загружена.")
        
    logger.info("--- Тестирование RagEngine ---")
    
    # Для этого теста убедитесь, что все ваши .env и settings.json настроены,
    # и в папке на Google Drive есть хотя бы один PDF или DOCX файл.
    try:
        engine = RagEngine()
        
        # Пример вопроса. Замените на свой, релевантный вашим документам.
        test_question = "Что написано в разделе 'Условия поставки'?"
        
        print(f"\nОтправка тестового вопроса: '{test_question}'")
        answer = engine.answer_query(test_question)
        
        print(f"\nПолученный ответ:\n{answer}")

    except Exception as e:
        logger.critical(f"Во время тестирования RagEngine произошла критическая ошибка: {e}", exc_info=True)
        
    logger.info("\nТестирование завершено.")
