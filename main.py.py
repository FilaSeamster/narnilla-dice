import random
import re
import json
import os
import time
import asyncio
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

# Конфигурация
TOKEN = 'vk1.a.YPaimp1hIjG4kcMNwLx09ZGCvlC-plBQMJrpOHRsYxl-dSTnmDim7-69sdaRAo05zn7y6hM_NCF69ylRHKZ1XJMcAGdFHlqd5xtmskiF4F944I0yqyZZul3uWEI_xUB5gL4A9XHe1hjcFk-YIWbM2cqtZR83IW0QfxHETfLvFDUI4aYcdDJAO4d7UNhyZnevSgCA5VskQCgJBQoDkW18vg'  # Укажи токен VK API здесь
GROUP_ID = 232138023  # ID группы VK
ALLOWED_USER_IDS = [333088694, 720772043]  # ID пользователей, которые могут использовать команды настроек
SAVE_DIR = "/home/sensen337" if os.path.exists("/home/sensen337") else "G:/Хлам"
SETTINGS_FILE = os.path.join(SAVE_DIR, "settings.json")
DELETE_DELAY = 2  # Глобальный таймер удаления сообщений по умолчанию (в секундах)
SETTINGS_DELETE_DELAY = 5  # Таймер удаления сообщений отладки (в секундах)

# Инициализация VK API
try:
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
except Exception as e:
    print(f"Ошибка инициализации VK API: {e}")
    exit(1)

# Загрузка настроек из файла
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке настроек: {e}")
        return {}

# Сохранение настроек в файл
def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")

# Проверка, прошло ли достаточно времени с последнего броска в чате
def check_timeout(chat_id, settings):
    chat_id = str(chat_id)
    if chat_id not in settings or 'timeout' not in settings[chat_id]:
        return True, 0
    timeout = settings[chat_id]['timeout']
    last_roll = settings[chat_id].get('last_roll', 0)
    current_time = time.time()
    elapsed = current_time - last_roll
    if elapsed >= timeout:
        return True, 0
    return False, int(timeout - elapsed)

# Парсинг команды X/rY±Z[ad|dis|фв|вшы]
def parse_dice_command(command_text, chat_id, settings):
    print(f"Parsing command: {command_text}")  # Отладочный вывод
    match = re.match(r'^/(\d*)[rRdDlLдДкКвВ](-?\d+)([+*-]\d+)?([ad|dis|фв|вшы]+)?$', command_text, re.IGNORECASE)
    if not match:
        print(f"Command {command_text} does not match regex")  # Отладочный вывод
        return None
    num_rolls = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier_str = match.group(3) if match.group(3) else None
    adv_dis = match.group(4).lower() if match.group(4) else None
    modifier = 0
    mod_type = None
    if modifier_str:
        mod_type = modifier_str[0]
        modifier = int(modifier_str[1:])
        if mod_type == '-':
            modifier = -modifier
    if abs(sides) < 2 or num_rolls < 1:
        print(f"Invalid sides {sides} or num_rolls {num_rolls}")  # Отладочный вывод
        return None
    chat_id_str = str(chat_id)
    if chat_id_str in settings:
        chat_settings = settings[chat_id_str]
        if 'rolls_limit' in chat_settings and chat_settings['rolls_limit'] > 0 and num_rolls > chat_settings['rolls_limit']:
            print(f"Rolls limit exceeded: {num_rolls} > {chat_settings['rolls_limit']}")  # Отладочный вывод
            return None
        if 'sides_limit' in chat_settings and chat_settings['sides_limit'] > 0 and abs(sides) > chat_settings['sides_limit']:
            print(f"Sides limit exceeded: {abs(sides)} > {chat_settings['sides_limit']}")  # Отладочный вывод
            return None
    print(f"Parsed command: rolls={num_rolls}, sides={sides}, modifier={modifier}, mod_type={mod_type}, is_negative={sides < 0}, adv_dis={adv_dis}")  # Отладочный вывод
    return num_rolls, abs(sides), modifier, mod_type, sides < 0, adv_dis

