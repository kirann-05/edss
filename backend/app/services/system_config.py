"""Runtime system settings that must be read from the store, not only from the environment.

Rule 7 says the data mode is "enforced in code and checked against the database, not only the
env file". The LLM guard therefore asks this object on every call, so flipping the mode in the
store takes effect at once with no restart. In memory for now. The Postgres version reads the
`system_config` table behind the same two methods (CHECKLIST F6).
"""

import threading
from typing import Literal

DataMode = Literal["synthetic", "real"]


class SystemConfig:
    def __init__(self, data_mode: DataMode) -> None:
        self._data_mode: DataMode = data_mode
        self._lock = threading.Lock()

    def data_mode(self) -> DataMode:
        with self._lock:
            return self._data_mode

    def set_data_mode(self, mode: DataMode) -> None:
        with self._lock:
            self._data_mode = mode
