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
                'main_menu_button_subs': "⭐ Мои подписки",
                'main_menu_button_profile': "👤 Профиль",
                'main_menu_button_search': "🔎 Поиск",
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
            },
            'be': {
                # Здесь только те ключи, которые отличаются от русского
                'main_menu_button_profile': "👤 Профіль",
                'main_menu_button_settings': "⚙️ Налады",
                'profile_menu_header': "👤 Ваш Профіль",
                'profile_button_location': "📍 Змяніць лакацыю",
                'profile_button_subs': "⭐ Мае падпіскі",
            },
            'en': {
                'welcome': "👋 Hi, {first_name}!\n\nI'm your guide to the world of events. I'll help you find interesting concerts, plays, and much more.\n\nLet's get set up. First, choose your home country:",
                'choose_travel_countries': "Great! Your home country is {home_country}.\n\nNow select the countries you are willing to travel to for events. You can add more or just click 'Done'.",
                'choose_local_cities': "Got it! Since you're staying in your home country, please select the cities whose events you want to see. You can choose from the popular ones below or find another city.",
                'setup_complete': "🎉 Setup complete! You can now use all the bot's features.",
                'main_menu_greeting': "Welcome back, {first_name}!",
                'main_menu_button_afisha': "🗓 Events",
                'main_menu_button_subs': "⭐ My Subscriptions",
                'main_menu_button_profile': "👤 Profile",
                'main_menu_button_search': "🔎 Search",
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