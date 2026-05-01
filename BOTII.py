import asyncio
import json
import os
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

def create_session():
    return AiohttpSession()
    
API_TOKEN = '8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk'
ADMIN_ID = 8420391742
DATA_FILE = "miner_data.json"

class Rarity(Enum):
    COMMON = ("Обычный", 70, 1.0)
    UNCOMMON = ("Необычный", 25, 2.5)
    RARE = ("Редкий", 4, 7.0)
    EPIC = ("Эпический", 0.9, 20.0)
    LEGENDARY = ("Легендарный", 0.1, 100.0)
    def __init__(self, name: str, chance: float, multiplier: float):
        self.rarity_name = name
        self.chance = chance
        self.price_multiplier = multiplier

class Resource:
    def __init__(self, name: str, emoji: str, base_price: float, rarity: Rarity):
        self.name = name
        self.emoji = emoji
        self.base_price = base_price
        self.rarity = rarity
    @property
    def sell_price(self) -> float:
        fluctuation = 1.0 + math.sin(datetime.now().timestamp() / 3600) * 0.3
        return self.base_price * self.rarity.price_multiplier * fluctuation
    @property
    def buy_price(self) -> float:
        return self.sell_price * 1.2

RESOURCES = {
    "stone": Resource("Камень", "🪨", 1.0, Rarity.COMMON),
    "coal": Resource("Уголь", "🪨", 1.5, Rarity.COMMON),
    "iron": Resource("Железо", "⛏️", 5.0, Rarity.UNCOMMON),
    "copper": Resource("Медь", "🪙", 3.0, Rarity.UNCOMMON),
    "silver": Resource("Серебро", "🥈", 15.0, Rarity.RARE),
    "gold": Resource("Золото", "🥇", 40.0, Rarity.RARE),
    "diamond": Resource("Алмаз", "💎", 150.0, Rarity.EPIC),
    "emerald": Resource("Изумруд", "💚", 200.0, Rarity.EPIC),
    "mythril": Resource("Мифрил", "🔮", 1000.0, Rarity.LEGENDARY),
    "platinum": Resource("Платина", "🪶", 800.0, Rarity.LEGENDARY)
}

class Pickaxe:
    def __init__(self, level: int, name: str, emoji: str, efficiency: int, durability: int, price: float):
        self.level = level; self.name = name; self.emoji = emoji
        self.efficiency = efficiency; self.durability = durability; self.price = price

PICKAXES = {
    1: Pickaxe(1, "Деревянная", "🪓", 1, 100, 0),
    2: Pickaxe(2, "Каменная", "⛏️", 2, 200, 500),
    3: Pickaxe(3, "Железная", "⚒️", 4, 400, 2000),
    4: Pickaxe(4, "Золотая", "🥇", 6, 600, 10000),
    5: Pickaxe(5, "Алмазная", "💎", 10, 1000, 50000),
    6: Pickaxe(6, "Мифриловая", "🔮", 15, 2000, 200000),
    7: Pickaxe(7, "Легендарная", "⚡", 25, 5000, 1000000)
}

class House:
    def __init__(self, level: int, name: str, emoji: str, defense: float, max_defense: float, decay_rate: float, price: float, daily_bonus: float = 0):
        self.level = level; self.name = name; self.emoji = emoji
        self.defense = defense; self.max_defense = max_defense
        self.decay_rate = decay_rate; self.price = price; self.daily_bonus = daily_bonus

HOUSES = {
    0: House(0, "Без дома", "🏕️", 0, 0, 0, 0, 0),
    1: House(1, "Землянка", "🛖", 30, 30, 0.5, 5000, 10),
    2: House(2, "Деревянный", "🏠", 80, 80, 0.3, 30000, 25),
    3: House(3, "Каменный", "🏰", 200, 200, 0.2, 100000, 50),
    4: House(4, "Особняк", "🏛️", 500, 500, 0.1, 500000, 100),
    5: House(5, "Дворец", "👑", 1500, 1500, 0.05, 2000000, 200)
}

