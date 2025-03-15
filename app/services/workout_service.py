from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import random

from app.models.user import User, ExperienceLevel
from app.models.workout import WorkoutPlan, Exercise, MuscleGroup, ExerciseType, Equipment


async def generate_workout_plan(session: AsyncSession, user: User) -> WorkoutPlan:
    """
    Генерирует план тренировок на основе параметров пользователя
    
    :param session: Сессия БД
    :param user: Пользователь
    :return: WorkoutPlan
    """
    # Определяем имя и описание плана
    plan_name = f"Программа для {user.first_name}"
    
    # Определяем описание в зависимости от опыта пользователя
    plan_description = ""
    if user.experience_level == ExperienceLevel.BEGINNER:
        plan_description = (
            "Программа для начинающих, направленная на развитие базовых двигательных навыков "
            "и укрепление основных групп мышц. Подходит для тех, кто только начинает тренироваться."
        )
    elif user.experience_level == ExperienceLevel.INTERMEDIATE:
        plan_description = (
            "Программа среднего уровня сложности, направленная на увеличение силы и мышечной массы. "
            "Включает разнообразные упражнения для комплексного развития."
        )
    elif user.experience_level == ExperienceLevel.ADVANCED:
        plan_description = (
            "Продвинутая программа для опытных атлетов, направленная на максимальное развитие "
            "силы и мышечной массы. Включает интенсивные и сложные упражнения."
        )
    else:
        plan_description = (
            "Персонализированная программа тренировок, направленная на развитие силы и набор "
            "мышечной массы с учетом ваших индивидуальных параметров."
        )
    
    # Создаем план тренировок
    workout_plan = WorkoutPlan(
        user_id=user.id,
        name=plan_name,
        description=plan_description,
        days_per_week=user.training_days_per_week,
        is_active=True
    )
    
    session.add(workout_plan)
    await session.commit()
    await session.refresh(workout_plan)
    
    # Получаем упражнения, подходящие для пользователя
    exercises = await get_exercises_for_user(session, user)
    
    # Группируем упражнения по группам мышц
    exercise_groups = {}
    for exercise in exercises:
        group = exercise.muscle_group.value
        if group not in exercise_groups:
            exercise_groups[group] = []
        exercise_groups[group].append(exercise)
    
    # Определяем набор упражнений в зависимости от опыта и количества дней тренировок
    if user.training_days_per_week <= 3:
        # При тренировках 2-3 раза в неделю используем полнотелые тренировки
        # или сплит верх/низ
        if user.experience_level == ExperienceLevel.BEGINNER:
            # Для новичков - полнотелые тренировки
            await add_fullbody_workout(session, workout_plan, exercise_groups)
        else:
            # Для средних и продвинутых - сплит верх/низ
            await add_upper_lower_split(session, workout_plan, exercise_groups)
    else:
        # При тренировках 4-6 раз в неделю используем сплит по группам мышц
        await add_muscle_group_split(session, workout_plan, exercise_groups, user.training_days_per_week)
    
    # Обновляем план тренировок в базе данных
    await session.commit()
    
    return workout_plan


async def get_exercises_for_user(session: AsyncSession, user: User) -> list[Exercise]:
    """
    Получает список упражнений, подходящих для пользователя
    
    :param session: Сессия БД
    :param user: Пользователь
    :return: Список упражнений
    """
    # Базовый запрос на получение упражнений
    query = select(Exercise)
    
    # Если у пользователя нет доступа к тренажерному залу, исключаем упражнения
    # которые требуют специального оборудования
    if not user.has_gym_access:
        query = query.where(
            Exercise.equipment.in_([
                Equipment.NONE, 
                Equipment.DUMBBELLS, 
                Equipment.KETTLEBELL, 
                Equipment.BANDS
            ])
        )
    
    # Если пользователь новичок, исключаем сложные упражнения
    if user.experience_level == ExperienceLevel.BEGINNER:
        query = query.where(Exercise.difficulty <= 3)
    
    # Выполняем запрос
    result = await session.execute(query)
    exercises = result.scalars().all()
    
    return exercises


