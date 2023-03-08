from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Place:
    name: str
    address: str
    business_hours: dict[str, str] = field(default_factory=lambda: {})
    photo_link: Optional[str] = None
    rate: Optional[str] = None
    reviews: Optional[str] = None
    extra_attrs: dict[str, str] = field(default_factory=lambda: {})
    traits: dict[str, list[str]] = field(default_factory=lambda: {})

    @property
    def identifier(self) -> Optional[str]:
        for attr_key, val in self.extra_attrs.items():
            if attr_key.startswith("Plus code"):
                return val

        return None

@dataclass
class GeoPlace:
    type: str = 'Point'
    coordinates: list = field(default_factory=list)
@dataclass
class ResInfo:
    name: str
    location: GeoPlace
    address: str
    href: str
    rating: float
    nums_of_review: int
    menu_list: str
