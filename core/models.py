"""
Pydantic data models for type safety and validation
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class Listing(BaseModel):
    """Represents a senior living facility listing"""
    
    title: str
    address: str
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., pattern=r'^\d{5}(-\d{4})?$')
    senior_place_url: str
    featured_image: Optional[str] = None
    description: Optional[str] = None
    care_types: List[str] = Field(default_factory=list)
    normalized_types: List[str] = Field(default_factory=list)
    price: Optional[str] = None
    price_high_end: Optional[str] = None
    second_person_fee: Optional[str] = None
    last_updated: Optional[str] = None
    
    # WordPress-specific
    wordpress_id: Optional[int] = None
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Ensure state is uppercase 2-letter code"""
        v = v.upper().strip()
        if len(v) != 2:
            raise ValueError('State must be 2-letter code')
        return v
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v):
        """Normalize zip code format"""
        v = v.strip()
        # Remove any non-digits except dash
        v = ''.join(c for c in v if c.isdigit() or c == '-')
        if not v:
            raise ValueError('Invalid zip code')
        return v
    
    model_config = ConfigDict(extra='allow')  # Allow additional fields from scraping


class ScrapeStats(BaseModel):
    """Statistics from a scraping run"""
    
    total_listings: int = 0
    new_listings: int = 0
    updated_listings: int = 0
    skipped_listings: int = 0
    failed_listings: int = 0
    care_type_updates: int = 0
    states_scraped: List[str] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class ScrapeResult(BaseModel):
    """Result of a scraping operation"""
    
    listings: List[Listing] = Field(default_factory=list)
    stats: ScrapeStats = Field(default_factory=ScrapeStats)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ImportResult(BaseModel):
    """Result of a WordPress import operation"""
    
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    blocked: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    batch_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total == 0:
            return 0.0
        return ((self.created + self.updated) / self.total) * 100
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

