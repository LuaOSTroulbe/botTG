import asyncio
import json
import os
from datetime import datetime
from typing import Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
import aiohttp

API_TOKEN = '8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk'
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
            self.data["users"][uid] = {"total_messages": 0}
        return self.data["users"][uid]

    def add_message(self, user_id: int):
        self.get_user(user_id)["total_messages"] += 1
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
        self.data["logs"] = self.data.get("logs", [])
        self.data["logs"].append({
            "user_id": user_id,
            "username": username,
            "text": text[:100],
            "time": datetime.now().isoformat()
        })
        self.data["logs"] = self.data["logs"][-100:]
        self.save()

    def get_logs(self, count: int = 20) -> list:
        return self.data.get("logs", [])[-count:]

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

class AIBrain:
    async def chat(self, text: str) -> str:
        url = "https://duckduckgo.com/duckchat/v1/chat"
        headers = {
            "Content-Type": "application/json",
            "x-vqd-4": "4-321" + str(int(datetime.now().timestamp()))[-6:]
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": text}]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["message"]
                    return f"Ошибка: {resp.status}"
        except Exception as e:
            return f"Ошибка: {str(e)[:50]}"

class AIBot:
    def __init__(self, token: str):
        self.token = token
        self.users = UserData(DATA_FILE)
        self.brain = AIBrain()
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("ban"))(self.cmd_ban)
        self.dp.message(Command("unban"))(self.cmd_unban)
        self.dp.message(Command("logs"))(self.cmd_logs)
        self.dp.message(F.text)(self.handle_message)

    def _is_admin(self, user_id: int) -> bool:
        return user_id == ADMIN_ID

    async def cmd_start(self, message: types.Message):
        await message.answer("Привет! Я бесплатный ИИ-помощник. Задай вопрос!")

    async def cmd_ban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if args:
            self.users.ban_user(int(args[0]))
            await message.answer(f"Пользователь {args[0]} заблокирован!")

    async def cmd_unban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if args:
            self.users.unban_user(int(args[0]))
            await message.answer(f"Пользователь {args[0]} разблокирован!")

    async def cmd_logs(self, message: types.Message):
        if not self._is_admin(message.from_user.id):
            return
        logs = self.users.get_logs(10)
        if not logs:
            await message.answer("Логи пусты")
            return
        text = "Сообщения:\n\n"
        for log in logs:
            text += f"{log['username']}: {log['text']}\n"
        await message.answer(text)

    async def handle_message(self, message: types.Message):
        if self.users.is_banned(message.from_user.id):
            await message.answer("Вы заблокированы!")
            return
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response = await self.brain.chat(message.text)
        self.users.add_message(message.from_user.id)
        await message.answer(response)

    async def run(self):
        session = create_session()
        bot = Bot(token=self.token, session=session)
        try:
            me = await bot.get_me()
            print(f"Бот @{me.username} запущен!")
            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            await bot.session.close()

async def main():
    bot = AIBot(API_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
