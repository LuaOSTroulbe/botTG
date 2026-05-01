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
HF_TOKEN = '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'  # ← Замени
ADMIN_ID = 8420391742
DATA_FILE = "ai_users.json"
API_URL = "API_URL = "API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

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
    def __init__(self, token: str):
        self.token = token

    async def chat(self, text: str) -> str:
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "inputs": f"<s>[INST] {text} [/INST]",
            "parameters": {"max_new_tokens": 500}
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data[0]["generated_text"].split("[/INST]")[-1].strip()
                    else:
                        return f"Ошибка: {resp.status}"
        except Exception as e:
            return f"Ошибка: {str(e)[:50]}"

class AIBot:
    def __init__(self, token: str, hf_token: str):
        self.token = token
        self.hf_token = hf_token
        self.users = UserData(DATA_FILE)
        self.brain = AIBrain(hf_token)
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
        await message.answer(
            f"Привет! Я ИИ-помощник на базе Mistral.\n\n"
            f"Задай мне любой вопрос!\n\n"
            f"/help - помощь\n"
            f"/clear - очистить историю"
        )

    async def cmd_help(self, message: types.Message):
        await message.answer("Я работаю на базе Mistral 7B. Просто напиши мне!")

    async def cmd_clear(self, message: types.Message):
        await message.answer("История очищена!")

    async def cmd_ban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if not args:
            await message.answer("Укажи ID: /ban {user_id}")
            return
        self.users.ban_user(int(args[0]))
        await message.answer(f"Пользователь {args[0]} заблокирован!")

    async def cmd_unban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        if not args:
            await message.answer("Укажи ID: /unban {user_id}")
            return
        self.users.unban_user(int(args[0]))
        await message.answer(f"Пользователь {args[0]} разблокирован!")

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
        text = f"Всего сообщений: {len(logs)}\n\n"
        for log in logs[-30:]:
            text += f"{log['username']} (ID:{log['user_id']}): {log['text']}\n"
        await message.answer(text)

    async def handle_message(self, message: types.Message):
        if self.users.is_banned(message.from_user.id):
            await message.answer("Вы заблокированы!")
            return
        if not message.text.startswith("/"):
            self.users.add_log(message.from_user.id, message.from_user.full_name, message.text)
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
    bot = AIBot(API_TOKEN, HF_TOKEN)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот завершает работу...")
