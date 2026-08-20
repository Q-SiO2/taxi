import pytest
from pydantic import ValidationError

from taximobile_api.domains.notifications.models import DevicePlatform, DeviceRegistrationKind
from taximobile_api.domains.notifications.schemas import DeviceRegistrationRequest


def test_device_registration_uses_only_supported_mobile_platforms() -> None:
    payload = {
        "registration_kind": DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
        "registration_id": "firebase-installation-id",
    }
    request = DeviceRegistrationRequest(platform=DevicePlatform.ANDROID, **payload)
    assert request.platform == DevicePlatform.ANDROID
    with pytest.raises(ValidationError):
        DeviceRegistrationRequest(platform="WEB", **payload)


def test_device_registration_rejects_empty_or_extra_input() -> None:
    with pytest.raises(ValidationError):
        DeviceRegistrationRequest(
            platform=DevicePlatform.IOS,
            registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
            registration_id="",
        )
    with pytest.raises(ValidationError):
        DeviceRegistrationRequest(
            platform=DevicePlatform.IOS,
            registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
            registration_id="firebase-installation-id",
            user_id="forbidden",
        )
