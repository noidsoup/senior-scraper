# Senior Scraper Comprehensive Improvement Plan

## Executive Summary

This plan outlines a systematic approach to elevate the Senior Scraper from a functional tool to a production-grade, maintainable, and scalable application. The improvements are organized into 4 phases over approximately 8-12 weeks.

---

## Phase 1: Foundation & Code Quality (Weeks 1-2)

### 1.1 Consolidate Shared Code
**Priority**: Critical  
**Effort**: 4 hours  
**Dependencies**: None

**Current Problem**: Care type mapping, constants, and utility functions are duplicated across 3+ files, causing sync bugs.

**Solution**:
```
senior-scraper/
├── core/
│   ├── __init__.py
│   ├── constants.py          # Care types, states, URLs
│   ├── models.py             # Pydantic data models
│   ├── utils.py              # Shared utilities
│   └── exceptions.py         # Custom exceptions
```

**Deliverables**:
- [ ] Create `core/constants.py` with CARE_TYPE_MAPPING, SUPPORTED_STATES, etc.
- [ ] Create `core/models.py` with Listing, ImportResult, ScrapeStats models
- [ ] Update all imports in orchestrator, importer, and dashboard
- [ ] Remove duplicate code from existing files

---

### 1.2 Add Type Hints & Documentation
**Priority**: High  
**Effort**: 6 hours  
**Dependencies**: 1.1

**Current Problem**: Limited type hints make refactoring risky and IDE support poor.

**Deliverables**:
- [ ] Add type hints to all public functions
- [ ] Add docstrings with Args/Returns/Raises
- [ ] Configure `mypy` for static type checking
- [ ] Add `py.typed` marker for library usage

**Example**:
```python
from typing import Optional, List, Dict, Tuple
from core.models import Listing, ScrapeResult

def scrape_state(
    state: str,
    max_pages: Optional[int] = None
) -> ScrapeResult:
    """
    Scrape all listings from Senior Place for a given state.
    
    Args:
        state: Two-letter state code (e.g., 'AZ', 'CA')
        max_pages: Optional limit on pages to scrape (for testing)
    
    Returns:
        ScrapeResult containing listings and statistics
    
    Raises:
        AuthenticationError: If Senior Place login fails
        RateLimitError: If scraping is blocked
    """
```

---

### 1.3 Configuration Management
**Priority**: High  
**Effort**: 3 hours  
**Dependencies**: 1.1

**Current Problem**: Configuration scattered across env files, hardcoded values, and CLI args.

**Solution**: Use Pydantic Settings for validated configuration:

```python
# core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # WordPress
    wp_url: str
    wp_username: str
    wp_password: str
    
    # Senior Place
    sp_username: str
    sp_password: str
    
    # Scraping behavior
    max_pages_per_state: int = 0  # 0 = unlimited
    request_delay_ms: int = 500
    max_retries: int = 3
    
    # Paths
    output_dir: str = "monthly_updates"
    cache_dir: str = ".cache"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Deliverables**:
- [ ] Create `core/config.py` with Settings class
- [ ] Migrate `wp_config.env` to `.env` format
- [ ] Add `.env.example` template
- [ ] Update all modules to use `settings` object

---

### 1.4 Error Handling & Custom Exceptions
**Priority**: High  
**Effort**: 2 hours  
**Dependencies**: 1.1

**Current Problem**: Generic exceptions make debugging difficult.

```python
# core/exceptions.py
class SeniorScraperError(Exception):
    """Base exception for all scraper errors"""
    pass

class AuthenticationError(SeniorScraperError):
    """Failed to authenticate with Senior Place or WordPress"""
    pass

class RateLimitError(SeniorScraperError):
    """Request was rate limited or blocked"""
    pass

class DataValidationError(SeniorScraperError):
    """Data failed validation"""
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"{field}='{value}': {reason}")

class WordPressAPIError(SeniorScraperError):
    """WordPress API returned an error"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"WordPress API error {status_code}: {message}")
```

---

## Phase 2: Reliability & Performance (Weeks 3-5)

### 2.1 Retry Logic with Exponential Backoff
**Priority**: Critical  
**Effort**: 3 hours  
**Dependencies**: 1.4

**Current Problem**: Single failures can crash entire scrape runs.

```python
# core/retry.py
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

def with_retry(max_attempts: int = 3):
    """Decorator for retryable operations"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

