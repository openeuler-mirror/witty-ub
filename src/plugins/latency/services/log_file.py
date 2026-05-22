from re import U

from latency.schemas.response import UploadLogFilesMsg


class LogFileService:
    @staticmethod
    async def upload_log_files(kb_id: str) -> UploadLogFilesMsg:
        return UploadLogFilesMsg(log_files_ids=[])
