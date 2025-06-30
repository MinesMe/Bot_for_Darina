# app/handlers/states.py

from aiogram.fsm.state import State, StatesGroup

# --- Состояния из afisha.py ---
class AfishaFlowFSM(StatesGroup):
    choosing_date_period = State()
    choosing_month = State()
    choosing_filter_type = State()
    temp_choosing_city = State()
    temp_waiting_city_input = State()
    temp_choosing_event_types = State()

class AddToSubsFSM(StatesGroup):
    waiting_for_event_numbers = State()

# --- Состояния из subscriptions.py ---
class SubscriptionFlow(StatesGroup):
    general_mobility_onboarding = State()
    selecting_general_regions = State()
    waiting_for_action = State()
    waiting_for_artist_name = State()
    choosing_mobility_type = State()
    selecting_custom_regions = State()

class CombinedFlow(StatesGroup):
    active = State()

# Если RecommendationFlow еще используется, добавьте и его
class RecommendationFlow(StatesGroup):
   selecting_artists = State()

class FavoritesFSM(StatesGroup):
    viewing_list = State()
    viewing_artist = State()
    editing_mobility = State()
    viewing_artist_events = State()