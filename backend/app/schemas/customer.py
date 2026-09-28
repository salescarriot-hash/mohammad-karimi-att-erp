from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    customer_type: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    tax_id: str | None = None
    notes: str | None = None

    @field_validator("name", "name_en", "country", "city", "tax_id", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    name_en: str | None = None
    customer_type: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    tax_id: str | None = None
    notes: str | None = None
    status: str | None = None

class CustomerOut(CustomerBase):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class ContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    position: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: EmailStr | None = None
    notes: str | None = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    position: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: EmailStr | None = None
    notes: str | None = None
    status: str | None = None

class ContactOut(ContactBase):
    id: int
    customer_id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class SiteBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    site_code: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    notes: str | None = None

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    site_code: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    notes: str | None = None
    status: str | None = None

class SiteOut(SiteBase):
    id: int
    customer_id: int
    status: str
    model_config = ConfigDict(from_attributes=True)