# Ролл кубиков
def roll_dice(num_rolls, sides, modifier, mod_type, is_negative, username, adv_dis=None):
    rolls = []
    if num_rolls == 1 and adv_dis in ['ad', 'фв', 'dis', 'вшы']:
        rolls = [random.randint(1, sides) for _ in range(2)]
        if adv_dis in ['ad', 'фв']:
            total = max(rolls)
            rolls_str = f'{rolls[0]}, {rolls[1]} (выбрано {total} с преимуществом)'
        else:
            total = min(rolls)
            rolls_str = f'{rolls[0]}, {rolls[1]} (выбрано {total} с помехой)'
    else:
        rolls = [random.randint(1, sides) for _ in range(num_rolls)]
        total = sum(rolls)
        rolls_str = ' + '.join(map(str, rolls))

    if mod_type == '+' or mod_type == '-':
        total += modifier
    elif mod_type == '*':
        total *= modifier

    if is_negative:
        total = -total
        rolls = [-r for r in rolls]
        rolls_str = ' + '.join(map(str, rolls)) if num_rolls > 1 else f'{-rolls[0]}, {-rolls[1]} (выбрано {-total} с {"преимуществом" if adv_dis in ["ad", "фв"] else "помехой"})' if adv_dis else str(-rolls[0])

    if num_rolls > 1 or adv_dis:
        if mod_type == '+':
            rolls_str += f' + {modifier}'
        elif mod_type == '-':
            rolls_str += f' - {abs(modifier)}'
        elif mod_type == '*':
            rolls_str += f' * {modifier}'
        return (f'Броски: {rolls_str} = {total}', total)
    else:
        if mod_type:
            symbol = '+' if mod_type == '+' else mod_type
            return (f'Бросок: {rolls[0]} {symbol} {abs(modifier)} = {total}', total)
        else:
            return (f'Бросок: {rolls[0]}', rolls[0])

# Асинхронная функция для удаления сообщения через задержку
async def delete_message_later(peer_id, conversation_message_id, delay):
    await asyncio.sleep(delay)
    try:
        vk.messages.delete(
            conversation_message_ids=[conversation_message_id],
            peer_id=peer_id,
            delete_for_all=1
        )
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

# Получение имени пользователя
def get_user_name(user_id):
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}".strip()
    except Exception as e:
        print(f"Ошибка при получении имени пользователя {user_id}: {e}")
        return f"User_{user_id}"

