import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Импорт моделей
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.models.base import BaseModel
from app.models.user import User
from app.models.workout import Workout, WorkoutPlan, Exercise
from app.models.nutrition import NutritionPlan, Meal, Recipe, Product
from app.models.progress import Progress, ProgressPhoto
from app.models.subscription import Subscription, Payment
from app.utils.db import Base

from app.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Интерпретация файла конфигурации для Logger Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Добавляем URL подключения
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Целевая метаинформация, которую мы хотим создать
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Запуск миграций в режиме "offline".
    
    Эта функция выключает выполнение SQL, но вместо этого создает
    скрипты для запуска позднее.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Запуск миграций в режиме "online".
    
    В этом сценарии мы создаем Engine и связываем соединение с контекстом.
    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
