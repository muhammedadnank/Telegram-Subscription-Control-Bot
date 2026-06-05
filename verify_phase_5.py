import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# Mock environment variables for config loading
os.environ["BOT_TOKEN"] = "123456789:AABBCCDDEEFFgg"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "verify_phase_5_db"
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
from handlers import admin as admin_handlers

# ── Mock aiogram context for ChatMemberUpdated ───────────────────────────────

class MockBot:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent_messages.append((chat_id, text))

class MockChat:
    def __init__(self, id, title):
        self.id = id
        self.title = title

class MockUser:
    def __init__(self, id, username, first_name, last_name):
        self.id = id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class MockChatMember:
    def __init__(self, user):
        self.user = user

class MockChatMemberUpdated:
    def __init__(self, bot, chat, from_user, old_chat_member, new_chat_member):
        self.bot = bot
        self.chat = chat
        self.from_user = from_user
        self.old_chat_member = old_chat_member
        self.new_chat_member = new_chat_member

# ── Run verification ─────────────────────────────────────────────────────────

async def run_verification():
    print("🚀 Starting Phase 5 Verification...")

    # Initialize settings
    mock_db.settings.docs = [{
        "_id": "global_settings",
        "admin_id": 999999,
        "warning_hours": [48, 12],
        "invite_link_expiry_hours": 2
    }]

    course_id = ObjectId()
    channel_id = -100123456
    user_id = 777777

    # 1. Setup mock database records
    mock_db.courses.docs = [{
        "_id": course_id,
        "name": "Maths Pro",
        "channel_id": channel_id,
        "price": 499,
        "duration_days": 30,
        "is_active": True
    }]

    mock_db.users.docs = [{
        "_id": user_id,
        "name": "Adnan",
        "username": "adnan_user",
        "registered_at": datetime.now(timezone.utc)
    }]

    # Create pending subscription
    sub_id = await subs_db.create_subscription(
        user_id=user_id,
        course_id=str(course_id),
        invite_link="https://t.me/joinchat/mock_link",
        amount_paid=499,
        is_renewal=False
    )

    # 2. Verify get_pending_subscription
    print("🧪 Testing get_pending_subscription...")
    pending = await subs_db.get_pending_subscription(user_id, channel_id)
    assert pending is not None
    assert pending["status"] == "pending_join"
    print("  - get_pending_subscription: PASS")

    # 3. Simulate on_user_join ChatMemberUpdated event
    print("🧪 Testing on_user_join handler...")
    bot_mock = MockBot()
    chat_mock = MockChat(channel_id, "Maths Pro Channel")
    joining_user = MockUser(user_id, "adnan_user", "Adnan", "Lastname")
    
    join_event = MockChatMemberUpdated(
        bot=bot_mock,
        chat=chat_mock,
        from_user=joining_user,
        old_chat_member=MockChatMember(joining_user),
        new_chat_member=MockChatMember(joining_user)
    )

    await admin_handlers.on_user_join(join_event)

    # 4. Verify DB updates for join activation
    activated_sub = await mock_db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    assert activated_sub["status"] == "active"
    assert activated_sub["joined_at"] is not None
    assert activated_sub["expires_at"] is not None
    
    expected_expiry = activated_sub["joined_at"] + timedelta(days=30)
    # Expiry should match within 2 seconds tolerance
    assert abs((activated_sub["expires_at"] - expected_expiry).total_seconds()) < 2
    print("  - DB subscription activation: PASS")

    # 5. Verify messaging to user and admin on join
    assert len(bot_mock.sent_messages) == 2
    
    # Message to user
    assert bot_mock.sent_messages[0][0] == user_id
    assert "Welcome to Maths Pro!" in bot_mock.sent_messages[0][1]
    
    # Message to admin
    assert bot_mock.sent_messages[1][0] == 999999
    assert "User Joined Channel" in bot_mock.sent_messages[1][1]
    assert "Adnan" in bot_mock.sent_messages[1][1]
    print("  - Notification messages: PASS")

    # 6. Verify get_active_subscription_by_channel
    print("🧪 Testing get_active_subscription_by_channel...")
    active_sub = await subs_db.get_active_subscription_by_channel(user_id, channel_id)
    assert active_sub is not None
    assert active_sub["status"] == "active"
    print("  - get_active_subscription_by_channel: PASS")

    # 7. Simulate on_user_leave ChatMemberUpdated event
    print("🧪 Testing on_user_leave handler...")
    leaving_user = MockUser(user_id, "adnan_user", "Adnan", "Lastname")
    leave_event = MockChatMemberUpdated(
        bot=bot_mock,
        chat=chat_mock,
        from_user=leaving_user,
        old_chat_member=MockChatMember(leaving_user),
        new_chat_member=MockChatMember(leaving_user)
    )

    await admin_handlers.on_user_leave(leave_event)

    # 8. Verify DB update on leave
    left_sub = await mock_db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    assert left_sub["left_at"] is not None
    assert left_sub["days_used"] is not None
    print("  - DB manual leave record: PASS")

    print("✅ Phase 5 Verification PASSED! 🎉")

if __name__ == "__main__":
    asyncio.run(run_verification())
