import asyncio
import os
from app.utils.db import init_models

async def main():
    # Создаем директорию для данных, если её нет
    os.makedirs("data/photos", exist_ok=True)
    
    # Инициализируем модели (создаем таблицы)
    await init_models()
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())