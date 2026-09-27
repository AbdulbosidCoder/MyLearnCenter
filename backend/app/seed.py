"""Demo themes so a fresh install has something to open. Runs only when there are no modules yet."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BlockType, Lesson, LessonBlock, Module

DEMO = [
    {
        "title": "Введение в Data Science",
        "description": "Что такое наука о данных и из каких шагов состоит работа с данными.",
        "lessons": [
            (
                "Что такое Data Science",
                "Data Science — это умение **задавать вопросы данным** и получать на них ответы.\n\n"
                "Типичный путь:\n\n"
                "1. Сформулировать вопрос.\n"
                "2. Собрать и очистить данные.\n"
                "3. Исследовать их и построить графики.\n"
                "4. Построить модель.\n"
                "5. Объяснить результат людям.",
            ),
            (
                "Данные и их типы",
                "- **Числовые**: рост, цена, температура.\n"
                "- **Категориальные**: город, цвет, марка машины.\n"
                "- **Текст, изображения, время** — особые виды данных.\n\n"
                "Таблица, где строка — объект, а столбец — признак, называется *датасетом*.",
            ),
        ],
    },
    {
        "title": "Статистика",
        "description": "Среднее, медиана, разброс и нормальное распределение.",
        "lessons": [
            (
                "Среднее и медиана",
                "**Среднее** — сумма значений, делённая на их количество.\n\n"
                "**Медиана** — значение посередине, если отсортировать данные.\n\n"
                "Если в данных есть выброс (например, одна огромная зарплата), "
                "среднее сильно сдвигается, а медиана почти нет.",
            ),
            (
                "Дисперсия и стандартное отклонение",
                "**Дисперсия** показывает, насколько значения в среднем удалены от среднего.\n\n"
                "**Стандартное отклонение** — корень из дисперсии, оно в тех же единицах, что и данные.",
            ),
        ],
    },
    {
        "title": "Линейная регрессия",
        "description": "Первая модель машинного обучения: прямая, которая лучше всего описывает точки.",
        "lessons": [
            (
                "Идея линейной регрессии",
                "Мы ищем прямую `y = w·x + b`, которая ближе всего проходит к точкам.\n\n"
                "«Ближе всего» значит, что сумма квадратов ошибок минимальна.",
            ),
        ],
    },
]


async def seed_demo_content(session: AsyncSession) -> None:
    if await session.scalar(select(func.count(Module.id))):
        return
    for m_pos, spec in enumerate(DEMO):
        module = Module(title=spec["title"], description=spec["description"], position=m_pos)
        for l_pos, (title, text) in enumerate(spec["lessons"]):
            module.lessons.append(
                Lesson(title=title, position=l_pos, blocks=[LessonBlock(type=BlockType.text, content=text)])
            )
        session.add(module)
    await session.commit()
