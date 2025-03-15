from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
import enum
from datetime import date
from app.models.base import BaseModel


class ActivityLevel(enum.Enum):
    """Уровень активности пользователя"""
    SEDENTARY = "sedentary"          # Сидячий образ жизни
    LIGHTLY_ACTIVE = "lightly_active" # Легкая активность (1-2 тренировки в неделю)
    MODERATELY_ACTIVE = "moderately_active" # Умеренная активность (3-5 тренировок в неделю)
    VERY_ACTIVE = "very_active"      # Высокая активность (6-7 тренировок в неделю)
    EXTREMELY_ACTIVE = "extremely_active" # Экстремальная активность (профессиональный спорт)


class ExperienceLevel(enum.Enum):
    """Уровень опыта пользователя"""
    BEGINNER = "beginner"            # Новичок (0-6 месяцев)
    INTERMEDIATE = "intermediate"    # Средний (6 месяцев - 2 года)
    ADVANCED = "advanced"            # Продвинутый (2+ лет)


class DietType(enum.Enum):
    """Тип диеты пользователя"""
    REGULAR = "regular"              # Обычная диета
    VEGETARIAN = "vegetarian"        # Вегетарианская
    VEGAN = "vegan"                  # Веганская
    KETO = "keto"                    # Кето
    PALEO = "paleo"                  # Палео
    MEDITERRANEAN = "mediterranean"  # Средиземноморская


class User(BaseModel):
    """Модель пользователя"""
    
    # Основные поля
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Параметры для расчета программы
    gender = Column(String(10), nullable=True)  # male/female
    birthdate = Column(Date, nullable=True)
    height = Column(Float, nullable=True)       # в сантиметрах
    weight = Column(Float, nullable=True)       # в килограммах
    target_weight = Column(Float, nullable=True)  # целевой вес
    activity_level = Column(Enum(ActivityLevel), nullable=True)
    experience_level = Column(Enum(ExperienceLevel), nullable=True)
    
    # Параметры питания
    diet_type = Column(Enum(DietType), default=DietType.REGULAR)
    allergies = Column(Text, nullable=True)  # Через запятую
    calories_goal = Column(Integer, nullable=True)
    protein_goal = Column(Integer, nullable=True)  # в граммах
    fat_goal = Column(Integer, nullable=True)     # в граммах
    carbs_goal = Column(Integer, nullable=True)   # в граммах
    
    # Параметры тренировок
    has_gym_access = Column(Boolean, default=False)
    training_days_per_week = Column(Integer, default=3)
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")


    
    # Статус подписки
    is_premium = Column(Boolean, default=False)
    
    # Отношения с другими таблицами
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    nutrition_plans = relationship("NutritionPlan", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def age(self):
        """Вычисляет возраст пользователя"""
        if not self.birthdate:
            return None
            
        today = date.today()
        return today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )
        
    @property
    def bmi(self):
        """Вычисляет индекс массы тела (ИМТ)"""
        if not self.height or not self.weight:
            return None
            
        # Формула: вес (кг) / (рост (м) ^ 2)
        height_in_meters = self.height / 100
        return self.weight / (height_in_meters ** 2)
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
