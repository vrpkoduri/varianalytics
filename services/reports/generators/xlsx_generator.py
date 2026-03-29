"""Excel report generator.

Produces formatted Excel workbooks with variance data, narrative
commentary, conditional formatting, and drill-down tabs for each
hierarchy dimension.
"""

from __future__ import annotations

from typing import Any


class XLSXGenerator:
    """Generate formatted Excel workbooks with narratives and drill-down tabs.

    Responsible for:
    - Summary sheet with P&L waterfall and materiality highlights.
    - Per-dimension drill-down tabs (Geo, Segment, LOB, Cost Centre).
    - Narrative commentary columns alongside variance figures.
    - Conditional formatting (red/green variance, bold material items).
    - Named ranges and Excel table formatting for downstream consumption.
    """

    async def generate(self, context: dict[str, Any]) -> bytes:
        """Generate an XLSX workbook from the supplied context.

        Args:
            context: Dictionary containing period data, narratives,
                     and formatting options.

        Returns:
            Raw XLSX bytes ready for storage or streaming.
        """
        raise NotImplementedError("XLSX generation not yet implemented.")
