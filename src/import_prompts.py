import logging
import sys

from excel_prompt_importer import ExcelPromptImporter


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('import_prompts.log')
        ]
    )


def main():
    """Основная функция импорта промптов"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Инициализируем импортер промптов
        importer = ExcelPromptImporter()

        # Обрабатываем файлы
        processed_count = importer.process_income_files()

        if processed_count > 0:
            logger.info(f"Успешно обработано промптов: {processed_count}")
        else:
            logger.warning("Промпты не были обработаны")

    except Exception as e:
        logger.error(f"Ошибка при импорте промптов: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
