import aiohttp
import asyncio
from functools import lru_cache
from typing import Dict, Optional
from datetime import datetime, timedelta
from config import WEATHER_API_KEY, FOOD_API_KEY, logger
from googletrans import Translator

class WeatherService:
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(minutes=30)
        
    async def get_temperature(self, city: str) -> float:
        """Получение температуры с кэшированием на 30 минут"""
        current_time = datetime.now()
        
        # Проверяем кэш
        if city in self._cache:
            if current_time - self._cache_time[city] < self._cache_duration:
                logger.info(f"Возвращаем кэшированную температуру для {city}")
                return self._cache[city]
        
        # Запрашиваем новые данные
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://api.openweathermap.org/data/2.5/weather"
                params = {
                    "q": city,
                    "appid": WEATHER_API_KEY,
                    "units": "metric"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        temp = data['main']['temp']
                        
                        # Обновляем кэш
                        self._cache[city] = temp
                        self._cache_time[city] = current_time
                        
                        logger.info(f"Получена новая температура для {city}: {temp}°C")
                        return temp
                    else:
                        logger.error(f"Ошибка API погоды: {response.status}")
                        return self._get_default_temp()
        except Exception as e:
            logger.error(f"Ошибка при получении погоды: {e}")
            return self._get_default_temp()
    
    def _get_default_temp(self) -> float:
        """Возвращает температуру по умолчанию"""
        return 20.0

class FoodService:
    def __init__(self):
        self._cache = {}
        
    async def get_food_info(self, food_name: str) -> Dict:
        """Получение информации о продукте с кэшированием"""
        food_name = food_name.lower()
        
        # Проверяем локальный кэш
        if food_name in self._cache:
            logger.info(f"Возвращаем кэшированную информацию о продукте {food_name}")
            return self._cache[food_name]
        
        async with Translator() as translator:
            eng_food_name_result = await translator.translate(food_name)
            eng_food_name = eng_food_name_result.text
            
        # Ищем через API
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.nal.usda.gov/fdc/v1/foods/search"
                params = {
                    "api_key": FOOD_API_KEY,
                    "query": eng_food_name,
                    "pageSize": 1,
                    "dataType": ["Survey (FNDDS)"]
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['foods']:
                            food = data['foods'][0]
                            nutrients = food.get('foodNutrients', [])
                            
                            calories = next(
                                (n['value'] for n in nutrients 
                                 if n.get('nutrientName', '').lower().startswith('energy')),
                                0
                            )
                            
                            result = {
                                'name': food.get('description', food_name).capitalize(),
                                'calories': calories,
                                'details': f"Порция: {food.get('servingSize', 100)}г",
                                'success': True
                            }
                            
                            self._cache[food_name] = result
                            return result
                            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о продукте: {e}")
        
        # Возвращаем данные по умолчанию при ошибке
        return self._get_default_food_info(food_name)
    
    def _get_default_food_info(self, food_name: str) -> Dict:
        """Возвращает информацию о продукте по умолчанию"""
        return {
            'name': food_name.capitalize(),
            'calories': 100,
            'details': 'Информация не найдена',
            'success': False
        }

# Создаем глобальные экземпляры сервисов
weather_service = WeatherService()
food_service = FoodService()

# Экспортируем функции для обратной совместимости
async def get_weather(city: str) -> float:
    return await weather_service.get_temperature(city)

async def get_food_info(food_name: str) -> Dict:
    return await food_service.get_food_info(food_name) 