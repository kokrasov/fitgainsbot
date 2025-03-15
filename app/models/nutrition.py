from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, Date, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel


# Таблица связи между рецептами и продуктами
recipe_product = Table(
    'recipe_product',
    BaseModel.metadata,
    Column('recipe_id', Integer, ForeignKey('recipe.id', ondelete='CASCADE')),
    Column('product_id', Integer, ForeignKey('product.id')),
    Column('amount', Float, nullable=False),  # Количество в граммах или мл
)


# Таблица связи между приемами пищи и рецептами
meal_recipe = Table(
    'meal_recipe',
    BaseModel.metadata,
    Column('meal_id', Integer, ForeignKey('meal.id', ondelete='CASCADE')),
    Column('recipe_id', Integer, ForeignKey('recipe.id')),
    Column('servings', Float, default=1.0),  # Количество порций
)


class MealType(enum.Enum):
    """Типы приемов пищи"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    PRE_WORKOUT = "pre_workout"
    POST_WORKOUT = "post_workout"


class ProductCategory(enum.Enum):
    """Категории продуктов"""
    MEAT = "meat"
    FISH = "fish"
    DAIRY = "dairy"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    GRAINS = "grains"
    NUTS = "nuts"
    LEGUMES = "legumes"
    OILS = "oils"
    SPICES = "spices"
    SWEETS = "sweets"
    DRINKS = "drinks"
    OTHER = "other"


class Product(BaseModel):
    """Модель продукта"""
    
    name = Column(String(255), nullable=False)
    category = Column(Enum(ProductCategory), nullable=False)
    calories = Column(Float, nullable=False)  # На 100г/мл
    protein = Column(Float, nullable=False)   # На 100г/мл
    fat = Column(Float, nullable=False)       # На 100г/мл
    carbs = Column(Float, nullable=False)     # На 100г/мл
    fiber = Column(Float, nullable=True)      # На 100г/мл
    
    # Связь с рецептами
    recipes = relationship("Recipe", secondary=recipe_product, back_populates="products")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, calories={self.calories})>"


class Recipe(BaseModel):
    """Модель рецепта"""
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    prep_time = Column(Integer, nullable=True)  # Время подготовки в минутах
    cook_time = Column(Integer, nullable=True)  # Время приготовления в минутах
    servings = Column(Integer, default=1)
    image_url = Column(String(255), nullable=True)
    
    # Связь с продуктами и приемами пищи
    products = relationship("Product", secondary=recipe_product, back_populates="recipes")
    meals = relationship("Meal", secondary=meal_recipe, back_populates="recipes")
    
    @property
    def total_calories(self):
        """Рассчитать общее количество калорий в рецепте"""
        total = 0
        for assoc in self.recipe_product_associations:
            total += assoc.product.calories * (assoc.amount / 100)
        return total
    
    @property
    def macros(self):
        """Рассчитать содержание макронутриентов в рецепте"""
        protein = sum(assoc.product.protein * (assoc.amount / 100) for assoc in self.recipe_product_associations)
        fat = sum(assoc.product.fat * (assoc.amount / 100) for assoc in self.recipe_product_associations)
        carbs = sum(assoc.product.carbs * (assoc.amount / 100) for assoc in self.recipe_product_associations)
        
        return {
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        }
    
    def __repr__(self):
        return f"<Recipe(id={self.id}, name={self.name})>"


class Meal(BaseModel):
    """Модель приема пищи"""
    
    nutrition_plan_id = Column(Integer, ForeignKey('nutritionplan.id', ondelete='CASCADE'), nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    time = Column(String(5), nullable=True)  # Формат "HH:MM"
    
    # Связь с рецептами и планом питания
    recipes = relationship("Recipe", secondary=meal_recipe, back_populates="meals")
    nutrition_plan = relationship("NutritionPlan", back_populates="meals")
    
    @property
    def total_calories(self):
        """Рассчитать общее количество калорий в приеме пищи"""
        total = 0
        for assoc in self.meal_recipe_associations:
            total += assoc.recipe.total_calories * assoc.servings
        return total
    
    @property
    def macros(self):
        """Рассчитать содержание макронутриентов в приеме пищи"""
        protein = 0
        fat = 0
        carbs = 0
        
        for assoc in self.meal_recipe_associations:
            recipe_macros = assoc.recipe.macros
            protein += recipe_macros["protein"] * assoc.servings
            fat += recipe_macros["fat"] * assoc.servings
            carbs += recipe_macros["carbs"] * assoc.servings
        
        return {
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        }
    
    def __repr__(self):
        return f"<Meal(id={self.id}, meal_type={self.meal_type}, nutrition_plan_id={self.nutrition_plan_id})>"


class NutritionPlan(BaseModel):
    """Модель плана питания"""
    
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    calories_target = Column(Integer, nullable=True)
    protein_target = Column(Integer, nullable=True)
    fat_target = Column(Integer, nullable=True)
    carbs_target = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Связь с пользователем и приемами пищи
    user = relationship("User", back_populates="nutrition_plans")
    meals = relationship("Meal", back_populates="nutrition_plan", cascade="all, delete-orphan")
    
    @property
    def total_calories(self):
        """Рассчитать общее количество калорий в плане питания"""
        return sum(meal.total_calories for meal in self.meals)
    
    @property
    def macros(self):
        """Рассчитать содержание макронутриентов в плане питания"""
        protein = sum(meal.macros["protein"] for meal in self.meals)
        fat = sum(meal.macros["fat"] for meal in self.meals)
        carbs = sum(meal.macros["carbs"] for meal in self.meals)
        
        return {
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        }
    
    def __repr__(self):
        return f"<NutritionPlan(id={self.id}, name={self.name}, user_id={self.user_id})>"