async def add_fullbody_workout(session: AsyncSession, workout_plan: WorkoutPlan, exercise_groups: dict) -> None:
    """
    Добавляет полнотелую тренировку (все группы мышц в одной тренировке)
    
    :param session: Сессия БД
    :param workout_plan: План тренировок
    :param exercise_groups: Словарь с упражнениями, сгруппированными по группам мышц
    """
    # Определяем основные группы мышц для полнотелой тренировки
    main_muscle_groups = [
        MuscleGroup.CHEST.value,
        MuscleGroup.BACK.value,
        MuscleGroup.LEGS.value,
        MuscleGroup.SHOULDERS.value,
        MuscleGroup.BICEPS.value,
        MuscleGroup.TRICEPS.value,
        MuscleGroup.ABS.value
    ]
    
    # Выбираем по одному упражнению из каждой основной группы мышц
    selected_exercises = []
    for group in main_muscle_groups:
        if group in exercise_groups and exercise_groups[group]:
            # Выбираем случайное упражнение из группы
            exercise = random.choice(exercise_groups[group])
            selected_exercises.append(exercise)
    
    # Добавляем выбранные упражнения в план тренировок
    workout_plan.exercises.extend(selected_exercises)


async def add_upper_lower_split(session: AsyncSession, workout_plan: WorkoutPlan, exercise_groups: dict) -> None:
    """
    Добавляет тренировки по схеме верх/низ
    
    :param session: Сессия БД
    :param workout_plan: План тренировок
    :param exercise_groups: Словарь с упражнениями, сгруппированными по группам мышц
    """
    # Определяем группы мышц для верхней части тела
    upper_body_groups = [
        MuscleGroup.CHEST.value,
        MuscleGroup.BACK.value,
        MuscleGroup.SHOULDERS.value,
        MuscleGroup.BICEPS.value,
        MuscleGroup.TRICEPS.value
    ]
    
    # Определяем группы мышц для нижней части тела
    lower_body_groups = [
        MuscleGroup.LEGS.value,
        MuscleGroup.CALVES.value,
        MuscleGroup.ABS.value
    ]
    
    # Выбираем упражнения для верхней части тела
    upper_body_exercises = []
    for group in upper_body_groups:
        if group in exercise_groups and exercise_groups[group]:
            # Выбираем 1-2 упражнения из каждой группы
            num_exercises = min(len(exercise_groups[group]), 2)
            exercises = random.sample(exercise_groups[group], num_exercises)
            upper_body_exercises.extend(exercises)
    
    # Выбираем упражнения для нижней части тела
    lower_body_exercises = []
    for group in lower_body_groups:
        if group in exercise_groups and exercise_groups[group]:
            # Выбираем 2-3 упражнения из каждой группы
            num_exercises = min(len(exercise_groups[group]), 3)
            exercises = random.sample(exercise_groups[group], num_exercises)
            lower_body_exercises.extend(exercises)
    
    # Добавляем выбранные упражнения в план тренировок
    workout_plan.exercises.extend(upper_body_exercises)
    workout_plan.exercises.extend(lower_body_exercises)


