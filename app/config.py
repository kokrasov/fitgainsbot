import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Простой класс настроек без Pydantic
class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Telegram Bot настройки
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "")
        
        # Администраторы
        self.ADMINS = []
        admins_str = os.getenv("ADMINS", "")
        if admins_str:
            try:
                self.ADMINS = [int(admin_id.strip()) for admin_id in admins_str.split(",") if admin_id.strip()]
            except (ValueError, TypeError):
                pass
        
        # База данных
        self.DB_USER = os.getenv("DB_USER", "postgres")
        self.DB_PASS = os.getenv("DB_PASS", "postgres")
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        self.DB_NAME = os.getenv("DB_NAME", "fitgains")
        
        # Настройки приложения
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Цены на подписки (в копейках)
        self.BASIC_SUBSCRIPTION_PRICE = 30000  # 300 рублей
        self.PREMIUM_SUBSCRIPTION_PRICE = 50000  # 500 рублей
        
        # Цены на разовые услуги (в копейках)
        self.PERSONAL_NUTRITION_PRICE = 9900  # 99 рублей
        self.PERSONAL_WORKOUT_PRICE = 19900  # 199 рублей
        self.TRAINER_CONSULTATION_PRICE = 29900  # 299 рублей
    
    @property
    def DATABASE_URL(self):
        """Получить строку подключения к БД"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Создаем экземпляр настроек
settings = Settings()