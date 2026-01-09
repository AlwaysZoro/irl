import motor.motor_asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise e
        self.ZoroBhaiya = self._client[database_name]
        self.col = self.ZoroBhaiya.user

    def new_user(self, id):
        return dict(
            _id=int(id),
            file_id=None,
            caption=None,
            format_template=None,
            media_type=None
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            try:
                await self.col.insert_one(user)
                logger.info(f"New user added: {u.id}")
                if Config.LOG_CHANNEL:
                     await b.send_message(Config.LOG_CHANNEL, f"#New_User: {u.mention} [{u.id}] started the bot.")
            except Exception as e:
                logger.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logger.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
            logger.info(f"User deleted: {user_id}")
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")

    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one(
                {"_id": int(id)}, 
                {"$set": {"file_id": file_id}},
                upsert=True
            )
            logger.info(f"Thumbnail set for user {id}")
        except Exception as e:
            logger.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logger.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(self, id, caption):
        try:
            await self.col.update_one(
                {"_id": int(id)}, 
                {"$set": {"caption": caption}},
                upsert=True
            )
            logger.info(f"Caption set for user {id}")
        except Exception as e:
            logger.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logger.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(self, id, format_template):
        """
        CRITICAL FIX: Save format template with upsert and proper error handling
        """
        try:
            result = await self.col.update_one(
                {"_id": int(id)}, 
                {"$set": {"format_template": format_template}},
                upsert=True  # Create document if doesn't exist
            )
            logger.info(f"Format template set for user {id}: {format_template} (matched: {result.matched_count}, modified: {result.modified_count}, upserted: {result.upserted_id})")
            
            # Verify it was saved
            verify = await self.col.find_one({"_id": int(id)})
            if verify:
                saved_format = verify.get("format_template")
                if saved_format == format_template:
                    logger.info(f"Format template verified for user {id}")
                else:
                    logger.error(f"Format template mismatch for user {id}: saved={saved_format}, expected={format_template}")
            else:
                logger.error(f"User document not found after upsert for user {id}")
                
        except Exception as e:
            logger.error(f"Error setting format template for user {id}: {e}")
            raise e

    async def get_format_template(self, id):
        """
        CRITICAL FIX: Get format template with better error handling and logging
        """
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                format_template = user.get("format_template", None)
                logger.info(f"Retrieved format template for user {id}: {format_template}")
                return format_template
            else:
                logger.warning(f"No user document found for user {id}")
                return None
        except Exception as e:
            logger.error(f"Error getting format template for user {id}: {e}")
            raise e

    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, 
                {"$set": {"media_type": media_type}},
                upsert=True
            )
            logger.info(f"Media preference set for user {id}: {media_type}")
        except Exception as e:
            logger.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logger.error(f"Error getting media preference for user {id}: {e}")
            return None

ZoroBhaiya = Database(Config.DB_URL, Config.DB_NAME)
