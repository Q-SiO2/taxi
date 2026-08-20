"""Validate TaxiMobile locale catalogs and prevent new inline UI prose."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = PROJECT_ROOT / "shared" / "src" / "commonMain" / "composeResources"
CATALOGS = {
    "en": RESOURCE_ROOT / "values" / "strings.xml",
    "fr": RESOURCE_ROOT / "values-fr" / "strings.xml",
    "ar": RESOURCE_ROOT / "values-ar" / "strings.xml",
}
PRESENTATION_ROOT = (
    PROJECT_ROOT
    / "shared"
    / "src"
    / "commonMain"
    / "kotlin"
    / "org"
    / "example"
    / "taximobile"
    / "feature"
)
PRESENTATION_FILES = (
    PRESENTATION_ROOT / "app" / "TaxiMobileScreen.kt",
    PRESENTATION_ROOT / "app" / "SharedSections.kt",
    PRESENTATION_ROOT / "passenger" / "PassengerHome.kt",
    PRESENTATION_ROOT / "driver" / "DriverHome.kt",
    *(PRESENTATION_ROOT / "ui" / "components").glob("*.kt"),
)
PLACEHOLDER = re.compile(r"%(?:\d+\$)?[a-zA-Z]")
DIRECT_LITERAL_PATTERNS = {
    "Text": re.compile(r"\bText\(\s*\""),
    "TaxiButton": re.compile(r"\bTaxiButton\(\s*\""),
    "ToastBanner": re.compile(r"\bToastBanner\(\s*\""),
    "StatusPill": re.compile(r"\bStatusPill\(\s*\""),
    "accessibility description": re.compile(
        r"\b(?:contentDescription|stateDescription)\s*=\s*\""
    ),
}


def load_catalog(path: Path) -> dict[str, str]:
    root = ElementTree.parse(path).getroot()
    if root.tag != "resources":
        raise ValueError(f"{path} must have a resources root")
    result: dict[str, str] = {}
    for item in root.findall("string"):
        name = item.get("name")
        value = "".join(item.itertext()).strip()
        if not name:
            raise ValueError(f"{path} contains a string without a name")
        if name in result:
            raise ValueError(f"{path} contains duplicate key {name}")
        if not value:
            raise ValueError(f"{path} contains blank value {name}")
        result[name] = value
    return result


def validate_catalog_data(catalogs: dict[str, dict[str, str]]) -> None:
    if set(catalogs) != {"en", "fr", "ar"}:
        raise ValueError("Catalogs must contain exactly en, fr, and ar")
    reference_keys = set(catalogs["en"])
    if not reference_keys:
        raise ValueError("The English catalog must not be empty")
    for locale, entries in catalogs.items():
        keys = set(entries)
        missing = sorted(reference_keys - keys)
        extra = sorted(keys - reference_keys)
        if missing or extra:
            raise ValueError(
                f"{locale} catalog key mismatch; missing={missing}, extra={extra}"
            )
        for key, english in catalogs["en"].items():
            expected = sorted(PLACEHOLDER.findall(english))
            actual = sorted(PLACEHOLDER.findall(entries[key]))
            if actual != expected:
                raise ValueError(
                    f"{locale}:{key} placeholders {actual} do not match {expected}"
                )


def validate_no_direct_presentation_literals(paths: tuple[Path, ...] = PRESENTATION_FILES) -> None:
    violations: list[str] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for label, pattern in DIRECT_LITERAL_PATTERNS.items():
            for match in pattern.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{line} uses inline {label} text")
    if violations:
        raise ValueError("Direct user-visible literals found:\n" + "\n".join(violations))


def validate_localization() -> None:
    catalogs = {locale: load_catalog(path) for locale, path in CATALOGS.items()}
    validate_catalog_data(catalogs)
    validate_no_direct_presentation_literals()


if __name__ == "__main__":
    validate_localization()
    print(
        f"Validated {len(load_catalog(CATALOGS['en']))} TaxiMobile strings "
        "across English, French, and Arabic catalogs."
    )
