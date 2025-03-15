from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, Date, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel


# Таблица связи между планами тренировок и упражнениями
workout_exercise = Table(
    'workout_exercise',
    BaseModel.metadata,
    Column('workout_plan_id', Integer, ForeignKey('workoutplan.id', ondelete='CASCADE')),
    Column('exercise_id', Integer, ForeignKey('exercise.id')),
    Column('sets', Integer, default=3),
    Column('reps', String, default="8-12"),  # Может быть в формате "8-12" или "до отказа"
    Column('rest', Integer, default=90),  # Отдых между подходами в секундах
    Column('order', Integer, default=0)  # Порядок выполнения
)


class MuscleGroup(enum.Enum):
    """Группы мышц"""
    CHEST = "chest"              # Грудные
    BACK = "back"                # Спина
    LEGS = "legs"                # Ноги
    SHOULDERS = "shoulders"      # Плечи
    BICEPS = "biceps"            # Бицепс
    TRICEPS = "triceps"          # Трицепс
    ABS = "abs"                  # Пресс
    CALVES = "calves"            # Икры
    FOREARMS = "forearms"        # Предплечья
    FULL_BODY = "full_body"      # Все тело


class ExerciseType(enum.Enum):
    """Типы упражнений"""
    COMPOUND = "compound"        # Базовые
    ISOLATION = "isolation"      # Изолированные
    CARDIO = "cardio"            # Кардио
    STRETCHING = "stretching"    # Растяжка


class Equipment(enum.Enum):
    """Оборудование для упражнений"""
    NONE = "none"                # Без оборудования
    DUMBBELLS = "dumbbells"      # Гантели
    BARBELL = "barbell"          # Штанга
    KETTLEBELL = "kettlebell"    # Гиря
    CABLE = "cable"              # Тросовый тренажер
    MACHINE = "machine"          # Тренажер
    BANDS = "bands"              # Резиновые ленты


class Exercise(BaseModel):
    """Модель упражнения"""
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    muscle_group = Column(Enum(MuscleGroup), nullable=False)
    exercise_type = Column(Enum(ExerciseType), nullable=False)
    equipment = Column(Enum(Equipment), nullable=False)
    difficulty = Column(Integer, default=1)  # От 1 до 5
    video_url = Column(String(255), nullable=True)
    image_url = Column(String(255), nullable=True)
    instructions = Column(Text, nullable=True)
    
    # Связь с планами тренировок
    workout_plans = relationship("WorkoutPlan", secondary=workout_exercise, back_populates="exercises")
    
    def __repr__(self):
        return f"<Exercise(id={self.id}, name={self.name}, muscle_group={self.muscle_group})>"


class WorkoutPlan(BaseModel):
    """Модель плана тренировок"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    days_per_week = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="workout_plans")
    exercises = relationship("Exercise", secondary=workout_exercise, back_populates="workout_plans")
    workout_sessions = relationship("Workout", back_populates="workout_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WorkoutPlan(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Workout(BaseModel):
    """Модель тренировки (записи о выполненной тренировке)"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    workout_plan_id = Column(Integer, ForeignKey('workoutplan.id'), nullable=True)
    date = Column(Date, nullable=False)
    duration = Column(Integer, nullable=True)  # Длительность в минутах
    completed = Column(Boolean, default=False)
    exercises_data = Column(JSON, nullable=True)  # JSON с информацией о выполненных упражнениях
    notes = Column(Text, nullable=True)
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="workouts")
    workout_plan = relationship("WorkoutPlan", back_populates="workout_sessions")
    
    def __repr__(self):
        return f"<Workout(id={self.id}, date={self.date}, user_id={self.user_id})>"
