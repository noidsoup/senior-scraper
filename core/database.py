"""
SQLite database layer for Senior Scraper
Provides persistent storage, queries, and import tracking
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import Listing, ScrapeResult, ImportResult, ScrapeStats
from .config import Settings, get_settings

Base = declarative_base()


class DBListing(Base):
    """Database model for listings"""
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    senior_place_url = Column(String, unique=True, index=True, nullable=False)
    wordpress_id = Column(Integer, nullable=True, index=True)

    # Basic listing info
    title = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String(2))
    zip_code = Column(String(10))

    # Extended data
    care_types = Column(JSON)  # List of care type strings
    normalized_types = Column(JSON)  # List of canonical care types
    description = Column(Text)
    featured_image = Column(String)

    # Pricing
    price = Column(String)
    price_high_end = Column(String)
    second_person_fee = Column(String)

    # Metadata
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_scraped = Column(DateTime)
    import_status = Column(String, default='pending')  # 'pending', 'imported', 'failed', 'updated'

    # Relationships
    import_batches = relationship("DBImportBatch", secondary="listing_import_association", back_populates="listings")

    def to_listing(self) -> Listing:
        """Convert to Listing model"""
        return Listing(
            title=self.title,
            address=self.address,
            city=self.city,
            state=self.state,
            zip_code=self.zip_code,
            senior_place_url=self.senior_place_url,
            wordpress_id=self.wordpress_id,
            care_types=self.care_types or [],
            normalized_types=self.normalized_types or [],
            description=self.description,
            featured_image=self.featured_image,
            price=self.price,
            price_high_end=self.price_high_end,
            second_person_fee=self.second_person_fee,
            last_updated=self.last_updated.isoformat() if self.last_updated else None
        )

    @classmethod
    def from_listing(cls, listing: Listing) -> 'DBListing':
        """Create from Listing model"""
        return cls(
            senior_place_url=listing.senior_place_url,
            wordpress_id=getattr(listing, 'wordpress_id', None),
            title=listing.title,
            address=listing.address,
            city=listing.city,
            state=listing.state,
            zip_code=listing.zip_code,
            care_types=listing.care_types,
            normalized_types=listing.normalized_types,
            description=getattr(listing, 'description', None),
            featured_image=getattr(listing, 'featured_image', None),
            price=getattr(listing, 'price', None),
            price_high_end=getattr(listing, 'price_high_end', None),
            second_person_fee=getattr(listing, 'second_person_fee', None),
            import_status='pending'
        )


class DBImportBatch(Base):
    """Database model for import batches"""
    __tablename__ = 'import_batches'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String, unique=True, index=True, nullable=False)  # e.g., "20241208_143022"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Batch statistics
    total_listings = Column(Integer, default=0)
    created = Column(Integer, default=0)
    updated = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    blocked = Column(Integer, default=0)
    failed = Column(Integer, default=0)

    # Metadata
    status = Column(String, default='in_progress')  # 'in_progress', 'completed', 'failed', 'rolled_back'
    csv_file = Column(String)  # Path to generated CSV
    notes = Column(Text)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    listings = relationship("DBListing", secondary="listing_import_association", back_populates="import_batches")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_listings == 0:
            return 0.0
        successful = self.created + self.updated
        return (successful / self.total_listings) * 100


class ListingImportAssociation(Base):
    """Association table for listings and import batches"""
    __tablename__ = 'listing_import_association'

    listing_id = Column(Integer, ForeignKey('listings.id'), primary_key=True)
    batch_id = Column(Integer, ForeignKey('import_batches.id'), primary_key=True)
    action = Column(String)  # 'created', 'updated', 'skipped', 'failed', 'blocked'
    wordpress_id = Column(Integer)  # WordPress ID after import
    error_message = Column(Text)  # If action was 'failed'


class Database:
    """Main database interface"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            settings = get_settings()
            db_path = settings.database_path

        # Ensure directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session"""
        return self.Session()

    # Listing operations
    def get_or_create_listing(self, url: str) -> DBListing:
        """Get existing listing or create new one"""
        with self.get_session() as session:
            listing = session.query(DBListing).filter_by(senior_place_url=url).first()
            if not listing:
                listing = DBListing(senior_place_url=url, title="", import_status='pending')
                session.add(listing)
                session.commit()
            return listing

    def upsert_listing(self, listing: Listing) -> DBListing:
        """Insert or update a listing"""
        with self.get_session() as session:
            # Try to find existing by URL
            db_listing = session.query(DBListing).filter_by(senior_place_url=listing.senior_place_url).first()

            if db_listing:
                # Update existing
                db_listing.title = listing.title
                db_listing.address = listing.address
                db_listing.city = listing.city
                db_listing.state = listing.state
                db_listing.zip_code = listing.zip_code
                db_listing.care_types = listing.care_types
                db_listing.normalized_types = listing.normalized_types
                db_listing.description = getattr(listing, 'description', None)
                db_listing.featured_image = getattr(listing, 'featured_image', None)
                db_listing.price = getattr(listing, 'price', None)
                db_listing.price_high_end = getattr(listing, 'price_high_end', None)
                db_listing.second_person_fee = getattr(listing, 'second_person_fee', None)
                db_listing.last_scraped = datetime.utcnow()
                db_listing.last_updated = datetime.utcnow()
            else:
                # Create new
                db_listing = DBListing.from_listing(listing)
                session.add(db_listing)

            session.commit()
            return db_listing

    def get_listing_by_url(self, url: str) -> Optional[DBListing]:
        """Get listing by Senior Place URL"""
        with self.get_session() as session:
            return session.query(DBListing).filter_by(senior_place_url=url).first()

    def get_listing_by_wp_id(self, wp_id: int) -> Optional[DBListing]:
        """Get listing by WordPress ID"""
        with self.get_session() as session:
            return session.query(DBListing).filter_by(wordpress_id=wp_id).first()

    def get_pending_listings(self, limit: Optional[int] = None) -> List[DBListing]:
        """Get listings pending import"""
        with self.get_session() as session:
            query = session.query(DBListing).filter_by(import_status='pending')
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_listings_by_state(self, state: str) -> List[DBListing]:
        """Get all listings for a state"""
        with self.get_session() as session:
            return session.query(DBListing).filter_by(state=state).all()

    def get_listings_by_care_type(self, care_type: str) -> List[DBListing]:
        """Get listings offering specific care type"""
        with self.get_session() as session:
            # Use JSON_CONTAINS for SQLite JSON fields
            return session.query(DBListing).filter(
                DBListing.normalized_types.contains([care_type])
            ).all()

    # Import batch operations
    def create_import_batch(self, batch_id: str, total_listings: int) -> DBImportBatch:
        """Create a new import batch"""
        with self.get_session() as session:
            batch = DBImportBatch(
                batch_id=batch_id,
                total_listings=total_listings,
                status='in_progress',
                started_at=datetime.utcnow()
            )
            session.add(batch)
            session.commit()
            return batch

    def update_batch_progress(self, batch_id: str, created: int = 0, updated: int = 0,
                            skipped: int = 0, blocked: int = 0, failed: int = 0):
        """Update batch progress counters"""
        with self.get_session() as session:
            batch = session.query(DBImportBatch).filter_by(batch_id=batch_id).first()
            if batch:
                batch.created += created
                batch.updated += updated
                batch.skipped += skipped
                batch.blocked += blocked
                batch.failed += failed
                session.commit()

    def complete_batch(self, batch_id: str, csv_file: str = None, notes: str = None):
        """Mark batch as completed"""
        with self.get_session() as session:
            batch = session.query(DBImportBatch).filter_by(batch_id=batch_id).first()
            if batch:
                batch.status = 'completed'
                batch.completed_at = datetime.utcnow()
                batch.csv_file = csv_file
                batch.notes = notes
                session.commit()

    def get_recent_batches(self, limit: int = 10) -> List[DBImportBatch]:
        """Get recent import batches"""
        with self.get_session() as session:
            return session.query(DBImportBatch).order_by(
                DBImportBatch.created_at.desc()
            ).limit(limit).all()

    # Statistics and analytics
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall statistics"""
        with self.get_session() as session:
            total_listings = session.query(DBListing).count()
            imported_listings = session.query(DBListing).filter(
                DBListing.import_status == 'imported'
            ).count()
            updated_listings = session.query(DBListing).filter(
                DBListing.import_status == 'updated'
            ).count()

            total_batches = session.query(DBImportBatch).count()
            completed_batches = session.query(DBImportBatch).filter(
                DBImportBatch.status == 'completed'
            ).count()

            # State distribution
            state_counts = session.query(
                DBListing.state,
                DBListing.id
            ).group_by(DBListing.state).all()

            return {
                'total_listings': total_listings,
                'imported_listings': imported_listings,
                'updated_listings': updated_listings,
                'pending_listings': total_listings - imported_listings - updated_listings,
                'total_batches': total_batches,
                'completed_batches': completed_batches,
                'state_distribution': dict(state_counts)
            }

    def get_listing_changes_since(self, since_datetime: datetime) -> List[DBListing]:
        """Get listings updated since a specific datetime"""
        with self.get_session() as session:
            return session.query(DBListing).filter(
                DBListing.last_updated >= since_datetime
            ).all()

    def rollback_batch(self, batch_id: str) -> bool:
        """Rollback an import batch (mark as rolled_back, but don't delete)"""
        with self.get_session() as session:
            batch = session.query(DBImportBatch).filter_by(batch_id=batch_id).first()
            if batch and batch.status == 'completed':
                batch.status = 'rolled_back'
                # Could also remove WordPress IDs, but keeping for audit trail
                session.commit()
                return True
        return False


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_database(db_path: Optional[str] = None):
    """Initialize database with schema"""
    db = Database(db_path)
    # Schema is created automatically by SQLAlchemy
    return db

