"""Small production formatter: event metadata and stack locations, never payloads."""
import json
import logging
from pathlib import Path
import traceback


class SafeProductionFormatter(logging.Formatter):
    def format(self, record):
        event = {
            "time": self.formatTime(record), "level": record.levelname,
            "logger": record.name,
            "source": f"{record.module}:{record.lineno}",
        }
        status = getattr(record, "status_code", None)
        if isinstance(status, int):
            event["status"] = status
        if record.exc_info and record.exc_info[0]:
            event["exception"] = record.exc_info[0].__name__
            cause = record.exc_info[1].__cause__
            sqlstate = getattr(cause, "sqlstate", None)
            if isinstance(sqlstate, str) and len(sqlstate) == 5 and sqlstate.isalnum():
                event["sqlstate"] = sqlstate
            event["stack"] = [
                f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                for frame in traceback.extract_tb(record.exc_info[2])
            ]
        # Messages, exception messages, source lines, locals, request objects,
        # cookies, URLs/query strings and SQL may contain credentials or finances.
        return json.dumps(event, ensure_ascii=True)
