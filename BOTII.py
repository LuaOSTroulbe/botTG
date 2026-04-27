import asyncio
import json
import os
import random
import ssl
import socket
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
    """Обычная сессия для Render"""
    timeout = ClientTimeout(total=120, connect=30, sock_read=90)
    return AiohttpSession(timeout=timeout)

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

    @property
    def sell_price(self) -> float:
        return self.base_price * self.rarity.price_multiplier


# Ресыы
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
        self.efficiency = efficiency  # Сколько руды добывает за раз
        self.durability = durability  # Прочность
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


# ыыы эта память сли што
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
        return {"players": {}, "events": [], "global_stats": {"total_mined": 0}}

    def _initialize_defaults(self):
        if "players" not in self.data:
            self.data["players"] = {}
        if "events" not in self.data:
            self.data["events"] = []
        if "global_stats" not in self.data:
            self.data["global_stats"] = {"total_mined": 0}

    def get_player(self, user_id: int) -> Dict:
        """Получить или создать игрока"""
        uid = str(user_id)
        if uid not in self.data["players"]:
            self.data["players"][uid] = self._new_player()
        return self.data["players"][uid]

    def _new_player(self) -> Dict:
        return {
            "name": "Шахтер",
            "balance": 100.0,
            "pickaxe_level": 1,
            "house_level": 0,
            "mine_resources": 100,  # Оставшиеся ресурсы в шахте
            "mine_max": 100,  # Максимальный объем шахты
            "mine_level": 1,  # Уровень шахты
            "inventory": {},  # {resource_name: amount}
            "total_mined": 0,
            "damage_dealt": 0,  # Урон по шахте (влияет на добычу)
            "energy": 100,  # Энергия (восстанавливается со временем)
            "max_energy": 100,
            "last_mine": None,  # Время последней добычи
            "last_energy_restore": None,
            "pickaxe_durability": PICKAXES[1].durability,
            "house_defense": 0,
            "bonuses": {"xp_multiplier": 1.0, "coin_multiplier": 1.0},
            "achievements": [],
            "created_at": datetime.now().isoformat()
        }

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


# --- ИГРОВАЯ ЛОГИКА ---
class MinerGame:
    def __init__(self, game_data: GameData):
        self.data = game_data

    def can_mine(self, player: Dict) -> Tuple[bool, str]:
        """Проверка возможности добычи"""
        if player["energy"] <= 0:
            return False, "❌ Нет энергии! Подожди восстановления."

        if player["mine_resources"] <= 0:
            return False, "⛔ Шахта истощена! Жди обновления."

        pickaxe = PICKAXES[player["pickaxe_level"]]
        if player["pickaxe_durability"] <= 0:
            return False, "🔨 Кирка сломана! Купи новую или почини."

        return True, ""

    def mine(self, player: Dict) -> Dict:
        """Процесс добычи"""
        pickaxe = PICKAXES[player["pickaxe_level"]]

        # Расчет базовой добычи
        base_amount = pickaxe.efficiency
        mine_level_bonus = 1 + (player["mine_level"] - 1) * 0.1

        # Бонусы из ивентов
        amount = int(base_amount * mine_level_bonus * player["bonuses"]["xp_multiplier"])

        # Генерация ресурсов
        mined_resources = {}
        for _ in range(amount):
            resource = self._random_resource()
            if resource:
                mined_resources[resource.name] = mined_resources.get(resource.name, 0) + 1

        # Обновление статистики
        player["mine_resources"] -= amount
        player["energy"] -= 20
        player["pickaxe_durability"] -= random.randint(1, 3)
        player["total_mined"] += amount
        player["damage_dealt"] += amount
        player["last_mine"] = datetime.now().isoformat()

        # Если шахта истощена - запускаем таймер восстановления
        if player["mine_resources"] <= 0:
            player["mine_resources"] = 0

        # Добавление в инвентарь
        for res_name, res_amount in mined_resources.items():
            player["inventory"][res_name] = player["inventory"].get(res_name, 0) + res_amount

        # Шанс на улучшение шахты
        if random.random() < 0.01:  # 1% шанс
            player["mine_level"] += 1
            player["mine_max"] = int(player["mine_max"] * 1.2)

        return mined_resources

    def _random_resource(self) -> Optional[Resource]:
        """Случайный ресурс на основе редкости"""
        roll = random.random() * 100

        for resource in RESOURCES.values():
            if roll <= resource.rarity.chance:
                return resource
            roll -= resource.rarity.chance

        return None  # Ничего не выпало

    def restore_mine(self, player: Dict):
        """Восстановление шахты"""
        if player["mine_resources"] <= 0:
            restore_time = 3600  # 1 час в секундах
            if player.get("last_mine"):
                last = datetime.fromisoformat(player["last_mine"])
                if (datetime.now() - last).seconds >= restore_time:
                    player["mine_resources"] = player["mine_max"]
                    player["damage_dealt"] = 0

    def restore_energy(self, player: Dict):
        """Восстановление энергии"""
        if player["energy"] < player["max_energy"]:
            if not player.get("last_energy_restore"):
                player["last_energy_restore"] = datetime.now().isoformat()
                player["energy"] = min(player["max_energy"], player["energy"] + 5)
            else:
                last = datetime.fromisoformat(player["last_energy_restore"])
                if (datetime.now() - last).seconds >= 300:  # Каждые 5 минут
                    player["energy"] = min(player["max_energy"], player["energy"] + 5)
                    player["last_energy_restore"] = datetime.now().isoformat()

    def sell_resource(self, player: Dict, resource_name: str, amount: int) -> Tuple[bool, str]:
        """Продажа ресурса"""
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

    def upgrade_pickaxe(self, player: Dict) -> Tuple[bool, str]:
        """Улучшение кирки"""
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
        """Починка кирки"""
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
        """Покупка дома"""
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
        """Ремонт дома"""
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
        """Износ дома"""
        if player["house_level"] > 0:
            house = HOUSES[player["house_level"]]
            player["house_defense"] -= house.decay_rate

            if player["house_defense"] <= 0:
                player["house_level"] = 0
                player["house_defense"] = 0
                player["max_energy"] = 100
                return "🏚️ Твой дом разрушился! Нужно строить новый."
        return None


# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    """Главная клавиатура"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⛏️ Копать", callback_data="mine")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="🎒 Инвентарь", callback_data="inventory")
    builder.button(text="🏪 Магазин", callback_data="shop")
    builder.button(text="🏠 Недвижимость", callback_data="realty")
    builder.button(text="🔨 Кирка", callback_data="pickaxe_menu")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_shop_keyboard():
    """Клавиатура магазина"""
    builder = InlineKeyboardBuilder()
    for res_name, resource in RESOURCES.items():
        builder.button(
            text=f"{resource.emoji} {resource.name} ({resource.rarity.rarity_name})",
            callback_data=f"sell_{res_name}"
        )
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def get_house_keyboard():
    """Клавиатура недвижимости"""
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
    """Клавиатура кирки"""
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


# --- БОТ ---
class MinerBot:
    def __init__(self, token: str, admin_id: int):
        self.token = token
        self.admin_id = admin_id
        self.game_data = GameData(DATA_FILE)
        self.game = MinerGame(self.game_data)
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков"""
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("admin"))(self.cmd_admin)
        self.dp.message(Command("event"))(self.cmd_event)
        self.dp.callback_query(F.data == "mine")(self.callback_mine)
        self.dp.callback_query(F.data == "stats")(self.callback_stats)
        self.dp.callback_query(F.data == "inventory")(self.callback_inventory)
        self.dp.callback_query(F.data == "shop")(self.callback_shop)
        self.dp.callback_query(F.data == "realty")(self.callback_realty)
        self.dp.callback_query(F.data == "pickaxe_menu")(self.callback_pickaxe_menu)
        self.dp.callback_query(F.data == "back_main")(self.callback_back_main)
        self.dp.callback_query(F.data == "repair_house")(self.callback_repair_house)
        self.dp.callback_query(F.data == "repair_pickaxe")(self.callback_repair_pickaxe)
        self.dp.callback_query(F.data.startswith("sell_"))(self.callback_sell)
        self.dp.callback_query(F.data.startswith("buy_pickaxe_"))(self.callback_buy_pickaxe)
        self.dp.callback_query(F.data.startswith("buy_house_"))(self.callback_buy_house)

    async def cmd_start(self, message: types.Message):
        """Начало игры"""
        player = self.game_data.get_player(message.from_user.id)
        player["name"] = message.from_user.full_name

        await message.answer(
            f"⛏️ *Добро пожаловать в Шахтер-Симулятор!*\n\n"
            f"🎮 Ты - шахтер, который добывает ресурсы, "
            f"продает их и строит свою империю!\n\n"
            f"🏪 Продавай ресурсы в магазине\n"
            f"🔨 Улучшай кирку для большей добычи\n"
            f"🏠 Покупай недвижимость для бонусов\n\n"
            f"*Выбери действие:*",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_admin(self, message: types.Message):
        """Админ-панель"""
        if message.from_user.id != self.admin_id:
            return

        await message.answer(
            "👑 *Админ-панель*\n\n"
            "Доступные команды:\n"
            "/event x2 - Запустить ивент x2 добыча\n"
            "/event reset - Сбросить ивенты\n"
            "/event restore_mines - Восстановить все шахты\n"
            "/event give_money {id} {amount} - Выдать деньги",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_event(self, message: types.Message, command: CommandObject):
        """Управление ивентами"""
        if message.from_user.id != self.admin_id:
            return

        args = command.args.split() if command.args else []

        if not args:
            await message.answer("❌ Укажи тип ивента!")
            return

        event_type = args[0]

        if event_type == "x2":
            # Запуск ивента x2
            for player in self.game_data.data["players"].values():
                player["bonuses"]["coin_multiplier"] = 2.0
                player["bonuses"]["xp_multiplier"] = 2.0

            self.game_data.data["events"].append({
                "type": "x2",
                "started": datetime.now().isoformat(),
                "duration": 3600  # 1 час
            })
            self.game_data.save()

            await message.answer("✅ Ивент x2 запущен на 1 час!")

        elif event_type == "reset":
            # Сброс всех ивентов
            for player in self.game_data.data["players"].values():
                player["bonuses"]["coin_multiplier"] = 1.0
                player["bonuses"]["xp_multiplier"] = 1.0

            self.game_data.data["events"] = []
            self.game_data.save()

            await message.answer("✅ Все ивенты сброшены!")

        elif event_type == "restore_mines":
            # Восстановление всех шахт
            for player in self.game_data.data["players"].values():
                player["mine_resources"] = player["mine_max"]
            self.game_data.save()

            await message.answer("✅ Все шахты восстановлены!")

        elif event_type == "give_money" and len(args) >= 3:
            target_id = int(args[1])
            amount = float(args[2])

            player = self.game_data.get_player(target_id)
            player["balance"] += amount
            self.game_data.save()

            await message.answer(f"✅ Выдано {amount:.0f} 💰 игроку {target_id}")

    async def callback_mine(self, callback: types.CallbackQuery):
        """Добыча ресурсов"""
        player = self.game_data.get_player(callback.from_user.id)

        # Восстановление
        self.game.restore_energy(player)
        self.game.restore_mine(player)

        # Проверка возможности добычи
        can_mine, message = self.game.can_mine(player)
        if not can_mine:
            await callback.answer(message, show_alert=True)
            return

        # Добыча
        mined = self.game.mine(player)

        # Формирование сообщения
        if mined:
            resources_text = "\n".join([
                f"{RESOURCES[name].emoji} {name}: {amount} шт."
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
        else:
            text = "🤷 Ничего не добыто. Попробуй еще раз!"

        self.game_data.save()

        await callback.message.edit_text(
            text,
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_stats(self, callback: types.CallbackQuery):
        """Статистика игрока"""
        player = self.game_data.get_player(callback.from_user.id)
        pickaxe = PICKAXES[player["pickaxe_level"]]
        house = HOUSES[player["house_level"]]

        text = (
            f"📊 *Статистика {callback.from_user.full_name}*\n\n"
            f"💰 Баланс: {player['balance']:.1f}\n"
            f"⚡ Энергия: {player['energy']}/{player['max_energy']}\n"
            f"🔨 Кирка: {pickaxe.emoji} {pickaxe.name} (ур.{pickaxe.level})\n"
            f"⛏️ Прочность: {player['pickaxe_durability']}/{pickaxe.durability}\n"
            f"🏠 Дом: {house.emoji} {house.name} (ур.{house.level})\n"
            f"🛡️ Защита дома: {player['house_defense']:.0f}/{house.max_defense}\n"
            f"⛏️ Шахта: {player['mine_resources']}/{player['mine_max']} "
            f"(ур.{player['mine_level']})\n"
            f"💎 Всего добыто: {player['total_mined']}\n"
            f"🎒 Ресурсов в инвентаре: {len(player['inventory'])} видов\n"
        )

        if player["bonuses"]["coin_multiplier"] > 1:
            text += f"\n🎉 Активен бонус x{player['bonuses']['coin_multiplier']}!"

        await callback.message.edit_text(
            text,
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_inventory(self, callback: types.CallbackQuery):
        """Инвентарь игрока"""
        player = self.game_data.get_player(callback.from_user.id)

        if not player["inventory"]:
            text = "🎒 *Инвентарь пуст*\n\nНачни копать, чтобы добыть ресурсы!"
        else:
            items_text = "\n".join([
                f"{RESOURCES[name].emoji} {name}: {amount} шт. "
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

        await callback.message.edit_text(
            text,
            reply_markup=get_shop_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_shop(self, callback: types.CallbackQuery):
        """Магазин"""
        player = self.game_data.get_player(callback.from_user.id)

        shop_text = "🏪 *Магазин ресурсов*\n\nВыбери ресурс для продажи:\n\n"
        shop_text += "\n".join([
            f"{r.emoji} {r.name} ({r.rarity.rarity_name}): "
            f"{r.sell_price:.1f}💰/шт."
            for r in RESOURCES.values()
        ])

        shop_text += f"\n\n💰 Твой баланс: {player['balance']:.1f}"

        await callback.message.edit_text(
            shop_text,
            reply_markup=get_shop_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_realty(self, callback: types.CallbackQuery):
        """Недвижимость"""
        player = self.game_data.get_player(callback.from_user.id)
        house = HOUSES[player["house_level"]]

        text = (
            f"🏠 *Недвижимость*\n\n"
            f"Текущий дом: {house.emoji} {house.name}\n"
            f"🛡️ Защита: {player['house_defense']:.0f}/{house.max_defense}\n"
            f"⚡ Бонус энергии: +{house.daily_bonus}\n\n"
            f"*Доступные дома:*\n\n"
        )

        for level, h in HOUSES.items():
            if level > player["house_level"]:
                text += (
                    f"{h.emoji} *{h.name}* (ур.{level})\n"
                    f"🛡️ Защита: {h.max_defense}\n"
                    f"⚡ Бонус энергии: +{h.daily_bonus}\n"
                    f"💰 Цена: {h.price:.0f}\n\n"
                )

        await callback.message.edit_text(
            text,
            reply_markup=get_house_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_pickaxe_menu(self, callback: types.CallbackQuery):
        """Меню кирки"""
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

    async def callback_sell(self, callback: types.CallbackQuery):
        """Продажа ресурса"""
        resource_name = callback.data.split("_")[1]
        player = self.game_data.get_player(callback.from_user.id)

        # Продаем все количество ресурса
        amount = player["inventory"].get(resource_name, 0)
        if amount == 0:
            await callback.answer("❌ Нет этого ресурса!", show_alert=True)
            return

        success, message = self.game.sell_resource(player, resource_name, amount)
        self.game_data.save()

        await callback.answer(message, show_alert=True)

    async def callback_buy_pickaxe(self, callback: types.CallbackQuery):
        """Покупка кирки"""
        level = int(callback.data.split("_")[2])

        # Если покупаем текущий уровень или ниже, отклоняем
        player = self.game_data.get_player(callback.from_user.id)
        if level <= player["pickaxe_level"]:
            await callback.answer("❌ У тебя уже есть эта кирка или лучше!", show_alert=True)
            return

        success, message = self.game.upgrade_pickaxe(player)
        self.game_data.save()

        await callback.answer(message, show_alert=True)

    async def callback_buy_house(self, callback: types.CallbackQuery):
        """Покупка дома"""
        level = int(callback.data.split("_")[2])
        player = self.game_data.get_player(callback.from_user.id)

        success, message = self.game.buy_house(player, level)
        self.game_data.save()

        await callback.answer(message, show_alert=True)

    async def callback_repair_house(self, callback: types.CallbackQuery):
        """Ремонт дома"""
        player = self.game_data.get_player(callback.from_user.id)

        success, message = self.game.repair_house(player)
        self.game_data.save()

        await callback.answer(message, show_alert=True)

    async def callback_repair_pickaxe(self, callback: types.CallbackQuery):
        """Починка кирки"""
        player = self.game_data.get_player(callback.from_user.id)

        success, message = self.game.repair_pickaxe(player)
        self.game_data.save()

        await callback.answer(message, show_alert=True)

    async def callback_back_main(self, callback: types.CallbackQuery):
        """Возврат в главное меню"""
        await callback.message.edit_text(
            "⛏️ *Главное меню*\nВыбери действие:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def run(self):
        """Запуск бота"""
        # Используем защищенную сессию
        session = create_session()
        bot = Bot(token=self.token, session=session)

        print("⛏️ Шахтер-Симулятор запускается...")
        try:
            me = await bot.get_me()
            print(f"✅ Бот @{me.username} успешно запущен!")

            # Запуск фоновой задачи для деградации домов
            asyncio.create_task(self._degradation_task())

            await self.dp.start_polling(bot)
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            print("💡 Попробуй включить VPN или используй прокси")
        finally:
            await bot.session.close()

    async def _degradation_task(self):
        """Фоновая задача для износа домов"""
        while True:
            await asyncio.sleep(3600)  # Каждый час

            for uid, player in self.game_data.data["players"].items():
                if player["house_level"] > 0:
                    result = self.game.degrade_house(player)
                    if result:
                        # Можно отправить уведомление игроку
                        pass

            self.game_data.save()


# --- ЗАПУСК ---
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

    👑 Админ-команды:
    /admin - панель администратора
    /event x2 - запуск ивента x2
    /event reset - сброс ивентов
    /event restore_mines - восстановление шахт
    /event give_money ID СУММА - выдача денег

    💡 Особенности:
    - 10 видов ресурсов разной редкости
    - 7 уровней кирок
    - 5 типов домов с бонусами
    - Система энергии
    - Износ инструментов и домов
    - Случайные улучшения шахт
    - Ивенты для администратора
    """)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Шахтер-симулятор завершает работу...")
