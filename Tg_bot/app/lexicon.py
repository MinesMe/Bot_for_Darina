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

EVENT_TYPE_EMOJI = {
    "Концерт": "🎵", "Театр": "🎭", "Спорт": "🏅", "Цирк": "🎪",
    "Выставка": "🎨", "Фестиваль": "🎉",
}

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
                'choose_travel_countries': "Отлично! Твоя страна — {home_country}.\n\nТеперь выбери страны, в которые ты готов поехать ради мероприятий. Можешь добавить другие или просто нажать 'Готово'.",
                'choose_local_cities': "Понял! Раз ты остаешься в своей стране, выбери города, афишу которых ты хочешь видеть. Ты можешь выбрать из популярных ниже или найти другой город.",
                'setup_complete': "🎉 Настройка завершена! Теперь ты можешь пользоваться всеми функциями бота.",
                'main_menu_greeting': "С возвращением, {first_name}!",
                'main_menu_button_afisha': "🗓 Афиша",
                'main_menu_button_subs': "➕ Найти/добавить артиста",
                'main_menu_button_profile': "👤 Профиль",
                'main_menu_button_search': "Заглушка",
                'finish_button': "✅ Готово",
                'back_button': "⬅️ Назад",
                'settings_intro': "Здесь ты можешь изменить свои настройки. Выбери страну проживания:",
                'no_regions_selected_alert': "Нужно выбрать хотя бы один регион!",
                'no_countries_selected_alert': "Нужно выбрать хотя бы одну страну!",
                'search_city_prompt': "Введите название города, который вы ищете:",
                'city_not_found': "😔 К сожалению, я не нашел такой город. Попробуйте ввести название еще раз.",
                'city_found_prompt': "Вот что я нашел. Выберите нужный город:",
                'profile_menu_header': "👤 Ваш Профиль",
                'profile_button_location': "📍 Изменить локацию",
                'profile_button_subs': "⭐ Мои подписки",
                'afisha_prompt_no_main_settings_v2': "Вы еще не настраивали свои основные предпочтения.\nХотите сделать это сейчас (настройки сохранятся) или указать параметры только для этого просмотра афиши?",
                'afisha_btn_setup_main_prefs': "🛠️ Настроить и сохранить",         # Текст для кнопки
                'afisha_btn_setup_temp_prefs': "➡️ Настроить для этого раза",    # Текст для кнопки
                
                'afisha_prompt_with_main_settings_v2': "Хотите посмотреть афишу по вашим сохраненным настройкам или указать другие параметры для этого раза?",
                'afisha_btn_use_my_settings': "✅ По моим настройкам",        # Текст для кнопки
                'afisha_btn_setup_other_temp': "⚙️ Указать другие",           # Текст для кнопки (ведет на тот же afisha_start_temp_setup_flow)

                'afisha_error_country_needed_for_main_setup_v2': "Для сохранения основных настроек ваша страна проживания должна быть уже задана. Пожалуйста, пройдите основной онбординг (команда /start) или настройте ваш профиль.",
                'afisha_error_country_not_set_v2': "Не удалось определить вашу страну. Пожалуйста, убедитесь, что вы прошли первоначальную настройку или указали страну в профиле.",
                
                'afisha_select_city_prompt_v2': "🌍 Страна: {country_name}.\nТеперь выберите город для афиши:",
                'error_state_lost_country_v2': "Ошибка сессии: информация о стране потеряна. Пожалуйста, начните процесс выбора афиши заново.",
                
                'afisha_city_selected_ask_types_v2': "🏙️ Город: {city_name}.\nТеперь выберите интересующие типы событий:",
                'afisha_alert_no_types_selected_v2': "Пожалуйста, выберите хотя бы один тип событий!",
                'afisha_alert_no_city_selected_critical_v2': "Критическая ошибка: город не был выбран! Пожалуйста, начните процесс заново.",

                'afisha_header_main_settings_saved_v2': "👍 Основные настройки для г. {city_name} сохранены! Вот афиша:",
                'afisha_error_main_save_no_country_critical_v2': "Критическая ошибка: страна для сохранения основных настроек не найдена! Настройки не были сохранены.",
                'afisha_header_temp_choice_v2': "⏳ Афиша для г. {city_name} по вашему временному выбору:",

                'afisha_loading_category_city_v2': "Загружаю «{category_name}» в г. {city_name}...",
                'afisha_no_events_for_category_city_v2': "😔 К сожалению, в г. {city_name} по категории «{category_name}» ничего не найдено.",
                
                'afisha_no_types_info_v2': "Типы событий не выбраны. Афиша не будет показана по категориям.", # Если бы был пропуск типов
                
                'afisha_error_incomplete_main_settings_v2': "Ваши основные настройки (город и/или типы событий) неполные или отсутствуют. Пожалуйста, настройте их через Профиль (команда /settings) или пройдите начальную настройку (/start), или выберите опцию для временной настройки афиши.",
                'afisha_error_no_types_in_main_settings_for_city_v2': "В ваших сохраненных настройках не указаны предпочитаемые типы событий для города {city_name}.",
                'afisha_header_by_main_settings_v2': "🗓️ Афиша по вашим сохраненным настройкам для г. {city_name}:",
                 'afisha_choose_period_prompt': "На какой период ищем события?",
                'afisha_choose_month_prompt': "Выберите интересующий вас месяц:",
                'afisha_choose_filter_type_prompt': "Отлично! Ищем с {date_from} по {date_to}.\n\nКак будем фильтровать?",
                'afisha_filter_by_my_prefs_button': "По моим предпочтениям",
                'afisha_filter_by_temporary_button': "Выбрать локацию и категории",
                'back_to_date_choice_button': "⬅️ К выбору периода",
                # Кнопки для клавиатуры выбора периода
                'period_today': "Сегодня",
                'period_tomorrow': "Завтра",
                'period_this_week': "На этой неделе",
                'period_this_weekend': "На выходных",
                'period_this_month': "На этот месяц",
                'period_other_month': "🗓 Выбрать другой месяц",

                'search_prompt_enter_query_v2': "Введите название события или имя артиста для поиска:",
                'search_searching_for_query_v2': "🔎 Ищу события: «{query_text}»...",
                'search_no_results_found_v2': "😔 По вашему запросу «{query_text}» ничего не найдено. Попробуйте другой запрос.",

                'main_menu_button_favorites': "⭐ Избранное",
                'favorites_menu_header_empty': "У вас пока нет избранных артистов или событий. Давайте добавим первого?",
                'favorites_menu_header': "Ваше избранное:\n{favorites_list}",
                'favorites_add_button': "➕ Добавить в избранное",
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
                'favorite_edit_regions_button': "✏️ Изменить регионы отслеживания",
                'favorite_edit_regions_prompt': "Измените регионы отслеживания для: {artist_name}",
                'favorite_regions_updated_alert': "✅ Регионы для избранного обновлены!",

                'afisha_add_to_subs_button': "➕ Добавить в подписки",
                'subs_enter_numbers_prompt': "Введите номера событий, которые хотите отслеживать, через запятую или пробел (например: 1, 3, 5).",
                'subs_invalid_numbers_error': "⚠️ Ошибка: номера {invalid_list} некорректны. Пожалуйста, вводите только те номера, что видите в списке.",
                'subs_added_success': "✅ Успешно добавлено в подписки: {count} шт.",
                'subs_no_valid_numbers_provided': "Вы не ввели ни одного корректного номера.",
                'subs_nan_error': "Пожалуйста, вводите только числа.",
                'subs_add_from_afisha_offer': "Вы можете добавить эти события в свои подписки.", # Текст перед кнопкой
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
                'subs_removed_alert': "Вы отписались от этого события.",
                'subs_not_found_alert': "Ошибка: подписка не найдена.",
                'back_to_subscriptions_list_button': "⬅️ К списку подписок",
                'back_to_profile_button': "⬅️ Назад ",

                'subs_reminder_header': "🔔 **Напоминание о ваших подписках:**",

                
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
                'welcome': "👋 Hi, {first_name}!\n\nI'm your guide to the world of events. I'll help you find interesting concerts, plays, and much more.\n\nLet's get set up. First, choose your home country:",
                'choose_travel_countries': "Great! Your home country is {home_country}.\n\nNow, choose the countries you're willing to travel to for events. You can add more or just click 'Done'.",
                'choose_local_cities': "Got it! Since you're staying in your home country, please select the cities whose events you want to see. You can choose from the popular ones below or find another city.",
                'setup_complete': "🎉 Setup complete! You can now use all the bot's features.",
                'main_menu_greeting': "Welcome back, {first_name}!",
                'main_menu_button_afisha': "🗓 Events",
                'main_menu_button_subs': "➕ Find/Add Artist",
                'main_menu_button_profile': "👤 Profile",
                'main_menu_button_search': "Placeholder",
                'finish_button': "✅ Done",
                'back_button': "⬅️ Back",
                'settings_intro': "Here you can change your settings. Choose your home country:",
                'no_regions_selected_alert': "You must select at least one region!",
                'no_countries_selected_alert': "You must select at least one country!",
                'search_city_prompt': "Enter the name of the city you are looking for:",
                'city_not_found': "😔 Unfortunately, I couldn't find that city. Please try entering the name again.",
                'city_found_prompt': "Here's what I found. Please select the correct city:",
                'profile_menu_header': "👤 Your Profile",
                'profile_button_location': "📍 Change Main Geo",
                'profile_button_subs': "⭐ My Subscriptions",
                'afisha_prompt_no_main_settings_v2': "You haven't set up your main preferences yet.\nWould you like to do it now (settings will be saved) or specify parameters just for this one time?",
                'afisha_btn_setup_main_prefs': "🛠️ Setup and Save",
                'afisha_btn_setup_temp_prefs': "➡️ Setup for this time",
                
                'afisha_prompt_with_main_settings_v2': "Would you like to see events based on your saved preferences, or specify other parameters for this time?",
                'afisha_btn_use_my_settings': "✅ By my preferences",
                'afisha_btn_setup_other_temp': "⚙️ Specify others",

                'afisha_error_country_needed_for_main_setup_v2': "To save your main preferences, your home country must be set. Please complete the main onboarding (/start) or set it up in your profile.",
                'afisha_error_country_not_set_v2': "Couldn't determine your country. Please make sure you've completed the initial setup or specified a country in your profile.",
                
                'afisha_select_city_prompt_v2': "🌍 Country: {country_name}.\nNow, choose a city for the events list:",
                'error_state_lost_country_v2': "Session error: country information was lost. Please start the process again.",
                
                'afisha_city_selected_ask_types_v2': "🏙️ City: {city_name}.\nNow, select the event types you are interested in:",
                'afisha_alert_no_types_selected_v2': "Please select at least one event type!",
                'afisha_alert_no_city_selected_critical_v2': "Critical error: no city was selected! Please start over.",

                'afisha_header_main_settings_saved_v2': "👍 Main preferences for {city_name} have been saved! Here are the events:",
                'afisha_error_main_save_no_country_critical_v2': "Critical error: country for saving main preferences not found! Settings were not saved.",
                'afisha_header_temp_choice_v2': "⏳ Events for {city_name} based on your temporary choice:",

                'afisha_loading_category_city_v2': "Loading '{category_name}' in {city_name}...",
                'afisha_no_events_for_category_city_v2': "😔 Unfortunately, nothing was found in {city_name} for the '{category_name}' category.",
                
                'afisha_no_types_info_v2': "Event types were not selected. The events list will not be shown by category.",
                
                'afisha_error_incomplete_main_settings_v2': "Your main preferences (city and/or event types) are incomplete or missing. Please set them up via Profile (/settings), complete the initial setup (/start), or choose the option for a temporary setup.",
                'afisha_error_no_types_in_main_settings_for_city_v2': "Your saved preferences do not specify preferred event types for {city_name}.",
                'afisha_header_by_main_settings_v2': "🗓️ Events list for {city_name} based on your saved preferences:",
                'afisha_choose_period_prompt': "For what period are we looking for events?",
                'afisha_choose_month_prompt': "Please select a month:",
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
                'search_searching_for_query_v2': "🔎 Searching for: '{query_text}'...",
                'search_no_results_found_v2': "😔 Nothing was found for your query '{query_text}'. Please try another query.",

                'main_menu_button_favorites': "⭐ Favorites",
                'favorites_menu_header_empty': "You have no favorites yet. Let's add the first one?",
                'favorites_menu_header': "Your Favorites:\n{favorites_list}",
                'favorites_add_button': "➕ Add to Favorites",
                'favorites_list_prompt': "Your Favorites. Click on an artist/event to manage it:",
                'favorite_artist_menu_prompt': "Manage favorite: {artist_name}",
                'favorites_remove_button': "🗑️ Remove from Favorites",
                'favorites_enter_name_prompt': "Enter the name of the artist, band, or festival you want to track:",
                'favorites_not_found': "Unfortunately, nothing was found for your query. Please try again or go back.",
                'favorites_found_prompt': "Here's what I found. Please select the correct one:",
                'favorites_added_alert': "✅ Added to favorites!",
                'favorites_remove_prompt': "Click on the artist/event you want to remove from your favorites:",
                'favorites_removed_alert': "🗑️ Removed from favorites.",
                'favorites_remove_empty_alert': "You have nothing in your favorites to remove.",
                'back_to_favorites_menu_button': "⬅️ Back to Favorites Menu",
                'back_to_favorites_list_button': "⬅️ Back to Favorites List",
                'favorites_added_final': "✅ Done! Added to favorites: {count} item(s).",
                'favorite_edit_regions_button': "✏️ Edit Tracking Regions",
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
                'subs_removed_alert': "You have unsubscribed from this event.",
                'subs_not_found_alert': "Error: subscription not found.",
                'back_to_subscriptions_list_button': "⬅️ Back to subscriptions",
                'back_to_profile_button': "⬅️ Back",

                'subs_reminder_header': "🔔 **Reminder of your subscriptions:**",
            }
        }
        # --- ВАЖНОЕ ИСПРАВЛЕНИЕ ---
        # Делаем русский язык "запасным" для белорусского
        lexicons['be'] = {**lexicons['ru'], **lexicons['be']}

        return lexicons.get(self.lang_code, lexicons['en'])

    def get(self, key: str):
        return self.lexicon.get(key, f"_{key}_")