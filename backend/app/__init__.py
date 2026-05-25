from __future__ import annotations

import asyncio
import sys

__version__ = "0.1.0"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
