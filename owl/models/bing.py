from typing import List, Optional
from pydantic import BaseModel, HttpUrl

#  Bing Search API Response Models

class RichFactItem(BaseModel):
    text: str

class RichFact(BaseModel):
    label: Optional[RichFactItem] = None
    items: List[RichFactItem] = []
    hint: Optional[RichFactItem] = None

class WebPage(BaseModel):
    id: HttpUrl
    name: str
    url: HttpUrl
    isFamilyFriendly: bool
    displayUrl: HttpUrl
    snippet: str
    dateLastCrawled: str
    language: str
    isNavigational: bool
    richFacts: Optional[List[RichFact]] = None 

class WebPages(BaseModel):
    webSearchUrl: HttpUrl
    totalEstimatedMatches: int
    value: List[WebPage]

class BingSearchResponse(BaseModel):
    _type: str
    queryContext: dict
    webPages: WebPages