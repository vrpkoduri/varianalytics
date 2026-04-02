"""PDF report generator using reportlab."""
import io
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

logger = logging.getLogger(__name__)

COBALT = colors.HexColor("#002C77")
TEAL = colors.HexColor("#00A8C7")
EMERALD = colors.HexColor("#2DD4A8")
CORAL = colors.HexColor("#F97066")


class PDFGenerator:
    """Generates PDF variance reports."""

    async def generate(self, context: Any) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=18, textColor=COBALT, spaceAfter=12)
        subtitle_style = ParagraphStyle("Subtitle2", parent=styles["Normal"], fontSize=10, textColor=colors.gray)
        heading_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=13, textColor=COBALT, spaceBefore=12)
        body_style = ParagraphStyle("Body2", parent=styles["Normal"], fontSize=9, leading=13)
        small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.gray)

        elements = []

        # Title
        elements.append(Paragraph("Variance Analysis Report", title_style))
        elements.append(Paragraph(f"{context.period_id} &middot; {context.view} vs {context.comparison_base}", subtitle_style))
        elements.append(Spacer(1, 12))

        # KPI Summary Table
        if context.summary_cards:
            elements.append(Paragraph("Key Performance Indicators", heading_style))
            kpi_data = [["Metric", "Actual", "Comparator", "Variance", "%"]]
            for card in context.summary_cards:
                kpi_data.append([
                    card.get("metric_name", ""),
                    f"${card.get('actual', 0):,.0f}",
                    f"${card.get('comparator', 0):,.0f}",
                    f"${card.get('variance_amount', 0):,.0f}",
                    f"{card.get('variance_pct', 0):.1f}%",
                ])
            kpi_table = Table(kpi_data, colWidths=[120, 80, 80, 80, 60])
            kpi_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COBALT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]))
            elements.append(kpi_table)
            elements.append(Spacer(1, 16))

        # Executive Summary (from narrative pyramid)
        elements.append(Paragraph("Executive Summary", heading_style))
        exec_narr = context.executive_summary.get("full_narrative") or context.executive_summary.get("fullNarrative", "")
        if exec_narr:
            for para in exec_narr.split("\n\n"):
                if para.strip():
                    elements.append(Paragraph(para.strip(), body_style))
                    elements.append(Spacer(1, 4))
        else:
            # Fallback to hardcoded summary
            summary_text = f"Analysis of {len(context.variances)} material variances for {context.period_id}."
            elements.append(Paragraph(summary_text, body_style))

        # Section Narratives
        if context.section_narratives:
            elements.append(Spacer(1, 8))
            for section in context.section_narratives:
                s_name = section.get("section_name") or section.get("sectionName", "")
                s_narr = section.get("narrative", "")
                if s_name and s_narr:
                    elements.append(Paragraph(f"{s_name}: {s_narr}", body_style))
                    elements.append(Spacer(1, 4))

        # Key Risks
        risks = context.executive_summary.get("key_risks") or context.executive_summary.get("keyRisks", [])
        if risks:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("Key Risks", heading_style))
            for risk in risks:
                r_text = risk.get("risk", str(risk)) if isinstance(risk, dict) else str(risk)
                elements.append(Paragraph(f"• {r_text}", body_style))

        elements.append(Spacer(1, 12))

        # Top Variances Table
        elements.append(Paragraph("Material Variances (Top 15)", heading_style))
        sorted_vars = sorted(context.variances, key=lambda v: abs(v.get("variance_amount", 0)), reverse=True)[:15]
        var_data = [["Account", "BU", "Variance $", "%", "Narrative"]]
        for v in sorted_vars:
            var_data.append([
                v.get("account_name", v.get("account_id", ""))[:30],
                v.get("bu_id", "").replace("_", " ").title()[:15],
                f"${v.get('variance_amount', 0):,.0f}",
                f"{v.get('variance_pct', 0):.1f}%",
                v.get("narrative_oneliner", "")[:50],
            ])
        var_table = Table(var_data, colWidths=[100, 70, 70, 50, 150])
        var_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COBALT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(var_table)
        elements.append(Spacer(1, 12))

        # Risk Flags
        if context.netting_alerts or context.trend_alerts:
            elements.append(Paragraph("Risk Flags", heading_style))
            for alert in (context.netting_alerts or [])[:3]:
                elements.append(Paragraph(
                    f"Netting: {alert.get('left', '')} / {alert.get('right', '')} (Net: {alert.get('net', '')})",
                    body_style,
                ))
            for alert in (context.trend_alerts or [])[:3]:
                elements.append(Paragraph(
                    f"Trend: {alert.get('description', '')} - {alert.get('projection', '')}",
                    body_style,
                ))

        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Marsh Vantage - Confidential - Generated by AI", small_style))

        doc.build(elements)
        return buffer.getvalue()
