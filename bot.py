import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import io
import pandas as pd
from collections import defaultdict
from config import BOT_TOKEN, logger
from utils import get_weather, get_food_info
import matplotlib
from typing import Dict, Any
from aiogram import BaseMiddleware
from typing import Callable, Awaitable
import signal
import sys

matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящие сообщения
        logger.info(f"Получено сообщение: {event.text}")
        return await handler(event, data)

class FitnessBot:
    def __init__(self):
        logger.info("Бот запущен!")
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.users: Dict[str, Dict[str, Any]] = {}
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Регистрация всех обработчиков команд"""
        # Добавляем middleware для логирования
        self.dp.message.middleware(LoggingMiddleware())
        
        # Регистрация основных команд
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_set_profile, Command("set_profile"))
        self.dp.message.register(self.cmd_log_water, Command("log_water"))
        self.dp.message.register(self.cmd_log_food, Command("log_food"))
        self.dp.message.register(self.cmd_log_workout, Command("log_workout"))
        self.dp.message.register(self.cmd_check_progress, Command("check_progress"))
        self.dp.message.register(self.cmd_plot_progress, Command("plot_progress"))
        self.dp.message.register(self.cmd_get_recommendations, Command("get_recommendations"))
        
        # Регистрация обработчиков состояний
        self.dp.message.register(self.process_weight, ProfileStates.waiting_weight)
        self.dp.message.register(self.process_height, ProfileStates.waiting_height)
        self.dp.message.register(self.process_age, ProfileStates.waiting_age)
        self.dp.message.register(self.process_activity, ProfileStates.waiting_activity)
        self.dp.message.register(self.process_city, ProfileStates.waiting_city)
        self.dp.message.register(self.process_food_name, FoodStates.waiting_food_name)
        self.dp.message.register(self.process_food_weight, FoodStates.waiting_food_weight)

    async def calculate_norms(self, user_data: dict, temp: float) -> tuple[float, float]:
        """Расчет норм воды и калорий"""
        water_norm = (user_data['weight'] * 30 + 
                     (user_data['activity'] // 30) * 500 +
                     (500 if temp > 25 else 0))
        
        calorie_norm = (10 * user_data['weight'] + 
                       6.25 * user_data['height'] - 
                       5 * user_data['age'] +
                       (user_data['activity'] / 30) * 100)
        
        return water_norm, calorie_norm

    async def cmd_start(self, message: Message):
        welcome_text = (
            "🤖 Привет! Я ваш персональный фитнес-помощник.\n\n"
            "Основные команды:\n"
            "📝 /set_profile - Настройка профиля\n"
            "💧 /log_water - Записать воду\n"
            "🍎 /log_food - Записать еду\n"
            "🏃 /log_workout - Записать тренировку\n"
            "📊 /check_progress - Проверить прогресс\n"
            "📈 /plot_progress - Графики прогресса\n"
            "💡 /get_recommendations - Получить рекомендации\n\n"
            "Для начала работы настройте профиль командой /set_profile"
        )
        await message.answer(welcome_text)

    async def cmd_set_profile(self, message: Message, state: FSMContext):
        await state.set_state(ProfileStates.waiting_weight)
        await message.answer("Введите ваш вес (в кг):")

    async def process_weight(self, message: Message, state: FSMContext):
        try:
            weight = float(message.text)
            await state.update_data(weight=weight)
            await state.set_state(ProfileStates.waiting_height)
            await message.answer("Введите ваш рост (в см):")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

    async def process_height(self, message: Message, state: FSMContext):
        try:
            height = float(message.text)
            await state.update_data(height=height)
            await state.set_state(ProfileStates.waiting_age)
            await message.answer("Введите ваш возраст:")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

    async def process_age(self, message: Message, state: FSMContext):
        try:
            age = int(message.text)
            await state.update_data(age=age)
            await state.set_state(ProfileStates.waiting_activity)
            await message.answer("Сколько минут активности у вас в день?")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

    async def process_activity(self, message: Message, state: FSMContext):
        try:
            activity = int(message.text)
            await state.update_data(activity=activity)
            await state.set_state(ProfileStates.waiting_city)
            await message.answer("В каком городе вы находитесь?")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

    async def process_city(self, message: Message, state: FSMContext):
        city = message.text
        user_id = str(message.from_user.id)
        data = await state.get_data()
        
        temp = await get_weather(city)
        water_norm, calorie_norm = await self.calculate_norms(data, temp)
        
        self.users[user_id] = {
            **data,
            'city': city,
            'water_goal': water_norm,
            'calorie_goal': calorie_norm,
            'logged_water': 0,
            'logged_calories': 0,
            'burned_calories': 0,
            'water_history': defaultdict(float),
            'calories_history': defaultdict(float),
            'food_preferences': []
        }
        
        await message.answer(
            f"✅ Профиль настроен!\n\n"
            f"💧 Норма воды: {water_norm:.0f} мл\n"
            f"🍎 Норма калорий: {calorie_norm:.0f} ккал"
        )
        await state.clear()

    async def cmd_log_water(self, message: Message):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return

        try:
            amount = int(message.text.split()[1])
            self.users[user_id]['logged_water'] += amount
            today = datetime.now().date()
            self.users[user_id]['water_history'][today] += amount
            
            remaining = max(0, self.users[user_id]['water_goal'] - 
                          self.users[user_id]['logged_water'])
            
            await message.answer(
                f"💧 Записано: {amount} мл воды\n"
                f"🎯 Осталось выпить: {remaining:.0f} мл"
            )
        except (IndexError, ValueError):
            await message.answer("Используйте команду так: /log_water <количество_в_мл>")

    async def cmd_log_food(self, message: Message, state: FSMContext):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return
        
        await state.set_state(FoodStates.waiting_food_name)
        await message.answer("🍽 Какой продукт вы съели? Введите название:")

    async def process_food_name(self, message: Message, state: FSMContext):
        food_info = await get_food_info(message.text)
        await state.update_data(food_info=food_info)
        
        await message.answer(
            f"🍴 {food_info['name']} — {food_info['calories']} ккал на 100 г\n"
            f"{food_info['details']}\n"
            f"⚖️ Сколько грамм вы съели?"
        )
        await state.set_state(FoodStates.waiting_food_weight)

    async def process_food_weight(self, message: Message, state: FSMContext):
        user_id = str(message.from_user.id)
        try:
            weight = float(message.text)
            data = await state.get_data()
            food_info = data['food_info']
            calories = (food_info['calories'] * weight) / 100
            
            self.users[user_id]['logged_calories'] += calories
            today = datetime.now().date()
            self.users[user_id]['calories_history'][today] += calories
            self.users[user_id]['food_preferences'].append(food_info['name'])
            
            await message.answer(f"✅ Записано: {calories:.1f} ккал")
            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

    async def cmd_log_workout(self, message: Message):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return

        try:
            _, workout_type, duration = message.text.split()
            duration = int(duration)
            
            calories_per_minute = {
                'бег': 10,
                'ходьба': 5,
                'велосипед': 7,
                'плавание': 8,
                'йога': 3
            }.get(workout_type.lower(), 5)
            
            burned = calories_per_minute * duration
            water_needed = (duration // 30) * 200
            
            self.users[user_id]['burned_calories'] += burned
            
            await message.answer(
                f"🏃‍♂️ {workout_type.capitalize()} {duration} минут\n"
                f"🔥 Сожжено калорий: {burned}\n"
                f"💧 Рекомендуется выпить: {water_needed} мл воды"
            )
        except (IndexError, ValueError):
            await message.answer(
                "Используйте команду так: /log_workout <тип_тренировки> <время_в_минутах>\n"
                "Например: /log_workout бег 30"
            )

    async def cmd_check_progress(self, message: Message):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return

        user = self.users[user_id]
        water_remaining = max(0, user['water_goal'] - user['logged_water'])
        net_calories = user['logged_calories'] - user['burned_calories']
        calories_remaining = max(0, user['calorie_goal'] - net_calories)

        await message.answer(
            "📊 Ваш прогресс:\n\n"
            f"💧 Вода:\n"
            f"- Выпито: {user['logged_water']} мл из {user['water_goal']:.0f} мл\n"
            f"- Осталось: {water_remaining:.0f} мл\n\n"
            f"🍎 Калории:\n"
            f"- Потреблено: {user['logged_calories']:.0f} ккал\n"
            f"- Сожжено: {user['burned_calories']:.0f} ккал\n"
            f"- Баланс: {net_calories:.0f} ккал\n"
            f"- До цели: {calories_remaining:.0f} ккал"
        )

    async def cmd_plot_progress(self, message: Message):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return

        if not self.users[user_id]['water_history'] and not self.users[user_id]['calories_history']:
            await message.answer("Пока нет данных для построения графиков.")
            return

        plt.style.use('bmh')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # График воды
        dates = list(self.users[user_id]['water_history'].keys())
        water_amounts = list(self.users[user_id]['water_history'].values())
        
        if dates and water_amounts:
            ax1.plot(dates, water_amounts, 'b-o', label='Потребление воды', 
                    linewidth=2, markersize=8)
            ax1.axhline(y=self.users[user_id]['water_goal'], color='r', 
                       linestyle='--', label='Цель')
            ax1.fill_between(dates, water_amounts, alpha=0.3, color='blue')
        
        ax1.set_title('Прогресс потребления воды', pad=20)
        ax1.set_ylabel('мл')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # График калорий
        calories_dates = list(self.users[user_id]['calories_history'].keys())
        calories_amounts = list(self.users[user_id]['calories_history'].values())
        
        if calories_dates and calories_amounts:
            ax2.plot(calories_dates, calories_amounts, 'g-o', 
                    label='Потребление калорий', linewidth=2, markersize=8)
            ax2.axhline(y=self.users[user_id]['calorie_goal'], color='r', 
                       linestyle='--', label='Цель')
            ax2.fill_between(calories_dates, calories_amounts, alpha=0.3, color='green')
        
        ax2.set_title('Прогресс потребления калорий', pad=20)
        ax2.set_ylabel('ккал')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        
        for ax in [ax1, ax2]:
            ax.tick_params(axis='both', which='major')
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        
        photo = BufferedInputFile(buf.getvalue(), filename="progress.png")
        await message.answer_photo(photo)
        
        plt.close('all')
        buf.close()

    async def cmd_get_recommendations(self, message: Message):
        user_id = str(message.from_user.id)
        if user_id not in self.users:
            await message.answer("Сначала настройте профиль командой /set_profile")
            return

        user = self.users[user_id]
        net_calories = user['logged_calories'] - user['burned_calories']
        water_progress = (user['logged_water'] / user['water_goal']) * 100

        recommendations = []

        if water_progress < 50:
            recommendations.append(
                "💧 Вы выпили меньше половины дневной нормы воды.\n"
                "Рекомендуется выпить стакан воды прямо сейчас!"
            )

        if net_calories > user['calorie_goal']:
            recommendations.extend([
                "🏃‍♂️ Рекомендуемые активности:",
                "- Бег (30 минут) - сожжет около 300 ккал",
                "- Плавание (45 минут) - сожжет около 400 ккал",
                "\n🥗 Низкокалорийные продукты:",
                "- Огурцы (15 ккал/100г)",
                "- Листовой салат (12 ккал/100г)",
                "- Томаты (20 ккал/100г)"
            ])
        elif net_calories < user['calorie_goal'] * 0.5:
            recommendations.extend([
                "🍎 Рекомендуемые продукты:",
                "- Бананы (89 ккал/100г)",
                "- Авокадо (160 ккал/100г)",
                "- Орехи (600 ккал/100г)"
            ])

        if user['food_preferences']:
            favorite_foods = pd.Series(user['food_preferences']).value_counts().head(3)
            recommendations.append("\n👍 Ваши любимые продукты:")
            for food, count in favorite_foods.items():
                recommendations.append(f"- {food} (использовано {count} раз)")

        await message.answer("\n".join(recommendations))

    async def start(self):
        """Запуск бота"""
        logger.info("Запуск бота...")
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Бот {bot_info.first_name} начинает работу")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise

class ProfileStates(StatesGroup):
    waiting_weight = State()
    waiting_height = State()
    waiting_age = State()
    waiting_activity = State()
    waiting_city = State()

class FoodStates(StatesGroup):
    waiting_food_name = State()
    waiting_food_weight = State()

if __name__ == '__main__':
    try:
        bot = FitnessBot()
        
        # Добавляем обработчик сигналов
        def signal_handler(signum, frame):
            logger.info("Received SIGTERM signal")
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, signal_handler)
        
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Бот остановлен!")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise 