"""Sentry Envelope format parser."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import orjson

logger = logging.getLogger(__name__)


@dataclass
class EnvelopeHeader:
    """Envelope header containing metadata."""

    event_id: Optional[str] = None
    dsn: Optional[str] = None
    sent_at: Optional[str] = None
    sdk: Optional[dict] = None
    trace: Optional[dict] = None


@dataclass
class EnvelopeItem:
    """Single item within an envelope."""

    item_type: str  # event, session, attachment, transaction
    headers: dict = field(default_factory=dict)
    payload: bytes = b""


@dataclass
class ParsedEnvelope:
    """Fully parsed envelope with header and items."""

    header: EnvelopeHeader
    items: List[EnvelopeItem] = field(default_factory=list)


class EnvelopeParser:
    """
    Sentry Envelope Format Parser.

    Format:
    ```
    {"event_id":"...","dsn":"...","sent_at":"..."}
    {"type":"event","length":1234}
    <payload bytes>
    {"type":"attachment","length":5678}
    <attachment bytes>
    ```

    Each item consists of:
    1. Item header line (JSON with type and optional length)
    2. Item payload (either length bytes or until next newline)
    """

    def parse(self, raw_body: bytes) -> ParsedEnvelope:
        """
        Parse raw envelope body.

        Args:
            raw_body: Raw bytes from HTTP request body

        Returns:
            ParsedEnvelope with header and items
        """
        if not raw_body:
            return ParsedEnvelope(header=EnvelopeHeader())

        # Split by newlines, but handle binary payloads carefully
        lines = raw_body.split(b"\n")

        if not lines:
            return ParsedEnvelope(header=EnvelopeHeader())

        # Parse envelope header (first line)
        header = self._parse_header(lines[0])

        # Parse items (remaining lines)
        items = self._parse_items(lines[1:], raw_body)

        return ParsedEnvelope(header=header, items=items)

    def _parse_header(self, header_line: bytes) -> EnvelopeHeader:
        """
        Parse envelope header from first line.

        Args:
            header_line: First line bytes

        Returns:
            EnvelopeHeader object
        """
        if not header_line or not header_line.strip():
            return EnvelopeHeader()

        try:
            data = orjson.loads(header_line)
            return EnvelopeHeader(
                event_id=data.get("event_id"),
                dsn=data.get("dsn"),
                sent_at=data.get("sent_at"),
                sdk=data.get("sdk"),
                trace=data.get("trace"),
            )
        except (orjson.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse envelope header: {e}")
            return EnvelopeHeader()

    def _parse_items(self, lines: List[bytes], raw_body: bytes) -> List[EnvelopeItem]:
        """
        Parse item header + payload pairs.

        Args:
            lines: Lines after header
            raw_body: Original raw body for byte-accurate extraction

        Returns:
            List of EnvelopeItem objects
        """
        items = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line or not line.strip():
                i += 1
                continue

            # Try to parse as item header
            try:
                item_header = orjson.loads(line)
            except (orjson.JSONDecodeError, ValueError):
                # Not a valid JSON header, skip
                i += 1
                continue

            item_type = item_header.get("type", "unknown")

            # Get payload
            payload, consumed = self._extract_item_payload(item_header, lines, i + 1)

            items.append(
                EnvelopeItem(
                    item_type=item_type,
                    headers=item_header,
                    payload=payload,
                )
            )

            i += 1 + consumed

        return items

    def _extract_item_payload(
        self, item_header: dict, lines: List[bytes], start_index: int
    ) -> Tuple[bytes, int]:
        """
        Extract item payload.

        If 'length' header is present, read that many bytes.
        Otherwise, read until next newline (next line).

        Args:
            item_header: Parsed item header dict
            lines: All lines
            start_index: Index to start reading from

        Returns:
            Tuple of (payload bytes, number of lines consumed)
        """
        if start_index >= len(lines):
            return b"", 0

        length = item_header.get("length")

        if length is not None:
            # Read exactly 'length' bytes
            # This is simplified - for exact byte handling, 
            # we'd need to work with the raw body directly
            payload_parts = []
            total_length = 0
            consumed = 0

            for j in range(start_index, len(lines)):
                part = lines[j]
                remaining = length - total_length

                if len(part) >= remaining:
                    payload_parts.append(part[:remaining])
                    consumed += 1
                    break
                else:
                    payload_parts.append(part)
                    payload_parts.append(b"\n")  # Re-add newline
                    total_length += len(part) + 1
                    consumed += 1

            return b"".join(payload_parts), consumed
        else:
            # No length specified, read single line as payload
            return lines[start_index], 1

    def extract_events(self, envelope: ParsedEnvelope) -> List[bytes]:
        """
        Extract event payloads from parsed envelope.

        Args:
            envelope: Parsed envelope

        Returns:
            List of event payload bytes
        """
        return [
            item.payload
            for item in envelope.items
            if item.item_type in ("event", "transaction")
        ]

    def extract_sessions(self, envelope: ParsedEnvelope) -> List[bytes]:
        """
        Extract session payloads from parsed envelope.

        Args:
            envelope: Parsed envelope

        Returns:
            List of session payload bytes
        """
        return [item.payload for item in envelope.items if item.item_type == "session"]