async def add_muscle_group_split(session: AsyncSession, workout_plan: WorkoutPlan, exercise_groups: dict, days_per_week: int) -> None:
    """
    Добавляет тренировки по схеме разделения по группам мышц
    
    :param session: Сессия БД
    :param workout_plan: План тренировок
    :param exercise_groups: Словарь с упражнениями, сгруппированными по группам мышц
    :param days_per_week: Количество тренировок в неделю
    """
    # Определяем схему разделения в зависимости от количества дней тренировок
    if days_per_week == 4:
        # 4 дня: грудь, спина, ноги, плечи+руки
        split_scheme = {
            "День 1": [MuscleGroup.CHEST.value],
            "День 2": [MuscleGroup.BACK.value],
            "День 3": [MuscleGroup.LEGS.value, MuscleGroup.CALVES.value],
            "День 4": [MuscleGroup.SHOULDERS.value, MuscleGroup.BICEPS.value, MuscleGroup.TRICEPS.value]
        }
    elif days_per_week == 5:
        # 5 дней: грудь, спина, ноги, плечи, руки
        split_scheme = {
            "День 1": [MuscleGroup.CHEST.value],
            "День 2": [MuscleGroup.BACK.value],
            "День 3": [MuscleGroup.LEGS.value, MuscleGroup.CALVES.value],
            "День 4": [MuscleGroup.SHOULDERS.value],
            "День 5": [MuscleGroup.BICEPS.value, MuscleGroup.TRICEPS.value]
        }
    elif days_per_week == 6:
        # 6 дней: Push/Pull/Legs x2
        split_scheme = {
            "День 1": [MuscleGroup.CHEST.value, MuscleGroup.SHOULDERS.value, MuscleGroup.TRICEPS.value],
            "День 2": [MuscleGroup.BACK.value, MuscleGroup.BICEPS.value, MuscleGroup.FOREARMS.value],
            "День 3": [MuscleGroup.LEGS.value, MuscleGroup.CALVES.value, MuscleGroup.ABS.value],
            "День 4": [MuscleGroup.CHEST.value, MuscleGroup.SHOULDERS.value, MuscleGroup.TRICEPS.value],
            "День 5": [MuscleGroup.BACK.value, MuscleGroup.BICEPS.value, MuscleGroup.FOREARMS.value],
            "День 6": [MuscleGroup.LEGS.value, MuscleGroup.CALVES.value, MuscleGroup.ABS.value]
        }
    else:
        # По умолчанию 3 дня: Push/Pull/Legs
        split_scheme = {
            "День 1": [MuscleGroup.CHEST.value, MuscleGroup.SHOULDERS.value, MuscleGroup.TRICEPS.value],
            "День 2": [MuscleGroup.BACK.value, MuscleGroup.BICEPS.value, MuscleGroup.FOREARMS.value],
            "День 3": [MuscleGroup.LEGS.value, MuscleGroup.CALVES.value, MuscleGroup.ABS.value]
        }
    
    # Выбираем упражнения для каждого дня
    all_selected_exercises = []
    
    for day, muscle_groups in split_scheme.items():
        day_exercises = []
        for group in muscle_groups:
            if group in exercise_groups and exercise_groups[group]:
                # Выбираем 2-3 упражнения из каждой группы
                num_exercises = min(len(exercise_groups[group]), 3)
                exercises = random.sample(exercise_groups[group], num_exercises)
                day_exercises.extend(exercises)
        
        all_selected_exercises.extend(day_exercises)
    
    # Добавляем выбранные упражнения в план тренировок
    workout_plan.exercises.extend(all_selected_exercises)


