from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import random
import math

from app.models.user import User, ActivityLevel, DietType
from app.models.nutrition import NutritionPlan, Meal, MealType, Recipe, Product, meal_recipe


async def calculate_recipe_calories(session, recipe):
    """Асинхронный расчет калорий для рецепта"""
    query = select(Product).join(recipe_product).filter(recipe_product.c.recipe_id == recipe.id)
    result = await session.execute(query)
    products = result.scalars().all()

    if not products:
        return 0

    # Упрощенный расчет средних значений
    return sum(product.calories for product in products) / len(products) * 100


async def calculate_recipe_macros(session, recipe):
    """Асинхронный расчет макронутриентов для рецепта"""
    query = select(Product).join(recipe_product).filter(recipe_product.c.recipe_id == recipe.id)
    result = await session.execute(query)
    products = result.scalars().all()

    if not products:
        return {"protein": 0, "fat": 0, "carbs": 0}

    # Упрощенный расчет средних значений
    protein = sum(product.protein for product in products) / len(products)
    fat = sum(product.fat for product in products) / len(products)
    carbs = sum(product.carbs for product in products) / len(products)

    return {"protein": protein, "fat": fat, "carbs": carbs}


def calculate_calories_and_macros(user: User) -> tuple[int, dict]:
    """
    Рассчитывает целевые калории и макронутриенты на основе данных пользователя

    :param user: Пользователь
    :return: Кортеж (целевые калории, словарь с макронутриентами)
    """
    # Проверяем наличие обязательных данных
    if not user.weight or not user.height or not user.age or not user.gender:
        # Возвращаем значения по умолчанию, если данных недостаточно
        return 2500, {'protein': 120, 'fat': 80, 'carbs': 300}

    # Расчет базового метаболизма по формуле Миффлина-Сан Жеора
    if user.gender == 'male':
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
    else:
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161

    # Коэффициент активности
    activity_multipliers = {
        ActivityLevel.SEDENTARY: 1.2,  # Малоподвижный образ жизни
        ActivityLevel.LIGHTLY_ACTIVE: 1.375,  # Тренировки 1-3 раза в неделю
        ActivityLevel.MODERATELY_ACTIVE: 1.55,  # Тренировки 3-5 раз в неделю
        ActivityLevel.VERY_ACTIVE: 1.725,  # Тренировки 6-7 раз в неделю
        ActivityLevel.EXTREMELY_ACTIVE: 1.9  # Тренировки 2 раза в день
    }

    # Получаем множитель активности из словаря (по умолчанию 1.375)
    activity_multiplier = activity_multipliers.get(user.activity_level, 1.375)

    # Расчет суточных потребностей в калориях (TDEE)
    tdee = bmr * activity_multiplier

    # Определяем цель на основе текущего и целевого веса
    # Если целевой вес не задан, используем текущий
    target_weight = user.target_weight or user.weight

    if target_weight > user.weight:
        # Для набора массы добавляем 10-15% калорий
        target_calories = tdee * 1.15
    elif target_weight < user.weight:
        # Для снижения веса уменьшаем на 15-20%
        target_calories = tdee * 0.85
    else:
        # Для поддержания веса используем текущие потребности
        target_calories = tdee

    # Округляем до ближайших 50 калорий
    target_calories = round(target_calories / 50) * 50

    # Расчет макронутриентов с учетом цели
    if target_weight > user.weight:
        # При наборе массы - больше белка и углеводов
        protein_per_kg = 2.0
        fat_percentage = 0.25  # 25% калорий из жиров
    elif target_weight < user.weight:
        # При снижении веса - больше белка, меньше жиров и углеводов
        protein_per_kg = 2.2
        fat_percentage = 0.30  # 30% калорий из жиров
    else:
        # При поддержании - умеренное количество всех нутриентов
        protein_per_kg = 1.8
        fat_percentage = 0.30  # 30% калорий из жиров

    # Расчет целевого потребления белка на основе веса
    target_protein = round(user.weight * protein_per_kg)

    # Расчет целевого потребления жиров
    target_fat = round((target_calories * fat_percentage) / 9)  # 9 калорий на грамм жира

    # Расчет целевого потребления углеводов (оставшиеся калории)
    protein_calories = target_protein * 4  # 4 калории на грамм белка
    fat_calories = target_fat * 9  # 9 калорий на грамм жира
    remaining_calories = target_calories - protein_calories - fat_calories
    target_carbs = round(remaining_calories / 4)  # 4 калории на грамм углеводов

    # Создаем словарь с целевыми макронутриентами
    macros = {
        'protein': target_protein,
        'fat': target_fat,
        'carbs': target_carbs
    }

    return int(target_calories), macros


