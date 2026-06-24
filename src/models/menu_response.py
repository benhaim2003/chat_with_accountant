from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MenuButton:
    label: str
    payload: str


@dataclass(frozen=True)
class MenuResponse:
    text: str
    buttons: tuple[MenuButton, ...] = field(default_factory=tuple)
