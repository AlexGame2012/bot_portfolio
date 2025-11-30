from logic import *
from config import *
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telebot import types

bot = TeleBot(TOKEN)
hide_board = types.ReplyKeyboardRemove()

CANCEL_BUTTON = "Отмена 🚫"
MAX_PROJECT_NAME_LENGTH = 100

attributes_of_projects = {
    'Имя проекта': ["Введите новое имя проекта", "project_name"],
    "Описание": ["Введите новое описание проекта", "description"],
    "Ссылка": ["Введите новую ссылку на проект", "url"],
    "Статус": ["Выберите новый статус задачи", "status_id"],
    "Фото": ["Отправьте новое фото для проекта", "photo"]
}


def check_cancel(message):
    if message.text and message.text == CANCEL_BUTTON:
        bot.send_message(
            message.chat.id, 
            "Операция отменена. Для просмотра команд используй /info", 
            reply_markup=hide_board
        )
        return True
    return False


def no_projects(message):
    bot.send_message(
        message.chat.id, 
        '📭 У тебя пока нет проектов!\nМожешь добавить их с помощью команды /new_project'
    )


def gen_inline_markup(rows):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    for row in rows:
        markup.add(InlineKeyboardButton(row, callback_data=row))
    return markup


def gen_markup(rows):
    markup = ReplyKeyboardMarkup(
        one_time_keyboard=True, 
        resize_keyboard=True,   
        row_width=1
    )
    for row in rows:
        markup.add(KeyboardButton(row))
    markup.add(KeyboardButton(CANCEL_BUTTON))
    return markup


def validate_project_name(message):
    name = message.text.strip()
    
    if not name:
        bot.send_message(message.chat.id, "❌ Название проекта не может быть пустым. Введите название:")
        return None
    
    if len(name) > MAX_PROJECT_NAME_LENGTH:
        bot.send_message(
            message.chat.id, 
            f"❌ Слишком длинное название. Максимум {MAX_PROJECT_NAME_LENGTH} символов."
        )
        return None
    
    return name


def info_project(message, user_id, project_name):
    info = manager.get_project_info(user_id, project_name)[0]
    skills = manager.get_project_skills(project_name)
    
    if not skills:
        skills = 'Навыки пока не добавлены'

    # Экранирование специальных символов для MarkdownV2
    def escape_markdown(text):
        if not text:
            return ""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

    text = f"""
📁 *Project name*: {escape_markdown(info[0])}
📝 *Description*: {escape_markdown(info[1])}
🔗 *Link*: {escape_markdown(info[2])}
📊 *Status*: {escape_markdown(info[3])}
🛠️ *Skills*: {escape_markdown(skills)}
"""
    if info[4]:
        bot.send_photo(message.chat.id, info[4], caption=text, reply_markup=hide_board, parse_mode='MarkdownV2')
    else:
        bot.send_message(message.chat.id, text, reply_markup=hide_board, parse_mode='MarkdownV2')



@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = """
👋 Привет! Я бот-менеджер проектов
Помогу тебе сохранить твои проекты и информацию о них! 🚀
"""
    bot.send_message(message.chat.id, welcome_text)
    info(message)


@bot.message_handler(commands=['info'])
def info(message):
    commands_info = """
📋 **Доступные команды:**

/newproject - добавить новый проект
/projects - показать все проекты
/skills - выбрать навык для проекта
/delete - удалить проект
/updateprojects - обновить проект

💡 Также ты можешь ввести имя проекта и узнать информацию о нем!
"""
    bot.send_message(message.chat.id, commands_info, reply_markup=hide_board, parse_mode='Markdown')


@bot.message_handler(commands=['newproject'])
def addtask_command(message):
    bot.send_message(message.chat.id, "📝 Введите название проекта:", reply_markup=hide_board)
    bot.register_next_step_handler(message, name_project)


def name_project(message):
    if check_cancel(message):
        return
        
    name = validate_project_name(message)
    if name is None:
        bot.register_next_step_handler(message, name_project)
        return
        
    user_id = message.from_user.id
    data = [user_id, name]
    
    bot.send_message(message.chat.id, "📄 Введите описание проекта:")
    bot.register_next_step_handler(message, description_project, data=data)


