import asyncio
import logging
from dataclasses import dataclass, field

from app.models.storage import EvictionResult
from app.services.azure_blob_service import AzureBlobService
from app.services.mongo_service import MongoService

logger = logging.getLogger(__name__)


@dataclass
class EvictionConfig:
    max_storage_bytes: int
    audio_ttl_hours: int
    min_retention_hours: int
    interval_seconds: int
    batch_size: int


class LRUEvictionService:
    def __init__(
        self,
        mongo: MongoService,
        blob: AzureBlobService,
        config: EvictionConfig,
    ):
        self._mongo = mongo
        self._blob = blob
        self._config = config
        self._running = False

    async def run_forever(self):
        self._running = True
        logger.info("LRU eviction service started")
        while self._running:
            try:
                result = await self.run_cycle()
                if result.evicted_count > 0:
                    logger.info(
                        f"LRU eviction: removed {result.evicted_count} files, "
                        f"freed {result.bytes_freed / 1024 / 1024:.1f}MB"
                    )
                if result.errors:
                    for err in result.errors:
                        logger.warning(f"LRU eviction error: {err}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"LRU eviction cycle failed: {e}")

            await asyncio.sleep(self._config.interval_seconds)

        logger.info("LRU eviction service stopped")

    async def run_cycle(self) -> EvictionResult:
        evicted_count = 0
        bytes_freed = 0
        errors: list[str] = []

        # 1. Evict TTL-expired files regardless of storage level
        ttl_candidates = await self._mongo.get_ttl_expired(
            self._config.audio_ttl_hours,
            self._config.min_retention_hours,
        )
        for doc in ttl_candidates:
            blob_name = doc["blob_name"]
            container = doc["container_name"]
            size = doc.get("file_size_bytes", 0)
            try:
                await self._blob.delete_blob(container, blob_name)
                await self._mongo.delete_audio_file_record(blob_name)
                evicted_count += 1
                bytes_freed += size
            except Exception as e:
                errors.append(f"TTL eviction failed for {blob_name}: {e}")

        # 2. Evict LRU if over storage cap
        total = await self._mongo.get_total_storage_bytes()
        if total > self._config.max_storage_bytes:
            lru_candidates = await self._mongo.get_lru_candidates(
                self._config.batch_size,
                self._config.min_retention_hours,
            )
            for doc in lru_candidates:
                if total <= self._config.max_storage_bytes:
                    break
                blob_name = doc["blob_name"]
                container = doc["container_name"]
                size = doc.get("file_size_bytes", 0)
                try:
                    await self._blob.delete_blob(container, blob_name)
                    await self._mongo.delete_audio_file_record(blob_name)
                    evicted_count += 1
                    bytes_freed += size
                    total -= size
                except Exception as e:
                    errors.append(f"LRU eviction failed for {blob_name}: {e}")

        return EvictionResult(evicted_count=evicted_count, bytes_freed=bytes_freed, errors=errors)