# Команда /timeout или /to
async def set_timeout(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return None
    chat_id = str(event.obj.message['peer_id'])
    try:
        value = int(event.obj.message['text'].split()[1])
        if value < 0:
            raise ValueError
        settings = load_settings()
        if chat_id not in settings:
            settings[chat_id] = {'chat_name': f"Chat_{chat_id}"}
        if value > 0:
            settings[chat_id]['timeout'] = value
            settings[chat_id]['last_roll'] = 0
        else:
            settings[chat_id].pop('timeout', None)
            settings[chat_id].pop('last_roll', None)
            if not settings[chat_id]:
                del settings[chat_id]
        save_settings(settings)
        msg = f'Таймаут для этого чата {"установлен: " + str(value) + " секунд" if value > 0 else "сброшен"}'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg
    except (IndexError, ValueError):
        msg = 'Использование: /timeout <секунды> (0 для сброса)'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg

# Команда /rollslimit или /rl
async def set_rolls_limit(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return None
    chat_id = str(event.obj.message['peer_id'])
    try:
        value = int(event.obj.message['text'].split()[1])
        if value < 0:
            raise ValueError
        settings = load_settings()
        if chat_id not in settings:
            settings[chat_id] = {'chat_name': f"Chat_{chat_id}"}
        if value > 0:
            settings[chat_id]['rolls_limit'] = value
        else:
            settings[chat_id].pop('rolls_limit', None)
            if not settings[chat_id]:
                del settings[chat_id]
        save_settings(settings)
        msg = f'Лимит количества бросков для этого чата {"установлен: " + str(value) if value > 0 else "сброшен"}'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg
    except (IndexError, ValueError):
        msg = 'Использование: /rollslimit <количество> (0 для сброса)'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg

# Команда /sideslimit или /sl
async def set_sides_limit(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return None
    chat_id = str(event.obj.message['peer_id'])
    try:
        value = int(event.obj.message['text'].split()[1])
        if value < 0:
            raise ValueError
        settings = load_settings()
        if chat_id not in settings:
            settings[chat_id] = {'chat_name': f"Chat_{chat_id}"}
        if value > 0:
            settings[chat_id]['sides_limit'] = value
        else:
            settings[chat_id].pop('sides_limit', None)
            if not settings[chat_id]:
                del settings[chat_id]
        save_settings(settings)
        msg = f'Лимит граней кубика для этого чата {"установлен: " + str(value) if value > 0 else "сброшен"}'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg
    except (IndexError, ValueError):
        msg = 'Использование: /sideslimit <граней> (0 для сброса)'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg

# Команда /deltimer или /dt
async def set_del_timer(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return None
    chat_id = str(event.obj.message['peer_id'])
    try:
        value = int(event.obj.message['text'].split()[1])
        if value < 0:
            raise ValueError
        settings = load_settings()
        if chat_id not in settings:
            settings[chat_id] = {'chat_name': f"Chat_{chat_id}"}
        if value > 0:
            settings[chat_id]['del_timer'] = value
        else:
            settings[chat_id].pop('del_timer', None)
            if not settings[chat_id]:
                del settings[chat_id]
        save_settings(settings)
        msg = f'Таймер удаления сообщений для этого чата {"установлен: " + str(value) + " секунд" if value > 0 else "сброшен"}'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg
    except (IndexError, ValueError):
        msg = 'Использование: /deltimer <секунды> (0 для сброса)'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg

# Команда /comlimit или /cl
async def set_com_limit(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return None
    chat_id = str(event.obj.message['peer_id'])
    try:
        value = int(event.obj.message['text'].split()[1])
        if value < 0:
            raise ValueError
        settings = load_settings()
        if chat_id not in settings:
            settings[chat_id] = {'chat_name': f"Chat_{chat_id}"}
        if value > 0:
            settings[chat_id]['com_limit'] = value
        else:
            settings[chat_id].pop('com_limit', None)
            if not settings[chat_id]:
                del settings[chat_id]
        save_settings(settings)
        msg = f'Лимит количества команд для этого чата {"установлен: " + str(value) if value > 0 else "сброшен"}'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg
    except (IndexError, ValueError):
        msg = 'Использование: /comlimit <количество> (0 для сброса)'
        if not is_multi:
            response = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=msg,
                random_id=random.randint(1, 1000000)
            )
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response,
                SETTINGS_DELETE_DELAY
            ))
        return msg

# Команды /timeoutlist, /tol, /rollslimitlist, /rll, /sideslimitlist, /sll, /deltimerlist, /dtl, /comlimitlist, /cll
async def timeout_list(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    settings = load_settings()
    response = 'Чаты с таймаутами:\n'
    has_items = False
    for chat_id, data in settings.items():
        if 'timeout' in data:
            response += f'{data["chat_name"]}: {data["timeout"]} секунд\n'
            has_items = True
    if not has_items:
        response = 'Таймауты не установлены ни в одном чате'
    if is_multi:
        return response
    response_id = vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=response,
        random_id=random.randint(1, 1000000)
    )
    asyncio.create_task(delete_message_later(
        event.obj.message['peer_id'],
        response_id,
        SETTINGS_DELETE_DELAY
    ))

async def rolls_limit_list(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    settings = load_settings()
    response = 'Чаты с лимитом количества бросков:\n'
    has_items = False
    for chat_id, data in settings.items():
        if 'rolls_limit' in data:
            response += f'{data["chat_name"]}: {data["rolls_limit"]}\n'
            has_items = True
    if not has_items:
        response = 'Лимиты количества бросков не установлены ни в одном чате'
    if is_multi:
        return response
    response_id = vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=response,
        random_id=random.randint(1, 1000000)
    )
    asyncio.create_task(delete_message_later(
        event.obj.message['peer_id'],
        response_id,
        SETTINGS_DELETE_DELAY
    ))

async def sides_limit_list(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    settings = load_settings()
    response = 'Чаты с лимитом граней кубика:\n'
    has_items = False
    for chat_id, data in settings.items():
        if 'sides_limit' in data:
            response += f'{data["chat_name"]}: {data["sides_limit"]}\n'
            has_items = True
    if not has_items:
        response = 'Лимиты граней кубика не установлены ни в одном чате'
    if is_multi:
        return response
    response_id = vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=response,
        random_id=random.randint(1, 1000000)
    )
    asyncio.create_task(delete_message_later(
        event.obj.message['peer_id'],
        response_id,
        SETTINGS_DELETE_DELAY
    ))

async def del_timer_list(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    settings = load_settings()
    response = 'Чаты с таймером удаления сообщений:\n'
    has_items = False
    for chat_id, data in settings.items():
        if 'del_timer' in data:
            response += f'{data["chat_name"]}: {data["del_timer"]} секунд\n'
            has_items = True
    if not has_items:
        response = 'Таймеры удаления сообщений не установлены ни в одном чате'
    if is_multi:
        return response
    response_id = vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=response,
        random_id=random.randint(1, 1000000)
    )
    asyncio.create_task(delete_message_later(
        event.obj.message['peer_id'],
        response_id,
        SETTINGS_DELETE_DELAY
    ))

async def com_limit_list(event, is_multi=False):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    settings = load_settings()
    response = 'Чаты с лимитом количества команд:\n'
    has_items = False
    for chat_id, data in settings.items():
        if 'com_limit' in data:
            response += f'{data["chat_name"]}: {data["com_limit"]}\n'
            has_items = True
    if not has_items:
        response = 'Лимиты количества команд не установлены ни в одном чате'
    if is_multi:
        return response
    response_id = vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=response,
        random_id=random.randint(1, 1000000)
    )
    asyncio.create_task(delete_message_later(
        event.obj.message['peer_id'],
        response_id,
        SETTINGS_DELETE_DELAY
    ))

# Обработчик нескольких команд настройки
async def handle_settings_command(event):
    if event.obj.message['from_id'] not in ALLOWED_USER_IDS:
        return
    command_text = event.obj.message['text'].strip()
    print(f"Settings command: {command_text}")  # Отладочный вывод
    lines = command_text.split('\n') if '\n' in command_text else [command_text]
    commands = []
    for line in lines:
        line_tokens = line.strip().split()
        i = 0
        while i < len(line_tokens):
            if line_tokens[i].startswith('/'):
                cmd = line_tokens[i].lower()
                arg = line_tokens[i + 1] if i + 1 < len(line_tokens) and not line_tokens[i + 1].startswith('/') else None
                commands.append((cmd, arg))
                if arg is not None:
                    i += 1
            i += 1
    
    if not commands or len(commands) > 5:
        response_id = vk.messages.send(
            peer_id=event.obj.message['peer_id'],
            message='Используйте от 1 до 5 команд настройки: /timeout, /timeoutlist, /rollslimit, /rollslimitlist, /sideslimit, /sideslimitlist, /deltimer, /deltimerlist, /comlimit, /comlimitlist (или их сокращения)',
            random_id=random.randint(1, 1000000)
        )
        asyncio.create_task(delete_message_later(
            event.obj.message['peer_id'],
            response_id,
            SETTINGS_DELETE_DELAY
        ))
        return

    results = []
    for cmd, arg in commands:
        event.obj.message['text'] = f"{cmd} {arg}" if arg else cmd
        if cmd in ['/timeout', '/to']:
            result = await set_timeout(event, is_multi=True)
        elif cmd in ['/rollslimit', '/rl']:
            result = await set_rolls_limit(event, is_multi=True)
        elif cmd in ['/sideslimit', '/sl']:
            result = await set_sides_limit(event, is_multi=True)
        elif cmd in ['/deltimer', '/dt']:
            result = await set_del_timer(event, is_multi=True)
        elif cmd in ['/comlimit', '/cl']:
            result = await set_com_limit(event, is_multi=True)
        elif cmd in ['/timeoutlist', '/tol']:
            result = await timeout_list(event, is_multi=True)
        elif cmd in ['/rollslimitlist', '/rll']:
            result = await rolls_limit_list(event, is_multi=True)
        elif cmd in ['/sideslimitlist', '/sll']:
            result = await sides_limit_list(event, is_multi=True)
        elif cmd in ['/deltimerlist', '/dtl']:
            result = await del_timer_list(event, is_multi=True)
        elif cmd in ['/comlimitlist', '/cll']:
            result = await com_limit_list(event, is_multi=True)
        else:
            result = f'Неизвестная команда: {cmd}'
        if result:
            results.append(result)
    
    if results:
        response_id = vk.messages.send(
            peer_id=event.obj.message['peer_id'],
            message='\n'.join(results),
            random_id=random.randint(1, 1000000)
        )
        asyncio.create_task(delete_message_later(
            event.obj.message['peer_id'],
            response_id,
            SETTINGS_DELETE_DELAY
        ))

# Обработчик команды /Начать, /help, /помощь
async def info(event):
    description = (
        "Рандомайзер (дайсроллер) для чатов, собран из говна и палок руками vk.com/rotten_curse при содействии vk.com/smallbatat (огромное тебе спасибо!)\n\n"
        "Для вызова этой инструкции используйте /help, /помощь или пропишите 'Начать'\n\n"
        "Используйте на выбор команды /d, /в, /к, /r, /д или /l с параметрами для броска кубиков\n\n"
        "Формат параметров: /XdY±Z[ad|dis|фв|вшы] (или /XвY±Z[ad|dis|фв|вшы], /XкY±Z[ad|dis|фв|вшы], и т.д.) в любом регистре\n"
        "- X: Количество бросков (опционально, по умолчанию 1)\n"
        "- Y: Количество граней кубика (минимум 2, можно использовать отрицательное число для инверсии)\n"
        "- ±Z: Модификатор (опционально, +, - или * число)\n"
        "- ad/фв: Преимущество (для одного кубика берётся максимум из двух бросков)\n"
        "- dis/вшы: Помеха (для одного кубика берётся минимум из двух бросков)\n\n"
        "Можно добавлять комментарии с помощью !, например: !комментарий с пробелами /d20ad !ещё комментарий\n\n"
        "Примеры:\n"
        "- /r20 или /d20: Один бросок кубика с 20 гранями\n"
        "- /d20ad: Один бросок d20 с преимуществом (берётся максимум из двух бросков)\n"
        "- /d20dis+5: Один бросок d20 с помехой, плюс 5\n"
        "- /2к6: Два броска кубика с 6 гранями, сумма\n"
        "- /д100+5: Один бросок с 100 гранями плюс 5\n"
        "- /3r10-2: Три броска с 10 гранями минус 2\n"
        "- /к-50фв: Один бросок с 50 гранями с преимуществом, результат инвертирован\n"
        "- /d20*3: Один бросок с 20 гранями, умноженный на 3\n"
        "- /10д20-50: 10 бросков кубика с 20 гранями минус 50\n"
        "- /6r-10+20: 6 бросков кубика с 10 гранями, инвертированных, плюс 20\n"
        "- !атака с силой /2r20 /d20вшы !финал: Два броска (обычный и с помехой) с комментариями\n\n"
        "Бот работает в чатах, если у него есть права на отправку и удаление сообщений\n"
    )
    vk.messages.send(
        peer_id=event.obj.message['peer_id'],
        message=description,
        random_id=random.randint(1, 1000000)
    )

# Функция для парсинга токенов (ещё более надёжная обработка текста)
def parse_tokens(text):
    # Удаляем лишние пробелы, переносы строк и нормализуем текст
    text = ' '.join(text.replace('\n', ' ').replace('\r', ' ').split())
    tokens = []
    i = 0
    while i < len(text):
        if text[i] == '!':
            j = i
            i += 1
            while i < len(text) and text[i] != '/':
                i += 1
            token = text[j:i].strip()
            if len(token) > 1:
                tokens.append(token)
        elif text[i] == '/':
            j = i
            i += 1
            while i < len(text) and not text[i].isspace() and text[i] != '!' and text[i] != '/':
                i += 1
            token = text[j:i].strip()
            if len(token) > 1:
                tokens.append(token)
        else:
            i += 1
    print(f"Parsed tokens: {tokens}, raw input: '{text}'")  # Максимальная отладка
    return tokens

# Асинхронная функция для удаления сообщения через задержку
async def delete_message_later(peer_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        vk.messages.delete(
            message_ids=[message_id],
            delete_for_all=1
        )
        print(f"Успешно удалено сообщение {message_id} для peer_id {peer_id}")
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при удалении сообщения {message_id} для peer_id {peer_id}: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при удалении сообщения {message_id} для peer_id {peer_id}: {e}")

# Обработчик кубиков (усиленная отладка и исправленное удаление)
async def handle_dice_command(event):
    chat_id = event.obj.message['peer_id']
    username = get_user_name(event.obj.message['from_id'])
    settings = load_settings()

    command_text = event.obj.message['text']
    is_group_chat = chat_id > 2000000000  # Проверка, беседа ли это
    print(f"Обработка команды: '{command_text}', peer_id: {chat_id}, from_id: {event.obj.message['from_id']}, is_group_chat: {is_group_chat}")

    # Проверка на дробные числа
    if re.match(r'^/\d*[rRdDlLдДкКвВ]-?\d*\.\d+', command_text, re.IGNORECASE):
        try:
            response_id = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message='Блять, олух, я понимаю только целые числа, не умничай тут блять',
                random_id=random.randint(1, 1000000)
            )
            print(f"Отправлено сообщение об ошибке дробных чисел, message_id: {response_id}")
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response_id,
                settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
            ))
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка отправки сообщения об ошибке дробных чисел: {e}")
        return

    tokens = parse_tokens(command_text)
    if not tokens:
        try:
            response_id = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message='Иди нахуй, не тот формат',
                random_id=random.randint(1, 1000000)
            )
            print(f"Отправлено сообщение о неверном формате, message_id: {response_id}")
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response_id,
                settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
            ))
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка отправки сообщения о неверном формате: {e}")
        return

    command_count = sum(1 for token in tokens if token.startswith('/'))
    chat_id_str = str(chat_id)
    if chat_id_str in settings and 'com_limit' in settings[chat_id_str] and settings[chat_id_str]['com_limit'] > 0 and command_count > settings[chat_id_str]['com_limit']:
        try:
            response_id = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message=f'Слишком много команд! Лимит: {settings[chat_id_str]["com_limit"]}',
                random_id=random.randint(1, 1000000)
            )
            print(f"Отправлено сообщение о превышении лимита команд, message_id: {response_id}")
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response_id,
                settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
            ))
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка отправки сообщения о превышении лимита: {e}")
        return

    results = []
    valid_results = []
    invalid_count = 0
    has_successful_roll = False

    for token in tokens:
        if token.startswith('!'):
            comment = token[1:].strip()
            results.append(comment)
            print(f"Обработан комментарий: '{comment}'")
        elif token.startswith('/'):
            parsed = parse_dice_command(token, chat_id, settings)
            if parsed:
                can_roll, remaining = check_timeout(chat_id, settings)
                if not can_roll:
                    try:
                        response_id = vk.messages.send(
                            peer_id=event.obj.message['peer_id'],
                            message=f'Подожди, осталось {remaining} секунд',
                            random_id=random.randint(1, 1000000)
                        )
                        print(f"Отправлено сообщение о таймауте, message_id: {response_id}")
                        asyncio.create_task(delete_message_later(
                            event.obj.message['peer_id'],
                            response_id,
                            settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
                        ))
                    except vk_api.exceptions.ApiError as e:
                        print(f"Ошибка отправки сообщения о таймауте: {e}")
                    return
                num_rolls, sides, modifier, mod_type, is_negative, adv_dis = parsed
                result, total = roll_dice(num_rolls, sides, modifier, mod_type, is_negative, username, adv_dis)
                valid_results.append(result)
                results.append(result)
                has_successful_roll = True
                print(f"Обработан бросок: '{result}', total: {total}")
            else:
                invalid_count += 1
                results.append(f'Иди нахуй, не тот формат')
                print(f"Неверный формат команды: '{token}'")

    if has_successful_roll and str(chat_id) in settings:
        settings = load_settings()
        if str(chat_id) in settings:
            settings[str(chat_id)]['last_roll'] = time.time()
            save_settings(settings)
            print(f"Обновлено время последнего броска для chat_id: {chat_id}")

    if invalid_count > 0 and not valid_results:
        try:
            response_id = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message='\n'.join(results) or 'Иди нахуй, не тот формат',
                random_id=random.randint(1, 1000000)
            )
            print(f"Отправлено сообщение с ошибками формата, message_id: {response_id}")
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response_id,
                settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
            ))
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка отправки сообщения с ошибками формата: {e}")
        return

    if not results:
        try:
            response_id = vk.messages.send(
                peer_id=event.obj.message['peer_id'],
                message='Иди нахуй, не тот формат',
                random_id=random.randint(1, 1000000)
            )
            print(f"Отправлено сообщение о пустом результате, message_id: {response_id}")
            asyncio.create_task(delete_message_later(
                event.obj.message['peer_id'],
                response_id,
                settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
            ))
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка отправки сообщения о пустом результате: {e}")
        return

    try:
        response_id = vk.messages.send(
            peer_id=event.obj.message['peer_id'],
            message='\n'.join(results),
            random_id=random.randint(1, 1000000)
        )
        print(f"Отправлен результат бросков, message_id: {response_id}")
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка отправки результатов бросков: {e}")
        return

    has_valid = any(not r.startswith('Иди нахуй') for r in results)
    if not has_valid:
        asyncio.create_task(delete_message_later(
            event.obj.message['peer_id'],
            response_id,
            settings.get(str(chat_id), {}).get('del_timer', DELETE_DELAY)
        ))

# Главная функция (добавлена отладка для peer_id)
def main():
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    message_text = event.obj.message['text'].lower()
                    peer_id = event.obj.message['peer_id']
                    from_id = event.obj.message['from_id']
                    print(f"Получено сообщение: {message_text}, peer_id: {peer_id}, from_id: {from_id}")  # Отладочный вывод
                    if message_text.startswith('/начать') or message_text.startswith('/help') or message_text.startswith('/помощь'):
                        asyncio.run(info(event))
                    elif message_text.startswith(('/timeout', '/to', '/timeoutlist', '/tol', '/rollslimit', '/rl', '/rollslimitlist', '/rll', '/sideslimit', '/sl', '/sideslimitlist', '/sll', '/deltimer', '/dt', '/deltimerlist', '/dtl', '/comlimit', '/cl', '/comlimitlist', '/cll')):
                        asyncio.run(handle_settings_command(event))
                    elif message_text.startswith('!') or message_text.startswith('/'):
                        asyncio.run(handle_dice_command(event))
        except Exception as e:
            print(f"Ошибка в Long Poll: {e}")
            time.sleep(5)  # Ждём перед повторной попыткой

if __name__ == '__main__':
    main()