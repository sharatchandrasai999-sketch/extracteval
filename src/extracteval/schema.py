"""Load a task definition (YAML) into a typed schema.

A "task" is the whole reusable unit: what fields to extract, their types, and
where the labeled data lives. Defining a new extraction problem is just writing
a YAML file — no code changes. That's what turns this from a one-off invoice
script into a general framework.
"""

from __future__ import annotations
import os
from dataclasses import dataclass

import yaml

VALID_TYPES = {"string", "number", "date", "enum"}


@dataclass
class Field:
    name: str
    type: str = "string"
    description: str = ""
    choices: list[str] | None = None  # for enum fields
    rules: list[str] | None = None    # e.g. ["required", "non_negative"]

    def __post_init__(self):
        if self.type not in VALID_TYPES:
            raise ValueError(f"Field '{self.name}': unknown type '{self.type}'. "
                             f"Use one of {sorted(VALID_TYPES)}.")
        if self.rules is None:
            self.rules = []


@dataclass
class Task:
    name: str
    description: str
    data_path: str
    fields: list[Field]

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def field(self, name: str) -> Field:
        return next(f for f in self.fields if f.name == name)


def load_task(path: str) -> Task:
    with open(path) as fh:
        raw = yaml.safe_load(fh)

    base = os.path.dirname(os.path.abspath(path))
    data_path = raw["data"]
    if not os.path.isabs(data_path):
        data_path = os.path.normpath(os.path.join(base, "..", data_path))

    fields = [Field(**f) for f in raw["fields"]]
    return Task(
        name=raw["name"],
        description=raw.get("description", ""),
        data_path=data_path,
        fields=fields,
    )
