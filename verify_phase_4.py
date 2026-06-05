import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# Mock environment variables for config loading
os.environ["BOT_TOKEN"] = "123456789:AABBCCDDEEFFgg"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "verify_phase_4_db"
os.environ["ADMIN_ID"] = "999999"

# Add 'bot' directory to path to resolve imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'bot')))

import database.db as db_module

# ── Mock MongoDB Client ──────────────────────────────────────────────────────

class MockCursor:
    def __init__(self, results):
        self.results = results

    def skip(self, n):
        self.results = self.results[n:]
        return self

    def limit(self, n):
        if n is not None:
            self.results = self.results[:n]
        return self

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length):
        if length is not None:
            return self.results[:length]
        return self.results

class MockCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(doc["_id"])

    async def find_one(self, query, projection=None):
        print(f"DEBUG: find_one query={query}, collection docs count={len(self.docs)}")
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if k == "$or":
                    or_match = False
                    for q in v:
                        if all(doc.get(sub_k) == sub_v for sub_k, sub_v in q.items()):
                            or_match = True
                            break
                    if not or_match:
                        match = False
                        break
                elif isinstance(v, dict):
                    if "$in" in v:
                        if doc.get(k) not in v["$in"]:
                            match = False
                            break
                elif doc.get(k) != v:
                    print(f"Mismatch doc field {k}: doc={repr(doc.get(k))}, query={repr(v)}")
                    match = False
                    break
            if match:
                if projection:
                    return {pk: doc[pk] for pk in projection if pk in doc}
                return doc
        return None

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc:
            if "$set" in update:
                for k, v in update["$set"].items():
                    doc[k] = v

    async def delete_many(self, query):
        self.docs = []

    def find(self, query=None, projection=None):
        query = query or {}
        matched = []
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if k == "$or":
                    or_match = False
                    for q in v:
                        sub_matched = True
                        for sk, sv in q.items():
                            val = doc.get(sk)
                            if val is None:
                                sub_matched = False
                                break
                            if isinstance(sv, dict) and "$regex" in sv:
                                if not sv["$regex"].search(str(val)):
                                    sub_matched = False
                                    break
                            elif val != sv:
                                sub_matched = False
                                break
                        if sub_matched:
                            or_match = True
                            break
                    if not or_match:
                        match = False
                        break
                elif isinstance(v, dict):
                    if "$in" in v:
                        if doc.get(k) not in v["$in"]:
                            match = False
                            break
                    elif "$gte" in v or "$lte" in v:
                        val = doc.get(k)
                        if val is None:
                            match = False
                            break
                        if "$gte" in v and val < v["$gte"]:
                            match = False
                        if "$lte" in v and val > v["$lte"]:
                            match = False
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                matched.append(doc)
        return MockCursor(matched)

    async def count_documents(self, query):
        cursor = self.find(query)
        return len(cursor.results)

class MockDatabase:
    def __init__(self):
        self.users = MockCollection()
        self.subscriptions = MockCollection()
        self.courses = MockCollection()
        self.settings = MockCollection()

# ── Patch DB functions ───────────────────────────────────────────────────────

mock_db = MockDatabase()
db_module.db = mock_db

async def mock_connect_db():
    pass

async def mock_close_db():
    pass

db_module.connect_db = mock_connect_db
db_module.close_db = mock_close_db

# Now import the operations
from database import users as users_db
from database import subscriptions as subs_db
from database import courses as courses_db
from utils import invite as invite_utils
from handlers import admin as admin_handlers

# ── Mock aiogram context ─────────────────────────────────────────────────────

class MockBot:
    def __init__(self):
        self.sent_messages = []
        self.created_links = []
        self.revoked_links = []

    async def create_chat_invite_link(self, chat_id, member_limit, expire_date):
        class InviteLink:
            invite_link = f"https://t.me/joinchat/mock_link_{chat_id}"
        self.created_links.append((chat_id, member_limit, expire_date))
        return InviteLink()

    async def revoke_chat_invite_link(self, chat_id, invite_link):
        self.revoked_links.append((chat_id, invite_link))

    async def send_message(self, chat_id, text, **kwargs):
        self.sent_messages.append((chat_id, text))

class MockMessage:
    def __init__(self):
        self.text = None
        self.reply_markup = None

    async def edit_text(self, text, reply_markup=None, **kwargs):
        self.text = text
        self.reply_markup = reply_markup
        return self

class MockCallbackQuery:
    def __init__(self, data, from_user_id):
        self.data = data
        class FromUser:
            id = from_user_id
            username = "test_username"
            first_name = "Test"
            last_name = "User"
            @property
            def full_name(self):
                return "Test User"
        self.from_user = FromUser()
        self.message = MockMessage()
        self.bot = MockBot()
        self.answered = False
        self.answer_text = None
        self.answer_alert = False

    async def answer(self, text=None, show_alert=False, **kwargs):
        self.answered = True
        self.answer_text = text
        self.answer_alert = show_alert