async def create_default_exercises(session: AsyncSession) -> None:
    """
    Создает базовый набор упражнений в базе данных
    
    :param session: Сессия БД
    """
    # Проверяем, есть ли уже упражнения в базе данных
    result = await session.execute(select(func.count()).select_from(Exercise))
    count = result.scalar_one()
    
    if count > 0:
        # Если упражнения уже есть, пропускаем
        return
    
    # Создаем базовый набор упражнений
    exercises = [
        # Грудные
        Exercise(
            name="Жим штанги лежа",
            description="Базовое упражнение для развития грудных мышц",
            muscle_group=MuscleGroup.CHEST,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.BARBELL,
            difficulty=3,
            instructions="Лежа на скамье, опустите штангу к груди и затем выжмите вверх"
        ),
        Exercise(
            name="Жим гантелей лежа",
            description="Упражнение для развития грудных мышц с акцентом на стабилизацию",
            muscle_group=MuscleGroup.CHEST,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="Лежа на скамье, опустите гантели к груди и затем выжмите вверх"
        ),
        Exercise(
            name="Отжимания от пола",
            description="Базовое упражнение для грудных мышц без оборудования",
            muscle_group=MuscleGroup.CHEST,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.NONE,
            difficulty=1,
            instructions="Примите упор лежа, опуститесь до касания грудью пола и вернитесь в исходное положение"
        ),
        Exercise(
            name="Сведение рук в кроссовере",
            description="Изолирующее упражнение для грудных мышц",
            muscle_group=MuscleGroup.CHEST,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.CABLE,
            difficulty=2,
            instructions="Стоя между блоками кроссовера, сведите руки перед собой, сосредоточившись на сокращении грудных мышц"
        ),
        
        # Спина
        Exercise(
            name="Подтягивания",
            description="Базовое упражнение для развития мышц спины",
            muscle_group=MuscleGroup.BACK,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.NONE,
            difficulty=3,
            instructions="Повисните на перекладине и подтянитесь до касания подбородком или грудью"
        ),
        Exercise(
            name="Тяга штанги в наклоне",
            description="Базовое упражнение для развития мышц спины",
            muscle_group=MuscleGroup.BACK,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.BARBELL,
            difficulty=3,
            instructions="В наклоне потяните штангу к нижней части груди, сосредоточившись на сведении лопаток"
        ),
        Exercise(
            name="Тяга гантели в наклоне",
            description="Упражнение для развития мышц спины с акцентом на одну сторону",
            muscle_group=MuscleGroup.BACK,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="В наклоне, опираясь одной рукой на скамью, потяните гантель к поясу"
        ),
        Exercise(
            name="Тяга вертикального блока",
            description="Упражнение для развития мышц спины с использованием тренажера",
            muscle_group=MuscleGroup.BACK,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.MACHINE,
            difficulty=1,
            instructions="Сидя в тренажере, потяните рукоять вниз до касания верхней части груди"
        ),
        
        # Ноги
        Exercise(
            name="Приседания со штангой",
            description="Базовое упражнение для развития мышц ног",
            muscle_group=MuscleGroup.LEGS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.BARBELL,
            difficulty=4,
            instructions="Со штангой на плечах, присядьте до параллели бедер с полом и вернитесь в исходное положение"
        ),
        Exercise(
            name="Приседания с гантелями",
            description="Упражнение для развития мышц ног с гантелями",
            muscle_group=MuscleGroup.LEGS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="С гантелями в руках, присядьте до параллели бедер с полом и вернитесь в исходное положение"
        ),
        Exercise(
            name="Выпады с гантелями",
            description="Упражнение для развития мышц ног с акцентом на одну ногу",
            muscle_group=MuscleGroup.LEGS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="С гантелями в руках, сделайте шаг вперед и опуститесь, затем вернитесь в исходное положение"
        ),
        Exercise(
            name="Разгибание ног в тренажере",
            description="Изолирующее упражнение для квадрицепсов",
            muscle_group=MuscleGroup.LEGS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.MACHINE,
            difficulty=1,
            instructions="Сидя в тренажере, разогните ноги до полного выпрямления"
        ),
        
        # Плечи
        Exercise(
            name="Жим штанги над головой",
            description="Базовое упражнение для развития плечевых мышц",
            muscle_group=MuscleGroup.SHOULDERS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.BARBELL,
            difficulty=3,
            instructions="Стоя, выжмите штангу над головой до полного выпрямления рук"
        ),
        Exercise(
            name="Жим гантелей над головой",
            description="Упражнение для развития плечевых мышц с гантелями",
            muscle_group=MuscleGroup.SHOULDERS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="Сидя или стоя, выжмите гантели над головой до полного выпрямления рук"
        ),
        Exercise(
            name="Махи гантелями в стороны",
            description="Изолирующее упражнение для средних дельт",
            muscle_group=MuscleGroup.SHOULDERS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.DUMBBELLS,
            difficulty=1,
            instructions="Стоя, поднимите гантели в стороны до уровня плеч"
        ),
        Exercise(
            name="Махи гантелями вперед",
            description="Изолирующее упражнение для передних дельт",
            muscle_group=MuscleGroup.SHOULDERS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.DUMBBELLS,
            difficulty=1,
            instructions="Стоя, поднимите гантели перед собой до уровня плеч"
        ),
        
        # Бицепс
        Exercise(
            name="Сгибание рук со штангой",
            description="Базовое упражнение для развития бицепсов",
            muscle_group=MuscleGroup.BICEPS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.BARBELL,
            difficulty=2,
            instructions="Стоя, согните руки со штангой, удерживая локти неподвижными"
        ),
        Exercise(
            name="Сгибание рук с гантелями",
            description="Упражнение для развития бицепсов с гантелями",
            muscle_group=MuscleGroup.BICEPS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.DUMBBELLS,
            difficulty=1,
            instructions="Стоя или сидя, согните руки с гантелями, удерживая локти неподвижными"
        ),
        Exercise(
            name="Концентрированное сгибание на бицепс",
            description="Изолирующее упражнение для бицепса с акцентом на пик",
            muscle_group=MuscleGroup.BICEPS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.DUMBBELLS,
            difficulty=1,
            instructions="Сидя, согните руку с гантелей, упираясь локтем во внутреннюю часть бедра"
        ),
        
        # Трицепс
        Exercise(
            name="Отжимания на трицепс",
            description="Упражнение для развития трицепсов без оборудования",
            muscle_group=MuscleGroup.TRICEPS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.NONE,
            difficulty=2,
            instructions="Примите упор лежа, расположив руки близко друг к другу, и выполните отжимание"
        ),
        Exercise(
            name="Французский жим с гантелей",
            description="Изолирующее упражнение для трицепсов",
            muscle_group=MuscleGroup.TRICEPS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.DUMBBELLS,
            difficulty=2,
            instructions="Лежа на скамье, опустите гантель за голову, сгибая руки в локтях, затем выпрямите руки"
        ),
        Exercise(
            name="Разгибание рук с верхнего блока",
            description="Изолирующее упражнение для трицепсов с использованием тренажера",
            muscle_group=MuscleGroup.TRICEPS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.CABLE,
            difficulty=1,
            instructions="Стоя спиной к блоку, разогните руки, удерживая локти неподвижными"
        ),
        
        # Пресс
        Exercise(
            name="Скручивания",
            description="Базовое упражнение для развития прямых мышц живота",
            muscle_group=MuscleGroup.ABS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.NONE,
            difficulty=1,
            instructions="Лежа на спине, поднимите верхнюю часть тела, сосредоточившись на сокращении мышц живота"
        ),
        Exercise(
            name="Планка",
            description="Статическое упражнение для укрепления кора",
            muscle_group=MuscleGroup.ABS,
            exercise_type=ExerciseType.COMPOUND,
            equipment=Equipment.NONE,
            difficulty=1,
            instructions="Примите положение упора лежа на локтях и удерживайте тело прямым, напрягая мышцы кора"
        ),
        Exercise(
            name="Подъем ног в висе",
            description="Упражнение для нижней части пресса",
            muscle_group=MuscleGroup.ABS,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.NONE,
            difficulty=3,
            instructions="В висе на перекладине, поднимите прямые ноги до горизонтального положения"
        ),
        
        # Икры
        Exercise(
            name="Подъем на носки стоя",
            description="Базовое упражнение для икроножных мышц",
            muscle_group=MuscleGroup.CALVES,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.NONE,
            difficulty=1,
            instructions="Стоя, поднимитесь на носки и медленно опуститесь"
        ),
        Exercise(
            name="Подъем на носки сидя",
            description="Упражнение для икроножных мышц с акцентом на камбаловидную мышцу",
            muscle_group=MuscleGroup.CALVES,
            exercise_type=ExerciseType.ISOLATION,
            equipment=Equipment.MACHINE,
            difficulty=1,
            instructions="Сидя в тренажере, поднимитесь на носки и медленно опуститесь"
        ),
    ]
    
    # Добавляем упражнения в базу данных
    for exercise in exercises:
        session.add(exercise)
    
    await session.commit()
