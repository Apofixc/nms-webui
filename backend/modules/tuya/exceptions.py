"""Кастомные исключения для модуля Tuya."""
from backend.core.exceptions import NMSError


class TuyaNotActiveError(NMSError):
    def __init__(self, message: str = "Tuya module is not active"):
        super().__init__(message=message, status_code=503, code="TUYA_NOT_ACTIVE")


class TuyaDeviceNotFoundError(NMSError):
    def __init__(self, device_id: str):
        super().__init__(
            message=f"Tuya device '{device_id}' not found",
            status_code=404,
            code="TUYA_DEVICE_NOT_FOUND",
            details={"device_id": device_id},
        )


class TuyaStorageError(NMSError):
    def __init__(self, message: str = "Tuya storage unavailable"):
        super().__init__(message=message, status_code=500, code="TUYA_STORAGE_UNAVAILABLE")


class TuyaCommandError(NMSError):
    def __init__(self, message: str = "Tuya command failed"):
        super().__init__(message=message, status_code=502, code="TUYA_COMMAND_FAILED")