# Usage
@with_retry(max_attempts=3)
async def fetch_listing_details(url: str) -> dict:
    ...
```

**Deliverables**:
- [ ] Add `tenacity` to requirements.txt
- [ ] Create retry decorator with configurable attempts
- [ ] Apply to all external API calls (WordPress, Senior Place)
- [ ] Add circuit breaker for repeated failures

---

### 2.2 Parallel Processing for Enrichment
**Priority**: High  
**Effort**: 6 hours  
**Dependencies**: 2.1

**Current Problem**: Enriching 12,000 listings sequentially takes hours.

```python
# scrapers/parallel_enricher.py
import asyncio
from asyncio import Semaphore
from typing import List
from core.models import Listing

class ParallelEnricher:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)
        self.stats = {'success': 0, 'failed': 0, 'skipped': 0}
    
    async def enrich_listing(self, listing: Listing) -> Listing:
        async with self.semaphore:
            # ... enrichment logic
            pass
    
    async def enrich_batch(self, listings: List[Listing]) -> List[Listing]:
        tasks = [self.enrich_listing(l) for l in listings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        enriched = []
        for listing, result in zip(listings, results):
            if isinstance(result, Exception):
                self.stats['failed'] += 1
                logger.error(f"Failed to enrich {listing.title}: {result}")
            else:
                self.stats['success'] += 1
                enriched.append(result)
        
        return enriched
```

**Expected Impact**: 3-5x faster enrichment (configurable concurrency).

---

### 2.3 Database Layer (SQLite)
**Priority**: High  
**Effort**: 8 hours  
**Dependencies**: 1.1, 1.2

**Current Problem**: CSV files scattered everywhere, no query capability, no history.

```python
# core/database.py
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Listing(Base):
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True)
    senior_place_url = Column(String, unique=True, index=True)
    wordpress_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String(2))
    zip_code = Column(String(10))
    care_types = Column(JSON)  # List of care types
    featured_image = Column(String)
    description = Column(String)
    
    # Tracking
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped = Column(DateTime)
    import_status = Column(String)  # 'pending', 'imported', 'failed', 'updated'

class ImportBatch(Base):
    __tablename__ = 'import_batches'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_listings = Column(Integer)
    created = Column(Integer)
    updated = Column(Integer)
    skipped = Column(Integer)
    failed = Column(Integer)
    csv_file = Column(String)
    status = Column(String)  # 'in_progress', 'completed', 'failed', 'rolled_back'

