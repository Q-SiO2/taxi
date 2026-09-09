import pytest

from taximobile_api.core.client_compatibility import (
    CLIENT_BUILD_HEADER,
    CLIENT_SURFACE_HEADER,
    CLIENT_VERSION_HEADER,
    ClientBuildIdentity,
    ClientCompatibilityPolicy,
    ClientCompatibilityStatus,
    ClientIdentityError,
    ClientSurface,
    ClientVersion,
    parse_client_identity,
)


def versions(value: str) -> tuple[tuple[str, str], ...]:
    return tuple((surface.value, value) for surface in ClientSurface)


def policy(*, minimum: str = "1.2.0", recommended: str = "1.4.0") -> ClientCompatibilityPolicy:
    return ClientCompatibilityPolicy(
        revision="pilot-2026-09",
        minimum_versions=versions(minimum),
        recommended_versions=versions(recommended),
    )


def identity(version: str) -> ClientBuildIdentity:
    return ClientBuildIdentity(
        surface=ClientSurface.ANDROID_PASSENGER,
        version=ClientVersion.parse(version),
        build=12,
    )


def test_numeric_client_versions_compare_without_lexical_errors() -> None:
    assert ClientVersion.parse("1.10.0") > ClientVersion.parse("1.9.99")
    assert ClientVersion.parse("2.0.0") > ClientVersion.parse("1.999.999")
    assert ClientVersion.parse("1.2.3.4") > ClientVersion.parse("1.2.3")
    assert str(ClientVersion.parse("1.2.3.0")) == "1.2.3"


@pytest.mark.parametrize(
    "value",
    ["", "1", "1.0", "01.0.0", "1.00.0", "1.0.0-beta", "v1.0.0", "1.0.-1"],
)
def test_client_version_parser_fails_closed(value: str) -> None:
    with pytest.raises(ClientIdentityError):
        ClientVersion.parse(value)


def test_policy_distinguishes_required_available_and_current_updates() -> None:
    active_policy = policy()

    assert active_policy.assess(identity("1.1.9")).status == ClientCompatibilityStatus.UPGRADE_REQUIRED
    assert active_policy.assess(identity("1.2.0")).status == ClientCompatibilityStatus.UPDATE_AVAILABLE
    assert active_policy.assess(identity("1.4.0")).status == ClientCompatibilityStatus.SUPPORTED
    assert active_policy.assess(identity("2.0.0")).status == ClientCompatibilityStatus.SUPPORTED


def test_policy_requires_every_surface_once_and_recommended_not_below_minimum() -> None:
    with pytest.raises(ValueError, match="every closed client surface"):
        ClientCompatibilityPolicy(
            revision="pilot-1",
            minimum_versions=((ClientSurface.ANDROID_PASSENGER.value, "1.0.0"),),
            recommended_versions=versions("1.0.0"),
        )
    with pytest.raises(ValueError, match="Recommended version cannot be below minimum"):
        policy(minimum="2.0.0", recommended="1.9.9")


def test_header_identity_is_closed_and_build_is_positive_and_bounded() -> None:
    headers = {
        CLIENT_SURFACE_HEADER.lower(): ClientSurface.IOS_DRIVER.value,
        CLIENT_VERSION_HEADER.lower(): "1.2.3",
        CLIENT_BUILD_HEADER.lower(): "42",
    }
    parsed = parse_client_identity(headers)
    assert parsed.surface == ClientSurface.IOS_DRIVER
    assert parsed.version == ClientVersion(1, 2, 3)
    assert parsed.build == 42

    for bad_headers in (
        {},
        {**headers, CLIENT_SURFACE_HEADER.lower(): "ANDROID"},
        {**headers, CLIENT_BUILD_HEADER.lower(): "0"},
        {**headers, CLIENT_BUILD_HEADER.lower(): "2147483648"},
        {**headers, CLIENT_VERSION_HEADER.lower(): "latest"},
    ):
        with pytest.raises(ClientIdentityError):
            parse_client_identity(bad_headers)
