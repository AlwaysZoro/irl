import motor.motor_asyncio
from config import Config

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users

    async def add_user(self, bot, message):
        """Add user to database"""
        user_id = message.from_user.id
        user_data = await self.users.find_one({"_id": user_id})
        
        if user_data:
            return
        
        await self.users.insert_one({
            "_id": user_id,
            "format_template": None,
            "caption": None,
            "thumbnail": None,
            "media_preference": None
        })

    async def total_users_count(self):
        """Get total users count"""
        count = await self.users.count_documents({})
        return count

    async def get_all_users(self):
        """Get all users"""
        return self.users.find({})

    async def delete_user(self, user_id):
        """Delete user from database"""
        await self.users.delete_one({"_id": user_id})

    async def set_format_template(self, user_id, format_template):
        """Set auto rename format template"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"format_template": format_template}},
            upsert=True
        )

    async def get_format_template(self, user_id):
        """Get auto rename format template"""
        user_data = await self.users.find_one({"_id": user_id})
        if user_data:
            return user_data.get("format_template")
        return None

    async def set_caption(self, user_id, caption):
        """Set custom caption"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"caption": caption}},
            upsert=True
        )

    async def get_caption(self, user_id):
        """Get custom caption"""
        user_data = await self.users.find_one({"_id": user_id})
        if user_data:
            return user_data.get("caption")
        return None

    async def set_thumbnail(self, user_id, file_id):
        """Set custom thumbnail"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"thumbnail": file_id}},
            upsert=True
        )

    async def get_thumbnail(self, user_id):
        """Get custom thumbnail"""
        user_data = await self.users.find_one({"_id": user_id})
        if user_data:
            return user_data.get("thumbnail")
        return None

    async def set_media_preference(self, user_id, media_type):
        """Set media upload preference"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"media_preference": media_type}},
            upsert=True
        )

    async def get_media_preference(self, user_id):
        """Get media upload preference"""
        user_data = await self.users.find_one({"_id": user_id})
        if user_data:
            return user_data.get("media_preference")
        return None

# Initialize database
ZoroBhaiya = Database(Config.DB_URL, Config.DB_NAME)
