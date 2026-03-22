from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoService:
    def __init__(self, url: str, database: str):
        self._client = AsyncIOMotorClient(url)
        self._db: AsyncIOMotorDatabase = self._client[database]

    async def create_indexes(self):
        audio = self._db["audio_files"]
        await audio.create_index("blob_name", unique=True)
        await audio.create_index("last_accessed")
        await audio.create_index("session_id")
        await audio.create_index("created_at")

        sheets = self._db["sheet_music"]
        await sheets.create_index("audio_file_id")
        await sheets.create_index("session_id")
        await sheets.create_index("created_at")

        sessions = self._db["sessions"]
        await sessions.create_index("session_token", unique=True)
        await sessions.create_index("last_active")

    async def close(self):
        self._client.close()

    # ── audio_files ────────────────────────────────────────────────────────

    async def insert_audio_file(self, doc: dict) -> str:
        result = await self._db["audio_files"].insert_one(doc)
        return str(result.inserted_id)

    async def get_audio_file_by_blob_name(self, blob_name: str) -> Optional[dict]:
        return await self._db["audio_files"].find_one({"blob_name": blob_name})

    async def update_last_accessed(self, blob_name: str):
        await self._db["audio_files"].update_one(
            {"blob_name": blob_name},
            {"$set": {"last_accessed": datetime.utcnow()}},
        )

    async def update_processing_status(self, blob_name: str, status: str, error: Optional[str] = None):
        update = {"$set": {"processing_status": status}}
        if error:
            update["$set"]["processing_error"] = error
        await self._db["audio_files"].update_one({"blob_name": blob_name}, update)

    async def get_total_storage_bytes(self) -> int:
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$file_size_bytes"}}}]
        async for doc in self._db["audio_files"].aggregate(pipeline):
            return doc.get("total", 0)
        return 0

    async def get_lru_candidates(self, limit: int, min_age_hours: int) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=min_age_hours)
        cursor = (
            self._db["audio_files"]
            .find({"created_at": {"$lt": cutoff}})
            .sort("last_accessed", 1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_ttl_expired(self, ttl_hours: int, min_age_hours: int) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        age_cutoff = datetime.utcnow() - timedelta(hours=min_age_hours)
        cursor = (
            self._db["audio_files"]
            .find({"last_accessed": {"$lt": cutoff}, "created_at": {"$lt": age_cutoff}})
            .sort("last_accessed", 1)
        )
        return await cursor.to_list(length=None)

    async def delete_audio_file_record(self, blob_name: str):
        await self._db["audio_files"].delete_one({"blob_name": blob_name})

    async def list_audio_files(self, session_id: Optional[str], limit: int, offset: int) -> list[dict]:
        query = {"session_id": session_id} if session_id else {}
        cursor = (
            self._db["audio_files"]
            .find(query)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    # ── sheet_music ────────────────────────────────────────────────────────

    async def insert_sheet_music(self, doc: dict) -> str:
        result = await self._db["sheet_music"].insert_one(doc)
        return str(result.inserted_id)

    async def get_sheet_by_id(self, sheet_id: str) -> Optional[dict]:
        try:
            oid = ObjectId(sheet_id)
        except Exception:
            return None
        doc = await self._db["sheet_music"].find_one({"_id": oid})
        if doc:
            await self._db["sheet_music"].update_one(
                {"_id": oid}, {"$set": {"last_accessed": datetime.utcnow()}}
            )
        return doc

    async def list_sheets(self, session_id: Optional[str], fmt: Optional[str], limit: int, offset: int) -> list[dict]:
        query: dict = {}
        if session_id:
            query["session_id"] = session_id
        if fmt:
            query["format"] = fmt
        cursor = (
            self._db["sheet_music"]
            .find(query, {"content": 0})  # exclude heavy content field
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def delete_sheet(self, sheet_id: str) -> bool:
        try:
            oid = ObjectId(sheet_id)
        except Exception:
            return False
        result = await self._db["sheet_music"].delete_one({"_id": oid})
        return result.deleted_count > 0

    # ── sessions ───────────────────────────────────────────────────────────

    async def create_session(self, token: str) -> str:
        now = datetime.utcnow()
        result = await self._db["sessions"].insert_one({
            "session_token": token,
            "created_at": now,
            "last_active": now,
            "audio_file_ids": [],
            "sheet_music_ids": [],
        })
        return str(result.inserted_id)

    async def get_session(self, token: str) -> Optional[dict]:
        return await self._db["sessions"].find_one({"session_token": token})

    async def update_session_activity(self, token: str):
        await self._db["sessions"].update_one(
            {"session_token": token},
            {"$set": {"last_active": datetime.utcnow()}},
        )

    async def add_audio_to_session(self, token: str, audio_file_id: str):
        await self._db["sessions"].update_one(
            {"session_token": token},
            {"$addToSet": {"audio_file_ids": audio_file_id}, "$set": {"last_active": datetime.utcnow()}},
        )

    async def add_sheet_to_session(self, token: str, sheet_id: str):
        await self._db["sessions"].update_one(
            {"session_token": token},
            {"$addToSet": {"sheet_music_ids": sheet_id}, "$set": {"last_active": datetime.utcnow()}},
        )