async def generate_nutrition_plan(session: AsyncSession, user: User, target_calories: int, macros: dict) -> NutritionPlan:
    """
    Генерирует план питания на основе параметров пользователя
    
    :param session: Сессия БД
    :param user: Пользователь
    :param target_calories: Целевое количество калорий
    :param macros: Словарь с целевыми макронутриентами
    :return: NutritionPlan
    """
    # Определяем имя и описание плана
    plan_name = f"План питания для {user.first_name}"
    
    # Определяем описание в зависимости от целей пользователя
    if user.target_weight > user.weight:
        plan_description = (
            "План питания, направленный на набор мышечной массы. "
            "Высокое содержание белка для поддержки роста мышц "
            "и достаточное количество калорий для обеспечения профицита энергии."
        )
    else:
        plan_description = (
            "План питания, направленный на поддержание текущего веса и улучшение состава тела. "
            "Сбалансированное содержание белков, жиров и углеводов для оптимальной производительности."
        )
    
    # Создаем план питания
    nutrition_plan = NutritionPlan(
        user_id=user.id,
        name=plan_name,
        description=plan_description,
        calories_target=target_calories,
        protein_target=macros['protein'],
        fat_target=macros['fat'],
        carbs_target=macros['carbs'],
        is_active=True
    )
    
    # Деактивируем предыдущие планы питания
    await session.execute(
        NutritionPlan.__table__.update()
        .where(NutritionPlan.user_id == user.id, NutritionPlan.id != nutrition_plan.id)
        .values(is_active=False)
    )
    
    session.add(nutrition_plan)
    await session.commit()
    await session.refresh(nutrition_plan)
    
    # Получаем рецепты, подходящие для пользователя
    recipes = await get_recipes_for_user(session, user)
    
    # Если рецептов нет, создаем базовые рецепты
    if not recipes:
        await create_default_recipes(session)
        recipes = await get_recipes_for_user(session, user)
    
    # Добавляем приемы пищи в план
    await add_meals_to_plan(session, nutrition_plan, recipes, target_calories, macros)
    
    # Обновляем план питания в базе данных
    await session.commit()
    
    return nutrition_plan


async def get_recipes_for_user(session: AsyncSession, user: User) -> list[Recipe]:
    """
    Получает список рецептов, подходящих для пользователя
    
    :param session: Сессия БД
    :param user: Пользователь
    :return: Список рецептов
    """
    # Базовый запрос на получение рецептов
    query = select(Recipe)
    
    # Если у пользователя есть диетические ограничения, учитываем их
    if user.diet_type != DietType.REGULAR:
        # В будущем здесь можно добавить логику для фильтрации рецептов
        # по типу диеты пользователя, например, вегетарианские/веганские рецепты
        pass
    
    # Если у пользователя есть аллергии, исключаем рецепты с аллергенами
    if user.allergies:
        # В будущем здесь можно добавить логику для исключения рецептов
        # с аллергенами, указанными пользователем
        pass
    
    # Выполняем запрос
    result = await session.execute(query)
    recipes = result.scalars().all()
    
    return recipes


