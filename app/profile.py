"""Profile domain object.

A `Profile` is the in-memory representation of one [Profile_N] section in
the firmware's Profiles.ini. Values are stored as raw strings (the INI form)
so that callers don't have to remember which keys are int / float / combo
when reading or writing — the FIELDS schema in `config.py` is the authority
on parsing/validation when needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Profile:
    """One Profile_N section's data, keyed by FIELDS key."""

    profile_id: int  # 1 through 5
    values: dict[str, str] = field(default_factory=dict)

    @property
    def section_name(self) -> str:
        return f"Profile_{self.profile_id}"

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def set(self, key: str, value: object) -> None:
        self.values[key] = str(value).strip()
