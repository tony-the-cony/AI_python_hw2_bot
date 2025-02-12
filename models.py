from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, date
from collections import defaultdict

@dataclass
class WorkoutSession:
    type: str
    duration: int
    calories_burned: float
    date: datetime = field(default_factory=datetime.now)
    
    @property
    def water_recommendation(self) -> float:
        """Рекомендуемое количество воды после тренировки"""
        return (self.duration // 30) * 200

@dataclass
class FoodEntry:
    name: str
    weight: float
    calories: float
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    date: datetime = field(default_factory=datetime.now)

@dataclass
class WaterEntry:
    amount: float
    date: datetime = field(default_factory=datetime.now)

@dataclass
class DailyStats:
    date: date
    water_consumed: float = 0
    calories_consumed: float = 0
    calories_burned: float = 0
    workouts: List[WorkoutSession] = field(default_factory=list)
    food_entries: List[FoodEntry] = field(default_factory=list)
    water_entries: List[WaterEntry] = field(default_factory=list)
    
    @property
    def net_calories(self) -> float:
        """Чистое количество калорий за день"""
        return self.calories_consumed - self.calories_burned

@dataclass
class UserProfile:
    user_id: int
    weight: float
    height: float
    age: int
    activity_minutes: int
    city: str
    water_goal: float = 0
    calorie_goal: float = 0
    stats: Dict[date, DailyStats] = field(default_factory=lambda: defaultdict(DailyStats))
    food_preferences: List[str] = field(default_factory=list)
    
    def add_water(self, amount: float) -> None:
        """Добавляет запись о потреблении воды"""
        today = datetime.now()
        entry = WaterEntry(amount=amount, date=today)
        
        day_stats = self.stats[today.date()]
        day_stats.water_consumed += amount
        day_stats.water_entries.append(entry)
        
    def add_food(self, name: str, weight: float, calories: float,
                protein: Optional[float] = None,
                fat: Optional[float] = None,
                carbs: Optional[float] = None) -> None:
        """Добавляет запись о приеме пищи"""
        today = datetime.now()
        entry = FoodEntry(
            name=name,
            weight=weight,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            date=today
        )
        
        day_stats = self.stats[today.date()]
        day_stats.calories_consumed += calories
        day_stats.food_entries.append(entry)
        self.food_preferences.append(name)
        
    def add_workout(self, workout_type: str, duration: int,
                   calories_burned: float) -> None:
        """Добавляет запись о тренировке"""
        today = datetime.now()
        session = WorkoutSession(
            type=workout_type,
            duration=duration,
            calories_burned=calories_burned,
            date=today
        )
        
        day_stats = self.stats[today.date()]
        day_stats.calories_burned += calories_burned
        day_stats.workouts.append(session)
        
    def get_stats(self, day: Optional[date] = None) -> DailyStats:
        """Получает статистику за определенный день"""
        if day is None:
            day = datetime.now().date()
        return self.stats[day]
        
    def get_water_progress(self) -> float:
        """Возвращает процент выполнения цели по воде"""
        today_stats = self.get_stats()
        if self.water_goal <= 0:
            return 0
        return (today_stats.water_consumed / self.water_goal) * 100
        
    def get_calorie_progress(self) -> float:
        """Возвращает процент выполнения цели по калориям"""
        today_stats = self.get_stats()
        if self.calorie_goal <= 0:
            return 0
        return (today_stats.net_calories / self.calorie_goal) * 100 