async def add_meals_to_plan(session: AsyncSession, nutrition_plan: NutritionPlan, recipes: list[Recipe], target_calories: int, macros: dict) -> None:
    """
    Добавляет приемы пищи в план питания
    
    :param session: Сессия БД
    :param nutrition_plan: План питания
    :param recipes: Список рецептов
    :param target_calories: Целевое количество калорий
    :param macros: Словарь с целевыми макронутриентами
    """
    # Распределяем калории и макронутриенты по приемам пищи
    meal_distribution = {
        MealType.BREAKFAST: 0.25,  # 25% дневных калорий на завтрак
        MealType.LUNCH: 0.35,      # 35% на обед
        MealType.DINNER: 0.30,     # 30% на ужин
        MealType.SNACK: 0.10       # 10% на перекус
    }
    
    # Создаем приемы пищи
    for meal_type, calorie_ratio in meal_distribution.items():
        # Рассчитываем целевые калории и макронутриенты для приема пищи
        meal_calories = target_calories * calorie_ratio
        meal_protein = macros['protein'] * calorie_ratio
        meal_fat = macros['fat'] * calorie_ratio
        meal_carbs = macros['carbs'] * calorie_ratio
        
        # Устанавливаем время приема пищи
        meal_time = get_meal_time(meal_type)
        
        # Создаем прием пищи
        meal = Meal(
            nutrition_plan_id=nutrition_plan.id,
            meal_type=meal_type,
            time=meal_time
        )
        
        session.add(meal)
        await session.commit()
        await session.refresh(meal)
        
        # Подбираем рецепты для приема пищи
        await add_recipes_to_meal(session, meal, recipes, meal_calories, meal_protein, meal_fat, meal_carbs)


async def add_recipes_to_meal(session, meal, recipes, target_calories, target_protein, target_fat, target_carbs):
    """
    Подбирает рецепты для приема пищи с учетом целевых калорий и макронутриентов
    """
    # Фильтруем рецепты по типу приема пищи
    suitable_recipes = filter_recipes_by_meal_type(recipes, meal.meal_type)

    if not suitable_recipes:
        # Если подходящих рецептов нет, берем все рецепты
        suitable_recipes = recipes

    # Создаем список с калориями для сортировки
    recipes_with_calories = []
    for recipe in suitable_recipes:
        calories = await calculate_recipe_calories(session, recipe)
        recipes_with_calories.append((recipe, calories))

    # Сортируем рецепты по близости к целевым калориям
    sorted_recipes = sorted(recipes_with_calories, key=lambda item: abs(item[1] - target_calories))

    # Выбираем первый рецепт из отсортированного списка и добавляем его к приему пищи
    import random
    if sorted_recipes:
        # Выбираем случайный рецепт из топ-3 наиболее подходящих по калориям
        top_recipes = sorted_recipes[:min(3, len(sorted_recipes))]
        main_recipe, main_calories = random.choice(top_recipes)

        # Избегаем ленивой загрузки meal.recipes, добавляя связь напрямую в таблицу
        await session.execute(
            meal_recipe.insert().values(
                meal_id=meal.id,
                recipe_id=main_recipe.id,
                servings=1.0
            )
        )

    await session.commit()


def filter_recipes_by_meal_type(recipes: list[Recipe], meal_type: MealType) -> list[Recipe]:
    """
    Фильтрует рецепты по типу приема пищи

    :param recipes: Список рецептов
    :param meal_type: Тип приема пищи
    :return: Отфильтрованный список рецептов
    """
    # Разделяем рецепты по типам приемов пищи
    meal_type_recipes = {
        MealType.BREAKFAST: ["Протеиновая овсянка с фруктами", "Омлет с овощами", "Творожная запеканка"],
        MealType.LUNCH: ["Куриная грудка с рисом и овощами", "Гречка с говядиной", "Лосось с сладким картофелем"],
        MealType.DINNER: ["Творог с ягодами и орехами", "Омлет с сыром", "Салат с куриной грудкой"],
        MealType.SNACK: ["Протеиновый коктейль с бананом", "Греческий йогурт с орехами", "Авокадо-тост"]
    }

    # Если для типа приема пищи нет специальных рецептов, используем все рецепты
    if meal_type not in meal_type_recipes:
        return recipes

    # Получаем названия рецептов для данного типа приема пищи
    suitable_recipe_names = meal_type_recipes[meal_type]

    # Фильтруем рецепты по названию
    suitable_recipes = [recipe for recipe in recipes if recipe.name in suitable_recipe_names]

    # Если подходящих рецептов нет, возвращаем все рецепты
    if not suitable_recipes:
        return recipes

    return suitable_recipes


