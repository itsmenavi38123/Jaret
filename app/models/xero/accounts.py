from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime

class XeroAccountBase(BaseModel):
    """Base model for Xero Account"""
    Code: Optional[str] = Field(None, max_length=10, description="Customer defined alpha numeric account code")
    Name: str = Field(..., max_length=150, description="Name of account")
    Type: str = Field(..., description="Account Type - see Account Types documentation")
    Status: Optional[Literal["ACTIVE", "ARCHIVED"]] = Field("ACTIVE", description="Account status")
    Description: Optional[str] = Field(None, max_length=4000, description="Description of the Account")
    TaxType: Optional[str] = Field(None, description="Tax Type - see Tax Types documentation")
    EnablePaymentsToAccount: Optional[bool] = Field(False, description="Whether account can have payments applied to it")
    ShowInExpenseClaims: Optional[bool] = Field(False, description="Whether account code is available for use with expense claims")
    AddToWatchlist: Optional[bool] = Field(False, description="Whether this account is shown in the Xero dashboard watchlist widget")

class XeroBankAccountBase(XeroAccountBase):
    """Base model for Xero Bank Account with additional bank-specific fields"""
    BankAccountNumber: Optional[str] = Field(None, description="For bank accounts only")
    BankAccountType: Optional[str] = Field(None, description="For bank accounts only - see Bank Account types")
    CurrencyCode: Optional[str] = Field(None, description="For bank accounts only")

class XeroAccountCreate(XeroAccountBase):
    """Model for creating a new Xero Account"""
    pass

class XeroBankAccountCreate(XeroBankAccountBase):
    """Model for creating a new Xero Bank Account"""
    pass

class XeroAccountUpdate(BaseModel):
    """Model for updating an existing Xero Account"""
    AccountID: str = Field(..., description="Unique identifier for the account")
    Code: Optional[str] = Field(None, max_length=10)
    Name: Optional[str] = Field(None, max_length=150)
    Type: Optional[str] = Field(None)
    Status: Optional[Literal["ACTIVE", "ARCHIVED"]] = Field(None)
    Description: Optional[str] = Field(None, max_length=4000)
    TaxType: Optional[str] = Field(None)
    EnablePaymentsToAccount: Optional[bool] = Field(None)
    ShowInExpenseClaims: Optional[bool] = Field(None)

class XeroBankAccountUpdate(XeroAccountUpdate):
    """Model for updating an existing Xero Bank Account"""
    BankAccountNumber: Optional[str] = Field(None)
    CurrencyCode: Optional[str] = Field(None)

class XeroAccountResponse(BaseModel):
    """Response model for Xero Account"""
    AccountID: str = Field(..., description="Unique identifier for the account")
    Code: Optional[str] = Field(None, max_length=10)
    Name: str = Field(..., max_length=150)
    Type: str = Field(..., description="Account Type")
    Status: str = Field(..., description="Account status")
    Description: Optional[str] = Field(None, max_length=4000)
    TaxType: Optional[str] = Field(None)
    EnablePaymentsToAccount: bool = Field(...)
    ShowInExpenseClaims: bool = Field(...)
    BankAccountNumber: Optional[str] = Field(None)
    BankAccountType: Optional[str] = Field(None)
    CurrencyCode: Optional[str] = Field(None)
    CreatedDateUTC: Optional[datetime] = Field(None)
    UpdatedDateUTC: Optional[datetime] = Field(None)

class XeroAccountListResponse(BaseModel):
    """Response model for list of Xero Accounts"""
    Accounts: list[XeroAccountResponse]
    Status: str = Field(..., description="Response status")

class XeroAccountArchiveRequest(BaseModel):
    """Request model for archiving a Xero Account"""
    AccountID: str = Field(..., description="Unique identifier for the account to archive")
    Status: Literal["ARCHIVED"] = Field("ARCHIVED", description="Status to set - must be ARCHIVED")

# Account Types as defined by Xero API
ACCOUNT_TYPES = [
    "BANK", "CURRENT", "CURRLIAB", "DEPRECIATN", "DIRECTCOSTS", "EQUITY",
    "EXPENSE", "FIXED", "INVENTORY", "LIABILITY", "NONCURRENT", "OTHERINCOME",
    "OVERHEADS", "PREPAYMENT", "REVENUE", "SALES", "TERMLIAB", "PAYGLIABILITY",
    "SUPERANNUATION", "WAGES", "WAGESPAYABLELIABILITY", "PAYG", "SUPERLIABILITY",
    "WAGESPAYABLE", "CISASSET", "CISLIABILITY"
]

# Bank Account Types
BANK_ACCOUNT_TYPES = [
    "BANK", "CREDITCARD", "PAYPAL", "OTHER"
]

# Common Tax Types (Australian examples - adjust based on your region)
TAX_TYPES = [
    "NONE", "EXEMPTOUTPUT", "INPUT", "OUTPUT", "EXEMPTINPUT", "EXEMPTEXPENSES",
    "EXEMPTCAPITAL", "EXEMPTEXPORT", "CAPITALEXINPUT", "GSTONCAPITAL", "OUTPUT2",
    "INPUT2", "CAPITALEXOUTPUT", "NOEXPENSE", "NOTAX", "EXEMPTINPUT2", "EXEMPTOUTPUT2"
]