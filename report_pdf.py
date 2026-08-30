from io import BytesIO
from datetime import datetime
import re
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)


def _fmt(value, digits=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _safe_text(value):
    """Convert arbitrary values to ReportLab-safe text."""
    if value is None:
        return ""
    return escape(str(value))


def _markdown_to_reportlab(value):
    """
    Convert the small amount of markdown produced by the LLM into
    ReportLab markup. This prevents **bold** from appearing literally
    in the PDF and safely escapes user/model text.
    """
    text = "" if value is None else str(value)

    # Escape first so model text cannot be interpreted as XML/HTML.
    text = escape(text)

    # Then restore the markdown constructs we intentionally support.
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br/>")

    return text


def _draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(40, 25, "Business AI - Business Intelligence Report")
    canvas.drawRightString(A4[0] - 40, 25, f"Page {doc.page}")
    canvas.restoreState()


def create_report_pdf(
    kpi,
    date,
    report,
    narratives,
    evidence,
    recommendations,
    graph_buffer=None,
):
    """
    Build the PDF from the SAME computed report object used by the API.

    Important:
    This function intentionally does not recalculate root causes.
    It only renders the supplied report/narratives/evidence/recommendations.
    """

    report = report or {}
    narratives = narratives or {}
    evidence = evidence or {}
    recommendations = recommendations or []

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        spaceAfter=8,
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        spaceAfter=5,
    )

    story = []

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            f"{_safe_text(kpi).upper()} Business Analysis Report",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Anomaly date: {_safe_text(date)} | "
            f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
            subtitle_style,
        )
    )

    # -----------------------------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------------------------

    story.append(Paragraph("Executive Summary", heading_style))

    drivers = report.get("drivers") or {}
    confidence = report.get("confidence") or {}

    primary_driver = drivers.get("primary_driver")
    primary_change = drivers.get("primary_driver_pct_change")

    summary_text = (
        f"The selected KPI was analyzed for {_safe_text(date)}. "
        f"The strongest identified driver was "
        f"<b>{_safe_text(primary_driver or 'N/A')}</b>, "
        f"which changed by {_fmt(primary_change)}% "
        f"relative to the comparison baseline. "
        f"Overall analysis confidence is "
        f"<b>{_safe_text(confidence.get('confidence', 'N/A'))}</b>."
    )

    story.append(Paragraph(summary_text, body_style))

    # -----------------------------------------------------
    # TARGET KPI SNAPSHOT
    # -----------------------------------------------------

    target_kpi = drivers.get("target_kpi", kpi)
    target_today = drivers.get("target_today_value")
    target_baseline = drivers.get("target_baseline_avg")
    target_change = drivers.get("target_kpi_pct_change")

    if any(v is not None for v in (target_today, target_baseline, target_change)):
        story.append(Paragraph("KPI Snapshot", heading_style))

        snapshot_rows = [
            ["Metric", "Value"],
            ["KPI", _safe_text(target_kpi)],
            ["Current", _fmt(target_today)],
            ["Baseline", _fmt(target_baseline)],
            ["% Change", f"{_fmt(target_change)}%"],
        ]

        snapshot_table = Table(
            snapshot_rows,
            colWidths=[2.5 * inch, 2.0 * inch],
            repeatRows=1,
        )
        snapshot_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(snapshot_table)
        story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # NET PROFIT SNAPSHOT
    # -----------------------------------------------------

    net_profit = report.get("net_profit_snapshot")

    if isinstance(net_profit, dict):
        story.append(Paragraph("Profitability Snapshot", heading_style))

        profit_rows = [
            ["Metric", "Value"],
            ["Revenue", f"${_fmt(net_profit.get('revenue'))}"],
            ["Cost", f"${_fmt(net_profit.get('cost'))}"],
            ["Net Profit", f"${_fmt(net_profit.get('net_profit'))}"],
            [
                "Status",
                "Profit" if net_profit.get("is_profit") is True
                else "Loss" if net_profit.get("is_profit") is False
                else "N/A",
            ],
        ]

        if net_profit.get("missing_cost_lines") is not None:
            profit_rows.append(
                [
                    "Lines with missing cost",
                    _safe_text(net_profit.get("missing_cost_lines")),
                ]
            )

        profit_table = Table(
            profit_rows,
            colWidths=[2.5 * inch, 2.0 * inch],
            repeatRows=1,
        )
        profit_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(profit_table)
        story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # ROOT CAUSE / DRIVER TABLE
    # -----------------------------------------------------

    story.append(Paragraph("Root Cause Analysis", heading_style))

    driver_rows = [
        ["Factor", "Type", "Current", "Baseline", "% Change", "Contribution"]
    ]

    for driver in drivers.get("drivers_ranked", []) or []:
        factor = driver.get("factor", "")
        driver_type = driver.get("driver_type", "KPI")

        contribution = driver.get("contribution_pct")
        contribution_text = (
            f"{_fmt(contribution, 1)}%"
            if contribution is not None
            else "N/A"
        )

        driver_rows.append(
            [
                _safe_text(factor),
                _safe_text(driver_type),
                _fmt(driver.get("today_value"), 4),
                _fmt(driver.get("baseline_avg"), 4),
                f"{_fmt(driver.get('pct_change'))}%",
                contribution_text,
            ]
        )

    if len(driver_rows) == 1:
        driver_rows.append(
            ["No driver data available", "", "", "", "", ""]
        )

    driver_table = Table(
        driver_rows,
        colWidths=[
            1.45 * inch,
            0.75 * inch,
            1.0 * inch,
            1.0 * inch,
            0.9 * inch,
            0.9 * inch,
        ],
        repeatRows=1,
    )

    driver_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(driver_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # PRODUCT DRIVER DETAILS
    # -----------------------------------------------------

    product_drivers = [
        d for d in (drivers.get("drivers_ranked", []) or [])
        if d.get("driver_type") == "product"
    ]

    if product_drivers:
        story.append(Paragraph("Product-Level Revenue Drivers", heading_style))

        product_rows = [
            ["Product", "Revenue Today", "Baseline", "% Change", "Contribution", "Volume Effect", "Price Effect"]
        ]

        for driver in product_drivers:
            product_rows.append(
                [
                    _safe_text(driver.get("factor", "")),
                    f"${_fmt(driver.get('today_value'))}",
                    f"${_fmt(driver.get('baseline_avg'))}",
                    f"{_fmt(driver.get('pct_change'))}%",
                    f"{_fmt(driver.get('contribution_pct'), 1)}%",
                    f"${_fmt(driver.get('volume_effect'))}",
                    f"${_fmt(driver.get('price_effect'))}",
                ]
            )

        product_table = Table(
            product_rows,
            colWidths=[
                1.25 * inch,
                1.0 * inch,
                0.9 * inch,
                0.75 * inch,
                0.8 * inch,
                0.85 * inch,
                0.75 * inch,
            ],
            repeatRows=1,
        )

        product_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        story.append(product_table)
        story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    story.append(Paragraph("Confidence", heading_style))

    confidence_text = (
        f"<b>Level:</b> {_safe_text(confidence.get('confidence', 'N/A'))}<br/>"
        f"<b>Score:</b> {_fmt(confidence.get('score'))}<br/>"
        f"<b>Abstain:</b> {_safe_text(confidence.get('should_abstain', 'N/A'))}<br/>"
        f"<b>Reason:</b> {_safe_text(confidence.get('reason', 'N/A'))}"
    )

    story.append(Paragraph(confidence_text, body_style))

    # -----------------------------------------------------
    # MULTI KPI
    # -----------------------------------------------------

    multi = report.get("multi_kpi_overlap") or {}

    story.append(Paragraph("Other Affected KPIs", heading_style))

    affected = multi.get("affected_kpis") or []

    if affected:
        multi_rows = [["KPI", "Z-score"]]

        for item in affected:
            multi_rows.append(
                [
                    _safe_text(item.get("kpi", "")),
                    _fmt(item.get("z_score")),
                ]
            )

        multi_table = Table(
            multi_rows,
            colWidths=[2.5 * inch, 1.5 * inch],
        )

        multi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                ]
            )
        )

        story.append(multi_table)
    else:
        story.append(
            Paragraph(
                "No other KPI anomalies were identified.",
                body_style,
            )
        )

    # -----------------------------------------------------
    # GRAPH
    # -----------------------------------------------------

    if graph_buffer:
        story.append(Paragraph("KPI Trend and Anomaly", heading_style))

        graph_buffer.seek(0)

        story.append(
            Image(
                graph_buffer,
                width=7.0 * inch,
                height=3.0 * inch,
            )
        )

    # -----------------------------------------------------
    # NARRATIVES
    # -----------------------------------------------------

    story.append(PageBreak())
    story.append(Paragraph("AI Business Narrative", heading_style))

    if narratives:
        for persona_key, result in narratives.items():
            if not isinstance(result, dict):
                continue

            display_name = result.get(
                "persona_display_name",
                persona_key,
            )

            narrative = result.get("narrative", "")

            story.append(
                Paragraph(
                    _safe_text(display_name),
                    styles["Heading3"],
                )
            )

            if narrative:
                story.append(
                    Paragraph(
                        _markdown_to_reportlab(narrative),
                        body_style,
                    )
                )
            else:
                story.append(
                    Paragraph(
                        "No narrative was available.",
                        body_style,
                    )
                )
    else:
        story.append(
            Paragraph(
                "No AI narratives were generated.",
                body_style,
            )
        )

    # -----------------------------------------------------
    # SUPPORTING EVIDENCE
    # -----------------------------------------------------

    story.append(Paragraph("Supporting Evidence", heading_style))

    evidence_items = evidence.get("evidence", []) if isinstance(evidence, dict) else []

    if evidence_items:
        for index, item in enumerate(evidence_items, start=1):
            text = item.get("text", "")
            source = item.get("source", "Unknown")
            item_date = item.get("date", "Unknown")

            story.append(
                Paragraph(
                    f"<b>{index}. {_safe_text(item_date)} - "
                    f"{_safe_text(source)}</b>: "
                    f"{_markdown_to_reportlab(text)}",
                    body_style,
                )
            )
    else:
        story.append(
            Paragraph(
                "No supporting evidence was retrieved.",
                body_style,
            )
        )

    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    story.append(Paragraph("Recommended Actions", heading_style))

    if recommendations:
        for index, recommendation in enumerate(recommendations[:3], start=1):
            recommendation = recommendation or {}

            action = recommendation.get("action", "")
            lever = recommendation.get("lever", "N/A")
            owner = recommendation.get("owner", "N/A")
            impact = recommendation.get("expected_impact", "N/A")
            monitor = recommendation.get("monitor", "N/A")
            final_score = recommendation.get("final_score")
            source = recommendation.get("source", "rule_based")

            score_text = (
                f"<b>Final score:</b> {_fmt(final_score)}<br/>"
                if final_score is not None
                else ""
            )

            story.append(
                Paragraph(
                    f"<b>#{index} {_safe_text(action)}</b><br/>"
                    f"<b>Lever:</b> {_safe_text(lever)}<br/>"
                    f"<b>Owner:</b> {_safe_text(owner)}<br/>"
                    f"<b>Expected impact:</b> {_safe_text(impact)}<br/>"
                    f"<b>Monitor:</b> {_safe_text(monitor)}<br/>"
                    f"<b>Source:</b> {_safe_text(source)}<br/>"
                    f"{score_text}",
                    body_style,
                )
            )
    else:
        story.append(
            Paragraph(
                "No recommendations were generated.",
                body_style,
            )
        )

    # -----------------------------------------------------
    # BUILD
    # -----------------------------------------------------

    doc.build(
        story,
        onFirstPage=_draw_header_footer,
        onLaterPages=_draw_header_footer,
    )

    buffer.seek(0)
    return buffer
