from pydantic import BaseModel, Field


class OfferID(BaseModel):
    value: str | None

    def __new__(cls, value: str):
        return value


class Context(BaseModel):
    value: str | None

    def __new__(cls, value: str):
        return value


class Token(BaseModel):
    value: str | None

    def __new__(cls, value: str):
        return value


class Region(BaseModel):
    id: int = Field(ge=1, le=25)
    name: str = None
    count: int = None
    url: str = None


class City(BaseModel):
    id: int = Field(ge=1)
    name: str = None


class Category(BaseModel):
    id: int = Field(ge=1)
    count: int | None = None
    name: str | None = None

    def __init__(self, id: int, name: str | None, count: int | None):
        super().__init__(id=id, name=name, count=count)

    def __repr__(self):
        return f"Category(id={self.id}, name={self.name}, count={self.count})"

    def __str__(self):
        return f"Category={self.id}, {self.name}, {self.count}"


class Limit(BaseModel):
    value: int = Field(ge=1, le=50)

    def __init__(self, value: int):
        super().__init__(value=value)

    def __repr__(self):
        return f"Limit({self.value})"

    def __str__(self):
        return str(self.value)


class Offset(BaseModel):
    value: int = Field(ge=0, le=1000)

    def __init__(self, value: int):
        super().__init__(value=value)

    def __repr__(self):
        return f"Offset({self.value})"

    def __str__(self):
        return str(self.value)


class OffersMeta(BaseModel):
    total: int
    visible_total: int
    regions: list[Region]

    def __init__(self, total, visible_total, regions):
        super().__init__(total=total, visible_total=visible_total, regions=regions)


class Offer(BaseModel):
    id: int | None = None
    title: str | None = None
    url: str | None = None
    posted_date: str | None = None
    seller_name: str | None = None
    phone_number: str | None = None
    price_usd: float | None = None
    price_uah: float | None = None
    price_str: str | None = None
    seller_city: str | None = None
    description: str | None = None