class Database:
    def __init__(self, db_path: str = "senior_scraper.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_or_create_listing(self, url: str) -> Listing:
        ...
    
    def mark_imported(self, url: str, wp_id: int):
        ...
    
    def get_pending_imports(self) -> List[Listing]:
        ...
```

**Benefits**:
- Query any listing by URL, state, care type
- Track import history and rollback capability
- Deduplication is automatic (unique constraint)
- No more CSV file management

---

### 2.4 Image Download & WordPress Media Upload
**Priority**: Medium  
**Effort**: 6 hours  
**Dependencies**: 2.1

**Current Problem**: Images link to Senior Place CDN - if it changes/blocks, all images break.

```python
# core/media.py
import aiohttp
import hashlib
from pathlib import Path

class MediaManager:
    def __init__(self, cache_dir: str = ".cache/images"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_image(self, url: str) -> Path:
        """Download image to local cache"""
        filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        local_path = self.cache_dir / filename
        
        if local_path.exists():
            return local_path
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    local_path.write_bytes(await resp.read())
                    return local_path
        
        raise Exception(f"Failed to download {url}")
    
    async def upload_to_wordpress(self, image_path: Path, title: str) -> int:
        """Upload image to WordPress media library, return media ID"""
        ...
```

---

## Phase 3: User Experience (Weeks 6-8)

### 3.1 Real-time Dashboard Updates (WebSockets)
**Priority**: Medium  
**Effort**: 8 hours  
**Dependencies**: Phase 2

**Current Problem**: Dashboard requires manual refresh to see progress.

```python
# web_interface/app.py
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

class ProgressEmitter:
    def __init__(self):
        self.socketio = socketio
    
    def emit_progress(self, event: str, data: dict):
        self.socketio.emit(event, data)

# In orchestrator
emitter.emit_progress('scrape_progress', {
    'state': 'AZ',
    'page': 5,
    'total_pages': 20,
    'listings_found': 250,
    'percent': 25
})
```

```javascript
// Frontend
const socket = io();
socket.on('scrape_progress', (data) => {
    updateProgressBar(data.percent);
    updateStats(data);
});
```

---

### 3.2 Dashboard Analytics & Visualizations
**Priority**: Low  
**Effort**: 6 hours  
**Dependencies**: 2.3

**Features**:
- [ ] Listings by state (pie chart)
- [ ] Listings over time (line chart)
- [ ] Care type distribution (bar chart)
- [ ] Import success rate (metrics)
- [ ] Recent activity timeline

```html
<!-- Using Chart.js -->
<canvas id="stateChart"></canvas>
<script>
const ctx = document.getElementById('stateChart');
new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['AZ', 'CA', 'CO', 'ID', 'NM', 'UT'],
        datasets: [{
            data: {{ state_counts | tojson }},
            backgroundColor: ['#667eea', '#764ba2', ...]
        }]
    }
});
</script>
```

---

### 3.3 Diff Viewer for Updates
**Priority**: Medium  
**Effort**: 4 hours  
**Dependencies**: 2.3

Show exactly what changed when updating a listing:

```html
<div class="diff-viewer">
    <h4>Care Types Changed</h4>
    <div class="diff-old">- Assisted Living Home</div>
    <div class="diff-new">+ Assisted Living Home, Memory Care</div>
    
    <h4>Price Changed</h4>
    <div class="diff-old">- $3,500/month</div>
    <div class="diff-new">+ $3,800/month</div>
</div>
```

---

### 3.4 Rollback Capability
**Priority**: Medium  
**Effort**: 4 hours  
**Dependencies**: 2.3

```python
# core/rollback.py
class RollbackManager:
    def __init__(self, db: Database):
        self.db = db
    
    def rollback_batch(self, batch_id: int):
        """Undo all changes from a specific import batch"""
        batch = self.db.get_batch(batch_id)
        
        for change in batch.changes:
            if change.action == 'create':
                # Delete from WordPress
                self.wp_client.delete_post(change.wp_id)
            elif change.action == 'update':
                # Restore previous values
                self.wp_client.update_post(change.wp_id, change.previous_data)
        
        batch.status = 'rolled_back'
        self.db.commit()
```

---

## Phase 4: Operations & Deployment (Weeks 9-12)

### 4.1 Structured Logging
**Priority**: High  
**Effort**: 3 hours  
**Dependencies**: None

```python
# core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            **getattr(record, 'extra', {})
        })

def setup_logging(log_file: str = "senior_scraper.log"):
    logger = logging.getLogger('senior_scraper')
    logger.setLevel(logging.INFO)
    
    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger
```

---

### 4.2 Automated Scheduling
**Priority**: Medium  
**Effort**: 4 hours  
**Dependencies**: 4.1

```python
# scheduler.py
import schedule
import time
from datetime import datetime

def run_monthly_update():
    logger.info("Starting scheduled monthly update")
    orchestrator = MonthlyUpdateOrchestrator.from_settings()
    asyncio.run(orchestrator.run_full_update())

def run_daily_health_check():
    logger.info("Running daily health check")
    # Check WordPress connection
    # Check Senior Place login
    # Send status email/Slack

schedule.every().day.at("02:00").do(run_daily_health_check)
schedule.every(30).days.do(run_monthly_update)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 4.3 Notifications (Email/Slack)
**Priority**: Medium  
**Effort**: 3 hours  
**Dependencies**: 4.1

```python
# core/notifications.py
import smtplib
from email.mime.text import MIMEText
import requests

class Notifier:
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def send_email(self, subject: str, body: str):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.settings.email_from
        msg['To'] = self.settings.email_to
        
        with smtplib.SMTP(self.settings.smtp_host) as server:
            server.send_message(msg)
    
    def send_slack(self, message: str):
        requests.post(self.settings.slack_webhook, json={
            'text': message,
            'blocks': [
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': message}}
            ]
        })
    
    def notify_completion(self, stats: dict):
        message = f"""
        ✅ Monthly Update Complete
        
        📊 Statistics:
        - New listings: {stats['new']}
        - Updated: {stats['updated']}
        - Skipped: {stats['skipped']}
        - Errors: {stats['errors']}
        
        ⏱️ Duration: {stats['duration']}
        """
        
        if self.settings.slack_webhook:
            self.send_slack(message)
        if self.settings.email_to:
            self.send_email("Senior Scraper Update Complete", message)
```

