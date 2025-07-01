# app/lexicon.py

LEXICON_COMMANDS_RU = {
    '/start': 'Перезапустить бота',
    '/settings': 'Открыть профиль'
}

LEXICON_COMMANDS_EN = {
    '/start': 'Restart the bot',
    '/settings': 'Open profile'
}

EVENT_TYPES_RU = ["Концерт", "Театр", "Спорт", "Цирк", "Выставка", "Фестиваль"]
EVENT_TYPES_EN = ["Concert", "Theater", "Sport", "Circus", "Exhibition", "Festival"]

RU_MONTH_NAMES = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
EN_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

EVENT_TYPE_MAPPING = {
    # 'универсальный_ключ': {'ru': 'Русский текст', 'en': 'Английский текст'},
    'concert':    {'ru': 'Концерт',    'en': 'Concert'},
    'theater':    {'ru': 'Театр',      'en': 'Theater'},
    'sport':      {'ru': 'Спорт',      'en': 'Sport'},
    'circus':     {'ru': 'Цирк',       'en': 'Circus'},
    'exhibition': {'ru': 'Выставка',   'en': 'Exhibition'},
    'festival':   {'ru': 'Фестиваль',  'en': 'Festival'},
}

EVENT_TYPE_EMOJI = {
    "Концерт": "🎵", "Театр": "🎭", "Спорт": "🏅", "Цирк": "🎪",
    "Выставка": "🎨", "Фестиваль": "🎉",
}

def get_event_type_keys() -> list[str]:
    return list(EVENT_TYPE_MAPPING.keys())

def get_event_type_display_name(key: str, lang_code: str) -> str:
    # По умолчанию 'en', если для языка нет перевода
    lang = 'ru' if lang_code == 'ru' else 'en'
    return EVENT_TYPE_MAPPING.get(key, {}).get(lang, key)

def get_event_type_storage_value(key: str) -> str:
    # Всегда возвращаем русскую версию. Если ее нет, возвращаем сам ключ.
    return EVENT_TYPE_MAPPING.get(key, {}).get('ru', key)

# Вспомогательная функция для получения названия на нужном языке
def get_event_type_name(key: str, lang_code: str) -> str:
    # По умолчанию 'en', если для языка нет перевода
    lang = lang_code if lang_code == 'ru' else 'en'
    return EVENT_TYPE_MAPPING.get(key, {}).get(lang, key)

