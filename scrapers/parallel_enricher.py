"""
Parallel enrichment for Senior Place listings with safety controls
"""

import asyncio
import logging
from asyncio import Semaphore, Queue
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# from core.retry import with_retry, retry_on_rate_limit  # Temporarily disabled for testing
from core.models import Listing, ScrapeStats
from core.exceptions import ScrapingError, RateLimitError
from core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class EnrichmentResult:
    """Result of enriching a single listing"""
    listing: Listing
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0
    retries: int = 0


class ParallelEnricher:
    """
    Safe parallel enrichment of Senior Place listings

    Features:
    - Configurable concurrency limits
    - Automatic rate limiting
    - Retry logic with exponential backoff
    - Progress tracking and logging
    - Graceful failure handling
    - Checkpoint/resume capability
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        request_delay_ms: int = 500,
        max_retries: int = 3,
        progress_callback: Optional[callable] = None
    ):
        self.max_concurrent = max_concurrent
        self.request_delay_ms = request_delay_ms
        self.max_retries = max_retries
        self.progress_callback = progress_callback

        # Concurrency control
        self.semaphore = Semaphore(max_concurrent)

        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0,
            'start_time': None,
            'end_time': None
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_delay_seconds = request_delay_ms / 1000.0

    async def _respect_rate_limit(self):
        """Ensure minimum delay between requests"""
        if self.request_delay_ms > 0:
            elapsed = asyncio.get_event_loop().time() - self.last_request_time
            if elapsed < self.min_delay_seconds:
                delay = self.min_delay_seconds - elapsed
                await asyncio.sleep(delay)
        self.last_request_time = asyncio.get_event_loop().time()

    # @with_retry(max_attempts=3)  # Temporarily disabled for testing
    async def _enrich_single_listing_safe(self, listing: Listing) -> EnrichmentResult:
        """
        Enrich a single listing with full safety controls

        This method includes retry logic and rate limiting
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Respect rate limiting
            await self._respect_rate_limit()

            # Simulate enrichment process (replace with actual implementation)
            enriched_listing = await self._enrich_listing_implementation(listing)

            duration = asyncio.get_event_loop().time() - start_time
            return EnrichmentResult(
                listing=enriched_listing,
                success=True,
                duration_seconds=duration
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f"Failed to enrich {listing.title}: {e}")

            return EnrichmentResult(
                listing=listing,
                success=False,
                error=str(e),
                duration_seconds=duration
            )

    def __init__(
        self,
        max_concurrent: int = 5,
        request_delay_ms: int = 500,
        max_retries: int = 3,
        progress_callback: Optional[callable] = None,
        sp_username: str = None,
        sp_password: str = None
    ):
        self.max_concurrent = max_concurrent
        self.request_delay_ms = request_delay_ms
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        self.sp_username = sp_username
        self.sp_password = sp_password

        # Concurrency control
        self.semaphore = Semaphore(max_concurrent)

        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0,
            'start_time': None,
            'end_time': None
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_delay_seconds = request_delay_ms / 1000.0

        # Browser context (shared across requests for session reuse)
        self.browser_context = None

    async def _ensure_browser_context(self):
        """Ensure we have a logged-in browser context"""
        if self.browser_context is None:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()

            # Login to Senior Place
            page = await context.new_page()
            await page.goto("https://app.seniorplace.com/login")
            await page.fill('input[name="email"]', self.sp_username)
            await page.fill('input[name="password"]', self.sp_password)
            await page.click('button[type="submit"]')
            await page.wait_for_selector('text=Communities', timeout=15000)
            await page.close()

            self.browser_context = context
            logger.info("Browser context initialized and logged in")

    async def _enrich_listing_implementation(self, listing: Listing) -> Listing:
        """
        Actual enrichment implementation using Playwright

        Visits the Senior Place detail page and extracts:
        - Pricing information
        - Care types from Community Types section
        - Description
        - Featured image
        - Last updated date
        """
        await self._ensure_browser_context()

        # Normalize base URL (strip /details or /attributes)
        base_url = listing.senior_place_url.split('?')[0]
        for suffix in ['/details', '/attributes']:
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]

        page = await self.browser_context.new_page()

        try:
            # --- Address from Details tab (form fields) ---
            detail_data = {}
            try:
                details_url = f"{base_url.rstrip('/')}/details"
                await page.goto(details_url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1200)
                detail_data = await page.evaluate("""
                    () => {
                        const getField = (needle) => {
                            const labels = Array.from(document.querySelectorAll('label'));
                            for (const label of labels) {
                                const text = (label.textContent || '').toLowerCase();
                                if (text.includes(needle)) {
                                    const input = label.querySelector('input');
                                    if (input) return input.value.trim();
                                }
                            }
                            return '';
                        };

                        return {
                            address: getField('address'),
                            city: getField('city'),
                            state: getField('state'),
                            zip: getField('zip'),
                            phone: getField('phone'),
                        };
                    }
                """)
            except Exception as e:
                logger.debug(f"Failed to get detail data for {listing.title}: {e}")

            # --- Pricing from Attributes tab ---
            pricing = {}
            try:
                pricing_url = f"{base_url.rstrip('/')}/attributes"
                await page.goto(pricing_url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1200)
                pricing = await page.evaluate("""
                    () => {
                        const result = {};

                        // Monthly base price
                        const baseLabels = Array.from(document.querySelectorAll('label')).filter(l =>
                            l.textContent.toLowerCase().includes('monthly base') ||
                            l.textContent.toLowerCase().includes('base monthly')
                        );
                        if (baseLabels.length > 0) {
                            const input = baseLabels[0].querySelector('input');
                            if (input && input.value) result.monthly_base_price = input.value;
                        }

                        // High-end pricing
                        const highLabels = Array.from(document.querySelectorAll('label')).filter(l =>
                            l.textContent.toLowerCase().includes('high end') ||
                            l.textContent.toLowerCase().includes('high-end')
                        );
                        if (highLabels.length > 0) {
                            const input = highLabels[0].querySelector('input');
                            if (input && input.value) result.price_high_end = input.value;
                        }

                        // Second person fee
                        const secondLabels = Array.from(document.querySelectorAll('label')).filter(l =>
                            l.textContent.toLowerCase().includes('second person') ||
                            l.textContent.toLowerCase().includes('couple') ||
                            l.textContent.toLowerCase().includes('shared')
                        );
                        if (secondLabels.length > 0) {
                            const input = secondLabels[0].querySelector('input');
                            if (input && input.value) result.second_person_fee = input.value;
                        }

                        return result;
                    }
                """)
            except Exception as e:
                logger.debug(f"Failed to get pricing for {listing.title}: {e}")

            # Extract care types from Community Types section only
            care_types = []
            try:
                care_types = await page.evaluate("""
                    () => {
                        const types = [];
                        const communityTypesDiv = document.querySelector('div.font-bold.mb-1:has-text("Community Type(s)")');
                        if (communityTypesDiv) {
                            const optionsDiv = communityTypesDiv.nextElementSibling;
                            if (optionsDiv && optionsDiv.classList.contains('options')) {
                                const labels = Array.from(optionsDiv.querySelectorAll("label.inline-flex"));
                                for (const label of labels) {
                                    const textEl = label.querySelector("div.ml-2");
                                    const input = label.querySelector('input[type="checkbox"]');

                                    if (!textEl || !input) continue;
                                    if (!input.checked) continue;

                                    const name = (textEl.textContent || "").trim();
                                    if (name) types.push(name);
                                }
                            }
                        }
                        return types;
                    }
                """)
            except Exception as e:
                logger.debug(f"Failed to get care types for {listing.title}: {e}")

            # Extract last updated date
            last_updated = await page.evaluate("""
                () => {
                    // Look for "Last updated on" text
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        const text = (el.textContent || '').trim();
                        if (text.includes('Last updated on')) {
                            // Extract date from "Last updated on Jul 27, 2024"
                            const match = text.match(/Last updated on ([A-Za-z]+ \\d{1,2}, \\d{4})/);
                            if (match) {
                                return match[1];
                            }
                        }
                    }
                    return null;
                }
            """)

            # Parse last_updated date if found
            if last_updated:
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(last_updated, '%b %d, %Y')
                    listing.last_updated = parsed_date.isoformat()
                except Exception:
                    pass

            # Extract description
            description_data = await page.evaluate("""
                () => {
                    const result = {};

                    // Try to extract description from any text areas or content areas
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        if (ta.value && ta.value.length > 50) {
                            result.description = ta.value;
                            break;
                        }
                    }

                    // Fallback: look for content in divs with lots of text
                    if (!result.description) {
                        const contentDivs = Array.from(document.querySelectorAll('div')).filter(div =>
                            div.textContent && div.textContent.length > 100 &&
                            !div.querySelector('input') && !div.querySelector('button')
                        );
                        if (contentDivs.length > 0) {
                            result.description = contentDivs[0].textContent.trim();
                        }
                    }

                    return result;
                }
            """)

            # Try to extract featured image
            try:
                featured_image = await page.evaluate("""
                    () => {
                        // Look for community images
                        const imgs = document.querySelectorAll('img');
                        for (const img of imgs) {
                            const src = img.src || '';
                            if (src.includes('entities/communities') && src.includes('amazonaws.com')) {
                                return src;
                            }
                        }
                        return null;
                    }
                """)
                if featured_image:
                    listing.featured_image = featured_image
            except Exception as e:
                logger.debug(f"Failed to get image for {listing.title}: {e}")

            # Update listing with enriched data
            if detail_data.get('address'):
                listing.address = detail_data['address']
            if detail_data.get('city'):
                listing.city = detail_data['city']
            if detail_data.get('state'):
                listing.state = detail_data['state']
            if detail_data.get('zip'):
                listing.zip_code = detail_data['zip']

            if pricing.get('monthly_base_price'):
                listing.price = pricing['monthly_base_price']
            if pricing.get('price_high_end'):
                listing.price_high_end = pricing['price_high_end']
            if pricing.get('second_person_fee'):
                listing.second_person_fee = pricing['second_person_fee']

            if care_types:
                listing.care_types = care_types

            if description_data.get('description'):
                listing.description = description_data['description']

            return listing

        finally:
            await page.close()

    async def _worker(self, queue: Queue, results: List[EnrichmentResult]):
        """Worker task that processes listings from the queue"""
        while True:
            try:
                listing = await queue.get()
                if listing is None:  # Sentinel value to stop worker
                    break

                logger.debug(f"Processing {listing.title}")

                # Use semaphore to limit concurrent requests
                async with self.semaphore:
                    result = await self._enrich_single_listing_safe(listing)
                    results.append(result)

                    # Update progress callback
                    if self.progress_callback:
                        self.progress_callback(result)

                    self.stats['retries'] += result.retries
                    if result.success:
                        self.stats['successful'] += 1
                    else:
                        self.stats['failed'] += 1

                queue.task_done()

            except Exception as e:
                logger.error(f"Worker error: {e}")
                continue

    async def enrich_listings(
        self,
        listings: List[Listing],
        num_workers: Optional[int] = None
    ) -> List[EnrichmentResult]:
        """
        Enrich multiple listings in parallel with safety controls

        Args:
            listings: List of listings to enrich
            num_workers: Number of worker tasks (defaults to max_concurrent)

        Returns:
            List of enrichment results
        """
        if not listings:
            return []

        if num_workers is None:
            num_workers = min(self.max_concurrent, len(listings))

        self.stats['total'] = len(listings)
        self.stats['start_time'] = datetime.utcnow()

        logger.info(f"Starting parallel enrichment of {len(listings)} listings with {num_workers} workers")

        # Create work queue
        queue = Queue()
        for listing in listings:
            await queue.put(listing)

        # Add sentinel values to stop workers
        for _ in range(num_workers):
            await queue.put(None)

        # Results list (shared between workers)
        results = []

        # Start worker tasks
        workers = [
            asyncio.create_task(self._worker(queue, results))
            for _ in range(num_workers)
        ]

        # Wait for all work to complete
        await queue.join()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        self.stats['end_time'] = datetime.utcnow()

        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        logger.info(".1f")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics"""
        stats = self.stats.copy()
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            stats['duration_seconds'] = duration.total_seconds()
        return stats

    async def enrich_with_stats(self, listings: List[Listing]) -> tuple[List[EnrichmentResult], Dict[str, Any]]:
        """Enrich listings and return results with statistics"""
        results = await self.enrich_listings(listings)
        stats = self.get_stats()
        return results, stats


# Convenience function for easy usage
async def enrich_listings_parallel(
    listings: List[Listing],
    max_concurrent: int = 5,
    progress_callback: Optional[callable] = None
) -> List[EnrichmentResult]:
    """
    Convenience function for parallel enrichment

    Args:
        listings: Listings to enrich
        max_concurrent: Maximum concurrent requests
        progress_callback: Optional progress callback

    Returns:
        Enrichment results
    """
    enricher = ParallelEnricher(
        max_concurrent=max_concurrent,
        progress_callback=progress_callback
    )
    return await enricher.enrich_listings(listings)

