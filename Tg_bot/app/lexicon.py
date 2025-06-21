# app/lexicon.py

LEXICON_COMMANDS_RU = {
    '/start': 'Перезапустить бота',
    '/settings': 'Открыть профиль'
}

LEXICON_COMMANDS_EN = {
    '/start': 'Restart the bot',
    '/settings': 'Open profile'
}


class Lexicon:
    def __init__(self, lang_code: str = 'en'):
        self.lang_code = lang_code if lang_code in ('ru', 'be') else 'en'
        self.lexicon = self._get_lexicon()

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

                'search_prompt_enter_query_v2': "Введите название события или имя артиста для поиска:",
                'search_searching_for_query_v2': "🔎 Ищу события: «{query_text}»...",
                'search_no_results_found_v2': "😔 По вашему запросу «{query_text}» ничего не найдено. Попробуйте другой запрос.",
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
                'choose_travel_countries': "Great! Your home country is {home_country}.\n\nNow select the countries you are willing to travel to for events. You can add more or just click 'Done'.",
                'choose_local_cities': "Got it! Since you're staying in your home country, please select the cities whose events you want to see. You can choose from the popular ones below or find another city.",
                'setup_complete': "🎉 Setup complete! You can now use all the bot's features.",
                'main_menu_greeting': "Welcome back, {first_name}!",
                'main_menu_button_afisha': "🗓 Events",
                'main_menu_button_subs': "➕ Find/Add Artist",
                'main_menu_button_profile': "👤 Profile",
                'main_menu_button_search': "Заглушка",
                'finish_button': "✅ Done",
                'back_button': "⬅️ Back",
                'settings_intro': "Here you can change your settings. Choose your home country:",
                'no_regions_selected_alert': "You must select at least one region!",
                'no_countries_selected_alert': "You must select at least one country!",
                'search_city_prompt': "Enter the name of the city you are looking for:",
                'city_not_found': "😔 Unfortunately, I couldn't find that city. Please try entering the name again.",
                'city_found_prompt': "Here's what I found. Please select the correct city:",
                'profile_menu_header': "👤 Your Profile",
                'profile_button_location': "📍 Change Location",
                'profile_button_subs': "⭐ My Subscriptions",
            }
        }
        # --- ВАЖНОЕ ИСПРАВЛЕНИЕ ---
        # Делаем русский язык "запасным" для белорусского
        lexicons['be'] = {**lexicons['ru'], **lexicons['be']}

        return lexicons.get(self.lang_code, lexicons['en'])

    def get(self, key: str):
        return self.lexicon.get(key, f"_{key}_")