def description_project(message, data):
    if check_cancel(message):
        return
        
    description = message.text.strip()
    if not description:
        bot.send_message(message.chat.id, "❌ Описание не может быть пустым. Введите описание:")
        bot.register_next_step_handler(message, description_project, data=data)
        return
        
    data.append(description) 
    bot.send_message(message.chat.id, "🔗 Введите ссылку на проект:")
    bot.register_next_step_handler(message, link_project, data=data)


def link_project(message, data):
    if check_cancel(message):
        return
        
    data.append(message.text.strip())  
    bot.send_message(
        message.chat.id, 
        "🖼️ Хотите добавить фото к проекту? Отправьте фото или напишите 'пропустить'", 
        reply_markup=gen_markup(['пропустить'])
    )
    bot.register_next_step_handler(message, handle_photo_choice, data=data)


def handle_photo_choice(message, data):
    if check_cancel(message):
        return
        
    if message.text and message.text.lower() == 'пропустить':
        data.append(None)  
        statuses = [x[0] for x in manager.get_statuses()] 
        bot.send_message(
            message.chat.id, 
            "📊 Выберите текущий статус проекта", 
            reply_markup=gen_markup(statuses)
        )
        bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)
    elif message.photo:
        photo_id = message.photo[-1].file_id
        data.append(photo_id)
        statuses = [x[0] for x in manager.get_statuses()] 
        bot.send_message(
            message.chat.id, 
            "📊 Выберите текущий статус проекта", 
            reply_markup=gen_markup(statuses)
        )
        bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)
    else:
        bot.send_message(
            message.chat.id, 
            "❌ Пожалуйста, отправьте фото или напишите 'пропустить'", 
            reply_markup=gen_markup(['пропустить'])
        )
        bot.register_next_step_handler(message, handle_photo_choice, data=data)


def callback_project(message, data, statuses):
    if check_cancel(message):
        return
        
    status = message.text
    if status not in statuses:
        bot.send_message(
            message.chat.id, 
            "❌ Вы выбрали статус не из списка, попробуйте еще раз!",
            reply_markup=gen_markup(statuses)
        )
        bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)
        return
        
    status_id = manager.get_status_id(status)
    data.append(status_id)
    
    manager.insert_project([tuple(data)])
    bot.send_message(message.chat.id, "✅ Проект сохранен!", reply_markup=hide_board)


@bot.message_handler(commands=['skills'])
def skill_handler(message):
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    
    if projects:
        projects_names = [x[2] for x in projects]
        bot.send_message(
            message.chat.id, 
            '🎯 Выберите проект для которого нужно выбрать навык', 
            reply_markup=gen_markup(projects_names)
        )
        bot.register_next_step_handler(message, skill_project, projects=projects_names)
    else:
        no_projects(message)


def skill_project(message, projects):
    if check_cancel(message):
        return
        
    project_name = message.text
    if project_name not in projects:
        bot.send_message(
            message.chat.id, 
            '❌ У вас нет такого проекта, попробуйте еще раз!', 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, skill_project, projects=projects)
    else:
        skills = [x[1] for x in manager.get_skills()]
        bot.send_message(message.chat.id, '🛠️ Выберите навык', reply_markup=gen_markup(skills))
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)


def set_skill(message, project_name, skills):
    if check_cancel(message):
        return
        
    skill = message.text
    user_id = message.from_user.id
        
    if skill not in skills:
        bot.send_message(
            message.chat.id, 
            '❌ Вы выбрали навык не из списка, попробуйте еще раз!', 
            reply_markup=gen_markup(skills)
        )
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)
        return
        
    manager.insert_skill(user_id, project_name, skill)
    bot.send_message(
        message.chat.id, 
        f'✅ Навык {skill} добавлен проекту {project_name}', 
        reply_markup=hide_board
    )


