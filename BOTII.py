import asyncio
import json
import os
from datetime import datetime
from typing import Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from google import genai

API_TOKEN = '8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk'
GEMINI_API_KEY = 'AIzaSyCQRw4-puFAC-lFoDv36lYOUwfZvx6_eZs'
ADMIN_ID = 8420391742
DATA_FILE = "ai_users.json"

def create_session():
    return AiohttpSession()

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
        return {"users": {}, "banned": [], "logs": []}

    def get_user(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "name": "Пользователь",
                "total_messages": 0,
                "created_at": datetime.now().isoformat()
            }
        return self.data["users"][uid]

    def add_message(self, user_id: int):
        user = self.get_user(user_id)
        user["total_messages"] += 1
        self.save()

    def is_banned(self, user_id: int) -> bool:
        return str(user_id) in self.data.get("banned", [])

    def ban_user(self, user_id: int):
        if str(user_id) not in self.data["banned"]:
            self.data["banned"].append(str(user_id))
        self.save()

    def unban_user(self, user_id: int):
        if str(user_id) in self.data["banned"]:
            self.data["banned"].remove(str(user_id))
        self.save()

    def add_log(self, user_id: int, username: str, text: str):
        self.data["logs"].append({
            "user_id": user_id,
            "username": username,
            "text": text[:100],
            "time": datetime.now().isoformat()
        })
        if len(self.data["logs"]) > 100:
            self.data["logs"] = self.data["logs"][-100:]
        self.save()

    def get_logs(self, count: int = 20) -> list:
        return self.data["logs"][-count:]

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

class AIBrain:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def chat(self, text: str) -> str:
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=text
            )
            return response.text
        except Exception as e:
            return f"Ошибка: {str(e)[:50]}"

class AIBot:
    def __init__(self, token: str, api_key: str):
        self.token = token
        self.api_key = api_key
        self.users = UserData(DATA_FILE)
        self.brain = AIBrain(api_key)
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("clear"))(self.cmd_clear)
        self.dp.message(Command("ban"))(self.cmd_ban)
        self.dp.message(Command("unban"))(self.cmd_unban)
        self.dp.message(Command("logs"))(self.cmd_logs)
        self.dp.message(Command("logall"))(self.cmd_logall)
        self.dp.message(F.text)(self.handle_message)

    def _is_admin(self, user_id: int) -> bool:
        return user_id == ADMIN_ID

    async def cmd_start(self, message: types.Message):
        user = self.users.get_user(message.from_user.id)
        user["name"] = message.from_user.full_name
        await message.answer(
            f"Привет! Я ИИ-помощник ВацапочкИИ.\n\n"
            f"Задай мне любой вопрос!\n\n"
            f"/help - помощь\n"
            f"/clear - очистить историю"
        )

    async def cmd_help(self, message: types.Message):
        await message.answer(
            f"Я работаю на базе Google Gemini 2.0 Flash.\n"
            f"Просто напиши мне сообщение!"
        )

    async def cmd_clear(self, message: types.Message):
        await message.answer("История очищена!")

    async def cmd_ban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if not args:
            await message.answer("Укажи ID: /ban {user_id}")
            return
        user_id = int(args[0])
        self.users.ban_user(user_id)
        await message.answer(f"Пользователь {user_id} заблокирован!")

    async def cmd_unban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if not args:
            await message.answer("Укажи ID: /unban {user_id}")
            return
        user_id = int(args[0])
        self.users.unban_user(user_id)
        await message.answer(f"Пользователь {user_id} разблокирован!")

    async def cmd_logs(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        count = int(args[0]) if args else 10
        logs = self.users.get_logs(count)
        if not logs:
            await message.answer("Логи пусты")
            return
        text = "Последние сообщения:\n\n"
        for log in logs:
            text += f"{log['username']} (ID:{log['user_id']}): {log['text']}\n"
        await message.answer(text)

    async def cmd_logall(self, message: types.Message):
        if not self._is_admin(message.from_user.id):
            return
        logs = self.users.data["logs"]
        if not logs:
            await message.answer("Логи пусты")
            return
        text = f"Всего сообщений: {len(logs)}\n\n"
        for log in logs[-30:]:
            text += f"{log['username']} (ID:{log['user_id']}): {log['text']}\n"
        await message.answer(text)

    async def handle_message(self, message: types.Message):
        if self.users.is_banned(message.from_user.id):
            await message.answer("Вы заблокированы!")
            return

        user = self.users.get_user(message.from_user.id)
        user["name"] = message.from_user.full_name

        if not message.text.startswith("/"):
            self.users.add_log(
                message.from_user.id,
                message.from_user.full_name,
                message.text
            )

        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response = self.brain.chat(message.text)
        self.users.add_message(message.from_user.id)
        await message.answer(response)

    async def run(self):
        session = create_session()
        bot = Bot(token=self.token, session=session)
        print("Бот запускается...")
        try:
            me = await bot.get_me()
            print(f"Бот @{me.username} запущен!")
            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            await bot.session.close()

async def main():
    bot = AIBot(API_TOKEN, GEMINI_API_KEY)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот завершает работу...")
