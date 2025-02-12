import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

class Config:
    def __init__(self):
        self._load_env()
        self._setup_logging()
        
    def _load_env(self):
        """Загрузка переменных окружения"""
        load_dotenv()
        
        self.bot_token = os.getenv("BOT_TOKEN")
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
        self.food_api_key = os.getenv("FOOD_API_KEY", "iYNcjx3WdiVo8iHPixsQjsTyVNWvBeuyB0EDeYW3")
        
        if not self.bot_token or not self.weather_api_key:
            raise ValueError("Не установлены необходимые переменные окружения")
            
    def _setup_logging(self):
        """Настройка системы логирования"""
        # Создаем директорию для логов если её нет
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем форматирование
        console_formatter = logging.Formatter(
            '%(asctime)s  %(levelname)s     %(message)s',
            datefmt='%b %d %I:%M:%S %p'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Файловый handler с ротацией
        file_handler = RotatingFileHandler(
            log_dir / "bot.log",
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        
        # Консольный handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Настраиваем корневой логгер
        self.logger = logging.getLogger("FitnessBot")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Отключаем логи от библиотек, но оставляем критические ошибки
        for log_name in ["aiohttp", "aiogram"]:
            lib_logger = logging.getLogger(log_name)
            lib_logger.setLevel(logging.ERROR)
            lib_logger.addHandler(console_handler)
            
        # Логируем успешную настройку
        self.logger.info("Система логирования настроена")
        self.logger.info("Конфигурация загружена успешно")
        
    @property
    def BOT_TOKEN(self) -> str:
        return self.bot_token
        
    @property
    def WEATHER_API_KEY(self) -> str:
        return self.weather_api_key
        
    @property
    def FOOD_API_KEY(self) -> str:
        return self.food_api_key

# Создаем глобальный экземпляр конфигурации
config = Config()

# Экспортируем для обратной совместимости
BOT_TOKEN = config.BOT_TOKEN
WEATHER_API_KEY = config.WEATHER_API_KEY
FOOD_API_KEY = config.FOOD_API_KEY
logger = config.logger 