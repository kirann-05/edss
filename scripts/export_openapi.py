"""Write the API contract to backend/openapi.json.

The frontend generates its TypeScript types from this file (make types), so a change to
an API schema that the UI does not handle becomes a compile error instead of a runtime bug.
"""

import json
from pathlib import Path

from app.main import create_app

OUTPUT = Path(__file__).resolve().parent.parent / "backend" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUTPUT.relative_to(OUTPUT.parent.parent)}")


if __name__ == "__main__":
    main()
