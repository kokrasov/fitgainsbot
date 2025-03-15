from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, Date, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Progress(BaseModel):
    """Модель записи прогресса пользователя"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    weight = Column(Float, nullable=True)  # Вес в кг
    
    # Замеры тела (в см)
    chest = Column(Float, nullable=True)  # Грудь
    waist = Column(Float, nullable=True)  # Талия
    hips = Column(Float, nullable=True)   # Бедра
    biceps_left = Column(Float, nullable=True)  # Левый бицепс
    biceps_right = Column(Float, nullable=True)  # Правый бицепс
    thigh_left = Column(Float, nullable=True)   # Левое бедро
    thigh_right = Column(Float, nullable=True)  # Правое бедро
    calf_left = Column(Float, nullable=True)    # Левая икра
    calf_right = Column(Float, nullable=True)   # Правая икра
    
    # Дополнительные показатели
    body_fat_percentage = Column(Float, nullable=True)  # Процент жира в теле
    muscle_mass = Column(Float, nullable=True)         # Мышечная масса в кг
    water_percentage = Column(Float, nullable=True)    # Процент воды в теле
    
    # Числовые показатели прогресса в упражнениях
    strength_data = Column(JSON, nullable=True)  # JSON с данными о силовых показателях
    
    # Заметки
    notes = Column(Text, nullable=True)
    
    # Связь с пользователем и фотографиями
    user = relationship("User", back_populates="progress_records")
    photos = relationship("ProgressPhoto", back_populates="progress", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Progress(id={self.id}, date={self.date}, user_id={self.user_id}, weight={self.weight})>"


class ProgressPhoto(BaseModel):
    """Модель фотографии прогресса"""
    
    progress_id = Column(Integer, ForeignKey('progress.id', ondelete='CASCADE'), nullable=False)
    photo_type = Column(String(50), nullable=False)  # front, side, back
    photo_path = Column(String(255), nullable=False)  # Путь к файлу фотографии
    
    # Связь с записью прогресса
    progress = relationship("Progress", back_populates="photos")
    
    def __repr__(self):
        return f"<ProgressPhoto(id={self.id}, progress_id={self.progress_id}, photo_type={self.photo_type})>"
