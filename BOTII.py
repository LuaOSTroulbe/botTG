import asyncio
import json
import os
import random
import ssl
import socket
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientTimeout, TCPConnector

# ============================================
# ОБХОД БЛОКИРОВКИ (ПРОСТОЙ И РАБОЧИЙ)
# ============================================
def create_session():
    return AiohttpSession()
    
# ностройкэ
API_TOKEN = '8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk'
ADMIN_ID = 8420391742  # Твой Telegram ID
DATA_FILE = "miner_data.json"

# Редкости  и т.д
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
        self.current_price = base_price * rarity.price_multiplier

    @property
    def sell_price(self) -> float:
        fluctuation = 1.0 + math.sin(datetime.now().timestamp() / 3600) * 0.3
        return self.base_price * self.rarity.price_multiplier * fluctuation

    @property
    def buy_price(self) -> float:
        # Цена покупки на 20% выше цены продажи
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
    def __init__(self, level: int, name: str, emoji: str, efficiency: int,
                 durability: int, price: float, min_level: int = 1):
        self.level = level
        self.name = name
        self.emoji = emoji
        self.efficiency = efficiency
        self.durability = durability
        self.price = price
        self.min_level = min_level


PICKAXES = {
    1: Pickaxe(1, "Деревянная кирка", "🪓", 1, 100, 0),
    2: Pickaxe(2, "Каменная кирка", "⛏️", 2, 200, 500),
    3: Pickaxe(3, "Железная кирка", "⚒️", 4, 400, 2000),
    4: Pickaxe(4, "Золотая кирка", "🥇", 6, 600, 10000),
    5: Pickaxe(5, "Алмазная кирка", "💎", 10, 1000, 50000),
    6: Pickaxe(6, "Мифриловая кирка", "🔮", 15, 2000, 200000),
    7: Pickaxe(7, "Легендарная кирка", "⚡", 25, 5000, 1000000)
}


class House:
    def __init__(self, level: int, name: str, emoji: str, defense: float,
                 max_defense: float, decay_rate: float, price: float,
                 daily_bonus: float = 0):
        self.level = level
        self.name = name
        self.emoji = emoji
        self.defense = defense
        self.max_defense = max_defense
        self.decay_rate = decay_rate
        self.price = price
        self.daily_bonus = daily_bonus