@bot.message_handler(commands=['projects'])
def get_projects(message):
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    
    if projects:
        text = "\n".join([f"📁 Project name: {x[2]} \n🔗 Link: {x[4]}\n" for x in projects])
        bot.send_message(
            message.chat.id, 
            text, 
            reply_markup=gen_inline_markup([x[2] for x in projects])
        )
    else:
        no_projects(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    project_name = call.data
    info_project(call.message, call.from_user.id, project_name)


@bot.message_handler(commands=['delete'])
def delete_handler(message):
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    
    if projects:
        text = "\n".join([f"📁 Project name: {x[2]} \n🔗 Link: {x[4]}\n" for x in projects])
        projects_names = [x[2] for x in projects]
        bot.send_message(message.chat.id, text, reply_markup=gen_markup(projects_names))
        bot.register_next_step_handler(message, delete_project, projects=projects_names)
    else:
        no_projects(message)


def delete_project(message, projects):
    if check_cancel(message):
        return
        
    project = message.text
    user_id = message.from_user.id

    if project not in projects:
        bot.send_message(
            message.chat.id, 
            '❌ У вас нет такого проекта, попробуйте выбрать еще раз!', 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, delete_project, projects=projects)
        return
        
    project_id = manager.get_project_id(project, user_id)
    manager.delete_project(user_id, project_id)
    bot.send_message(message.chat.id, f'🗑️ Проект {project} удален!', reply_markup=hide_board)


@bot.message_handler(commands=['updateprojects'])
def update_project(message):
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    
    if projects:
        projects_names = [x[2] for x in projects]
        bot.send_message(
            message.chat.id, 
            "🔄 Выберите проект, который хотите изменить", 
            reply_markup=gen_markup(projects_names)
        )
        bot.register_next_step_handler(message, update_project_step_2, projects=projects_names)
    else:
        no_projects(message)


def update_project_step_2(message, projects):
    if check_cancel(message):
        return
        
    project_name = message.text
    if project_name not in projects:
        bot.send_message(
            message.chat.id, 
            "❌ Проект не найден! Выберите проект, который хотите изменить:", 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, update_project_step_2, projects=projects)
        return
        
    bot.send_message(
        message.chat.id, 
        "📝 Выберите, что требуется изменить в проекте", 
        reply_markup=gen_markup(attributes_of_projects.keys())
    )
    bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)


def update_project_step_3(message, project_name):
    if check_cancel(message):
        return
        
    attribute = message.text
    reply_markup = None 
    
    if attribute not in attributes_of_projects.keys():
        bot.send_message(
            message.chat.id, 
            "❌ Выберите параметр из списка:", 
            reply_markup=gen_markup(attributes_of_projects.keys())
        )
        bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)
        return
        
    elif attribute == "Статус":
        rows = manager.get_statuses()
        reply_markup = gen_markup([x[0] for x in rows])
        
    bot.send_message(
        message.chat.id, 
        attributes_of_projects[attribute][0], 
        reply_markup=reply_markup
    )
    bot.register_next_step_handler(
        message, 
        update_project_step_4, 
        project_name=project_name, 
        attribute=attributes_of_projects[attribute][1]
    )


def update_project_step_4(message, project_name, attribute): 
    if check_cancel(message):
        return
        
    if attribute == "photo":
        if message.photo:
            update_info = message.photo[-1].file_id
        else:
            update_info = None
    else:
        update_info = message.text
        
    if attribute == "status_id":
        rows = manager.get_statuses()
        if update_info in [x[0] for x in rows]:
            update_info = manager.get_status_id(update_info)
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Выбран неверный статус, попробуйте еще раз!", 
                reply_markup=gen_markup([x[0] for x in rows])
            )
            bot.register_next_step_handler(
                message, 
                update_project_step_4, 
                project_name=project_name, 
                attribute=attribute
            )
            return
            
    user_id = message.from_user.id
    data = (update_info, project_name, user_id)
    manager.update_projects(attribute, data)
    bot.send_message(message.chat.id, "✅ Готово! Обновления внесены!", reply_markup=hide_board)


@bot.message_handler(func=lambda message: True)
def text_handler(message):
    user_id = message.from_user.id
    projects = [x[2] for x in manager.get_projects(user_id)]
    project = message.text
    
    if project in projects:
        info_project(message, user_id, project)
        return
        
    bot.reply_to(message, "🤔 Тебе нужна помощь?")
    info(message)


# ========== ЗАПУСК БОТА ==========

if __name__ == '__main__':
    manager = DB_Manager(DATABASE)
    print("🚀 Бот запущен и готов к работе!")
    bot.infinity_polling()