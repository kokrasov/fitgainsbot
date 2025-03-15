from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings

# Создание асинхронного движка для работы с базой данных
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True if settings.LOG_LEVEL == "DEBUG" else False,
)

# Создание фабрики сессий для работы с базой данных
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Базовый класс для всех моделей
Base = declarative_base()


async def get_session() -> AsyncSession:
    """
    Генератор сессий для работы с базой данных
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_models():
    """
    Инициализация моделей в базе данных
    """
    from app.models.base import BaseModel
    from app.models.user import User
    from app.models.workout import Workout, Exercise, WorkoutPlan
    from app.models.nutrition import NutritionPlan, Meal, Recipe, Product
    from app.models.progress import Progress, ProgressPhoto
    from app.models.subscription import Subscription, Payment
    
    async with engine.begin() as conn:
        # Для разработки - пересоздаем таблицы
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
