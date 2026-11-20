"""Allow running the app with ``python -m taskmanager``."""

from .cli import main

raise SystemExit(main())
