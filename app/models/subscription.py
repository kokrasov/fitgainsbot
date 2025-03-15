from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timedelta
from app.models.base import BaseModel


class SubscriptionType(enum.Enum):
    """Типы подписок"""
    BASIC = "basic"  # Базовая подписка
    PREMIUM = "premium"  # Премиум подписка


class PaymentStatus(enum.Enum):
    """Статусы платежей"""
    PENDING = "pending"  # Ожидание оплаты
    COMPLETED = "completed"  # Оплачено
    FAILED = "failed"  # Ошибка при оплате
    REFUNDED = "refunded"  # Возврат средств


class Subscription(BaseModel):
    """Модель подписки пользователя"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subscription_type = Column(Enum(SubscriptionType), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=False)
    
    # Связь с пользователем и платежами
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    
    @property
    def is_valid(self):
        """Проверка, активна ли подписка в настоящий момент"""
        now = datetime.utcnow()
        return self.is_active and now >= self.start_date and now <= self.end_date
    
    @property
    def days_left(self):
        """Количество дней до окончания подписки"""
        now = datetime.utcnow()
        if now > self.end_date:
            return 0
        return (self.end_date - now).days
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, type={self.subscription_type}, is_active={self.is_active})>"


class Payment(BaseModel):
    """Модель платежа"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscription.id'), nullable=True)
    amount = Column(Integer, nullable=False)  # Сумма в копейках
    currency = Column(String(3), default="RUB")
    payment_method = Column(String(50), nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_id = Column(String(255), nullable=True)  # ID платежа в платежной системе
    description = Column(String(255), nullable=True)
    
    # Связь с пользователем и подпиской
    user = relationship("User")
    subscription = relationship("Subscription", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount/100}, status={self.status})>"
