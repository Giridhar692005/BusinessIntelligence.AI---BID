from io import BytesIO
from datetime import datetime

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

    story = []

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            f"{kpi.upper()} Business Analysis Report",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Anomaly date: {date} | Generated: {datetime.now():%Y-%m-%d %H:%M}",
            subtitle_style,
        )
    )

    # -----------------------------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------------------------

    story.append(
        Paragraph("Executive Summary", heading_style)
    )

    drivers = report.get("drivers", {})
    confidence = report.get("confidence", {})

    primary_driver = drivers.get("primary_driver")
    primary_change = drivers.get("primary_driver_pct_change")

    summary_text = (
        f"The selected KPI was analyzed for {date}. "
        f"The strongest identified driver was "
        f"<b>{primary_driver or 'N/A'}</b>, "
        f"which changed by {_fmt(primary_change)}% "
        f"relative to the comparison baseline. "
        f"Overall analysis confidence is "
        f"<b>{confidence.get('confidence', 'N/A')}</b>."
    )

    story.append(
        Paragraph(
            summary_text,
            body_style,
        )
    )

    # -----------------------------------------------------
    # ROOT CAUSE / DRIVER TABLE
    # -----------------------------------------------------

    story.append(
        Paragraph("Root Cause Analysis", heading_style)
    )

    driver_rows = [
        [
            "Factor",
            "Current",
            "Baseline",
            "% Change",
        ]
    ]

    for driver in drivers.get("drivers_ranked", []):

        driver_rows.append(
            [
                str(driver.get("factor", "")),
                _fmt(driver.get("today_value"), 4),
                _fmt(driver.get("baseline_avg"), 4),
                f"{_fmt(driver.get('pct_change'))}%",
            ]
        )

    if len(driver_rows) == 1:
        driver_rows.append(
            ["No driver data available", "", "", ""]
        )

    driver_table = Table(
        driver_rows,
        colWidths=[2.1 * inch, 1.15 * inch, 1.15 * inch, 1.15 * inch],
        repeatRows=1,
    )

    driver_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(driver_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    story.append(
        Paragraph("Confidence", heading_style)
    )

    confidence_text = (
        f"<b>Level:</b> {confidence.get('confidence', 'N/A')}<br/>"
        f"<b>Score:</b> {_fmt(confidence.get('score'))}<br/>"
        f"<b>Abstain:</b> {confidence.get('should_abstain', 'N/A')}<br/>"
        f"<b>Reason:</b> {confidence.get('reason', 'N/A')}"
    )

    story.append(
        Paragraph(
            confidence_text,
            body_style,
        )
    )

    # -----------------------------------------------------
    # MULTI KPI
    # -----------------------------------------------------

    multi = report.get(
        "multi_kpi_overlap",
        {}
    )

    story.append(
        Paragraph("Other Affected KPIs", heading_style)
    )

    affected = multi.get(
        "affected_kpis",
        []
    )

    if affected:

        multi_rows = [["KPI", "Z-score"]]

        for item in affected:

            multi_rows.append(
                [
                    str(item.get("kpi", "")),
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

        story.append(
            Paragraph(
                "KPI Trend and Anomaly",
                heading_style,
            )
        )

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

    story.append(
        Paragraph(
            "AI Business Narrative",
            heading_style,
        )
    )

    for persona_key, result in narratives.items():

        display_name = result.get(
            "persona_display_name",
            persona_key,
        )

        narrative = result.get(
            "narrative",
            "",
        )

        story.append(
            Paragraph(
                display_name,
                styles["Heading3"],
            )
        )

        if narrative:

            story.append(
                Paragraph(
                    narrative.replace("\n", "<br/>"),
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

    # -----------------------------------------------------
    # SUPPORTING EVIDENCE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Supporting Evidence",
            heading_style,
        )
    )

    evidence_items = (
        evidence.get("evidence", [])
        if evidence
        else []
    )

    if evidence_items:

        for index, item in enumerate(
            evidence_items,
            start=1,
        ):

            text = item.get(
                "text",
                "",
            )

            source = item.get(
                "source",
                "Unknown",
            )

            item_date = item.get(
                "date",
                "Unknown",
            )

            story.append(
                Paragraph(
                    f"<b>{index}. {item_date} - {source}</b>: {text}",
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

    story.append(
        Paragraph(
            "Recommended Actions",
            heading_style,
        )
    )

    if recommendations:

        for index, recommendation in enumerate(
            recommendations[:3],
            start=1,
        ):

            action = recommendation.get(
                "action",
                "",
            )

            lever = recommendation.get(
                "lever",
                "N/A",
            )

            owner = recommendation.get(
                "owner",
                "N/A",
            )

            impact = recommendation.get(
                "expected_impact",
                "N/A",
            )

            monitor = recommendation.get(
                "monitor",
                "N/A",
            )

            final_score = recommendation.get(
                "final_score"
            )

            source = recommendation.get(
                "source",
                "rule_based",
            )

            score_text = (
                f"<b>Final score:</b> {_fmt(final_score)}<br/>"
                if final_score is not None
                else ""
            )

            story.append(
                Paragraph(
                    f"<b>#{index} {action}</b><br/>"
                    f"<b>Lever:</b> {lever}<br/>"
                    f"<b>Owner:</b> {owner}<br/>"
                    f"<b>Expected impact:</b> {impact}<br/>"
                    f"<b>Monitor:</b> {monitor}<br/>"
                    f"<b>Source:</b> {source}<br/>"
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