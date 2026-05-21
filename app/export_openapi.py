"""Dump the FastAPI OpenAPI schema to stdout for CI."""

import json
import sys

from app.main import app


def main() -> None:
    schema = app.openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