def get_meal_time(meal_type: MealType) -> str:
    """
    Возвращает стандартное время для приема пищи
    
    :param meal_type: Тип приема пищи
    :return: Время в формате "HH:MM"
    """
    meal_times = {
        MealType.BREAKFAST: "08:00",
        MealType.LUNCH: "13:00",
        MealType.DINNER: "19:00",
        MealType.SNACK: "16:00",
        MealType.PRE_WORKOUT: "10:00",
        MealType.POST_WORKOUT: "12:00"
    }
    
    return meal_times.get(meal_type, "12:00")


async def create_default_recipes(session: AsyncSession) -> None:
    """
    Создает базовый набор рецептов и продуктов в базе данных
    
    :param session: Сессия БД
    """
    # Проверяем, есть ли уже рецепты в базе данных
    result = await session.execute(select(func.count()).select_from(Recipe))
    count = result.scalar_one()
    
    if count > 0:
        # Если рецепты уже есть, пропускаем
        return
    
    # Сначала создаем базовые продукты
    products = {
        "chicken_breast": Product(
            name="Куриная грудка",
            category=ProductCategory.MEAT,
            calories=165,
            protein=31,
            fat=3.6,
            carbs=0,
            fiber=0
        ),
        "beef": Product(
            name="Говядина (нежирная)",
            category=ProductCategory.MEAT,
            calories=250,
            protein=26,
            fat=17,
            carbs=0,
            fiber=0
        ),
        "salmon": Product(
            name="Лосось",
            category=ProductCategory.FISH,
            calories=208,
            protein=20,
            fat=13,
            carbs=0,
            fiber=0
        ),
        "eggs": Product(
            name="Яйца куриные",
            category=ProductCategory.DAIRY,
            calories=155,
            protein=13,
            fat=11,
            carbs=1.1,
            fiber=0
        ),
        "milk": Product(
            name="Молоко 2.5%",
            category=ProductCategory.DAIRY,
            calories=52,
            protein=2.8,
            fat=2.5,
            carbs=4.7,
            fiber=0
        ),
        "greek_yogurt": Product(
            name="Греческий йогурт",
            category=ProductCategory.DAIRY,
            calories=59,
            protein=10,
            fat=0.4,
            carbs=3.6,
            fiber=0
        ),
        "cottage_cheese": Product(
            name="Творог 5%",
            category=ProductCategory.DAIRY,
            calories=121,
            protein=18,
            fat=5,
            carbs=3,
            fiber=0
        ),
        "rice": Product(
            name="Рис (вареный)",
            category=ProductCategory.GRAINS,
            calories=130,
            protein=2.7,
            fat=0.3,
            carbs=28,
            fiber=0.4
        ),
        "oats": Product(
            name="Овсянка",
            category=ProductCategory.GRAINS,
            calories=380,
            protein=13,
            fat=7,
            carbs=68,
            fiber=10
        ),
        "buckwheat": Product(
            name="Гречка (вареная)",
            category=ProductCategory.GRAINS,
            calories=110,
            protein=4,
            fat=0.8,
            carbs=20,
            fiber=2.7
        ),
        "bread_whole_grain": Product(
            name="Хлеб цельнозерновой",
            category=ProductCategory.GRAINS,
            calories=265,
            protein=13,
            fat=3.2,
            carbs=43,
            fiber=7
        ),
        "sweet_potato": Product(
            name="Сладкий картофель",
            category=ProductCategory.VEGETABLES,
            calories=86,
            protein=1.6,
            fat=0.1,
            carbs=20,
            fiber=3
        ),
        "potato": Product(
            name="Картофель (вареный)",
            category=ProductCategory.VEGETABLES,
            calories=77,
            protein=2,
            fat=0.1,
            carbs=17,
            fiber=1.8
        ),
        "broccoli": Product(
            name="Брокколи",
            category=ProductCategory.VEGETABLES,
            calories=34,
            protein=2.8,
            fat=0.4,
            carbs=7,
            fiber=2.6
        ),
        "spinach": Product(
            name="Шпинат",
            category=ProductCategory.VEGETABLES,
            calories=23,
            protein=2.9,
            fat=0.4,
            carbs=3.6,
            fiber=2.2
        ),
        "tomato": Product(
            name="Помидоры",
            category=ProductCategory.VEGETABLES,
            calories=18,
            protein=0.9,
            fat=0.2,
            carbs=3.9,
            fiber=1.2
        ),
        "cucumber": Product(
            name="Огурцы",
            category=ProductCategory.VEGETABLES,
            calories=15,
            protein=0.7,
            fat=0.1,
            carbs=3.6,
            fiber=0.5
        ),
        "banana": Product(
            name="Банан",
            category=ProductCategory.FRUITS,
            calories=89,
            protein=1.1,
            fat=0.3,
            carbs=22.8,
            fiber=2.6
        ),
        "apple": Product(
            name="Яблоко",
            category=ProductCategory.FRUITS,
            calories=52,
            protein=0.3,
            fat=0.2,
            carbs=14,
            fiber=2.4
        ),
        "berries": Product(
            name="Ягоды (смесь)",
            category=ProductCategory.FRUITS,
            calories=57,
            protein=0.7,
            fat=0.3,
            carbs=14,
            fiber=2.4
        ),
        "olive_oil": Product(
            name="Оливковое масло",
            category=ProductCategory.OILS,
            calories=884,
            protein=0,
            fat=100,
            carbs=0,
            fiber=0
        ),
        "nuts": Product(
            name="Орехи (смесь)",
            category=ProductCategory.NUTS,
            calories=607,
            protein=21,
            fat=54,
            carbs=19,
            fiber=8.3
        ),
        "avocado": Product(
            name="Авокадо",
            category=ProductCategory.FRUITS,
            calories=160,
            protein=2,
            fat=15,
            carbs=9,
            fiber=7
        ),
        "cheese": Product(
            name="Сыр (твердый)",
            category=ProductCategory.DAIRY,
            calories=402,
            protein=25,
            fat=33,
            carbs=1.3,
            fiber=0
        ),
        "protein_powder": Product(
            name="Протеиновый порошок",
            category=ProductCategory.OTHER,
            calories=380,
            protein=80,
            fat=3.5,
            carbs=7.5,
            fiber=0
        ),
        "honey": Product(
            name="Мед",
            category=ProductCategory.SWEETS,
            calories=304,
            protein=0.3,
            fat=0,
            carbs=82.4,
            fiber=0.2
        )
    }
    
    # Добавляем продукты в базу данных
    for product in products.values():
        session.add(product)
    
    await session.commit()
    
    # Теперь создаем рецепты
    recipes = [
        # Завтраки
        Recipe(
            name="Протеиновая овсянка с фруктами",
            description="Сытная овсянка с добавлением протеина и фруктов",
            prep_time=5,
            cook_time=5,
            servings=1,
            instructions=(
                "1. Смешать овсянку с водой или молоком\n"
                "2. Варить 3-5 минут или подогреть в микроволновке\n"
                "3. Добавить протеиновый порошок и тщательно перемешать\n"
                "4. Добавить нарезанный банан и ягоды\n"
                "5. По желанию добавить мед"
            )
        ),
        Recipe(
            name="Омлет с овощами",
            description="Белковый завтрак с овощами",
            prep_time=5,
            cook_time=10,
            servings=1,
            instructions=(
                "1. Взбить яйца в миске\n"
                "2. Нарезать овощи мелкими кубиками\n"
                "3. Разогреть сковороду с небольшим количеством масла\n"
                "4. Обжарить овощи 2-3 минуты\n"
                "5. Залить овощи взбитыми яйцами\n"
                "6. Готовить под крышкой на среднем огне 5-7 минут"
            )
        ),
        Recipe(
            name="Творожная запеканка",
            description="Высокобелковая запеканка, которую можно приготовить заранее",
            prep_time=10,
            cook_time=30,
            servings=2,
            instructions=(
                "1. Смешать творог с яйцами и медом\n"
                "2. Добавить овсяные хлопья и тщательно перемешать\n"
                "3. Выложить смесь в форму для запекания\n"
                "4. Запекать при 180°C около 30 минут"
            )
        ),
        
        # Обеды
        Recipe(
            name="Куриная грудка с рисом и овощами",
            description="Классический обед бодибилдера",
            prep_time=10,
            cook_time=20,
            servings=1,
            instructions=(
                "1. Нарезать куриную грудку на кусочки\n"
                "2. Обжарить курицу на сковороде до готовности\n"
                "3. Отварить рис согласно инструкции на упаковке\n"
                "4. Нарезать и обжарить овощи\n"
                "5. Смешать все ингредиенты и приправить по вкусу"
            )
        ),
        Recipe(
            name="Гречка с говядиной",
            description="Питательное блюдо, богатое белком и сложными углеводами",
            prep_time=10,
            cook_time=30,
            servings=1,
            instructions=(
                "1. Нарезать говядину небольшими кусочками\n"
                "2. Обжарить говядину до готовности\n"
                "3. Отварить гречку согласно инструкции\n"
                "4. Смешать говядину с гречкой\n"
                "5. Приправить по вкусу"
            )
        ),
        Recipe(
            name="Лосось с сладким картофелем",
            description="Блюдо, богатое белком и полезными жирами",
            prep_time=10,
            cook_time=20,
            servings=1,
            instructions=(
                "1. Разогреть духовку до 200°C\n"
                "2. Приправить лосось солью и перцем\n"
                "3. Нарезать сладкий картофель кубиками и сбрызнуть оливковым маслом\n"
                "4. Запекать лосось и картофель в духовке 15-20 минут"
            )
        ),
        
        # Ужины
        Recipe(
            name="Творог с ягодами и орехами",
            description="Легкий ужин с высоким содержанием белка",
            prep_time=5,
            cook_time=0,
            servings=1,
            instructions=(
                "1. Смешать творог с ягодами\n"
                "2. Посыпать измельченными орехами\n"
                "3. По желанию добавить мед"
            )
        ),
        Recipe(
            name="Омлет с сыром",
            description="Быстрый и белковый ужин",
            prep_time=5,
            cook_time=10,
            servings=1,
            instructions=(
                "1. Взбить яйца в миске\n"
                "2. Добавить тертый сыр\n"
                "3. Приправить солью и перцем\n"
                "4. Вылить на разогретую сковороду с маслом\n"
                "5. Готовить под крышкой 5-7 минут"
            )
        ),
        Recipe(
            name="Салат с куриной грудкой",
            description="Легкий ужин с большим количеством белка",
            prep_time=10,
            cook_time=15,
            servings=1,
            instructions=(
                "1. Отварить или запечь куриную грудку\n"
                "2. Нарезать овощи (огурцы, помидоры, листья салата)\n"
                "3. Нарезать куриную грудку\n"
                "4. Смешать все ингредиенты\n"
                "5. Заправить оливковым маслом"
            )
        ),
        
        # Перекусы
        Recipe(
            name="Протеиновый коктейль с бананом",
            description="Быстрый и питательный перекус",
            prep_time=5,
            cook_time=0,
            servings=1,
            instructions=(
                "1. Смешать в блендере протеиновый порошок, банан и молоко\n"
                "2. Взбить до однородной консистенции"
            )
        ),
        Recipe(
            name="Греческий йогурт с орехами",
            description="Белковый перекус с полезными жирами",
            prep_time=3,
            cook_time=0,
            servings=1,
            instructions=(
                "1. Выложить греческий йогурт в миску\n"
                "2. Посыпать измельченными орехами\n"
                "3. По желанию добавить мед"
            )
        ),
        Recipe(
            name="Авокадо-тост",
            description="Полезный перекус с хорошими жирами и углеводами",
            prep_time=5,
            cook_time=3,
            servings=1,
            instructions=(
                "1. Поджарить ломтик цельнозернового хлеба\n"
                "2. Размять авокадо вилкой\n"
                "3. Намазать авокадо на тост\n"
                "4. Приправить солью и перцем"
            )
        )
    ]
    
    # Добавляем рецепты в базу данных
    for recipe in recipes:
        session.add(recipe)
    
    await session.commit()
    
    # Обновляем рецепты, добавляя к ним продукты
    recipe_products = {
        "Протеиновая овсянка с фруктами": [
            (products["oats"], 50),  # 50г овсянки
            (products["milk"], 200),  # 200мл молока
            (products["protein_powder"], 30),  # 30г протеинового порошка
            (products["banana"], 100),  # 100г банана
            (products["berries"], 50),  # 50г ягод
            (products["honey"], 10)  # 10г меда
        ],
        "Омлет с овощами": [
            (products["eggs"], 150),  # 150г яиц (примерно 3 яйца)
            (products["tomato"], 100),  # 100г помидоров
            (products["spinach"], 50),  # 50г шпината
            (products["olive_oil"], 5)  # 5г оливкового масла
        ],
        "Творожная запеканка": [
            (products["cottage_cheese"], 250),  # 250г творога
            (products["eggs"], 100),  # 100г яиц (примерно 2 яйца)
            (products["oats"], 30),  # 30г овсяных хлопьев
            (products["honey"], 20)  # 20г меда
        ],
        "Куриная грудка с рисом и овощами": [
            (products["chicken_breast"], 150),  # 150г куриной грудки
            (products["rice"], 150),  # 150г риса
            (products["broccoli"], 100),  # 100г брокколи
            (products["olive_oil"], 5)  # 5г оливкового масла
        ],
        "Гречка с говядиной": [
            (products["beef"], 150),  # 150г говядины
            (products["buckwheat"], 150),  # 150г гречки
            (products["olive_oil"], 5)  # 5г оливкового масла
        ],
        "Лосось с сладким картофелем": [
            (products["salmon"], 150),  # 150г лосося
            (products["sweet_potato"], 200),  # 200г сладкого картофеля
            (products["olive_oil"], 10)  # 10г оливкового масла
        ],
        "Творог с ягодами и орехами": [
            (products["cottage_cheese"], 200),  # 200г творога
            (products["berries"], 100),  # 100г ягод
            (products["nuts"], 20),  # 20г орехов
            (products["honey"], 10)  # 10г меда
        ],
        "Омлет с сыром": [
            (products["eggs"], 150),  # 150г яиц (примерно 3 яйца)
            (products["cheese"], 30),  # 30г сыра
            (products["olive_oil"], 5)  # 5г оливкового масла
        ],
        "Салат с куриной грудкой": [
            (products["chicken_breast"], 150),  # 150г куриной грудки
            (products["tomato"], 100),  # 100г помидоров
            (products["cucumber"], 100),  # 100г огурцов
            (products["olive_oil"], 10)  # 10г оливкового масла
        ],
        "Протеиновый коктейль с бананом": [
            (products["protein_powder"], 30),  # 30г протеинового порошка
            (products["banana"], 100),  # 100г банана
            (products["milk"], 250)  # 250мл молока
        ],
        "Греческий йогурт с орехами": [
            (products["greek_yogurt"], 200),  # 200г йогурта
            (products["nuts"], 20),  # 20г орехов
            (products["honey"], 10)  # 10г меда
        ],
        "Авокадо-тост": [
            (products["bread_whole_grain"], 50),  # 50г хлеба
            (products["avocado"], 100),  # 100г авокадо
        ]
    }

    # Получаем все рецепты из базы данных
    all_recipes = (await session.execute(select(Recipe))).scalars().all()

    # Связываем рецепты с продуктами
    for recipe in all_recipes:
        if recipe.name in recipe_products:
            for product, amount in recipe_products[recipe.name]:
                # Создаем запись в ассоциативной таблице
                await session.execute(
                    recipe_product.insert().values(
                        recipe_id=recipe.id,
                        product_id=product.id,
                        amount=amount
                    )
                )
    
    await session.commit()


from app.models.nutrition import ProductCategory, recipe_product
