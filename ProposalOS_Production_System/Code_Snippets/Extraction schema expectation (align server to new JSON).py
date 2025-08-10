from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class Regulation(BaseModel):
    family: Literal["FAR","DFARS","CAS","Agency","Other"]
    section: str

class Locator(BaseModel):
    document: str
    section: Optional[str] = None
    page: Optional[int] = None
    lines: Optional[str] = None

class ExtractedFact(BaseModel):
    element: Literal["Travel","Materials","Subcontracts","Fringe","Overhead","G&A","ODC","Fee/Profit","Ambiguous"]
    classification: Literal["direct","indirect","fee","ambiguous"]
    regulation: Regulation
    citation_text: str = Field(max_length=300)  # enforced via post-processor word count
    locator: Locator
    confidence: float
    ambiguity_reason: Optional[str] = None

class ExtractionResponse(BaseModel):
    facts: List[ExtractedFact] = []
