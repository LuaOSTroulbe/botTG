import asyncio
import json
import os
import ssl
from datetime import datetime
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

# ============================================
# НАСТРОЙКИ
# ============================================
API_TOKEN = '8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk'
OPENROUTER_API_KEY = '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'  # ← ЗАМЕНИ НА СВОЙ КЛЮЧ
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DATA_FILE = "ai_users.json"
ADMIN_ID = 8420391742

# ============================================
# ОБХОД БЛОКИРОВКИ
# ============================================
def create_session():
    return AiohttpSession()

# ============================================
# ПАМЯТЬ ПОЛЬЗОВАТЕЛЕЙ
# ============================================
class UserData:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"users": {}}

    def get_user(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "name": "Пользователь",
                "history": [],
                "total_messages": 0,
                "created_at": datetime.now().isoformat()
            }
        return self.data["users"][uid]

    def add_message(self, user_id: int, role: str, content: str):
        user = self.get_user(user_id)
        user["history"].append({"role": role, "content": content})
        if len(user["history"]) > 20:  # Держим последние 20 сообщений
            user["history"] = user["history"][-20:]
        user["total_messages"] += 1
        self.save()

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

# ============================================
# ИИ ЛОГИКА (OpenRouter)
# ============================================
class AIBrain:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def chat(self, messages: list, model: str = "google/gemini-2.0-flash-001") -> str:
        """Отправка запроса к OpenRouter"""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        try:
            async with self.session.post(OPENROUTER_URL, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"❌ Ошибка API: {resp.status}"
        except Exception as e:
            return f"❌ Ошибка соединения: {str(e)[:50]}"

# ============================================
# БОТ
# ============================================
class AIBot:
    def __init__(self, token: str, api_key: str):
        self.token = token
        self.api_key = api_key
        self.users = UserData(DATA_FILE)
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("clear"))(self.cmd_clear)
        self.dp.message(Command("model"))(self.cmd_model)
        self.dp.message(F.text)(self.handle_message)
        self.dp.callback_query(F.data.startswith("model_"))(self.callback_model)

    async def cmd_start(self, message: types.Message):
        user = self.users.get_user(message.from_user.id)
        user["name"] = message.from_user.full_name

        dev_tag = " 👑 Разработчик" if message.from_user.id == ADMIN_ID else ""
        await message.answer(
            f"🤖 *ИИ-Ассистент*\n\n"
            f"👤 {message.from_user.full_name}{dev_tag}\n"
            f"💬 Сообщений: {user['total_messages']}\n\n"
            f"Я твой личный ИИ-помощник. Задай мне любой вопрос!\n\n"
            f"📋 *Команды:*\n"
            f"/clear - Очистить историю\n"
            f"/model - Сменить модель ИИ",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_clear(self, message: types.Message):
        user = self.users.get_user(message.from_user.id)
        user["history"] = []
        self.users.save()
        await message.answer("✅ История диалога очищена!")

    async def cmd_model(self, message: types.Message):
        builder = InlineKeyboardBuilder()
        builder.button(text="Gemini Flash (быстрый)", callback_data="model_gemini")
        builder.button(text="GPT-3.5 Turbo", callback_data="model_gpt")
        builder.button(text="Claude Haiku", callback_data="model_claude")
        builder.adjust(1)
        await message.answer("🎯 *Выбери модель ИИ:*", reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def callback_model(self, callback: types.CallbackQuery):
        model_map = {
            "model_gemini": "google/gemini-2.0-flash-001",
            "model_gpt": "openai/gpt-3.5-turbo",
            "model_claude": "anthropic/claude-3-haiku"
        }
        model = model_map.get(callback.data, "google/gemini-2.0-flash-001")
        user = self.users.get_user(callback.from_user.id)
        user["current_model"] = model
        self.users.save()
        await callback.answer(f"✅ Модель: {model}", show_alert=True)
        await callback.message.delete()

    async def handle_message(self, message: types.Message):
        user = self.users.get_user(message.from_user.id)
        user["name"] = message.from_user.full_name

        # Индикатор "печатает"
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Формируем контекст
        system_msg = {
            "role": "system",
            "content": f"Ты - дружелюбный ИИ-ассистент. Общаешься с {message.from_user.full_name}. Отвечай на русском языке."
        }
        
        model = user.get("current_model", "google/gemini-2.0-flash-001")
        messages = [system_msg] + user["history"][-15:] + [{"role": "user", "content": message.text}]

        # Запрос к ИИ
        async with AIBrain(self.api_key) as ai:
            response = await ai.chat(messages, model)

        # Сохраняем историю
        self.users.add_message(message.from_user.id, "user", message.text)
        self.users.add_message(message.from_user.id, "assistant", response)

        # Отправляем ответ
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)

    async def run(self):
        session = create_session()
        bot = Bot(token=self.token, session=session)
        print("🤖 ИИ-Бот запускается...")
        try:
            me = await bot.get_me()
            print(f"✅ Бот @{me.username} успешно запущен!")
            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
        finally:
            await bot.session.close()

async def main():
    bot = AIBot(API_TOKEN, OPENROUTER_API_KEY)
    await bot.run()

if __name__ == "__main__":
    print("🤖 ИИ БОТ ДЛЯ TELEGRAM")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот завершает работу...")
