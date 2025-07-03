#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Third-party imports
import jsonschema


def error_exit(message: str) -> None:
    """Print error message and exit with error code"""
    print(f"❌ {message}")
    sys.exit(1)


def load_schema(schema_path: Path) -> Dict:
    """Load and parse the schema file"""
    if not schema_path.exists():
        error_exit(f"Schema file not found: {schema_path}")

    try:
        with open(schema_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"Invalid schema JSON: {e}")
    except Exception as e:
        error_exit(f"Error reading schema file: {e}")


def validate_manifest(manifest_path: Path, schema: Dict) -> Tuple[bool, str]:
    """Validate a single manifest file against the schema"""
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

    try:
        jsonschema.validate(manifest, schema)
        return True, ""
    except jsonschema.exceptions.ValidationError as e:
        return False, f"{e.json_path}: {e.message}"
    except jsonschema.exceptions.SchemaError as e:
        return False, f"Schema error: {e}"


def find_server_files(servers_dir: Path) -> List[Path]:
    """Find all server JSON files in the servers directory"""
    if not servers_dir.exists() or not servers_dir.is_dir():
        error_exit(f"Servers directory not found: {servers_dir}")

    server_files = []
    for file_path in servers_dir.glob("*.json"):
        if file_path.is_file():
            server_files.append(file_path)

    return server_files


def main() -> int:
    """Validate all MCP server JSON files"""
    # Determine the paths relative to this script
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    schema_path = repo_root / "mcp-registry" / "schema" / "server-schema.json"
    servers_dir = repo_root / "mcp-registry" / "servers"

    # Load the schema
    schema = load_schema(schema_path)

    # Find all server JSON files
    server_files = find_server_files(servers_dir)

    if not server_files:
        print("No server files found to validate.")
        return 0

    print(f"Found {len(server_files)} server files to validate.")

    # Validate each server file
    any_errors = False
    for server_path in server_files:
        server_name = server_path.stem
        valid, error_msg = validate_manifest(server_path, schema)

        if valid:
            print(f"✓ {server_name}: Valid")
        else:
            print(f"✗ {server_name}: Invalid")
            print(f"  - {error_msg}")
            any_errors = True

    return 1 if any_errors else 0


if __name__ == "__main__":
    sys.exit(main())
