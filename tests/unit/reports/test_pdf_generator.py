"""Tests for PDF report generator."""
import pytest
from services.reports.generators.pdf_generator import PDFGenerator
from services.reports.generators.data_provider import ReportContext


@pytest.fixture
def sample_context():
    return ReportContext(
        period_id="2026-06",
        summary_cards=[{"metric_name": "Revenue", "actual": 938000, "comparator": 951000, "variance_amount": -13000, "variance_pct": -1.38}],
        variances=[{"account_name": "Advisory", "bu_id": "marsh", "variance_amount": 6900, "variance_pct": 15.3, "narrative_oneliner": "test"}],
    )


class TestPDFGenerator:
    @pytest.mark.asyncio
    async def test_generates_valid_pdf(self, sample_context):
        gen = PDFGenerator()
        data = await gen.generate(sample_context)
        assert isinstance(data, bytes)
        assert data[:4] == b'%PDF'  # PDF magic bytes
