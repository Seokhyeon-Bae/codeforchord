import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient

logger = logging.getLogger(__name__)


class AzureBlobService:
    def __init__(self, connection_string: str, account_name: str, account_key: str):
        self._connection_string = connection_string
        self._account_name = account_name
        self._account_key = account_key
        self._client: Optional[AsyncBlobServiceClient] = None

    async def _get_client(self) -> AsyncBlobServiceClient:
        if self._client is None:
            self._client = AsyncBlobServiceClient.from_connection_string(self._connection_string)
        return self._client

    async def ensure_container(self, container_name: str):
        client = await self._get_client()
        container_client = client.get_container_client(container_name)
        try:
            await container_client.get_container_properties()
        except ResourceNotFoundError:
            await container_client.create_container(public_access=None)
            logger.info(f"Created private container: {container_name}")

    async def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str,
    ) -> str:
        client = await self._get_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        from azure.storage.blob import ContentSettings
        await blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    async def upload_blob_stream(
        self,
        container_name: str,
        blob_name: str,
        stream: AsyncIterator[bytes],
        content_type: str,
        length: int,
    ) -> str:
        client = await self._get_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        from azure.storage.blob import ContentSettings

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        data = b"".join(chunks)

        await blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    def generate_sas_url(self, container_name: str, blob_name: str, expiry_minutes: int = 60) -> tuple[str, datetime]:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        sas_token = generate_blob_sas(
            account_name=self._account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        url = f"https://{self._account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        return url, expiry

    async def download_blob(self, container_name: str, blob_name: str) -> bytes:
        client = await self._get_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        stream = await blob_client.download_blob()
        return await stream.readall()

    async def delete_blob(self, container_name: str, blob_name: str) -> bool:
        client = await self._get_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        try:
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            logger.warning(f"Blob not found during delete: {container_name}/{blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {container_name}/{blob_name}: {e}")
            return False

    async def get_blob_size(self, container_name: str, blob_name: str) -> Optional[int]:
        client = await self._get_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        try:
            props = await blob_client.get_blob_properties()
            return props.size
        except ResourceNotFoundError:
            return None

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
