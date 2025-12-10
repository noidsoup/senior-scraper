"""
Custom exceptions for Senior Scraper
"""


class SeniorScraperError(Exception):
    """Base exception for all scraper errors"""
    pass


class AuthenticationError(SeniorScraperError):
    """Failed to authenticate with Senior Place or WordPress"""
    pass


class RateLimitError(SeniorScraperError):
    """Request was rate limited or blocked"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class DataValidationError(SeniorScraperError):
    """Data failed validation"""
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"{field}='{value}': {reason}")


class WordPressAPIError(SeniorScraperError):
    """WordPress API returned an error"""
    def __init__(self, status_code: int, message: str, response_body: str = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"WordPress API error {status_code}: {message}")


class ScrapingError(SeniorScraperError):
    """Error during scraping operation"""
    def __init__(self, url: str, message: str):
        self.url = url
        super().__init__(f"Scraping error for {url}: {message}")


class ImportError(SeniorScraperError):
    """Error during WordPress import"""
    def __init__(self, listing_title: str, message: str):
        self.listing_title = listing_title
        super().__init__(f"Import error for '{listing_title}': {message}")