class GameData:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load()
        self._initialize_defaults()

    def _load(self) -> Dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"players": {}, "events": [], "global_stats": {"total_mined": 0, "next_player_id": 1}, "logs": []}

    def _initialize_defaults(self):
        if "players" not in self.data: self.data["players"] = {}
        if "events" not in self.data: self.data["events"] = []
        if "global_stats" not in self.data: self.data["global_stats"] = {"total_mined": 0, "next_player_id": 1}
        if "logs" not in self.data: self.data["logs"] = []
        if "next_player_id" not in self.data["global_stats"]: self.data["global_stats"]["next_player_id"] = 1

    def get_player(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.data["players"]:
            self.data["players"][uid] = self._new_player()
        return self.data["players"][uid]

    def _new_player(self) -> Dict:
        player_id = self.data["global_stats"]["next_player_id"]
        self.data["global_stats"]["next_player_id"] += 1
        return {
            "name": "Шахтер", "tg_name": "Шахтер", "player_id": player_id,
            "balance": 100.0, "pickaxe_level": 1, "house_level": 0,
            "mine_resources": 100, "mine_max": 100, "mine_level": 1,
            "inventory": {}, "total_mined": 0, "energy": 100, "max_energy": 100,
            "last_mine": None, "last_energy_restore": None,
            "pickaxe_durability": PICKAXES[1].durability, "house_defense": 0,
            "bonuses": {"xp_multiplier": 1.0, "coin_multiplier": 1.0},
            "banned": False, "created_at": datetime.now().isoformat()
        }

    def add_log(self, user_id: int, username: str, action: str):
        self.data["logs"].append({"user_id": user_id, "username": username, "action": action, "time": datetime.now().isoformat()})
        if len(self.data["logs"]) > 200: self.data["logs"] = self.data["logs"][-200:]

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

class MinerGame:
    def __init__(self, game_data: GameData):
        self.data = game_data

    def can_mine(self, player: Dict) -> Tuple[bool, str]:
        if player.get("banned", False): return False, "🚫 Аккаунт заблокирован!"
        if player["energy"] < 10: return False, "❌ Нет энергии!"
        if player["mine_resources"] <= 0: return False, "⛔ Шахта истощена!"
        if player["pickaxe_durability"] <= 0: return False, "🔨 Кирка сломана!"
        return True, ""

    def mine(self, player: Dict) -> Dict:
        pickaxe = PICKAXES[player["pickaxe_level"]]
        amount = int(pickaxe.efficiency * player["bonuses"]["xp_multiplier"])
        mined_resources = {}
        for _ in range(amount):
            resource = self._random_resource()
            if resource:
                for key, res in RESOURCES.items():
                    if res.name == resource.name:
                        mined_resources[key] = mined_resources.get(key, 0) + 1
                        break
        player["mine_resources"] = max(0, player["mine_resources"] - amount)
        player["energy"] = max(0, player["energy"] - 10)
        player["pickaxe_durability"] = max(0, player["pickaxe_durability"] - random.randint(1, 2))
        player["total_mined"] += amount
        player["last_mine"] = datetime.now().isoformat()
        for res_name, res_amount in mined_resources.items():
            player["inventory"][res_name] = player["inventory"].get(res_name, 0) + res_amount
        if random.random() < 0.01:
            player["mine_level"] += 1
            player["mine_max"] = int(player["mine_max"] * 1.2)
        self.data.data["global_stats"]["total_mined"] += amount
        self.data.save()
        return mined_resources

    def _random_resource(self) -> Optional[Resource]:
        roll = random.random() * 100
        for resource in RESOURCES.values():
            if roll <= resource.rarity.chance: return resource
            roll -= resource.rarity.chance
        return None

    def restore_energy(self, player: Dict):
        if player["energy"] < player["max_energy"]:
            if not player.get("last_energy_restore"):
                player["last_energy_restore"] = datetime.now().isoformat()
                player["energy"] = min(player["max_energy"], player["energy"] + 3)
            else:
                last = datetime.fromisoformat(player["last_energy_restore"])
                if (datetime.now() - last).seconds >= 120:
                    player["energy"] = min(player["max_energy"], player["energy"] + 3)
                    player["last_energy_restore"] = datetime.now().isoformat()

    def sell_resource(self, player: Dict, resource_name: str, amount: int) -> Tuple[bool, str]:
        if resource_name not in RESOURCES: return False, "❌ Неизвестный ресурс!"
        if resource_name not in player["inventory"]: return False, "❌ Нет этого ресурса!"
        if player["inventory"][resource_name] < amount: amount = player["inventory"][resource_name]
        price = RESOURCES[resource_name].sell_price * player["bonuses"]["coin_multiplier"] * amount
        player["inventory"][resource_name] -= amount
        if player["inventory"][resource_name] <= 0: del player["inventory"][resource_name]
        player["balance"] += price
        return True, f"✅ Продано {amount}x {RESOURCES[resource_name].emoji} за {price:.1f} 💰"

    def buy_resource(self, player: Dict, resource_name: str, amount: int) -> Tuple[bool, str]:
        if resource_name not in RESOURCES: return False, "❌ Неизвестный ресурс!"
        total_cost = RESOURCES[resource_name].buy_price * amount
        if player["balance"] < total_cost: return False, f"❌ Нужно {total_cost:.1f} 💰"
        player["balance"] -= total_cost
        player["inventory"][resource_name] = player["inventory"].get(resource_name, 0) + amount
        return True, f"✅ Куплено {amount}x {RESOURCES[resource_name].emoji}"

    def get_leaderboard(self) -> List[Tuple[str, int, float]]:
        players = []
        for uid, p in self.data.data["players"].items():
            if not p.get("banned", False):
                name = p.get("tg_name", p.get("name", "Шахтер"))
                players.append((name, p["player_id"], p["total_mined"]))
        players.sort(key=lambda x: x[2], reverse=True)
        return players[:10]

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⛏️ Копать", callback_data="mine")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="🎒 Инвентарь", callback_data="inventory")
    builder.button(text="🏪 Магазин", callback_data="shop")
    builder.button(text="🏠 Недвижимость", callback_data="realty")
    builder.button(text="⛏ Кирка", callback_data="pickaxe_menu")
    builder.button(text="🏆 Топ", callback_data="leaderboard")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

class MinerBot:
    def __init__(self, token: str, admin_id: int):
        self.token = token
        self.admin_id = admin_id
        self.game_data = GameData(DATA_FILE)
        self.game = MinerGame(self.game_data)
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        self.dp.message(F.text.lower().in_(["копать", "шахта", "добыча"]))(self.cmd_text_mine)
        self.dp.message(F.text.lower().in_(["статистика", "профиль", "стат"]))(self.cmd_text_stats)
        self.dp.message(F.text.lower().in_(["инвентарь", "ресурсы", "инв"]))(self.cmd_text_inventory)
        self.dp.message(F.text.lower().in_(["магазин", "рынок", "магаз"]))(self.cmd_text_shop)
        self.dp.message(F.text.lower().in_(["недвижимость", "дом"]))(self.cmd_text_realty)
        self.dp.message(F.text.lower().in_(["кирка", "инструмент"]))(self.cmd_text_pickaxe)
        self.dp.message(F.text.lower().in_(["топ", "лидеры", "таблица"]))(self.cmd_text_leaderboard)
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("id"))(self.cmd_id)
        self.dp.message(Command("pay"))(self.cmd_pay)
        self.dp.message(Command("admin"))(self.cmd_admin)
        self.dp.message(Command("event"))(self.cmd_event)
        self.dp.message(Command("announce"))(self.cmd_announce)
        self.dp.message(Command("ban"))(self.cmd_ban)
        self.dp.message(Command("unban"))(self.cmd_unban)
        self.dp.message(Command("logs"))(self.cmd_logs)
        self.dp.message(Command("logall"))(self.cmd_logall)
        self.dp.message(F.chat.type.in_(["group", "supergroup"]))(self.on_group_message)
        self.dp.callback_query(F.data == "mine")(self.callback_mine)
        self.dp.callback_query(F.data == "stats")(self.callback_stats)
        self.dp.callback_query(F.data == "inventory")(self.callback_inventory)
        self.dp.callback_query(F.data == "shop")(self.callback_shop)
        self.dp.callback_query(F.data == "realty")(self.callback_realty)
        self.dp.callback_query(F.data == "pickaxe_menu")(self.callback_pickaxe_menu)
        self.dp.callback_query(F.data == "back_main")(self.callback_back_main)
        self.dp.callback_query(F.data == "leaderboard")(self.callback_leaderboard)
        self.dp.callback_query(F.data.startswith("shopres_"))(self.callback_shop_resource)

    def _is_admin(self, uid): return uid == self.admin_id
    def _get_by_id(self, pid):
        for uid, p in self.game_data.data["players"].items():
            if p.get("player_id") == pid: return uid, p
        return None

    async def notify_all(self, text: str, bot: Bot):
        for uid in self.game_data.data["players"]:
            try: await bot.send_message(int(uid), f"📢 {text}")
            except: pass

    async def on_group_message(self, message: types.Message):
        p = self.game_data.get_player(message.from_user.id)
        p["tg_name"] = message.from_user.full_name
        self.game_data.save()

    async def cmd_text_mine(self, message: types.Message):
        await self._do_mine(message, message.from_user.id)

    async def _do_mine(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        player["tg_name"] = message.from_user.full_name
        self.game.restore_energy(player)
        can_mine, msg = self.game.can_mine(player)
        if not can_mine:
            await message.answer(msg)
            return
        mined = self.game.mine(player)
        if mined:
            resources_text = "\n".join([f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт." for name, amount in mined.items()])
            pickaxe = PICKAXES[player["pickaxe_level"]]
            text = f"⛏️ *Добыча завершена!*\n\nДобыто:\n{resources_text}\n\n⚡ Энергия: {player['energy']}/{player['max_energy']}\n⛏️ Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n💎 Шахта: {player['mine_resources']}/{player['mine_max']}"
        else:
            text = "🤷 Ничего не добыто."
        self.game_data.save()
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_stats(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        player["tg_name"] = message.from_user.full_name
        pickaxe = PICKAXES[player["pickaxe_level"]]
        house = HOUSES[player["house_level"]]
        dev_tag = " 🛠 Разработчик" if message.from_user.id == self.admin_id else ""
        ban_status = " 🚫 ЗАБЛОКИРОВАН" if player.get("banned") else ""
        text = f"📊 *Профиль #{player['player_id']}*\n👤 {message.from_user.full_name}\n{dev_tag}{ban_status}\n\n💰 Баланс: {player['balance']:.1f}\n⚡ Энергия: {player['energy']}/{player['max_energy']}\n🔨 Кирка: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n⛏️ Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n🏠 Дом: {house.emoji} {house.name} (ур.{house.level})\n🛡️ Прочность дома: {player['house_defense']:.0f}/{house.max_defense}\n⛏️ Шахта: {player['mine_resources']}/{player['mine_max']} (ур.{player['mine_level']})\n💎 Добыто: {player['total_mined']}\n🎒 Видов ресурсов: {len(player['inventory'])}"
        if player["bonuses"]["coin_multiplier"] > 1: text += f"\n🎉 Бонус x{player['bonuses']['coin_multiplier']}!"
        self.game_data.save()
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_inventory(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        if not player["inventory"]:
            text = "🎒 *Инвентарь пуст*"
        else:
            items_text = "\n".join([f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт. (~{RESOURCES[name].sell_price * amount:.0f}💰)" for name, amount in sorted(player["inventory"].items(), key=lambda x: RESOURCES[x[0]].sell_price, reverse=True)])
            total = sum(RESOURCES[name].sell_price * amount for name, amount in player["inventory"].items())
            text = f"🎒 *Инвентарь*\n\n{items_text}\n\n💰 Стоимость: {total:.0f}"
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="back_main")
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_shop(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        shop_text = "🏪 *Магазин*\n\n"
        shop_text += "\n".join([f"{r.emoji} {r.name} ({r.rarity.rarity_name})\n  📈 Продажа: {r.sell_price:.1f}💰 | Покупка: {r.buy_price:.1f}💰" for r in RESOURCES.values()])
        shop_text += f"\n\n💰 Баланс: {player['balance']:.1f}"
        await message.answer(shop_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_realty(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        house = HOUSES[player["house_level"]]
        text = f"🏠 *Недвижимость*\n\nТекущий дом: {house.emoji} {house.name}\n🛡️ Прочность: {player['house_defense']:.0f}/{house.max_defense}\n⚡ Бонус энергии: +{house.daily_bonus}\n\n*Доступные дома:*\n\n"
        for level, h in HOUSES.items():
            if level > player["house_level"]:
                text += f"{h.emoji} *{h.name}* (ур.{level})\n🛡️ Прочность: {h.max_defense}\n⚡ Бонус энергии: +{h.daily_bonus}\n💰 Цена: {h.price:.0f}\n\n"
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_pickaxe(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        pickaxe = PICKAXES[player["pickaxe_level"]]
        text = f"🔨 *Кирка*\n\nТекущая: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n⛏️ Эффективность: {pickaxe.efficiency}\n💪 Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n\n*Доступные кирки:*\n\n"
        for level, p in PICKAXES.items():
            if level > player["pickaxe_level"]:
                text += f"{p.emoji} *{p.name}* (ур.{level})\n⛏️ Эффективность: {p.efficiency}\n💪 Прочность: {p.durability}\n💰 Цена: {p.price:.0f}\n\n"
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_leaderboard(self, message: types.Message):
        top = self.game.get_leaderboard()
        if not top:
            text = "🏆 *Топ игроков*\n\nПока никого нет!"
        else:
            text = "🏆 *Топ-10*\n\n"
            for i, (name, pid, mined) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} #{pid} {name}: {mined} ед.\n"
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_start(self, message: types.Message):
        p = self.game_data.get_player(message.from_user.id)
        p["tg_name"] = message.from_user.full_name
        self.game_data.save()
        await message.answer(
            f"⛏️ *Дарова я ВацапочкИИ!*\n\n"
            f"🆔 ID: {p['player_id']}\n💰 Баланс: {p['balance']:.1f}\n\n"
            f"Кнопки внизу или команды: Копать, Стат, Инвентарь, Магазин, Дом, Кирка, Топ\n\n"
            f"/id — узнать ID\n/pay ID СУММА — перевести деньги",
            reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_id(self, message: types.Message):
        p = self.game_data.get_player(message.from_user.id)
        await message.answer(f"🆔 Твой ID: {p['player_id']}")

    async def cmd_pay(self, message: types.Message, command: CommandObject):
        args = command.args.split() if command.args else []
        if len(args) < 2: await message.answer("❌ /pay ID СУММА"); return
        target_id = int(args[0]); amount = float(args[1])
        if amount <= 0: await message.answer("❌ Сумма > 0!"); return
        result = self._get_by_id(target_id)
        if not result: await message.answer("❌ Игрок не найден!"); return
        to_uid, to_player = result
        from_player = self.game_data.get_player(message.from_user.id)
        if from_player["balance"] < amount: await message.answer("❌ Недостаточно денег!"); return
        from_player["balance"] -= amount
        to_player["balance"] += amount
        self.game_data.add_log(message.from_user.id, message.from_user.full_name, f"Перевел {amount}💰 игроку #{target_id}")
        self.game_data.save()
        await message.answer(f"✅ Переведено {amount:.1f} 💰 игроку #{target_id}")
        try: await message.bot.send_message(int(to_uid), f"💰 Игрок #{from_player['player_id']} перевел вам {amount:.1f} 💰")
        except: pass

    async def cmd_admin(self, message: types.Message):
        if not self._is_admin(message.from_user.id): return
        await message.answer("👑 *Админ-панель*\n/event x2|x3|lucky|energize|halfprice|reset|restore|give ID SUM\n/announce ТЕКСТ\n/ban ID | /unban ID\n/logs [число] | /logall", parse_mode=ParseMode.MARKDOWN)

    async def cmd_event(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id): return
        args = command.args.split() if command.args else []
        if not args: return
        et = args[0]; msg = ""
        if et == "x2":
            for p in self.game_data.data["players"].values(): p["bonuses"]["xp_multiplier"] = 2.0
            msg = "🎉 Ивент: x2 добыча!"
        elif et == "x3":
            for p in self.game_data.data["players"].values(): p["bonuses"]["xp_multiplier"] = 3.0
            msg = "🎉 Ивент: x3 добыча!"
        elif et == "lucky":
            for uid, p in self.game_data.data["players"].items():
                if not p.get("banned") and random.random() < 0.3:
                    r = random.choice(["diamond","emerald","mythril","platinum"])
                    p["inventory"][r] = p["inventory"].get(r,0) + random.randint(1,3)
            msg = "🎉 Ящик с сюрпризом открыт!"
        elif et == "energize":
            for p in self.game_data.data["players"].values(): p["energy"] = p["max_energy"]
            msg = "⚡ Энергия восстановлена!"
        elif et == "halfprice":
            for p in self.game_data.data["players"].values(): p["bonuses"]["coin_multiplier"] = 0.5
            msg = "🏷️ Скидка 50% в магазине!"
        elif et == "reset":
            for p in self.game_data.data["players"].values(): p["bonuses"]["xp_multiplier"] = 1.0; p["bonuses"]["coin_multiplier"] = 1.0
            msg = "✅ Ивенты сброшены!"
        elif et == "restore":
            for p in self.game_data.data["players"].values(): p["mine_resources"] = p["mine_max"]
            msg = "✅ Шахты восстановлены!"
        elif et == "give" and len(args) >= 3:
            r = self._get_by_id(int(args[1]))
            if r: r[1]["balance"] += float(args[2]); msg = f"✅ Выдано {args[2]} 💰 игроку #{args[1]}"
        self.game_data.save()
        if msg:
            await message.answer(msg)
            await self.notify_all(msg, message.bot)

    async def cmd_announce(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id): return
        text = command.args
        if not text: await message.answer("❌ /announce ТЕКСТ"); return
        await self.notify_all(f"📢 Объявление:\n{text}", message.bot)
        await message.answer("✅ Отправлено!")

    async def cmd_ban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id): return
        args = command.args.split() if command.args else []
        if not args: return
        r = self._get_by_id(int(args[0]))
        if r: r[1]["banned"] = True; self.game_data.save(); await message.answer(f"🚫 Игрок #{args[0]} заблокирован!")

    async def cmd_unban(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id): return
        args = command.args.split() if command.args else []
        if not args: return
        r = self._get_by_id(int(args[0]))
        if r: r[1]["banned"] = False; self.game_data.save(); await message.answer(f"✅ Игрок #{args[0]} разблокирован!")

    async def cmd_logs(self, message: types.Message, command: CommandObject):
        if not self._is_admin(message.from_user.id): return
        args = command.args.split() if command.args else []
        count = int(args[0]) if args else 10
        logs = self.game_data.data.get("logs", [])[-count:]
        if not logs: await message.answer("📋 Логи пусты"); return
        text = "📋 *Последние действия:*\n\n"
        for log in logs: text += f"👤 {log['username']} (ID:{log['user_id']}): {log['action']}\n"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_logall(self, message: types.Message):
        if not self._is_admin(message.from_user.id): return
        logs = self.game_data.data.get("logs", [])
        if not logs: await message.answer("📋 Логи пусты"); return
        text = f"📋 *Всего записей: {len(logs)}*\n\n"
        for log in logs[-30:]: text += f"👤 {log['username']} (ID:{log['user_id']}): {log['action']}\n"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

    async def callback_mine(self, callback: types.CallbackQuery):
        await self._do_mine(callback, callback.from_user.id)
        await callback.answer()

    async def callback_stats(self, callback: types.CallbackQuery):
        player = self.game_data.get_player(callback.from_user.id)
        player["tg_name"] = callback.from_user.full_name
        pickaxe = PICKAXES[player["pickaxe_level"]]
        house = HOUSES[player["house_level"]]
        dev_tag = " 🛠 Разработчик" if callback.from_user.id == self.admin_id else ""
        ban_status = " 🚫 ЗАБЛОКИРОВАН" if player.get("banned") else ""
        text = f"📊 *Профиль #{player['player_id']}*\n👤 {callback.from_user.full_name}\n{dev_tag}{ban_status}\n\n💰 Баланс: {player['balance']:.1f}\n⚡ Энергия: {player['energy']}/{player['max_energy']}\n🔨 Кирка: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n⛏️ Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n🏠 Дом: {house.emoji} {house.name} (ур.{house.level})\n🛡️ Прочность дома: {player['house_defense']:.0f}/{house.max_defense}\n⛏️ Шахта: {player['mine_resources']}/{player['mine_max']} (ур.{player['mine_level']})\n💎 Добыто: {player['total_mined']}\n🎒 Видов ресурсов: {len(player['inventory'])}"
        if player["bonuses"]["coin_multiplier"] > 1: text += f"\n🎉 Бонус x{player['bonuses']['coin_multiplier']}!"
        self.game_data.save()
        await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def callback_inventory(self, callback: types.CallbackQuery):
        player = self.game_data.get_player(callback.from_user.id)
        if not player["inventory"]:
            text = "🎒 *Инвентарь пуст*"
        else:
            items_text = "\n".join([f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт. (~{RESOURCES[name].sell_price * amount:.0f}💰)" for name, amount in sorted(player["inventory"].items(), key=lambda x: RESOURCES[x[0]].sell_price, reverse=True)])
            total = sum(RESOURCES[name].sell_price * amount for name, amount in player["inventory"].items())
            text = f"🎒 *Инвентарь*\n\n{items_text}\n\n💰 Стоимость: {total:.0f}"
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="back_main")
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def callback_shop(self, callback: types.CallbackQuery):
        player = self.game_data.get_player(callback.from_user.id)
        shop_text = "🏪 *Магазин*\n\n"
        shop_text += "\n".join([f"{r.emoji} {r.name} ({r.rarity.rarity_name})\n  📈 Продажа: {r.sell_price:.1f}💰 | Покупка: {r.buy_price:.1f}💰" for r in RESOURCES.values()])
        shop_text += f"\n\n💰 Баланс: {player['balance']:.1f}"
        await callback.message.edit_text(shop_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def callback_shop_resource(self, callback: types.CallbackQuery):
        res_name = callback.data.split("_")[1]
        resource = RESOURCES[res_name]
        text = f"{resource.emoji} *{resource.name}*\n\n📈 Продажа: {resource.sell_price:.1f}💰\n📉 Покупка: {resource.buy_price:.1f}💰"
        builder = InlineKeyboardBuilder()
        builder.button(text="🛒 Купить 1", callback_data=f"buy_{res_name}")
        builder.button(text="💰 Продать всё", callback_data=f"sell_{res_name}")
        builder.button(text="🔙 Назад", callback_data="shop")
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def callback_realty(self, callback: types.CallbackQuery):
        player = self.game_data.get_player(callback.from_user.id)
        house = HOUSES[player["house_level"]]
        text = f"🏠 *Недвижимость*\n\nТекущий дом: {house.emoji} {house.name}\n🛡️ Прочность: {player['house_defense']:.0f}/{house.max_defense}\n\n*Доступные дома:*\n\n"
        for level, h in HOUSES.items():
            if level > player["house_level"]:
                text += f"{h.emoji} *{h.name}* (ур.{level})\n🛡️ Прочность: {h.max_defense}\n💰 Цена: {h.price:.0f}\n\n"
        builder = InlineKeyboardBuilder()
        for level, h in HOUSES.items():
            if level > player["house_level"]:
                builder.button(text=f"{h.emoji} {h.name} - {h.price:.0f}💰", callback_data=f"buyhouse_{level}")
        builder.button(text="🔙 Назад", callback_data="back_main")
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def callback_pickaxe_menu(self, callback: types.CallbackQuery):
        player = self.game_data.get_player(callback.from_user.id)
        pickaxe = PICKAXES[player["pickaxe_level"]]
        text = f"🔨 *Кирка*\n\nТекущая: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n⛏️ Эффективность: {pickaxe.efficiency}\n💪 Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n\n*Доступные кирки:*\n\n"
        builder = InlineKeyboardBuilder()
        for level, p in PICKAXES.items():
            if level > player["pickaxe_level"]:
                text += f"{p.emoji} *{p.name}* (ур.{level})\n⛏️ Эффективность: {p.efficiency}\n💰 Цена: {p.price:.0f}\n\n"
                builder.button(text=f"{p.emoji} {p.name} - {p.price:.0f}💰", callback_data=f"buypick_{level}")
        builder.button(text="🔙 Назад", callback_data="back_main")
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def callback_leaderboard(self, callback: types.CallbackQuery):
        top = self.game.get_leaderboard()
        if not top: text = "🏆 *Топ игроков*\n\nПока никого нет!"
        else:
            text = "🏆 *Топ-10*\n\n"
            for i, (name, pid, mined) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} #{pid} {name}: {mined} ед.\n"
        await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
        await callback.answer()

    async def callback_back_main(self, callback: types.CallbackQuery):
        await callback.message.edit_text("⛏️ *Главное меню*\nВыбери действие:", reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def run(self):
        session = create_session()
        bot = Bot(token=self.token, session=session)
        print("⛏️ Шахтер-Симулятор запускается...")
        try:
            me = await bot.get_me()
            print(f"✅ Бот @{me.username} успешно запущен!")
            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        finally:
            await bot.session.close()

async def main():
    bot = MinerBot(API_TOKEN, ADMIN_ID)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот завершает работу...")