# ── Run verification ─────────────────────────────────────────────────────────

async def run_verification():
    print("🚀 Starting Phase 4 Verification...")

    # Initialize settings and default data
    mock_db.settings.docs = [{
        "_id": "global_settings",
        "admin_id": 999999,
        "warning_hours": [48, 12],
        "invite_link_expiry_hours": 2
    }]

    # Create dummy course and user
    course_id = ObjectId()
    mock_db.courses.docs = [{
        "_id": course_id,
        "name": "Maths Pro",
        "channel_id": -100123456,
        "price": 499,
        "duration_days": 30,
        "is_active": True
    }]

    user_id = 777777
    mock_db.users.docs = [{
        "_id": user_id,
        "name": "Adnan",
        "username": "adnan_user",
        "registered_at": datetime.now(timezone.utc)
    }]

    # 1. Test invite utils: create_one_time_link
    print("🧪 Testing utils/invite.py...")
    bot_mock = MockBot()
    link = await invite_utils.create_one_time_link(bot_mock, -100123456, 2)
    assert link == "https://t.me/joinchat/mock_link_-100123456"
    assert len(bot_mock.created_links) == 1
    assert bot_mock.created_links[0][0] == -100123456
    assert bot_mock.created_links[0][1] == 1 # member limit is 1

    await invite_utils.revoke_link(bot_mock, -100123456, link)
    assert len(bot_mock.revoked_links) == 1
    assert bot_mock.revoked_links[0] == (-100123456, link)
    print("  - Invite utils: PASS")

    # 2. Test cb_give_select_course (list active courses)
    print("🧪 Testing cb_give_select_course (Step 1: list courses)...")
    callback = MockCallbackQuery(data=f"give_{user_id}", from_user_id=999999)
    await admin_handlers.cb_give_select_course(callback)
    
    assert callback.answered is True
    assert "Give Access — Select Course" in callback.message.text
    assert callback.message.reply_markup is not None
    # Verify the buttons
    buttons = callback.message.reply_markup.inline_keyboard
    assert len(buttons) == 2 # 1 course button + 1 back button
    assert buttons[0][0].callback_data == f"give_{user_id}:{course_id}"
    print("  - Course listing: PASS")

    # 3. Test cb_give_select_course (Step 2: confirmation screen)
    print("🧪 Testing cb_give_select_course (Step 2: confirmation screen)...")
    callback = MockCallbackQuery(data=f"give_{user_id}:{course_id}", from_user_id=999999)
    await admin_handlers.cb_give_select_course(callback)

    assert callback.answered is True
    assert "Confirm Grant Access" in callback.message.text
    assert "Maths Pro" in callback.message.text
    assert "₹499" in callback.message.text
    assert "New Subscription" in callback.message.text
    assert callback.message.reply_markup is not None
    
    buttons = callback.message.reply_markup.inline_keyboard
    assert len(buttons) == 1
    assert buttons[0][0].callback_data == f"confirm_give_{user_id}:{course_id}"
    assert buttons[0][1].callback_data == f"give_{user_id}"
    print("  - Confirmation screen: PASS")

    # 4. Test cb_confirm_give (Step 3: confirm and grant)
    print("🧪 Testing cb_confirm_give...")
    callback = MockCallbackQuery(data=f"confirm_give_{user_id}:{course_id}", from_user_id=999999)
    await admin_handlers.cb_confirm_give(callback)

    assert callback.answered is True
    assert "Access Granted Successfully!" in callback.message.text
    
    # Check that bot sent invite link message to user
    bot_ref = callback.bot
    assert len(bot_ref.sent_messages) == 1
    assert bot_ref.sent_messages[0][0] == user_id
    assert "https://t.me/joinchat/mock_link_-100123456" in bot_ref.sent_messages[0][1]

    # Check database status
    sub = await mock_db.subscriptions.find_one({"user_id": user_id, "course_id": course_id})
    assert sub is not None
    assert sub["status"] == "pending_join"
    assert sub["is_renewal"] is False
    assert sub["amount_paid"] == 499
    assert sub["invite_link"] == "https://t.me/joinchat/mock_link_-100123456"
    print("  - Access grant callback logic: PASS")

    # 5. Test check warning duplicate active subscriptions
    print("🧪 Testing warning on duplicate active subscriptions...")
    # Mark user's subscription as active
    sub["status"] = "active"
    
    callback = MockCallbackQuery(data=f"give_{user_id}:{course_id}", from_user_id=999999)
    await admin_handlers.cb_give_select_course(callback)
    
    print(f"DEBUG: callback.message.text={repr(callback.message.text)}")
    assert "already has an active subscription" in callback.message.text
    assert "Renewal" in callback.message.text # check_is_renewal should return True now
    print("  - Duplicate warning logic: PASS")

    print("✅ Phase 4 Verification PASSED! 🎉")

if __name__ == "__main__":
    asyncio.run(run_verification())
