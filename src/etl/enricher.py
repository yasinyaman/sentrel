"""Event data enrichment with GeoIP and user-agent parsing."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Optional imports for enrichment
try:
    import geoip2.database

    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False
    logger.debug("geoip2 not available, GeoIP enrichment disabled")

try:
    from user_agents import parse as parse_user_agent

    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False
    logger.debug("user-agents not available, UA enrichment disabled")


class EventEnricher:
    """
    Enrich event data with additional information.

    Supports:
    - GeoIP location from IP addresses
    - User-agent parsing for browser/OS detection
    """

    def __init__(self, geoip_db_path: Optional[str] = None):
        """
        Initialize enricher.

        Args:
            geoip_db_path: Path to MaxMind GeoIP2 database file
        """
        self.geoip_reader = None

        if geoip_db_path and GEOIP_AVAILABLE:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logger.info(f"GeoIP database loaded: {geoip_db_path}")
            except Exception as e:
                logger.warning(f"Failed to load GeoIP database: {e}")

    def enrich(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all enrichments to document.

        Args:
            document: Event document dict

        Returns:
            Enriched document
        """
        document = self._enrich_geoip(document)
        document = self._enrich_user_agent(document)
        return document

    def _enrich_geoip(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add geo location from IP address.

        Args:
            document: Event document

        Returns:
            Document with geo field added
        """
        if not self.geoip_reader:
            return document

        # Get IP from user context
        ip = document.get("user", {}).get("ip")
        if not ip:
            return document

        # Skip private/local IPs
        if self._is_private_ip(ip):
            return document

        try:
            response = self.geoip_reader.city(ip)

            geo = {
                "country_code": response.country.iso_code,
                "country_name": response.country.name,
            }

            if response.subdivisions:
                geo["region_name"] = response.subdivisions.most_specific.name

            if response.city.name:
                geo["city"] = response.city.name

            if response.location.latitude and response.location.longitude:
                geo["location"] = {
                    "lat": response.location.latitude,
                    "lon": response.location.longitude,
                }

            document["geo"] = geo

        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip}: {e}")

        return document

    def _enrich_user_agent(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user-agent string for browser/OS info.

        Only enriches if browser/os fields are missing.

        Args:
            document: Event document

        Returns:
            Document with browser/os fields enriched
        """
        if not USER_AGENTS_AVAILABLE:
            return document

        # Check if already has browser/os info
        if document.get("browser") and document.get("os"):
            return document

        # Try to get user-agent from raw_event request headers
        user_agent = self._extract_user_agent(document)
        if not user_agent:
            return document

        try:
            parsed = parse_user_agent(user_agent)

            # Enrich browser if missing
            if not document.get("browser") and parsed.browser.family != "Other":
                document["browser"] = {
                    "name": parsed.browser.family,
                    "version": parsed.browser.version_string or None,
                }

            # Enrich OS if missing
            if not document.get("os") and parsed.os.family != "Other":
                document["os"] = {
                    "name": parsed.os.family,
                    "version": parsed.os.version_string or None,
                }

            # Enrich device if missing
            if not document.get("device") and parsed.device.family != "Other":
                document["device"] = {
                    "family": parsed.device.family,
                    "brand": parsed.device.brand or None,
                    "model": parsed.device.model or None,
                }

        except Exception as e:
            logger.debug(f"User-agent parsing failed: {e}")

        return document

    def _extract_user_agent(self, document: Dict[str, Any]) -> Optional[str]:
        """
        Extract user-agent string from document.

        Args:
            document: Event document

        Returns:
            User-agent string or None
        """
        # Try raw_event first
        raw_event = document.get("raw_event", {})
        if raw_event:
            request = raw_event.get("request", {})
            headers = request.get("headers", {})

            for key, value in headers.items():
                if key.lower() == "user-agent":
                    return value

        return None

    def _is_private_ip(self, ip: str) -> bool:
        """
        Check if IP is private/local.

        Args:
            ip: IP address string

        Returns:
            True if private/local
        """
        if not ip:
            return True

        # Simple check for common private ranges
        if ip.startswith(("10.", "172.", "192.168.", "127.", "::1", "fe80:")):
            return True

        if ip in ("localhost", "127.0.0.1", "::1"):
            return True

        return False

    def close(self):
        """Close GeoIP reader."""
        if self.geoip_reader:
            self.geoip_reader.close()
            self.geoip_reader = None
            logger.info("GeoIP reader closed")


# Global enricher instance
_enricher: Optional[EventEnricher] = None


def get_enricher(geoip_db_path: Optional[str] = None) -> EventEnricher:
    """
    Get global enricher instance.

    Args:
        geoip_db_path: Optional path to GeoIP database

    Returns:
        EventEnricher instance
    """
    global _enricher

    if _enricher is None:
        _enricher = EventEnricher(geoip_db_path)

    return _enricher
