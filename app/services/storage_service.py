"""
Storage Service
MinIO/S3 파일 저장소 관리
"""

import logging
from typing import Optional
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.security import encrypt_file, decrypt_file

logger = logging.getLogger(__name__)


class StorageService:
    """
    파일 저장소 관리 서비스
    MinIO 또는 S3 사용
    """

    def __init__(self):
        self.client = Minio(
            settings.STORAGE_ENDPOINT,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            secure=settings.STORAGE_USE_SSL
        )
        self._ensure_buckets_exist()

    def _ensure_buckets_exist(self):
        """버킷이 존재하지 않으면 생성"""
        for bucket_name in [settings.STORAGE_BUCKET_PUBLIC, settings.STORAGE_BUCKET_PRIVATE]:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
            except S3Error as e:
                logger.error(f"Error creating bucket {bucket_name}: {e}")

    async def save_file(
        self,
        file_content: bytes,
        document_id: str,
        filename: str,
        is_private: bool = False,
        encrypt: bool = False
    ) -> str:
        """
        파일을 적절한 버킷에 저장

        Args:
            file_content: 파일 내용
            document_id: 문서 ID
            filename: 파일명
            is_private: 개인 문서 여부
            encrypt: 암호화 여부

        Returns:
            str: 저장 경로
        """
        try:
            # 저장할 버킷 선택
            bucket = settings.STORAGE_BUCKET_PRIVATE if is_private else settings.STORAGE_BUCKET_PUBLIC

            # 암호화 처리
            if encrypt and is_private:
                file_content = encrypt_file(file_content)
                logger.info(f"File encrypted for document {document_id}")

            # 저장 경로 생성
            object_name = f"{document_id}/{filename}"

            # MinIO에 업로드
            self.client.put_object(
                bucket,
                object_name,
                BytesIO(file_content),
                length=len(file_content),
                content_type='application/pdf'
            )

            storage_path = f"{bucket}/{object_name}"
            logger.info(f"File saved: {storage_path}")

            return storage_path

        except S3Error as e:
            logger.error(f"Error saving file: {e}")
            raise Exception(f"Failed to save file: {str(e)}")

    async def get_file(
        self,
        storage_path: str,
        is_encrypted: bool = False
    ) -> bytes:
        """
        저장소에서 파일 읽기

        Args:
            storage_path: 저장 경로 (bucket/object_name)
            is_encrypted: 암호화 여부

        Returns:
            bytes: 파일 내용
        """
        try:
            # 경로 파싱
            parts = storage_path.split('/', 1)
            if len(parts) != 2:
                raise ValueError("Invalid storage path")

            bucket, object_name = parts

            # MinIO에서 다운로드
            response = self.client.get_object(bucket, object_name)
            file_content = response.read()
            response.close()
            response.release_conn()

            # 복호화 처리
            if is_encrypted:
                file_content = decrypt_file(file_content)
                logger.info(f"File decrypted: {storage_path}")

            logger.info(f"File retrieved: {storage_path}")
            return file_content

        except S3Error as e:
            logger.error(f"Error retrieving file: {e}")
            raise Exception(f"Failed to retrieve file: {str(e)}")

    async def delete_file(self, storage_path: str):
        """
        파일 삭제

        Args:
            storage_path: 저장 경로
        """
        try:
            parts = storage_path.split('/', 1)
            if len(parts) != 2:
                raise ValueError("Invalid storage path")

            bucket, object_name = parts

            self.client.remove_object(bucket, object_name)
            logger.info(f"File deleted: {storage_path}")

        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise Exception(f"Failed to delete file: {str(e)}")

    async def file_exists(self, storage_path: str) -> bool:
        """
        파일 존재 여부 확인

        Args:
            storage_path: 저장 경로

        Returns:
            bool: 존재 여부
        """
        try:
            parts = storage_path.split('/', 1)
            if len(parts) != 2:
                return False

            bucket, object_name = parts

            self.client.stat_object(bucket, object_name)
            return True

        except S3Error:
            return False

    async def get_file_size(self, storage_path: str) -> Optional[int]:
        """
        파일 크기 조회

        Args:
            storage_path: 저장 경로

        Returns:
            Optional[int]: 파일 크기 (bytes)
        """
        try:
            parts = storage_path.split('/', 1)
            if len(parts) != 2:
                return None

            bucket, object_name = parts

            stat = self.client.stat_object(bucket, object_name)
            return stat.size

        except S3Error:
            return None
