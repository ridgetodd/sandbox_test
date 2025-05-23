from pydantic import BaseModel, Field
from typing import List, Optional


class LegalDocumentCheck(BaseModel):
    valid_document: bool = Field(description="Is the document received a legal document")
    confidence_level: float = Field(description="Confidence level between 0 and 1")


class LegalParty(BaseModel):
    name: str = Field(description="Name of party in the legal document")
    role: str = Field(description="Role/designation of the party (e.g. employer, contractor)")
    contact_info: Optional[str] = Field(description="Contact information if available")


class LegalSummaryData(BaseModel):
    document_type: str = Field(description="Type of legal document (e.g. contract, NDA)")
    effective_date: str = Field(description="When the document takes effect")
    expiration_date: Optional[str] = Field(description="When the document expires, if applicable")
    parties: List[LegalParty] = Field(description="Key parties involved in the document")
    key_terms: List[str] = Field(description="Important terms and conditions")
    obligations: List[str] = Field(description="Key obligations of involved parties")
    governing_law: Optional[str] = Field(description="Jurisdiction/governing law if specified")
