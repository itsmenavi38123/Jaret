from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class XeroAccountBase(BaseModel):
    Code: Optional[str] = Field(None, max_length=10)
    Name: str = Field(..., max_length=150)
    Type: str = Field(..., description="Account type")
    Status: Optional[Literal["ACTIVE", "ARCHIVED"]] = "ACTIVE"
    Description: Optional[str] = Field(None, max_length=4000)
    TaxType: Optional[str] = None
    EnablePaymentsToAccount: Optional[bool] = False
    ShowInExpenseClaims: Optional[bool] = False
    AddToWatchlist: Optional[bool] = False


class XeroBankAccountBase(XeroAccountBase):
    BankAccountNumber: Optional[str] = None
    BankAccountType: Optional[str] = None
    CurrencyCode: Optional[str] = None


class XeroAccountCreate(XeroAccountBase):
    pass


class XeroBankAccountCreate(XeroBankAccountBase):
    Type: Literal["BANK"] = "BANK"


class XeroAccountUpdate(BaseModel):
    AccountID: str
    Code: Optional[str] = Field(None, max_length=10)
    Name: Optional[str] = Field(None, max_length=150)
    Type: Optional[str] = None
    Status: Optional[Literal["ACTIVE", "ARCHIVED"]] = None
    Description: Optional[str] = Field(None, max_length=4000)
    TaxType: Optional[str] = None
    EnablePaymentsToAccount: Optional[bool] = None
    ShowInExpenseClaims: Optional[bool] = None


class XeroBankAccountUpdate(XeroAccountUpdate):
    BankAccountNumber: Optional[str] = None
    CurrencyCode: Optional[str] = None


class XeroAccountArchiveRequest(BaseModel):
    AccountID: str
    Status: Literal["ARCHIVED"] = "ARCHIVED"


class XeroAccountResponse(BaseModel):
    AccountID: str
    Code: Optional[str] = None
    Name: str
    Type: str
    Status: str
    Description: Optional[str] = None
    TaxType: Optional[str] = None
    EnablePaymentsToAccount: Optional[bool] = None
    ShowInExpenseClaims: Optional[bool] = None
    BankAccountNumber: Optional[str] = None
    BankAccountType: Optional[str] = None
    CurrencyCode: Optional[str] = None
    CreatedDateUTC: Optional[datetime] = None
    UpdatedDateUTC: Optional[datetime] = None


ACCOUNT_TYPES = [
    "BANK",
    "CURRENT",
    "CURRLIAB",
    "DIRECTCOSTS",
    "EQUITY",
    "EXPENSE",
    "FIXED",
    "INVENTORY",
    "LIABILITY",
    "NONCURRENT",
    "OVERHEADS",
    "PREPAYMENT",
    "REVENUE",
    "SALES",
    "TERMLIAB",
    "PAYGLIABILITY",
    "SUPERANNUATION",
    "WAGES",
]

BANK_ACCOUNT_TYPES = ["BANK", "CREDITCARD", "PAYPAL", "OTHER"]

TAX_TYPES = [
    "NONE",
    "INPUT",
    "OUTPUT",
    "EXEMPTEXPENSES",
    "EXEMPTCAPITAL",
    "CAPITALEXINPUT",
    "GSTONCAPITAL",
]
