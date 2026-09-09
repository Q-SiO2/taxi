"""Generate TaxiMobile's deterministic API, migration, and permission inventory.

The report contains source contracts only. It deliberately excludes configuration,
database contents, identities, secrets, and deployment-acceptance claims. Generation
fails when the migration graph is ambiguous, an API operation identifier is reused,
or a server role is absent from the permission mapping.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
HTTP_METHODS = frozenset({"delete", "get", "head", "options", "patch", "post", "put"})


class InventoryError(RuntimeError):
    """A source contract cannot be represented unambiguously."""


@dataclass(frozen=True, slots=True)
class MigrationRecord:
    revision: str
    down_revisions: tuple[str, ...]
    path: str


def _assigned_literal(tree: ast.Module, name: str, path: Path) -> object:
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is not None:
            try:
                return ast.literal_eval(value)
            except (ValueError, TypeError) as error:
                raise InventoryError(f"{path.name}: {name} must be a literal") from error
    raise InventoryError(f"{path.name}: missing {name}")


def read_migration_records(
    migration_root: Path,
    *,
    workspace_root: Path = WORKSPACE_ROOT,
) -> tuple[MigrationRecord, ...]:
    records: list[MigrationRecord] = []
    for path in sorted(migration_root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise InventoryError(f"Cannot parse migration {path.name}: {error}") from error
        revision = _assigned_literal(tree, "revision", path)
        down_revision = _assigned_literal(tree, "down_revision", path)
        if not isinstance(revision, str) or not revision:
            raise InventoryError(f"{path.name}: revision must be a non-empty string")
        if down_revision is None:
            parents: tuple[str, ...] = ()
        elif isinstance(down_revision, str) and down_revision:
            parents = (down_revision,)
        elif isinstance(down_revision, (tuple, list)) and all(
            isinstance(parent, str) and parent for parent in down_revision
        ):
            parents = tuple(down_revision)
        else:
            raise InventoryError(
                f"{path.name}: down_revision must be null, a string, or strings"
            )
        try:
            display_path = path.resolve().relative_to(workspace_root.resolve()).as_posix()
        except ValueError:
            display_path = path.name
        records.append(MigrationRecord(revision, parents, display_path))
    return validate_migration_graph(records)


def validate_migration_graph(
    records: Iterable[MigrationRecord],
) -> tuple[MigrationRecord, ...]:
    ordered = tuple(sorted(records, key=lambda record: record.revision))
    if not ordered:
        raise InventoryError("No migrations found")
    by_revision: dict[str, MigrationRecord] = {}
    for record in ordered:
        if record.revision in by_revision:
            raise InventoryError(f"Duplicate migration revision {record.revision}")
        by_revision[record.revision] = record
    revisions = set(by_revision)
    referenced = {
        parent for record in ordered for parent in record.down_revisions
    }
    missing = sorted(referenced - revisions)
    if missing:
        raise InventoryError(f"Unknown migration parent(s): {', '.join(missing)}")
    roots = sorted(record.revision for record in ordered if not record.down_revisions)
    heads = sorted(revisions - referenced)
    if len(roots) != 1:
        raise InventoryError(f"Expected one migration root, found {len(roots)}")
    if len(heads) != 1:
        raise InventoryError(f"Expected one migration head, found {len(heads)}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(revision: str) -> None:
        if revision in visiting:
            raise InventoryError(f"Migration cycle includes {revision}")
        if revision in visited:
            return
        visiting.add(revision)
        for parent in by_revision[revision].down_revisions:
            visit(parent)
        visiting.remove(revision)
        visited.add(revision)

    for revision in sorted(revisions):
        visit(revision)
    return ordered


def migration_inventory(records: Sequence[MigrationRecord]) -> dict[str, object]:
    referenced = {parent for record in records for parent in record.down_revisions}
    heads = sorted({record.revision for record in records} - referenced)
    roots = sorted(record.revision for record in records if not record.down_revisions)
    return {
        "count": len(records),
        "heads": heads,
        "roots": roots,
        "revisions": [
            {
                "revision": record.revision,
                "down_revisions": list(record.down_revisions),
                "path": record.path,
            }
            for record in records
        ],
    }


def api_inventory(
    openapi: Mapping[str, object],
    websocket_paths: Iterable[str],
) -> dict[str, object]:
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        raise InventoryError("OpenAPI document has no path mapping")
    operations: list[dict[str, object]] = []
    operation_ids: set[str] = set()
    for path in sorted(paths):
        definition = paths[path]
        if not isinstance(path, str) or not isinstance(definition, Mapping):
            raise InventoryError("OpenAPI path entries must be mappings")
        for method in sorted(HTTP_METHODS & {str(key).lower() for key in definition}):
            operation = definition.get(method)
            if not isinstance(operation, Mapping):
                raise InventoryError(f"{method.upper()} {path} has no operation mapping")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise InventoryError(f"{method.upper()} {path} has no operationId")
            if operation_id in operation_ids:
                raise InventoryError(f"Duplicate API operationId {operation_id}")
            operation_ids.add(operation_id)
            tags = operation.get("tags", [])
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise InventoryError(f"{method.upper()} {path} has invalid tags")
            operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation_id,
                    "tags": sorted(tags),
                }
            )
    sockets = sorted(set(websocket_paths))
    if any(not isinstance(path, str) or not path.startswith("/") for path in sockets):
        raise InventoryError("WebSocket paths must be absolute path templates")
    return {
        "http_operation_count": len(operations),
        "websocket_operation_count": len(sockets),
        "http_operations": operations,
        "websocket_paths": sockets,
    }


def permission_inventory(
    all_permissions: Iterable[str],
    all_roles: Iterable[str],
    role_permissions: Mapping[str, Iterable[str]],
) -> dict[str, object]:
    permissions = sorted(set(all_permissions))
    roles = sorted(set(all_roles))
    if set(role_permissions) != set(roles):
        missing = sorted(set(roles) - set(role_permissions))
        extra = sorted(set(role_permissions) - set(roles))
        raise InventoryError(
            "Role-permission mapping mismatch: "
            f"missing={','.join(missing) or '-'} extra={','.join(extra) or '-'}"
        )
    permission_set = set(permissions)
    unknown = sorted(
        {
            permission
            for values in role_permissions.values()
            for permission in values
            if permission not in permission_set
        }
    )
    if unknown:
        raise InventoryError(f"Unknown mapped permission(s): {', '.join(unknown)}")
    rows = [
        {
            "role": role,
            "permissions": sorted(set(role_permissions[role])),
        }
        for role in roles
    ]
    return {
        "permission_count": len(permissions),
        "role_count": len(roles),
        "permissions": permissions,
        "roles": rows,
    }


def generate_inventory(root: Path = WORKSPACE_ROOT) -> dict[str, object]:
    backend_source = root / "backend" / "src"
    if str(backend_source) not in sys.path:
        sys.path.insert(0, str(backend_source))

    from starlette.routing import WebSocketRoute
    from taximobile_api.domains.administration.models import AdministrativeRoleTemplate
    from taximobile_api.domains.administration.permissions import (
        OperationsPermission,
        ROLE_PERMISSIONS,
    )
    from taximobile_api.main import create_app

    app = create_app()
    role_mapping = {
        role.value: [permission.value for permission in permissions]
        for role, permissions in ROLE_PERMISSIONS.items()
    }
    migrations = read_migration_records(
        root / "backend" / "migrations" / "versions",
        workspace_root=root,
    )
    return {
        "schema_version": 1,
        "evidence_level": "SOURCE_CONTRACT_INVENTORY",
        "deployment_accepted": False,
        "api": api_inventory(
            app.openapi(),
            (
                route.path
                for route in app.routes
                if isinstance(route, WebSocketRoute)
            ),
        ),
        "migrations": migration_inventory(migrations),
        "permissions": permission_inventory(
            (permission.value for permission in OperationsPermission),
            (role.value for role in AdministrativeRoleTemplate),
            role_mapping,
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        inventory = generate_inventory()
    except InventoryError as error:
        print(str(error), file=sys.stderr)
        return 1
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "Wrote source contract inventory with "
        f"{inventory['api']['http_operation_count']} HTTP operations, "
        f"{inventory['migrations']['count']} migrations, and "
        f"{inventory['permissions']['role_count']} roles to {arguments.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