class Lexicon:
    def __init__(self, lang_code: str = 'en'):
        self.lang_code = lang_code if lang_code in ('ru', 'be') else 'en'
        self.lexicon = self._get_lexicon()

        if self.lang_code == 'ru':
            self.EVENT_TYPES = EVENT_TYPES_RU
            self.MONTH_NAMES = RU_MONTH_NAMES
        else:
            self.EVENT_TYPES = EVENT_TYPES_EN
            self.MONTH_NAMES = EN_MONTH_NAMES

    def _get_lexicon(self):
        lexicons = {
            'ru': {
                'welcome': "👋 Привет, {first_name}!\n\nЯ твой гид в мире событий. Я помогу тебе найти интересные концерты, спектакли и многое другое.\n\nДавай настроимся. Сначала выбери свою страну проживания:",
                'setup_complete': "🎉 Настройка завершена! Теперь ты можешь пользоваться всеми функциями бота.",
                'main_menu_greeting': "С возвращением, {first_name}!",
                'main_menu_button_afisha': "🗓 Афиша",
                'main_menu_button_subs': "⭐ Мои подписки",
                'main_menu_button_profile': "👤 Профиль",
                "find_another_city": "🔎 Найти другой город",
                'finish_button': "✅ Готово",
                'settings_intro': "Здесь ты можешь изменить свои настройки. Выбери страну проживания:",
                'search_city_prompt': "Введите название города, который вы ищете:",
                'city_not_found': "😔 К сожалению, я не нашел такой город. Попробуйте ввести название еще раз.",
                'city_found_prompt': "Вот что я нашел. Выберите нужный город:",
                'profile_menu_header': "👤 Ваш Профиль",
                'configure': 'Настроить',
                'skip_settings': 'Пропустить настройку',
                'profile_button_location': "📍 Изменить мои предпочтения",
                'profile_general_geo': '🌍 Настройка общей мобильности',
                'back_to_profile':'⬅️ Назад в профиль',
                'back_to_choose_country': '⬅️ Назад к выбору страны',
                'save_changes': '✅ Сохранить изменения',
                'back_to_choose_city': '⬅️ Назад к выбору города',
                "setup_general_mobility": '👍 Да, настроить',
                'skip_general_mobility': '➡️ Пропустить',
                'write_artist':'✍️ Написать артиста',
                'import_artists': '📥 Импортировать',
                'general_mobility_settings': '🛠️ Настроить общую мобильность',

                # --- НОВЫЕ КЛЮЧИ ДЛЯ КЛАВИАТУР И ХЭНДЛЕРОВ ---
                'use_general_mobility_button': "🌍 Использовать общие",
                'setup_custom_mobility_button': "⚙️ Настроить для этой подписки",
                'add_another_artist_button': "✍️ Добавить еще артиста",
                'import_more_button': "📥 Импортировать еще",
                'cancel_button': "Отмена",
                'onboarding_mobility_prompt': "Для добавления артиста вам надо настроить страны, куда вы готовы полететь. Это общая настройка, которую можно будет использовать для всех подписок. Вы можете пропустить этот шаг.",
                'action_prompt_with_mobility_setup': "Напиши исполнителя/событие для отслеживания. Также ты можешь сначала настроить общую мобильность.",
                'action_prompt_default': "Напиши исполнителя/событие для отслеживания. Также я могу импортировать их.",
                'general_mobility_selection_prompt': "Отлично! Выбери страны, которые войдут в твою 'общую мобильность'.",
                'general_mobility_skipped_prompt': "Хорошо. Теперь напиши исполнителя/событие для отслеживания или импортируй их.",
                'enter_artist_name_prompt': "Введите имя артиста или название группы:",
                'import_in_development_alert': "Функция импорта находится в разработке.",
                'favorites_not_found_try_again': "По твоему запросу никого не найдено. Попробуй еще раз.",
                'favorites_found_prompt_select_artist': "Вот кого я нашел. Выбери нужного артиста:",
                'artist_mobility_choice_prompt': "Артист: {artist_name}. Хотите добавить страны для отслеживания конкретно для этой подписки или использовать общие настройки?",
                'artist_set_tracking_countries_prompt': "Артист: {artist_name}. Укажите страны для отслеживания.",
                'artist_added_with_general_settings_alert': "Артист {artist_name} добавлен с общими настройками.",
                'artist_added_with_custom_settings_alert': "Артист {artist_name} добавлен с кастомными настройками.",
                'sub_added_to_queue': "Подписка добавлена в очередь на сохранение.\n",
                'queue_for_adding_header': "\n<b>Очередь на добавление:</b>\n",
                'general_mobility_saved_prompt_action': "Отлично! Теперь напиши исполнителя/событие или импортируй их.",
                'nothing_to_add_alert': "Вы ничего не добавили в очередь.",
                'failed_to_add_artists': "Не удалось добавить выбранных артистов.",
                'cancel_alert': "Отменено.",
                'artist_not_found_error': "Ошибка: артист не найден.",
                # ---------------------------------------------------
                
                'afisha_choose_period_prompt': "На какой период ищем события?",
                'afisha_choose_month_prompt': "Выберите интересующий вас месяц:",
                'afisha_choose_filter_type_prompt': "Отлично! Ищем с {date_from} по {date_to}.\n\nКак будем фильтровать?",
                'afisha_filter_by_my_prefs_button': "По моим предпочтениям",
                'afisha_filter_by_temporary_button': "Выбрать локацию и категории",
                'back_to_date_choice_button': "⬅️ К выбору периода",
                'period_today': "Сегодня",
                'period_tomorrow': "Завтра",
                'period_this_week': "На этой неделе",
                'period_this_weekend': "На выходных",
                'period_this_month': "На этот месяц",
                'period_other_month': "🗓 Выбрать другой месяц",
                'search_prompt_enter_query_v2': "Введите название события или имя артиста для поиска:",
                'search_searching_for_query_v2': "🔎 Ищу события: «{query_text}»...",
                'search_no_results_found_v2': "😔 По вашему запросу «{query_text}» ничего не найдено. Попробуйте другой запрос.",
                'main_menu_button_favorites': "➕ Найти/добавить артиста",
                'favorites_menu_header_empty': "У вас пока нет избранных артистов или событий. Давайте добавим первого?",
                'favorites_menu_header': "Ваше избранное:\n{favorites_list}",
                'favorites_list_prompt': "Ваше избранное. Нажмите на артиста/событие для управления им:",
                'favorite_artist_menu_prompt': "Управление избранным: {artist_name}",
                'favorites_remove_button': "🗑️ Удалить из избранного",
                'favorites_enter_name_prompt': "Введите имя артиста, группы или название фестиваля, который хотите отслеживать:",
                'favorites_not_found': "К сожалению, по вашему запросу ничего не найдено. Попробуйте еще раз или вернитесь назад.",
                'favorites_found_prompt': "Вот кого я нашел. Выберите нужный вариант:",
                'favorites_added_alert': "✅ Добавлено в избранное!",
                'favorites_remove_prompt': "Нажмите на артиста/событие, которое хотите удалить из избранного:",
                'favorites_removed_alert': "🗑️ Удалено из избранного.",
                'favorites_remove_empty_alert': "У вас нет ничего в избранном для удаления.",
                'back_to_favorites_menu_button': "⬅️ Назад в меню 'Избранное'",
                'back_to_favorites_list_button': "⬅️ К списку избранного",
                'favorites_added_final': "✅ Готово! Добавлено в избранное: {count} шт.",
                'favorite_edit_regions_button':  "🌍 Изменить общую мобильность",
                'favorite_edit_regions_prompt': "Измените регионы отслеживания для: {artist_name}",
                'favorite_regions_updated_alert': "✅ Регионы для избранного обновлены!",
                'afisha_add_to_subs_button': "➕ Добавить в подписки",
                'subs_enter_numbers_prompt': "Введите номера событий, которые хотите отслеживать, через запятую или пробел (например: 1, 3, 5).",
                'subs_invalid_numbers_error': "⚠️ Ошибка: номера {invalid_list} некорректны. Пожалуйста, вводите только те номера, что видите в списке.",
                'subs_added_success': "✅ Успешно добавлено в подписки: {count} шт.",
                'subs_no_valid_numbers_provided': "Вы не ввели ни одного корректного номера.",
                'subs_nan_error': "Пожалуйста, вводите только числа.",
                'subs_add_from_afisha_offer': "Вы можете добавить эти события в свои подписки.",
                'edit_mobility_prompt': "Измените свой список стран для 'общей мобильности'. Эти настройки будут применяться ко всем вашим избранным артистам по умолчанию.",
                'mobility_saved_alert': "✅ Общие настройки мобильности сохранены!",
                'subs_menu_header_active': "Вы отслеживаете следующие события.\nНажмите на любое, чтобы управлять им:",
                'subs_menu_header_empty': "У вас нет активных подписок на события. Вы можете добавить их из 'Афиши'.",
                'subs_status_active': "Активна",
                'subs_status_paused': "На паузе",
                'subs_pause_button': "⏸️ Поставить на паузу",
                'subs_resume_button': "▶️ Возобновить",
                'subs_unsubscribe_button': "🗑️ Отписаться",
                'subs_paused_alert': "🔔 Напоминания по этому событию приостановлены.",
                'subs_resumed_alert': "🔔 Напоминания по этому событию возобновлены.",
                'subs_removed_alert': "❌ Вы отписались от {item_name}. ",
                'subs_not_found_alert': "Ошибка: подписка не найдена.",
                'back_to_subscriptions_list_button': "⬅️ К списку подписок",
                'back_button': "⬅️ Назад",
                'no_regions_selected_alert': "Нужно выбрать хотя бы один регион!",
                'subs_reminder_header': "🔔 **Напоминание о ваших подписках:**",

                'edit_geo_choose_country_prompt': "Выберите вашу страну проживания:",
                'edit_geo_city_prompt': "Страна: {country_name}. Теперь выберите город.",
                'edit_geo_event_types_prompt': "Город: {city_name}. Теперь выберите интересующие типы событий.",
                'generic_error_try_again': "Произошла ошибка, попробуйте снова.",
                'select_at_least_one_event_type_alert': "Пожалуйста, выберите хотя бы один тип событий.",
                'settings_changed_successfully_alert': "Настройки успешно изменены!",
                'invalid_event_id_error': "Ошибка: неверный ID события.",
                'sub_or_event_not_found_error': "Подписка или событие не найдено.",
                'date_not_specified': "Дата не указана",
                'subscription_details_view': "Подписка на событие: {title}\nДата: {date}\n\nСтатус: {status}",
                'profile_button_manage_subs': "⭐ Мои подписки", # Для клавиатуры профиля
                'profile_button_favorites': "⭐ Избранные", # Новая кнопка в профиле

                'afisha_nothing_found_for_query': "По вашему запросу ничего не найдено.",
                'afisha_prefs_not_configured_alert': "Ваши предпочтения не настроены. Пожалуйста, настройте их в Профиле.",
                'afisha_results_by_prefs_header': "Вот что я нашел по вашим предпочтениям для г. {city_name}:",
                'afisha_no_results_for_prefs_period': "По вашим предпочтениям и выбранному периоду ничего не найдено.",
                'afisha_temp_select_city_prompt': "Страна: {country_name}. Теперь выберите город.",
                'afisha_temp_select_types_prompt': "Город: {city_name}. Теперь выберите интересующие типы событий:",
                'afisha_results_for_city_header': "Вот что я нашел для г. {city_name}:",
                'afisha_must_find_events_first_alert': "Сначала нужно найти события через Афишу или Поиск.",
                'default_country_for_temp_search': "Беларусь", # Страна по умолчанию, если не задана у пользователя

                'unknown_command': "Я не знаю такой команды. Воспользуйтесь кнопками меню.",

                'favorite_artist_find_error_alert': "Ошибка: не удалось найти артиста. Возвращаю в список.",
                'artist_not_in_db_alert': "Артист больше не найден в базе.",
                'event_added_to_subs_alert': "✅ Событие добавлено в 'Мои подписки'!",
                'error_adding_event_to_subs_alert': "Ошибка! Не удалось добавить событие.",

                'onboarding_country_selected_prompt': "Отлично, твоя страна: {country_name}. Дальше вам надо настроить город проживания и предпочитаемые типы ивентов.",
                'onboarding_city_selection_prompt': "Отлично, твоя страна: {country_name}. Теперь выбери свой город или пропусти этот шаг.",
                'onboarding_event_type_prompt': "Отлично, твой город: {city_name}. Выбери типы событий, которые тебе интересны. Это поможет мне давать лучшие рекомендации.",
                'onboarding_back_to_city_prompt': "Твоя страна: {country_name}. Выбери свой город или пропусти.",

                'recommendations_after_add_favorite': "Мы заметили, что вы добавили в избранное {artist_name}! ✨\n\nВозможно, вам также понравятся эти исполнители:",
                'unknown_artist': "Неизвестный артист",
                'new_event_title': "Новое событие",
                'new_event_for_favorite_notification': "{emoji} У вашего избранного артиста {artist_name} появилось новое событие!\n\n🎵 {event_title}\n📍 {event_city}, {event_country}",
                'user_blocked_bot_log': "Пользователь {user_id} заблокировал бота.", # Для логов, но можно и для админа в будущем
                'failed_to_send_notification_log': "Не удалось отправить уведомление пользователю {user_id}: {e}", # Аналогично

                'tickets_available': "В наличии",
                'reminder_event_item': "<b>{index}. {title}</b>\n📅 {date}\n🎟️ Билеты: {tickets}", # Формат одного события в списке напоминаний
                'reminder_user_blocked_log': "Пользователь {user_id} заблокировал бота. Деактивируем его подписки.",
                'reminder_failed_to_send_log': "Не удалось отправить уведомление пользователю {user_id}: {e}",

                'no_info': "Нет информации",
                'no_future_events_for_favorites': "На данный момент для них нет предстоящих событий. Мы сообщим, как только что-то появится!",
                'recommendations_after_add_favorite': "Мы заметили, что вы добавили в избранное {artist_name}! ✨\n\nНа основе этого, возможно, вам также понравятся эти исполнители:",
                'select_all_button': 'Выбрать все',
                'unselect_all_button': 'Снять все',
                'artist_already_in_queue_alert': "Артист {artist_name} уже в очереди на добавление.",
                'add_more_prompt': "\n\nЧтобы добавить еще, просто напишите имя следующего артиста. Или нажмите 'Готово', чтобы завершить.",

                'artist_search_exact_match': "Вот кого я нашел:",
                'artist_search_suggestion': "Точного совпадения не найдено. Возможно, вы имели в виду кого-то из этих исполнителей?",
                'favorite_view_events_button': '🎟️ Просмотреть события',
                'favorite_events_header': 'Найденные события для {artist_name}:',
                'favorite_events_in_tracked_regions': '📍 В отслеживаемых регионах:',
                'favorite_events_in_other_regions': '🌍 Также найдены в других регионах:',
                'favorite_edit_regions_button':  "🌍 Изменить регионы для артиста",
                'session_expired_alert': 'Эта сессия просмотра событий устарела. Пожалуйста, найдите события заново.',

                
            },
            'be': {
                # Здесь только те ключи, которые отличаются от русского
                'main_menu_button_profile': "👤 Профіль",
                'main_menu_button_settings': "⚙️ Налады",
                'profile_menu_header': "👤 Ваш Профіль",
                'profile_button_location': "📍 Змяніць лакацыю",
                'profile_button_subs': "➕ Знайсці/дадаць выканаўцу",
            },
            'en': {
                'welcome': "👋 Hi, {first_name}!\n\nI'm your guide to the world of events. I'll help you find interesting concerts, plays, and much more.\n\nLet's get set up. First, choose your country of residence:",
                'setup_complete': "🎉 Setup complete! You can now use all the bot's features.",
                'main_menu_greeting': "Welcome back, {first_name}!",
                'main_menu_button_afisha': "🗓 Events",
                'main_menu_button_subs': "⭐ My Subs",
                'main_menu_button_profile': "👤 Profile",
                "find_another_city": "🔎 Find another city",
                'finish_button': "✅ Done",
                'settings_intro': "Here you can change your settings. Choose your country of residence:",
                'search_city_prompt': "Enter the name of the city you are looking for:",
                'city_not_found': "😔 Unfortunately, I couldn't find that city. Please try entering the name again.",
                'city_found_prompt': "Here's what I found. Please select the correct city:",
                'profile_menu_header': "👤 Your Profile",
                'configure': 'Configure',
                'skip_settings': 'Skip setup',
                'profile_button_location': "📍 Change my preferences",
                'profile_general_geo': '🌍 Configure General Mobility',
                'back_to_profile':'⬅️ Back to Profile',
                'back_to_choose_country': '⬅️ Back to country selection',
                'save_changes': '✅ Save Changes',
                'back_to_choose_city': '⬅️ Back to city selection',
                "setup_general_mobility": '👍 Yes, configure',
                'skip_general_mobility': '➡️ Skip',
                'write_artist':'✍️ Write artist name',
                'import_artists': '📥 Import',
                'general_mobility_settings': '🛠️ Configure General Mobility',

                # --- NEW KEYS FOR KEYBOARDS AND HANDLERS ---
                'use_general_mobility_button': "🌍 Use general settings",
                'setup_custom_mobility_button': "⚙️ Configure for this subscription",
                'add_another_artist_button': "✍️ Add another artist",
                'import_more_button': "📥 Import more",
                'cancel_button': "Cancel",
                'onboarding_mobility_prompt': "To add an artist, you need to set up the countries you are willing to travel to. This is a general setting that can be used for all subscriptions. You can skip this step.",
                'action_prompt_with_mobility_setup': "Enter an artist/event to track. You can also configure your general mobility first.",
                'action_prompt_default': "Enter an artist/event to track. I can also import them.",
                'general_mobility_selection_prompt': "Great! Select the countries that will be part of your 'general mobility'.",
                'general_mobility_skipped_prompt': "Okay. Now, enter an artist/event to track or import them.",
                'enter_artist_name_prompt': "Enter the name of the artist or band:",
                'import_in_development_alert': "The import function is under development.",
                'favorites_not_found_try_again': "Nothing was found for your query. Please try again.",
                'favorites_found_prompt_select_artist': "Here's who I found. Select the correct artist:",
                'artist_mobility_choice_prompt': "Artist: {artist_name}. Would you like to add tracking countries specifically for this subscription, or use your general settings?",
                'artist_set_tracking_countries_prompt': "Artist: {artist_name}. Please specify the countries to track.",
                'artist_added_with_general_settings_alert': "Artist {artist_name} has been added with general settings.",
                'artist_added_with_custom_settings_alert': "Artist {artist_name} has been added with custom settings.",
                'sub_added_to_queue': "Subscription added to the save queue.\n",
                'queue_for_adding_header': "\n<b>Queue for adding:</b>\n",
                'general_mobility_saved_prompt_action': "Great! Now, enter an artist/event or import them.",
                'nothing_to_add_alert': "You haven't added anything to the queue.",
                'failed_to_add_artists': "Failed to add the selected artists.",
                'cancel_alert': "Cancelled.",
                'artist_not_found_error': "Error: artist not found.",
                # ---------------------------------------------------
                
                'afisha_choose_period_prompt': "For what period are we looking for events?",
                'afisha_choose_month_prompt': "Please select a month of interest:",
                'afisha_choose_filter_type_prompt': "Great! Searching from {date_from} to {date_to}.\n\nHow should we filter?",
                'afisha_filter_by_my_prefs_button': "By my preferences",
                'afisha_filter_by_temporary_button': "Choose location and categories",
                'back_to_date_choice_button': "⬅️ Back to period selection",
                'period_today': "Today",
                'period_tomorrow': "Tomorrow",
                'period_this_week': "This week",
                'period_this_weekend': "This weekend",
                'period_this_month': "This month",
                'period_other_month': "🗓 Choose another month",
                'search_prompt_enter_query_v2': "Enter an event name or artist to search:",
                'search_searching_for_query_v2': "🔎 Searching for events: '{query_text}'...",
                'search_no_results_found_v2': "😔 Nothing was found for your query '{query_text}'. Please try another query.",
                'main_menu_button_favorites': "➕ Find/Add Artist",
                'profile_button_favorites': "⭐ Favorities", # Новая кнопка в профиле
                'favorites_menu_header_empty': "You don't have any favorite artists or events yet. Shall we add the first one?",
                'favorites_menu_header': "Your Favorites:\n{favorites_list}",
                'favorites_list_prompt': "Your Favorites. Click on an artist/event to manage it:",
                'favorite_artist_menu_prompt': "Manage favorite: {artist_name}",
                'favorites_remove_button': "🗑️ Remove from Favorites",
                'favorites_enter_name_prompt': "Enter the name of the artist, band, or festival you want to track:",
                'favorites_not_found': "Unfortunately, nothing was found for your query. Please try again or go back.",
                'favorites_found_prompt': "Here's what I found. Please select the correct option:",
                'favorites_added_alert': "✅ Added to favorites!",
                'favorites_remove_prompt': "Click on the artist/event you want to remove from your favorites:",
                'favorites_removed_alert': "🗑️ Removed from favorites.",
                'favorites_remove_empty_alert': "You have nothing in your favorites to remove.",
                'back_to_favorites_menu_button': "⬅️ Back to Favorites Menu",
                'back_to_favorites_list_button': "⬅️ Back to Favorites List",
                'favorites_added_final': "✅ Done! Added to favorites: {count} item(s).",
                'favorite_edit_regions_button': "🌍 Edit general settings",
                'favorite_edit_regions_prompt': "Edit tracking regions for: {artist_name}",
                'favorite_regions_updated_alert': "✅ Favorite's regions have been updated!",
                'afisha_add_to_subs_button': "➕ Add to Subscriptions",
                'subs_enter_numbers_prompt': "Enter the numbers of the events you want to track, separated by a comma or space (e.g., 1, 3, 5).",
                'subs_invalid_numbers_error': "⚠️ Error: The numbers {invalid_list} are invalid. Please enter only the numbers you see in the list.",
                'subs_added_success': "✅ Successfully added to subscriptions: {count} item(s).",
                'subs_no_valid_numbers_provided': "You did not provide any valid numbers.",
                'subs_nan_error': "Please enter numbers only.",
                'subs_add_from_afisha_offer': "You can add these events to your subscriptions.",
                'edit_mobility_prompt': "Edit your list of countries for 'general mobility'. These settings will apply to all your favorite artists by default.",
                'mobility_saved_alert': "✅ General mobility settings saved!",
                'subs_menu_header_active': "You are tracking the following events.\nClick on any to manage it:",
                'subs_menu_header_empty': "You have no active event subscriptions. You can add them from the 'Events' section.",
                'subs_status_active': "Active",
                'subs_status_paused': "Paused",
                'subs_pause_button': "⏸️ Pause",
                'subs_resume_button': "▶️ Resume",
                'subs_unsubscribe_button': "🗑️ Unsubscribe",
                'subs_paused_alert': "🔔 Reminders for this event have been paused.",
                'subs_resumed_alert': "🔔 Reminders for this event have been resumed.",
                'subs_removed_alert': "❌ You have unsubscribed from {item_name}.",
                'subs_not_found_alert': "Error: subscription not found.",
                'back_to_subscriptions_list_button': "⬅️ Back to subscriptions list",
                'back_button': "⬅️ Back",
                'no_regions_selected_alert': "You must select at least one region!",
                'subs_reminder_header': "🔔 **Reminder of your subscriptions:**",

                'edit_geo_choose_country_prompt': "Select your country of residence:",
                'edit_geo_city_prompt': "Country: {country_name}. Now select a city.",
                'edit_geo_event_types_prompt': "City: {city_name}. Now select the event types you are interested in.",
                'generic_error_try_again': "An error occurred, please try again.",
                'select_at_least_one_event_type_alert': "Please select at least one event type.",
                'settings_changed_successfully_alert': "Settings changed successfully!",
                'invalid_event_id_error': "Error: invalid event ID.",
                'sub_or_event_not_found_error': "Subscription or event not found.",
                'date_not_specified': "Date not specified",
                'subscription_details_view': "Subscription for event: {title}\nDate: {date}\n\nStatus: {status}",
                'profile_button_manage_subs': "⭐ My Event Subscriptions",

                'afisha_nothing_found_for_query': "Nothing was found for your request.",
                'afisha_prefs_not_configured_alert': "Your preferences are not configured. Please set them up in your Profile.",
                'afisha_results_by_prefs_header': "Here's what I found based on your preferences for {city_name}:",
                'afisha_no_results_for_prefs_period': "Nothing was found for your preferences and the selected period.",
                'afisha_temp_select_city_prompt': "Country: {country_name}. Now select a city.",
                'afisha_temp_select_types_prompt': "City: {city_name}. Now select the event types you are interested in:",
                'afisha_results_for_city_header': "Here's what I found for {city_name}:",
                'afisha_must_find_events_first_alert': "You must first find events via Events or Search.",
                'default_country_for_temp_search': "Belarus",

                'unknown_command': "I don't know this command. Please use the menu buttons.",

                'favorite_artist_find_error_alert': "Error: could not find the artist. Returning to the list.",
                'artist_not_in_db_alert': "Artist no longer found in the database.",
                'event_added_to_subs_alert': "✅ Event added to 'My Subscriptions'!",
                'error_adding_event_to_subs_alert': "Error! Failed to add the event.",

                'onboarding_country_selected_prompt': "Great, your country is: {country_name}. Next, you need to set up your city of residence and preferred event types.",
                'onboarding_city_selection_prompt': "Great, your country is: {country_name}. Now choose your city or skip this step.",
                'onboarding_event_type_prompt': "Great, your city is: {city_name}. Select the types of events you're interested in. This will help me give better recommendations.",
                'onboarding_back_to_city_prompt': "Your country: {country_name}. Choose your city or skip.",

                'recommendations_after_add_favorite': "We noticed you've added {artist_name} to your favorites! ✨\n\nPerhaps you'll also like these artists:",
                'unknown_artist': "Unknown Artist",
                'new_event_title': "New Event",
                'new_event_for_favorite_notification': "{emoji} A new event has been announced for your favorite artist {artist_name}!\n\n🎵 {event_title}\n📍 {event_city}, {event_country}",
                'user_blocked_bot_log': "User {user_id} has blocked the bot.",
                'failed_to_send_notification_log': "Failed to send notification to user {user_id}: {e}",

                'tickets_available': "Available",
                'reminder_event_item': "<b>{index}. {title}</b>\n📅 {date}\n🎟️ Tickets: {tickets}",
                'reminder_user_blocked_log': "User {user_id} has blocked the bot. Deactivating their subscriptions.",
                'reminder_failed_to_send_log': "Failed to send reminder to user {user_id}: {e}",

                'no_info': "No information",
                'no_future_events_for_favorites': "Currently, there are no upcoming events for them. We'll notify you as soon as something is announced!",
                'recommendations_after_add_favorite': "We noticed you've added {artist_name} to your favorites! ✨\n\nBased on this, you might also like these artists:",
                'select_all_button': 'Select All',
                'unselect_all_button': 'Unselect All',  
                'artist_already_in_queue_alert': "Artist {artist_name} is already in the adding queue.",
                'add_more_prompt': "\n\nTo add more, just type the next artist's name. Or press 'Done' to finish.",
                'artist_search_exact_match': "Here's who I found:",
                'artist_search_suggestion': "No exact match found. Perhaps you meant one of these artists?",
                'favorite_view_events_button': '🎟️ View Events',
                'favorite_events_header': 'Found events for {artist_name}:',
                'favorite_events_in_tracked_regions': '📍 In Tracked Regions:',
                'favorite_events_in_other_regions': '🌍 Also Found in Other Regions:',
                'favorite_edit_regions_button': "🌍 Edit regions for this artist", # Исправил текст для логичности
                'profile_button_favorites': "⭐ My Favorites",
                'session_expired_alert': 'This event viewing session has expired. Please find the events again.',
            }
        }
        # --- ВАЖНОЕ ИСПРАВЛЕНИЕ ---
        # Делаем русский язык "запасным" для белорусского
        lexicons['be'] = {**lexicons['ru'], **lexicons['be']}

        return lexicons.get(self.lang_code, lexicons['en'])

    def get(self, key: str):
        return self.lexicon.get(key, f"_{key}_")