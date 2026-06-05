"""
Finite State Machine state group definitions.
"""

from aiogram.fsm.state import State, StatesGroup


class AddCourseState(StatesGroup):
    waiting_name = State()
    waiting_photo = State()          # Optional — [⏭ Skip] available
    waiting_channel_id = State()
    waiting_price = State()
    waiting_confirm = State()


class EditCourseState(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_photo = State()


class BroadcastState(StatesGroup):
    selecting_target = State()
    waiting_message = State()
    waiting_confirm = State()


class SearchState(StatesGroup):
    waiting_query = State()


class SettingsState(StatesGroup):
    waiting_invite_expiry = State()
    waiting_warning_hours = State()
