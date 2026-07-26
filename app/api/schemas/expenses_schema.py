from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class ExpenseCategory(str, Enum):
    SUELDOS = "Sueldos"
    MEDICAMENTOS = "Medicamentos"
    ABARROTES = "Abarrotes"
    OTROS = "Otros"

class ExtractedExpense(BaseModel):
    amount: float
    currency: str
    merchant: str
    date: str
    category: ExpenseCategory = Field(..., description="Categorize based on: Transfers/People -> Sueldos; Pharmacies/Medicines -> Medicamentos; Supermarkets -> Abarrotes; Else -> Otros")
    description: str