---

### 4.4 Docker Deployment
**Priority**: Low  
**Effort**: 4 hours  
**Dependencies**: Phase 1-3

```dockerfile
# Dockerfile
FROM python:3.10-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

# Create non-root user
RUN useradd -m scraper && chown -R scraper:scraper /app
USER scraper

EXPOSE 5000

CMD ["python", "web_interface/app.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  scraper:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
    
  scheduler:
    build: .
    command: python scheduler.py
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    depends_on:
      - scraper
    restart: unless-stopped
```

---

## Phase 5: Testing & Quality (Ongoing)

### 5.1 Expand Test Coverage
**Current**: 75 tests (unit + API)  
**Target**: 150+ tests (add integration + E2E)

```python
# tests/integration/test_full_workflow.py
@pytest.mark.integration
async def test_scrape_enrich_import_workflow():
    """Test complete workflow from scrape to WordPress"""
    # 1. Scrape a single state with page limit
    orchestrator = MonthlyUpdateOrchestrator.from_test_settings()
    listings = await orchestrator.scrape_state('UT', max_pages=1)
    
    assert len(listings) > 0
    assert all(l.title for l in listings)
    
    # 2. Enrich listings
    enriched = await orchestrator.enrich_listings(listings[:5])
    assert all(l.care_types for l in enriched)
    
    # 3. Generate import file
    csv_path = orchestrator.generate_csv(enriched)
    assert csv_path.exists()
    
    # 4. Import to WordPress (sandbox)
    results = await importer.import_csv(csv_path, dry_run=True)
    assert results.errors == 0
```

### 5.2 Mocked External Services
```python
# tests/conftest.py
@pytest.fixture
def mock_senior_place(responses):
    """Mock Senior Place API responses"""
    responses.add(
        responses.GET,
        "https://app.seniorplace.com/communities",
        json={'listings': [...]},
        status=200
    )
    return responses

@pytest.fixture  
def mock_wordpress(responses):
    """Mock WordPress API"""
    responses.add(
        responses.GET,
        re.compile(r".*/wp-json/wp/v2/listing.*"),
        json=[],
        status=200
    )
    return responses
```

---

## Timeline Summary

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| 1 | Foundation | 2 weeks | Shared code, types, config, exceptions |
| 2 | Reliability | 3 weeks | Retry logic, parallelization, database |
| 3 | UX | 3 weeks | Real-time updates, analytics, rollback |
| 4 | Operations | 3 weeks | Logging, scheduling, notifications, Docker |
| 5 | Testing | Ongoing | Integration tests, mocks, coverage |

---

## Resource Requirements

### Dependencies to Add
```txt
# requirements.txt additions
tenacity>=8.2.0          # Retry logic
pydantic-settings>=2.0   # Configuration
sqlalchemy>=2.0          # Database ORM
flask-socketio>=5.3      # WebSocket support
schedule>=1.2            # Task scheduling
chart.js                 # Frontend charts (CDN)
```

### Estimated Effort
- **Total**: ~80-100 hours
- **Can be done incrementally** - each phase is independent
- **Recommended**: 1 phase every 2-3 weeks

---

## Success Metrics

After implementing all phases:

| Metric | Current | Target |
|--------|---------|--------|
| Test coverage | ~60% | 90%+ |
| Scrape time (6 states) | 2-3 hours | 30-45 min |
| Import reliability | ~95% | 99.9% |
| Manual intervention | Frequent | Rare |
| Deployment time | Manual | 1-click |
| Rollback capability | None | Full |

---

## Getting Started

Start with **Phase 1.1** (Consolidate Shared Code) - it's quick, low-risk, and enables everything else.

```bash
# Create the new structure
mkdir -p core tests/integration
touch core/__init__.py core/constants.py core/models.py core/config.py
```

Would you like me to begin implementing Phase 1?