HOUSES = {
    0: House(0, "Без дома", "🏕️", 0, 0, 0, 0, 0),
    1: House(1, "Землянка", "🛖", 30, 30, 0.5, 5000, 10),
    2: House(2, "Деревянный дом", "🏠", 80, 80, 0.3, 30000, 25),
    3: House(3, "Каменный дом", "🏰", 200, 200, 0.2, 100000, 50),
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
            except:
                pass
        return {"players": {}, "events": [], "global_stats": {"total_mined": 0, "next_player_id": 1}, "logs": []}

    def _initialize_defaults(self):
        if "players" not in self.data:
            self.data["players"] = {}
        if "events" not in self.data:
            self.data["events"] = []
        if "global_stats" not in self.data:
            self.data["global_stats"] = {"total_mined": 0, "next_player_id": 1}
        if "logs" not in self.data:
            self.data["logs"] = []
        if "next_player_id" not in self.data["global_stats"]:
            self.data["global_stats"]["next_player_id"] = 1

    def get_player(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.data["players"]:
            self.data["players"][uid] = self._new_player()
        return self.data["players"][uid]

    def _new_player(self) -> Dict:
        player_id = self.data["global_stats"]["next_player_id"]
        self.data["global_stats"]["next_player_id"] += 1
        return {
            "name": "Шахтер",
            "tg_name": "Шахтер",
            "player_id": player_id,
            "balance": 100.0,
            "pickaxe_level": 1,
            "house_level": 0,
            "mine_resources": 100,
            "mine_max": 100,
            "mine_level": 1,
            "inventory": {},
            "total_mined": 0,
            "damage_dealt": 0,
            "energy": 100,
            "max_energy": 100,
            "last_mine": None,
            "last_energy_restore": None,
            "pickaxe_durability": PICKAXES[1].durability,
            "house_defense": 0,
            "bonuses": {"xp_multiplier": 1.0, "coin_multiplier": 1.0},
            "achievements": [],
            "banned": False,
            "created_at": datetime.now().isoformat()
        }

    def add_log(self, user_id: int, username: str, action: str):
        self.data["logs"].append({
            "user_id": user_id,
            "username": username,
            "action": action,
            "time": datetime.now().isoformat()
        })
        if len(self.data["logs"]) > 200:
            self.data["logs"] = self.data["logs"][-200:]

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


class MinerGame:
    def __init__(self, game_data: GameData):
        self.data = game_data

    def can_mine(self, player: Dict) -> Tuple[bool, str]:
        if player.get("banned", False):
            return False, "🚫 Ваш аккаунт заблокирован!"
        if player["energy"] <= 0:
            return False, "❌ Нет энергии! Подожди восстановления."
        if player["mine_resources"] <= 0:
            return False, "⛔ Шахта истощена! Жди обновления."
        pickaxe = PICKAXES[player["pickaxe_level"]]
        if player["pickaxe_durability"] <= 0:
            return False, "🔨 Кирка сломана! Купи новую или почини."
        return True, ""

    def mine(self, player: Dict) -> Dict:
        pickaxe = PICKAXES[player["pickaxe_level"]]
        base_amount = pickaxe.efficiency
        mine_level_bonus = 1 + (player["mine_level"] - 1) * 0.1
        amount = int(base_amount * mine_level_bonus * player["bonuses"]["xp_multiplier"])

        mined_resources = {}
        for _ in range(amount):
            resource = self._random_resource()
            if resource:
                eng_key = None
                for key, res in RESOURCES.items():
                    if res.name == resource.name:
                        eng_key = key
                        break
                if eng_key:
                    mined_resources[eng_key] = mined_resources.get(eng_key, 0) + 1

        player["mine_resources"] = max(0, player["mine_resources"] - amount)
        player["energy"] = max(0, player["energy"] - 10)
        player["pickaxe_durability"] = max(0, player["pickaxe_durability"] - random.randint(1, 2))
        player["total_mined"] += amount
        player["damage_dealt"] += amount
        player["last_mine"] = datetime.now().isoformat()

        if player["mine_resources"] <= 0:
            player["mine_resources"] = 0

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
            if roll <= resource.rarity.chance:
                return resource
            roll -= resource.rarity.chance
        return None

    def restore_mine(self, player: Dict):
        if player["mine_resources"] <= 0:
            restore_time = 3600
            if player.get("last_mine"):
                last = datetime.fromisoformat(player["last_mine"])
                if (datetime.now() - last).seconds >= restore_time:
                    player["mine_resources"] = player["mine_max"]
                    player["damage_dealt"] = 0

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
        if resource_name not in RESOURCES:
            return False, "❌ Неизвестный ресурс!"
        if resource_name not in player["inventory"]:
            return False, "❌ У тебя нет этого ресурса!"
        if player["inventory"][resource_name] < amount:
            amount = player["inventory"][resource_name]
        resource = RESOURCES[resource_name]
        price = resource.sell_price * player["bonuses"]["coin_multiplier"] * amount
        player["inventory"][resource_name] -= amount
        if player["inventory"][resource_name] <= 0:
            del player["inventory"][resource_name]
        player["balance"] += price
        return True, f"✅ Продано {amount}x {resource.emoji} {resource.name} за {price:.1f} 💰"

    def buy_resource(self, player: Dict, resource_name: str, amount: int) -> Tuple[bool, str]:
        """Покупка руды в магазине"""
        if resource_name not in RESOURCES:
            return False, "❌ Неизвестный ресурс!"
        resource = RESOURCES[resource_name]
        total_cost = resource.buy_price * amount
        if player["balance"] < total_cost:
            return False, f"❌ Не хватает денег! Нужно {total_cost:.1f} 💰"
        player["balance"] -= total_cost
        player["inventory"][resource_name] = player["inventory"].get(resource_name, 0) + amount
        return True, f"✅ Куплено {amount}x {resource.emoji} {resource.name} за {total_cost:.1f} 💰"

    def upgrade_pickaxe(self, player: Dict) -> Tuple[bool, str]:
        next_level = player["pickaxe_level"] + 1
        if next_level not in PICKAXES:
            return False, "🏆 У тебя максимальный уровень кирки!"
        next_pickaxe = PICKAXES[next_level]
        if player["balance"] < next_pickaxe.price:
            return False, f"❌ Не хватает денег! Нужно {next_pickaxe.price:.0f} 💰"
        player["balance"] -= next_pickaxe.price
        player["pickaxe_level"] = next_level
        player["pickaxe_durability"] = next_pickaxe.durability
        return True, f"✅ Куплена {next_pickaxe.emoji} {next_pickaxe.name}!"

    def repair_pickaxe(self, player: Dict) -> Tuple[bool, str]:
        pickaxe = PICKAXES[player["pickaxe_level"]]
        if player["pickaxe_durability"] >= pickaxe.durability:
            return False, "✅ Кирка и так в порядке!"
        repair_cost = pickaxe.price * 0.3
        if player["balance"] < repair_cost:
            return False, f"❌ Не хватает денег! Нужно {repair_cost:.0f} 💰"
        player["balance"] -= repair_cost
        player["pickaxe_durability"] = pickaxe.durability
        return True, f"✅ Кирка починена за {repair_cost:.0f} 💰"

    def buy_house(self, player: Dict, house_level: int) -> Tuple[bool, str]:
        if house_level not in HOUSES:
            return False, "❌ Неизвестный дом!"
        if house_level <= player["house_level"]:
            return False, "❌ У тебя уже есть дом лучше или такой же!"
        house = HOUSES[house_level]
        if player["balance"] < house.price:
            return False, f"❌ Не хватает денег! Нужно {house.price:.0f} 💰"
        player["balance"] -= house.price
        player["house_level"] = house_level
        player["house_defense"] = house.defense
        player["max_energy"] = 100 + house.daily_bonus
        return True, f"✅ Куплен {house.emoji} {house.name}!"

    def repair_house(self, player: Dict) -> Tuple[bool, str]:
        if player["house_level"] == 0:
            return False, "❌ У тебя нет дома!"
        house = HOUSES[player["house_level"]]
        if player["house_defense"] >= house.max_defense:
            return False, "✅ Дом в отличном состоянии!"
        repair_cost = house.price * 0.1
        if player["balance"] < repair_cost:
            return False, f"❌ Не хватает денег! Нужно {repair_cost:.0f} 💰"
        player["balance"] -= repair_cost
        player["house_defense"] = house.max_defense
        return True, f"✅ Дом отремонтирован за {repair_cost:.0f} 💰"

    def degrade_house(self, player: Dict):
        if player["house_level"] > 0:
            house = HOUSES[player["house_level"]]
            player["house_defense"] -= house.decay_rate
            if player["house_defense"] <= 0:
                player["house_level"] = 0
                player["house_defense"] = 0
                player["max_energy"] = 100
                return "🏚️ Твой дом разрушился! Нужно покупать новый."
        return None

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
    builder.button(text="🏆 Таблица лидеров", callback_data="leaderboard")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def get_shop_keyboard():
    builder = InlineKeyboardBuilder()
    for res_name, resource in RESOURCES.items():
        sell_price_str = f"{resource.sell_price:.1f}"
        buy_price_str = f"{resource.buy_price:.1f}"
        builder.button(
            text=f"{resource.emoji} {resource.name} ({resource.rarity.rarity_name})",
            callback_data=f"shopres_{res_name}"
        )
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def get_resource_action_keyboard(res_name: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить", callback_data=f"buyres_{res_name}")
    builder.button(text="💰 Продать", callback_data=f"sell_{res_name}")
    builder.button(text="🔙 Назад в магазин", callback_data="shop")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_house_keyboard():
    builder = InlineKeyboardBuilder()
    for level, house in HOUSES.items():
        if level > 0:
            builder.button(
                text=f"{house.emoji} {house.name} - {house.price:.0f}💰",
                callback_data=f"buy_house_{level}"
            )
    builder.button(text="🔧 Ремонт дома", callback_data="repair_house")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_pickaxe_keyboard():
    builder = InlineKeyboardBuilder()
    for level, pickaxe in PICKAXES.items():
        builder.button(
            text=f"{pickaxe.emoji} {pickaxe.name} - {pickaxe.price:.0f}💰",
            callback_data=f"buy_pickaxe_{level}"
        )
    builder.button(text="🔧 Починить кирку", callback_data="repair_pickaxe")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(1)
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
        # Текстовые команды
        self.dp.message(F.text.lower().in_(["копать", "шахта", "добыча"]))(self.cmd_text_mine)
        self.dp.message(F.text.lower().in_(["статистика", "профиль"]))(self.cmd_text_stats)
        self.dp.message(F.text.lower().in_(["инвентарь", "ресурсы"]))(self.cmd_text_inventory)
        self.dp.message(F.text.lower().in_(["магазин", "рынок"]))(self.cmd_text_shop)
        self.dp.message(F.text.lower().in_(["недвижимость", "дом"]))(self.cmd_text_realty)
        self.dp.message(F.text.lower().in_(["кирка", "инструмент"]))(self.cmd_text_pickaxe)
        self.dp.message(F.text.lower().in_(["топ", "лидеры", "таблица"]))(self.cmd_text_leaderboard)
        
        # Команды
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
        self.dp.message(Command("setpickaxe"))(self.cmd_setpickaxe)
        self.dp.message(Command("sethouse"))(self.cmd_sethouse)
        self.dp.message(Command("resetplayer"))(self.cmd_resetplayer)
        
        # Авто-регистрация в группах
        self.dp.message(F.chat.type.in_(["group", "supergroup"]))(self.on_group_message)
        self.dp.my_chat_member()(self.on_bot_added_to_group)
        
        # Callbacks
        self.dp.callback_query(F.data == "mine")(self.callback_mine)
        self.dp.callback_query(F.data == "stats")(self.callback_stats)
        self.dp.callback_query(F.data == "inventory")(self.callback_inventory)
        self.dp.callback_query(F.data == "shop")(self.callback_shop)
        self.dp.callback_query(F.data == "realty")(self.callback_realty)
        self.dp.callback_query(F.data == "pickaxe_menu")(self.callback_pickaxe_menu)
        self.dp.callback_query(F.data == "back_main")(self.callback_back_main)
        self.dp.callback_query(F.data == "repair_house")(self.callback_repair_house)
        self.dp.callback_query(F.data == "repair_pickaxe")(self.callback_repair_pickaxe)
        self.dp.callback_query(F.data == "leaderboard")(self.callback_leaderboard)
        self.dp.callback_query(F.data.startswith("shopres_"))(self.callback_shop_resource)
        self.dp.callback_query(F.data.startswith("buyres_"))(self.callback_buy_resource)
        self.dp.callback_query(F.data.startswith("sell_"))(self.callback_sell)
        self.dp.callback_query(F.data.startswith("buy_pickaxe_"))(self.callback_buy_pickaxe)
        self.dp.callback_query(F.data.startswith("buy_house_"))(self.callback_buy_house)

    def _is_admin_or_dev(self, user_id: int) -> bool:
        return user_id == self.admin_id

    def _get_player_by_id(self, player_id: int) -> Optional[Tuple[str, Dict]]:
        for uid, p in self.game_data.data["players"].items():
            if p.get("player_id") == player_id:
                return uid, p
        return None

    def _get_player_by_username(self, username: str) -> Optional[Tuple[str, Dict]]:
        for uid, p in self.game_data.data["players"].items():
            if p.get("tg_name", "").lower() == username.lower():
                return uid, p
        return None

    async def notify_all(self, text: str, bot: Bot):
        for uid in self.game_data.data["players"]:
            try:
                await bot.send_message(int(uid), text)
            except:
                pass

    async def on_bot_added_to_group(self, event: types.ChatMemberUpdated):
        chat = event.chat
        if chat.type in ["group", "supergroup"]:
            try:
                self.game_data.get_player(event.from_user.id)
                self.game_data.save()
            except:
                pass

    async def on_group_message(self, message: types.Message):
        p = self.game_data.get_player(message.from_user.id)
        p["tg_name"] = message.from_user.full_name
        self.game_data.save()

    async def cmd_text_mine(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        player["tg_name"] = message.from_user.full_name
        self.game.restore_energy(player)
        self.game.restore_mine(player)
        can_mine, msg = self.game.can_mine(player)
        if not can_mine:
            await message.answer(msg)
            return
        mined = self.game.mine(player)
        if mined:
            resources_text = "\n".join([
                f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт."
                for name, amount in mined.items()
            ])
            pickaxe = PICKAXES[player["pickaxe_level"]]
            text = (
                f"⛏️ *Добыча завершена!*\n\n"
                f"Добыто:\n{resources_text}\n\n"
                f"⚡ Энергия: {player['energy']}/{player['max_energy']}\n"
                f"⛏️ Прочность кирки: {player['pickaxe_durability']}/{pickaxe.durability}\n"
                f"💎 Ресурсов в шахте: {player['mine_resources']}/{player['mine_max']}"
            )
            self.game_data.add_log(message.from_user.id, message.from_user.full_name, f"Добыл: {', '.join([f'{RESOURCES[n].name} x{a}' for n,a in mined.items()])}")
        else:
            text = "🤷 Ничего не добыто. Попробуй еще раз!"
        self.game_data.save()
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_text_stats(self, message: types.Message):
        await self.show_stats(message, message.from_user.id)

    async def cmd_text_inventory(self, message: types.Message):
        await self.show_inventory(message, message.from_user.id)

    async def cmd_text_shop(self, message: types.Message):
        await self.show_shop(message, message.from_user.id)

    async def cmd_text_realty(self, message: types.Message):
        await self.show_realty(message, message.from_user.id)

    async def cmd_text_pickaxe(self, message: types.Message):
        await self.show_pickaxe(message, message.from_user.id)

    async def cmd_text_leaderboard(self, message: types.Message):
        await self.show_leaderboard(message)

    async def show_stats(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        pickaxe = PICKAXES[player["pickaxe_level"]]
        house = HOUSES[player["house_level"]]
        dev_tag = " 🛠 Разработчик" if user_id == self.admin_id else ""
        ban_status = " 🚫 АККАУНТ ЗАБЛОКИРОВАН" if player.get("banned", False) else ""
        text = (
            f"📊 *Профиль #{player['player_id']}*\n"
            f"👤 Имя: {message.from_user.full_name}\n"
            f"{dev_tag}{ban_status}\n\n"
            f"💰 Баланс: {player['balance']:.1f}\n"
            f"⚡ Энергия: {player['energy']}/{player['max_energy']}\n"
            f"🔨 Кирка: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n"
            f"⛏️ Прочность кирки: {player['pickaxe_durability']}/{pickaxe.durability}\n"
            f"🏠 Дом: {house.emoji} {house.name} (ур.{house.level})\n"
            f"🛡️ Прочность дома: {player['house_defense']:.0f}/{house.max_defense}\n"
            f"⛏️ Шахта: {player['mine_resources']}/{player['mine_max']} (ур.{player['mine_level']})\n"
            f"💎 Всего добыто: {player['total_mined']}\n"
            f"🎒 Ресурсов в инвентаре: {len(player['inventory'])} видов\n"
        )
        if player["bonuses"]["coin_multiplier"] > 1:
            text += f"\n🎉 Активен бонус x{player['bonuses']['coin_multiplier']}!"
        elif player["bonuses"]["coin_multiplier"] < 1:
            text += f"\n🏷️ Скидка 50% в магазине!"
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def show_inventory(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        if not player["inventory"]:
            text = "🎒 *Инвентарь пуст*\n\nНачни копать, чтобы добыть ресурсы!"
        else:
            items_text = "\n".join([
                f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт. (~{RESOURCES[name].sell_price * amount:.0f}💰)"
                for name, amount in sorted(player["inventory"].items(), key=lambda x: RESOURCES[x[0]].sell_price, reverse=True)
            ])
            total_value = sum(RESOURCES[name].sell_price * amount for name, amount in player["inventory"].items())
            text = f"🎒 *Инвентарь*\n\n{items_text}\n\n💰 Общая стоимость: {total_value:.0f}"
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="back_main")
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def show_shop(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        shop_text = "🏪 *Магазин ресурсов*\n\nВыберите ресурс для покупки или продажи:\n\n"
        shop_text += "\n".join([
            f"{r.emoji} {r.name} ({r.rarity.rarity_name})\n  📈 Курс: продажа {r.sell_price:.1f}💰 | покупка {r.buy_price:.1f}💰"
            for r in RESOURCES.values()
        ])
        shop_text += f"\n\n💰 Твой баланс: {player['balance']:.1f}"
        await message.answer(shop_text, reply_markup=get_shop_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def show_realty(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        house = HOUSES[player["house_level"]]
        text = (
            f"🏠 *Недвижимость*\n\n"
            f"Текущий дом: {house.emoji} {house.name}\n"
            f"🛡️ Прочность: {player['house_defense']:.0f}/{house.max_defense}\n"
            f"⚡ Бонус энергии: +{house.daily_bonus}\n\n*Доступные дома:*\n\n"
        )
        for level, h in HOUSES.items():
            if level > player["house_level"]:
                text += f"{h.emoji} *{h.name}* (ур.{level})\n🛡️ Прочность: {h.max_defense}\n⚡ Бонус энергии: +{h.daily_bonus}\n💰 Цена: {h.price:.0f}\n\n"
        await message.answer(text, reply_markup=get_house_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def show_pickaxe(self, message: types.Message, user_id: int):
        player = self.game_data.get_player(user_id)
        pickaxe = PICKAXES[player["pickaxe_level"]]
        text = (
            f"🔨 *Кирка*\n\n"
            f"Текущая: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n"
            f"⛏️ Эффективность: {pickaxe.efficiency} ед. за удар\n"
            f"💪 Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n\n*Доступные кирки:*\n\n"
        )
        for level, p in PICKAXES.items():
            if level > player["pickaxe_level"]:
                text += f"{p.emoji} *{p.name}* (ур.{level})\n⛏️ Эффективность: {p.efficiency}\n💪 Прочность: {p.durability}\n💰 Цена: {p.price:.0f}\n\n"
        await message.answer(text, reply_markup=get_pickaxe_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, message: types.Message):
        top_players = self.game.get_leaderboard()
        if not top_players:
            text = "🏆 *Таблица лидеров*\n\nПока никто не добыл ресурсы!"
        else:
            text = "🏆 *Таблица лидеров (Топ-10)*\n\n"
            for i, (name, pid, mined) in enumerate(top_players, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} #{pid} {name}: {mined} ед.\n"
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_start(self, message: types.Message):
        player = self.game_data.get_player(message.from_user.id)
        player["tg_name"] = message.from_user.full_name
        dev_tag = " 🛠 Разработчик" if message.from_user.id == self.admin_id else ""
        ban_status = " 🚫 ЗАБЛОКИРОВАНЫЙ АККАУНТ" if player.get("banned", False) else ""
        await message.answer(
            f"*Дарова я ВацапочкИИ. Бот для чатов. Что бы не было скучно, снизу небольшой туториал по боту. Обязательно прочитай!*\n\n"
            f"🆔 Ваш игровой ID: {player['player_id']}\n"
            f"{dev_tag}{ban_status}\n\n"
            f"Это игра про шахту. Внутри бота добывай ресурсы, что бы продавать их и покупать недвижимость. "
            f"И еще быть в топе игроков.\n\n"
            f"Следи за курсом руды. Она может как упасть, так и вырасти. "
            f"Ты можешь закупиться рудой и, когда она вырастит в цене, продать дороже и разбогатеть.\n\n"
            f"Улучшай свою кирку, что бы копать быстрее и получать ценные ресурсы, "
            f"которые можно продать в магазине или хранить в инвентаре.\n\n"
            f"Вот и все. Снизу можешь выбрать действия. Удачи!\n\n"
            f"*Выбери действие:*\n"
            f"/id — узнать свой ID\n/pay ID СУММА — перевести деньги\n"
            f"💬 *Текстовые команды:* Копать, Статистика, Инвентарь, Магазин, Недвижимость, Кирка, Топ",
            reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_id(self, message: types.Message):
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            p = self.game_data.get_player(target_id)
            await message.answer(f"🆔 ID пользователя {message.reply_to_message.from_user.full_name}: {p['player_id']}")
        else:
            p = self.game_data.get_player(message.from_user.id)
            await message.answer(f"🆔 Твой ID: {p['player_id']}")

    async def cmd_pay(self, message: types.Message, command: CommandObject):
        args = command.args.split() if command.args else []
        if len(args) < 2:
            await message.answer("❌ /pay ID СУММА")
            return
        target_id = int(args[0])
        amount = float(args[1])
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной!")
            return
        result = self._get_player_by_id(target_id)
        if not result:
            await message.answer("❌ Игрок не найден!")
            return
        to_uid, to_player = result
        from_player = self.game_data.get_player(message.from_user.id)
        if from_player["balance"] < amount:
            await message.answer("❌ Недостаточно денег!")
            return
        from_player["balance"] -= amount
        to_player["balance"] += amount
        self.game_data.add_log(message.from_user.id, message.from_user.full_name, f"Перевел {amount}💰 игроку #{target_id}")
        self.game_data.save()
        await message.answer(f"✅ Переведено {amount:.1f} 💰 игроку #{target_id}")
        try:
            await message.bot.send_message(int(to_uid), f"💰 Игрок #{from_player['player_id']} перевел вам {amount:.1f} 💰")
        except:
            pass

    async def cmd_admin(self, message: types.Message):
        if not self._is_admin_or_dev(message.from_user.id):
            return
        await message.answer(
            "👑 *Админ-панель*\n\n"
            "Доступные команды:\n"
            "/event x2 - Запустить ивент x2 добыча\n"
            "/event x3 - Запустить ивент x3 добыча\n"
            "/event luckytime - Ящик с сюрпризом (шанс на редкий предмет)\n"
            "/event energize - Полное восстановление энергии всем\n"
            "/event halfprice - Скидка 50% на всё в магазине\n"
            "/event reset - Сбросить ивенты\n"
            "/event restore_mines - Восстановить все шахты\n"
            "/event give_money {id} {amount} - Выдать деньги\n"
            "/announce ТЕКСТ - Оповещение всем\n"
            "/logs [число] - Логи\n"
            "/logall - Все логи\n"
            "/ban {player_id} - Заблокировать игрока\n"
            "/unban {player_id} - Разблокировать игрока\n"
            "/setpickaxe {player_id} {level} - Установить уровень кирки\n"
            "/sethouse {player_id} {level} - Установить уровень дома\n"
            "/resetplayer {player_id} - Сбросить игрока",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_announce(self, message: types.Message, command: CommandObject):
        if not self._is_admin_or_dev(message.from_user.id):
            return
        text = command.args
        if not text:
            await message.answer("❌ /announce ТЕКСТ")
            return
        await self.notify_all(f"📢 Объявление от разработчика:\n{text}", message.bot)
        await message.answer("✅ Оповещение отправлено всем!")

    async def cmd_logs(self, message: types.Message, command: CommandObject):
        if not self._is_admin_or_dev(message.from_user.id):
            return
        args = command.args.split() if command.args else []
        count = int(args[0]) if args else 10
        logs = self.game_data.data.get("logs", [])[-count:]
        if not logs:
            await message.answer("📋 Логи пусты")
            return
        text = "📋 *Последние действия:*\n\n"
        for log in logs:
            text += f"👤 {log['username']} (ID:{log['user_id']}): {log['action']}\n"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_logall(self, message: types.Message):
        if not self._is_admin_or_dev(message.from_user.id):
            return
        logs = self.game_data.data.get("logs", [])
        if not logs:
            await message.answer("📋 Логи пусты")
            return
        text = f"📋 *Всего записей: {len(logs)}*\n\n"
        for log in logs[-30:]:
            text += f"👤 {log['username']} (ID:{log['user_id']}): {log['action']}\n"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_event(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if not args:
        await message.answer("❌ Укажи тип ивента!\nДоступные: x2, x3, luckytime, energize, halfprice, reset, restore_mines, give_money")
        return
    event_type = args[0]
    msg = ""

    if event_type == "x2":
        for player in self.game_data.data["players"].values():
            player["bonuses"]["coin_multiplier"] = 2.0
            player["bonuses"]["xp_multiplier"] = 2.0
        self.game_data.data["events"].append({
            "type": "x2",
            "started": datetime.now().isoformat(),
            "duration": 3600
        })
        self.game_data.save()
        msg = "🎉 Ивент: x2 добыча! Действует 1 час!"

    elif event_type == "x3":
        for player in self.game_data.data["players"].values():
            player["bonuses"]["coin_multiplier"] = 3.0
            player["bonuses"]["xp_multiplier"] = 3.0
        self.game_data.data["events"].append({
            "type": "x3",
            "started": datetime.now().isoformat(),
            "duration": 1800
        })
        self.game_data.save()
        msg = "🎉 Ивент: x3 добыча! Действует 30 минут!"

    elif event_type == "luckytime":
        lucky_players = []
        for uid, player in self.game_data.data["players"].items():
            if not player.get("banned", False) and random.random() < 0.3:
                rare_resources = ["diamond", "emerald", "mythril", "platinum"]
                chosen = random.choice(rare_resources)
                player["inventory"][chosen] = player["inventory"].get(chosen, 0) + random.randint(1, 5)
                lucky_players.append(player.get("tg_name", player["name"]))
        self.game_data.save()
        if lucky_players:
            msg = f"🎉 Ящик с сюрпризом открыт!\nСчастливчики: {', '.join(lucky_players[:5])}"
        else:
            msg = "🎉 Ящик с сюрпризом открыт! Но никто не получил редкий ресурс."

    elif event_type == "energize":
        for player in self.game_data.data["players"].values():
            player["energy"] = player["max_energy"]
        self.game_data.save()
        msg = "⚡ Энергия полностью восстановлена всем игрокам!"

    elif event_type == "halfprice":
        for player in self.game_data.data["players"].values():
            player["bonuses"]["coin_multiplier"] = 0.5
        self.game_data.data["events"].append({
            "type": "halfprice",
            "started": datetime.now().isoformat(),
            "duration": 3600
        })
        self.game_data.save()
        msg = "🏷️ Скидка 50% на всё в магазине! Действует 1 час!"

    elif event_type == "reset":
        for player in self.game_data.data["players"].values():
            player["bonuses"]["coin_multiplier"] = 1.0
            player["bonuses"]["xp_multiplier"] = 1.0
        self.game_data.data["events"] = []
        self.game_data.save()
        msg = "✅ Все ивенты сброшены!"

    elif event_type == "restore_mines":
        for player in self.game_data.data["players"].values():
            player["mine_resources"] = player["mine_max"]
        self.game_data.save()
        msg = "✅ Все шахты восстановлены!"

    elif event_type == "give_money" and len(args) >= 3:
        target_id = int(args[1])
        amount = float(args[2])
        result = self._get_player_by_id(target_id)
        if not result:
            await message.answer("❌ Игрок не найден!")
            return
        uid, player = result
        player["balance"] += amount
        self.game_data.save()
        msg = f"✅ Выдано {amount:.0f} 💰 игроку #{target_id}"

    if msg:
        await message.answer(msg)
        await self.notify_all(f"📢 {msg}", message.bot)
        self.game_data.add_log(message.from_user.id, "Админ", f"Ивент: {msg}")

async def cmd_ban(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if not args:
        await message.answer("❌ Укажи ID игрока: /ban {player_id}")
        return
    player_id = int(args[0])
    result = self._get_player_by_id(player_id)
    if not result:
        await message.answer("❌ Игрок не найден!")
        return
    uid, player = result
    if uid == str(self.admin_id):
        await message.answer("❌ Нельзя заблокировать разработчика!")
        return
    player["banned"] = True
    self.game_data.add_log(message.from_user.id, "Админ", f"Заблокировал игрока #{player_id}")
    self.game_data.save()
    await message.answer(f"🚫 Игрок #{player_id} ({player.get('tg_name', player['name'])}) заблокирован!")

async def cmd_unban(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if not args:
        await message.answer("❌ Укажи ID игрока: /unban {player_id}")
        return
    player_id = int(args[0])
    result = self._get_player_by_id(player_id)
    if not result:
        await message.answer("❌ Игрок не найден!")
        return
    uid, player = result
    player["banned"] = False
    self.game_data.add_log(message.from_user.id, "Админ", f"Разблокировал игрока #{player_id}")
    self.game_data.save()
    await message.answer(f"✅ Игрок #{player_id} ({player.get('tg_name', player['name'])}) разблокирован!")

async def cmd_setpickaxe(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if len(args) < 2:
        await message.answer("❌ Формат: /setpickaxe {player_id} {level}")
        return
    player_id = int(args[0])
    level = int(args[1])
    if level not in PICKAXES:
        await message.answer("❌ Неверный уровень кирки (1-7)!")
        return
    result = self._get_player_by_id(player_id)
    if not result:
        await message.answer("❌ Игрок не найден!")
        return
    uid, player = result
    player["pickaxe_level"] = level
    player["pickaxe_durability"] = PICKAXES[level].durability
    self.game_data.save()
    await message.answer(f"✅ Игроку #{player_id} установлена кирка уровня {level}!")

async def cmd_sethouse(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if len(args) < 2:
        await message.answer("❌ Формат: /sethouse {player_id} {level}")
        return
    player_id = int(args[0])
    level = int(args[1])
    if level not in HOUSES:
        await message.answer("❌ Неверный уровень дома (0-5)!")
        return
    result = self._get_player_by_id(player_id)
    if not result:
        await message.answer("❌ Игрок не найден!")
        return
    uid, player = result
    player["house_level"] = level
    player["house_defense"] = HOUSES[level].defense
    player["max_energy"] = 100 + HOUSES[level].daily_bonus
    self.game_data.save()
    await message.answer(f"✅ Игроку #{player_id} установлен дом уровня {level}!")

async def cmd_resetplayer(self, message: types.Message, command: CommandObject):
    if not self._is_admin_or_dev(message.from_user.id):
        return
    args = command.args.split() if command.args else []
    if not args:
        await message.answer("❌ Укажи ID игрока: /resetplayer {player_id}")
        return
    player_id = int(args[0])
    result = self._get_player_by_id(player_id)
    if not result:
        await message.answer("❌ Игрок не найден!")
        return
    uid, player = result
    if uid == str(self.admin_id):
        await message.answer("❌ Нельзя сбросить разработчика!")
        return
    player.update({
        "balance": 100.0,
        "pickaxe_level": 1,
        "house_level": 0,
        "mine_resources": 100,
        "mine_max": 100,
        "mine_level": 1,
        "inventory": {},
        "total_mined": 0,
        "damage_dealt": 0,
        "energy": 100,
        "max_energy": 100,
        "pickaxe_durability": PICKAXES[1].durability,
        "house_defense": 0,
        "bonuses": {"xp_multiplier": 1.0, "coin_multiplier": 1.0},
        "achievements": []
    })
    self.game_data.add_log(message.from_user.id, "Админ", f"Сбросил игрока #{player_id}")
    self.game_data.save()
    await message.answer(f"✅ Игрок #{player_id} сброшен до начального состояния!")

async def callback_mine(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    player["tg_name"] = callback.from_user.full_name
    self.game.restore_energy(player)
    self.game.restore_mine(player)
    can_mine, message = self.game.can_mine(player)
    if not can_mine:
        await callback.answer(message, show_alert=True)
        return
    mined = self.game.mine(player)
    if mined:
        resources_text = "\n".join([
            f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт."
            for name, amount in mined.items()
        ])
        pickaxe = PICKAXES[player["pickaxe_level"]]
        text = (
            f"⛏️ *Добыча завершена!*\n\n"
            f"Добыто:\n{resources_text}\n\n"
            f"⚡ Энергия: {player['energy']}/{player['max_energy']}\n"
            f"⛏️ Прочность кирки: {player['pickaxe_durability']}/{pickaxe.durability}\n"
            f"💎 Ресурсов в шахте: {player['mine_resources']}/{player['mine_max']}"
        )
        self.game_data.add_log(callback.from_user.id, callback.from_user.full_name, f"Добыл: {', '.join([f'{RESOURCES[n].name} x{a}' for n,a in mined.items()])}")
    else:
        text = "🤷 Ничего не добыто. Попробуй еще раз!"
    self.game_data.save()
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_stats(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    pickaxe = PICKAXES[player["pickaxe_level"]]
    house = HOUSES[player["house_level"]]
    dev_tag = " 🛠 Разработчик" if callback.from_user.id == self.admin_id else ""
    ban_status = " 🚫 АККАУНТ ЗАБЛОКИРОВАН" if player.get("banned", False) else ""

    text = (
        f"📊 *Профиль #{player['player_id']}*\n"
        f"👤 Имя: {callback.from_user.full_name}\n"
        f"{dev_tag}{ban_status}\n\n"
        f"💰 Баланс: {player['balance']:.1f}\n"
        f"⚡ Энергия: {player['energy']}/{player['max_energy']}\n"
        f"🔨 Кирка: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n"
        f"⛏️ Прочность кирки: {player['pickaxe_durability']}/{pickaxe.durability}\n"
        f"🏠 Дом: {house.emoji} {house.name} (ур.{house.level})\n"
        f"🛡️ Прочность дома: {player['house_defense']:.0f}/{house.max_defense}\n"
        f"⛏️ Шахта: {player['mine_resources']}/{player['mine_max']} "
        f"(ур.{player['mine_level']})\n"
        f"💎 Всего добыто: {player['total_mined']}\n"
        f"🎒 Ресурсов в инвентаре: {len(player['inventory'])} видов\n"
    )
    if player["bonuses"]["coin_multiplier"] > 1:
        text += f"\n🎉 Активен бонус x{player['bonuses']['coin_multiplier']}!"
    elif player["bonuses"]["coin_multiplier"] < 1:
        text += f"\n🏷️ Скидка 50% в магазине!"
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_inventory(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    if not player["inventory"]:
        text = "🎒 *Инвентарь пуст*\n\nНачни копать, чтобы добыть ресурсы!"
    else:
        items_text = "\n".join([
            f"{RESOURCES[name].emoji} {RESOURCES[name].name}: {amount} шт. "
            f"(~{RESOURCES[name].sell_price * amount:.0f}💰)"
            for name, amount in sorted(
                player["inventory"].items(),
                key=lambda x: RESOURCES[x[0]].sell_price,
                reverse=True
            )
        ])
        total_value = sum(
            RESOURCES[name].sell_price * amount
            for name, amount in player["inventory"].items()
        )
        text = (
            f"🎒 *Инвентарь*\n\n"
            f"{items_text}\n\n"
            f"💰 Общая стоимость: {total_value:.0f}"
        )
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_main")
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_shop(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    shop_text = "🏪 *Магазин ресурсов*\n\nВыберите ресурс для покупки или продажи:\n\n"
    shop_text += "\n".join([
        f"{r.emoji} {r.name} ({r.rarity.rarity_name})\n"
        f"  📈 Курс: продажа {r.sell_price:.1f}💰 | покупка {r.buy_price:.1f}💰"
        for r in RESOURCES.values()
    ])
    shop_text += f"\n\n💰 Твой баланс: {player['balance']:.1f}"
    await callback.message.edit_text(
        shop_text,
        reply_markup=get_shop_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_shop_resource(self, callback: types.CallbackQuery):
    res_name = callback.data.split("_")[1]
    resource = RESOURCES[res_name]
    text = (
        f"{resource.emoji} *{resource.name}* ({resource.rarity.rarity_name})\n\n"
        f"📈 Курс продажи: {resource.sell_price:.1f}💰/шт.\n"
        f"📉 Курс покупки: {resource.buy_price:.1f}💰/шт.\n\n"
        f"Выберите действие:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_resource_action_keyboard(res_name),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_buy_resource(self, callback: types.CallbackQuery):
    res_name = callback.data.split("_")[1]
    player = self.game_data.get_player(callback.from_user.id)
    resource = RESOURCES[res_name]
    success, message = self.game.buy_resource(player, res_name, 1)
    self.game_data.add_log(callback.from_user.id, callback.from_user.full_name, f"Купил {resource.name}")
    self.game_data.save()
    await callback.answer(message, show_alert=True)
    await self.callback_shop(callback)

async def callback_realty(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    house = HOUSES[player["house_level"]]
    text = (
        f"🏠 *Недвижимость*\n\n"
        f"Текущий дом: {house.emoji} {house.name}\n"
        f"🛡️ Прочность: {player['house_defense']:.0f}/{house.max_defense}\n"
        f"⚡ Бонус энергии: +{house.daily_bonus}\n\n"
        f"*Доступные дома:*\n\n"
    )
    for level, h in HOUSES.items():
        if level > player["house_level"]:
            text += (
                f"{h.emoji} *{h.name}* (ур.{level})\n"
                f"🛡️ Прочность: {h.max_defense}\n"
                f"⚡ Бонус энергии: +{h.daily_bonus}\n"
                f"💰 Цена: {h.price:.0f}\n\n"
            )
    await callback.message.edit_text(
        text,
        reply_markup=get_house_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_pickaxe_menu(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    pickaxe = PICKAXES[player["pickaxe_level"]]
    text = (
        f"🔨 *Кирка*\n\n"
        f"Текущая: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n"
        f"⛏️ Эффективность: {pickaxe.efficiency} ед. за удар\n"
        f"💪 Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n\n"
        f"*Доступные кирки:*\n\n"
    )
    for level, p in PICKAXES.items():
        if level > player["pickaxe_level"]:
            text += (
                f"{p.emoji} *{p.name}* (ур.{level})\n"
                f"⛏️ Эффективность: {p.efficiency}\n"
                f"💪 Прочность: {p.durability}\n"
                f"💰 Цена: {p.price:.0f}\n\n"
            )
    await callback.message.edit_text(
        text,
        reply_markup=get_pickaxe_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_leaderboard(self, callback: types.CallbackQuery):
    top_players = self.game.get_leaderboard()
    if not top_players:
        text = "🏆 *Таблица лидеров*\n\nПока никто не добыл ресурсы!"
    else:
        text = "🏆 *Таблица лидеров (Топ-10)*\n\n"
        for i, (name, pid, mined) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} #{pid} {name}: {mined} ед.\n"
    await callback.message.answer(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

async def callback_sell(self, callback: types.CallbackQuery):
    resource_name = callback.data.split("_")[1]
    player = self.game_data.get_player(callback.from_user.id)
    amount = player["inventory"].get(resource_name, 0)
    if amount == 0:
        await callback.answer("❌ Нет этого ресурса!", show_alert=True)
        return
    success, message = self.game.sell_resource(player, resource_name, amount)
    self.game_data.add_log(callback.from_user.id, callback.from_user.full_name, f"Продал {RESOURCES[resource_name].name} x{amount}")
    self.game_data.save()
    await callback.answer(message, show_alert=True)
    await self.callback_shop(callback)

async def callback_buy_pickaxe(self, callback: types.CallbackQuery):
    level = int(callback.data.split("_")[2])
    player = self.game_data.get_player(callback.from_user.id)
    if level <= player["pickaxe_level"]:
        await callback.answer("❌ У тебя уже есть эта кирка или лучше!", show_alert=True)
        return
    success, message = self.game.upgrade_pickaxe(player)
    self.game_data.add_log(callback.from_user.id, callback.from_user.full_name, f"Купил кирку ур.{level}")
    self.game_data.save()
    await callback.answer(message, show_alert=True)

async def callback_buy_house(self, callback: types.CallbackQuery):
    level = int(callback.data.split("_")[2])
    player = self.game_data.get_player(callback.from_user.id)
    success, message = self.game.buy_house(player, level)
    self.game_data.add_log(callback.from_user.id, callback.from_user.full_name, f"Купил дом ур.{level}")
    self.game_data.save()
    await callback.answer(message, show_alert=True)

async def callback_repair_house(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    success, message = self.game.repair_house(player)
    self.game_data.save()
    await callback.answer(message, show_alert=True)

async def callback_repair_pickaxe(self, callback: types.CallbackQuery):
    player = self.game_data.get_player(callback.from_user.id)
    success, message = self.game.repair_pickaxe(player)
    self.game_data.save()
    await callback.answer(message, show_alert=True)

async def callback_back_main(self, callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⛏️ *Главное меню*\nВыбери действие:",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    async def run(self):
        session = create_session()
        bot = Bot(token=self.token, session=session)
        print("⛏️ Шахтер-Симулятор запускается...")
        try:
            me = await bot.get_me()
            print(f"✅ Бот @{me.username} успешно запущен!")
            asyncio.create_task(self._degradation_task())
            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            print("💡 Попробуй включить VPN или используй прокси")
        finally:
            await bot.session.close()

    async def _degradation_task(self):
        while True:
            await asyncio.sleep(3600)
            for uid, player in self.game_data.data["players"].items():
                if player["house_level"] > 0:
                    result = self.game.degrade_house(player)
            self.game_data.save()


async def main():
    bot = MinerBot(API_TOKEN, ADMIN_ID)
    await bot.run()


if __name__ == "__main__":
    print("""
    ⛏️  ШАХТЕР-СИМУЛЯТОР v2.0
    ========================
    🎮 Управление:
    - Кнопка "Копать" - добыча ресурсов
    - "Статистика" - просмотр прогресса
    - "Инвентарь" - просмотр и продажа ресурсов
    - "Магазин" - продажа ресурсов
    - "Недвижимость" - покупка домов
    - "Кирка" - улучшение инструмента
    - "Таблица лидеров" - топ-10 игроков

    💬 Текстовые команды:
    Копать, Статистика, Инвентарь, Магазин, Недвижимость, Кирка, Топ

    👑 Админ-команды:
    /admin - панель администратора
    /event x2 - ивент x2
    /event reset - сброс ивентов
    /event restore_mines - восстановление шахт
    /event give_money ID СУММА - выдача денег
    /ban ID - блокировка игрока
    /unban ID - разблокировка
    /setpickaxe ID УРОВЕНЬ - установить кирку
    /sethouse ID УРОВЕНЬ - установить дом
    /resetplayer ID - сбросить игрока
    /announce ТЕКСТ - оповещение всем
    /logs [число] - логи
    /logall - все логи

    💡 Новые фичи:
    - Курс руды (меняется ±30%)
    - ID игроков (от 1)
    - Таблица лидеров
    - Блокировка/разблокировка
    - Приписка "Разработчик"
    - Текстовые команды
    - Авто-регистрация в группах
    - Просмотр своего и чужого ID
    - Перевод денег (/pay)
    - Логи для админа
    - Оповещение всем (/announce)
    - Уведомления об ивентах
    - Инвентарь сохраняется
    - Энергия исправлена
    - Ники из Telegram
    """)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Шахтер-симулятор завершает работу...")