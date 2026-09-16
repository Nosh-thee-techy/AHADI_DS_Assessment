"""Briefing copy. Short sentences. No clinic jargon."""

from __future__ import annotations

import html

import pandas as pd

from dashboard.components.i18n import t
from dashboard.components.prepare import county_rank, format_value, ordinal

PLAIN_UNITS = {
    "child_density": "children under 5 per km²",
    "child_dependency_ratio": "children under 5 for every 100 people aged 15–64",
    "elderly_dependency_ratio": "people aged 65+ for every 100 people aged 15–64",
    "dependency_ratio": "children under 5 plus people 65+ for every 100 aged 15–64",
    "pct_children": "% of people under 5",
    "pct_elderly": "% of people aged 65+",
    "total_population": "people",
    "children_under_5": "children under 5",
    "elderly_65plus": "people aged 65+",
    "growth_pct": "% growth since 2021",
    "sex_ratio": "males per 100 females",
}


def county_briefing(row: pd.Series, national: pd.Series, column: str, indicator_label: str) -> list[tuple[str, str]]:
    name = str(row["county_label"])
    child_gap = row["pct_children"] - national["pct_children"]
    elderly_gap = row["pct_elderly"] - national["pct_elderly"]
    mapped = format_value(row[column], column)
    nat_mapped = format_value(national[column], column)
    unit = PLAIN_UNITS[column]

    first = (
        "On this map",
        f"{name} is {mapped} {unit}. Kenya as a whole is {nat_mapped}.",
    )
    if child_gap >= 1.5:
        second = (
            "Who lives here",
            f"{row['pct_children']:.1f}% of people here are under 5. Kenya is {national['pct_children']:.1f}%. "
            "This county needs vaccines, under-five clinics, and food programmes more than extra old-age wards.",
        )
    elif elderly_gap >= 0.8:
        second = (
            "Who lives here",
            f"{row['pct_elderly']:.1f}% of people here are 65 or older. Kenya is {national['pct_elderly']:.1f}%. "
            "Heart disease, diabetes, and care for older people will take more of the county budget.",
        )
    else:
        second = (
            "Who lives here",
            f"The age mix is close to Kenya ({row['pct_children']:.1f}% under 5, {row['pct_elderly']:.1f}% aged 65+). "
            f"The raw numbers still matter: {row['children_under_5']:,.0f} children under 5 "
            f"and {row['elderly_65plus']:,.0f} people aged 65+.",
        )
    return [first, second]


def kenya_briefing(frame: pd.DataFrame, year: int, column: str, indicator_label: str) -> list[tuple[str, str]]:
    child = ", ".join(frame.nlargest(3, "pct_children")["county_label"].tolist())
    old = ", ".join(frame.nlargest(3, "pct_elderly")["county_label"].tolist())
    dense = ", ".join(frame.nlargest(3, "child_density")["county_label"].tolist())
    young = ", ".join(frame.nlargest(3, "child_dependency_ratio")["county_label"].tolist())
    unit = PLAIN_UNITS[column]
    return [
        (
            "This map",
            f"{indicator_label} in {year} runs from "
            f"{format_value(frame[column].min(), column)} to "
            f"{format_value(frame[column].max(), column)} {unit}.",
        ),
        (
            "Youngest and oldest",
            f"Youngest share under 5: {child}. Oldest share 65+: {old}.",
        ),
        (
            "Density is not youth",
            f"Most children in a small area: {dense}. "
            f"Most children compared with working-age adults: {young}. "
            "A crowded city and a young rural county need different clinics.",
        ),
    ]


def site_header_html() -> str:
    return (
        "<div class='site-header' role='banner'>"
        f"<p class='kicker'>{html.escape(t('ministry'))}</p>"
        f"<p class='page-title'>{html.escape(t('title'))}</p>"
        f"<p class='site-header-tag'>{html.escape(t('header.tag'))}</p>"
        f"<p class='site-header-years'>{html.escape(t('header.kind'))} · {html.escape(t('header.meta'))}</p>"
        "</div>"
    )


def site_footer_html() -> str:
    columns = (
        ("footer.source", "footer.source_body"),
        ("footer.read", "footer.read_body"),
        ("footer.note", "footer.note_body"),
    )
    cells = "".join(
        "<div>"
        f"<p class='kicker'>{html.escape(t(kicker))}</p>"
        f"<p>{html.escape(t(body))}</p>"
        "</div>"
        for kicker, body in columns
    )
    return f"<div class='site-footer' role='contentinfo'><div class='site-footer-inner'>{cells}</div></div>"


def how_to_html() -> str:
    return f"""
    <div class="how">
      <p class="kicker">{html.escape(t("how.kicker"))}</p>
      <p class="how-lede">{html.escape(t("how.lede"))}</p>
      <ol class="how-steps">
        <li><span>1</span><div><strong>{html.escape(t("how.1_title"))}</strong> {html.escape(t("how.1_body"))}</div></li>
        <li><span>2</span><div><strong>{html.escape(t("how.2_title"))}</strong> {html.escape(t("how.2_body"))}</div></li>
        <li><span>3</span><div><strong>{html.escape(t("how.3_title"))}</strong> {html.escape(t("how.3_body"))}</div></li>
      </ol>
    </div>
    """


def _delta_pp(value: float, other: float, label: str) -> tuple[str, str]:
    gap = float(value) - float(other)
    if abs(gap) < 0.05:
        return "is-flat", t("delta.same", label=label)
    css = "is-up" if gap > 0 else "is-down"
    return css, t("delta.vs", gap=gap, label=label)


def place_metrics_html(
    row: pd.Series,
    baseline: pd.Series,
    place: str,
    baseline_label: str,
) -> str:
    """High-contrast KPI cards for the place on the pyramid, vs the comparison line."""
    same = place == baseline_label
    child_css, child_delta = _delta_pp(row["pct_children"], baseline["pct_children"], baseline_label)
    old_css, old_delta = _delta_pp(row["pct_elderly"], baseline["pct_elderly"], baseline_label)
    dep_css, dep_delta = _delta_pp(row["child_dependency_ratio"], baseline["child_dependency_ratio"], baseline_label)
    of_compare = ""
    if not same and baseline["total_population"]:
        share = row["total_population"] / baseline["total_population"] * 100
        of_compare = t("kpi.of", pct=f"{share:.1f}", place=baseline_label)
    elif same:
        of_compare = t("kpi.total_people")
    people_sub = of_compare if of_compare else t("kpi.people", n=f"{row['total_population']:,.0f}")

    def card(kicker: str, hero: str, sub: str, delta: str = "", css: str = "") -> str:
        delta_html = f"<p class='kpi-delta {css}'>{html.escape(delta)}</p>" if delta else ""
        return (
            "<article class='place-kpi'>"
            f"<p class='kicker'>{html.escape(kicker)}</p>"
            f"<p class='kpi-value'>{html.escape(hero)}</p>"
            f"<p class='kpi-sub'>{html.escape(sub)}</p>"
            f"{delta_html}"
            "</article>"
        )

    cards = [
        card(t("kpi.population"), format_value(row["total_population"], "total_population"), people_sub),
        card(
            t("place.under5"),
            f"{row['pct_children']:.1f}%",
            t("kpi.children", n=f"{row['children_under_5']:,.0f}")
            if same
            else f"{baseline_label} {baseline['pct_children']:.1f}%",
            "" if same else child_delta,
            child_css,
        ),
        card(
            t("place.old"),
            f"{row['pct_elderly']:.1f}%",
            t("kpi.people", n=f"{row['elderly_65plus']:,.0f}")
            if same
            else f"{baseline_label} {baseline['pct_elderly']:.1f}%",
            "" if same else old_delta,
            old_css,
        ),
        card(
            t("kpi.dependency"),
            f"{row['child_dependency_ratio']:.1f}",
            t("kpi.dep_unit")
            if same
            else f"{baseline_label} {baseline['child_dependency_ratio']:.1f}",
            "" if same else dep_delta,
            dep_css,
        ),
    ]
    return f"<div class='place-kpis'>{''.join(cards)}</div>"


def who_lives_here_html(
    row: pd.Series,
    baseline: pd.Series,
    place: str,
    baseline_label: str,
    frame: pd.DataFrame | None = None,
) -> str:
    """Scanable takeaways. Numbers first, not a paragraph."""
    if place == baseline_label:
        items = [
            f"<li><strong>{row['pct_children']:.1f}%</strong> {html.escape(t('who.under5'))}</li>",
            f"<li><strong>{row['pct_elderly']:.1f}%</strong> {html.escape(t('who.old'))}</li>",
            f"<li><strong>{row['child_dependency_ratio']:.1f}</strong> {html.escape(t('who.dep'))}</li>",
            (
                f"<li><strong>{row['children_under_5']:,.0f}</strong> {html.escape(t('who.child_n'))} · "
                f"<strong>{row['elderly_65plus']:,.0f}</strong> {html.escape(t('who.old_n'))}</li>"
            ),
        ]
        if frame is not None and len(frame):
            young = ", ".join(frame.nlargest(3, "pct_children")["county_label"].tolist())
            old = ", ".join(frame.nlargest(3, "pct_elderly")["county_label"].tolist())
            items.append(f"<li>{html.escape(t('who.youngest', names=young))}</li>")
            items.append(f"<li>{html.escape(t('who.oldest', names=old))}</li>")
    else:
        items = [
            (
                f"<li><strong>{row['pct_children']:.1f}%</strong> {html.escape(t('who.under5'))} · "
                f"{html.escape(baseline_label)} {baseline['pct_children']:.1f}%</li>"
            ),
            (
                f"<li><strong>{row['pct_elderly']:.1f}%</strong> {html.escape(t('who.old'))} · "
                f"{html.escape(baseline_label)} {baseline['pct_elderly']:.1f}%</li>"
            ),
            (
                f"<li><strong>{row['child_dependency_ratio']:.1f}</strong> {html.escape(t('who.dep_short'))} · "
                f"{html.escape(baseline_label)} {baseline['child_dependency_ratio']:.1f}</li>"
            ),
            (
                f"<li><strong>{row['children_under_5']:,.0f}</strong> {html.escape(t('who.child_n'))} · "
                f"<strong>{row['elderly_65plus']:,.0f}</strong> {html.escape(t('who.old_n'))}</li>"
            ),
        ]
    return (
        "<div class='takes-wrap'>"
        f"<p class='kicker'>{html.escape(t('who'))}</p>"
        f"<ul class='takes'>{''.join(items)}</ul>"
        "</div>"
    )


def interpretation_cards(
    row: pd.Series,
    national: pd.Series,
    place: str,
    frame: pd.DataFrame,
) -> list[tuple[str, str, str, str]]:
    """Short health reading. Numbers from this view, not a generic essay."""
    child_gap = float(row["pct_children"]) - float(national["pct_children"])
    elderly_gap = float(row["pct_elderly"]) - float(national["pct_elderly"])
    if child_gap >= 1.5:
        place_body = t(
            "interpret.place_child",
            pct=f"{row['pct_children']:.1f}",
            kenya=f"{national['pct_children']:.1f}",
            n=f"{row['children_under_5']:,.0f}",
        )
    elif elderly_gap >= 0.8:
        place_body = t(
            "interpret.place_old",
            pct=f"{row['pct_elderly']:.1f}",
            kenya=f"{national['pct_elderly']:.1f}",
            n=f"{row['elderly_65plus']:,.0f}",
        )
    else:
        place_body = t(
            "interpret.place_both",
            child=f"{row['pct_children']:.1f}",
            old=f"{row['pct_elderly']:.1f}",
            n_child=f"{row['children_under_5']:,.0f}",
            n_old=f"{row['elderly_65plus']:,.0f}",
        )
    young = ", ".join(frame.nlargest(3, "pct_children")["county_label"].tolist())
    old = ", ".join(frame.nlargest(3, "pct_elderly")["county_label"].tolist())
    dense = ", ".join(frame.nlargest(3, "child_density")["county_label"].tolist())
    dep = ", ".join(frame.nlargest(3, "child_dependency_ratio")["county_label"].tolist())
    return [
        (
            t("interpret.dep"),
            f"{row['child_dependency_ratio']:.1f}",
            t("interpret.dep_sub", value=f"{row['child_dependency_ratio']:.1f}"),
            t("interpret.dep_body"),
        ),
        (
            t("interpret.place", place=place),
            place,
            f"{row['pct_children']:.1f}% · {row['pct_elderly']:.1f}%",
            place_body,
        ),
        (
            t("interpret.policy"),
            str(frame.nlargest(1, "pct_children").iloc[0]["county_label"]),
            t("interpret.policy_sub"),
            t("interpret.policy_body", young=young, old=old, dense=dense, dep=dep),
        ),
    ]


def table_analytics(
    frame: pd.DataFrame,
    national: pd.Series,
    column: str,
    indicator_label: str,
    focus_county: str | None = None,
) -> list[tuple[str, str, str, str]]:
    """Open cards that describe the county table. Each card is kicker, hero, sub, body."""
    n = len(frame)
    kenya_val = float(national[column])
    above = int((frame[column] > kenya_val).sum())
    high = frame.nlargest(1, column).iloc[0]
    low = frame.nsmallest(1, column).iloc[0]
    unit = t(f"unit.{column}") if column in PLAIN_UNITS else PLAIN_UNITS.get(column, "")
    top = ", ".join(frame.nlargest(3, column)["county_label"].tolist())
    bottom = ", ".join(frame.nsmallest(3, column)["county_label"].tolist())
    cards = [
        (
            t("analytics.high"),
            str(high["county_label"]),
            f"{format_value(high[column], column)} {unit}",
            t(
                "analytics.high_body",
                indicator=indicator_label.lower(),
                next=", ".join(frame.nlargest(3, column)["county_label"].tolist()[1:]),
            ),
        ),
        (
            t("analytics.low"),
            str(low["county_label"]),
            f"{format_value(low[column], column)} {unit}",
            t(
                "analytics.low_body",
                next=", ".join(frame.nsmallest(3, column)["county_label"].tolist()[1:]),
            ),
        ),
        (
            t("analytics.above"),
            f"{above} of {n}",
            t("analytics.above_sub", value=format_value(kenya_val, column), unit=unit),
            t(
                "analytics.above_body",
                above=above,
                below=n - above,
                indicator=indicator_label.lower(),
                top=top,
                bottom=bottom,
            ),
        ),
    ]
    if focus_county and focus_county != "Kenya":
        rank, total = county_rank(frame, focus_county, column)
        row = frame.loc[frame["county"] == focus_county].iloc[0]
        median = float(frame[column].median())
        side = t("analytics.above_side") if row[column] > median else t("analytics.below_side")
        cards.append(
            (
                t("analytics.pinned"),
                str(row["county_label"]),
                f"{ordinal(rank)} of {total}",
                t(
                    "analytics.pinned_body",
                    value=format_value(row[column], column),
                    unit=unit,
                    side=side,
                    median=format_value(median, column),
                ),
            )
        )
    else:
        dense = frame.nlargest(1, "child_density").iloc[0]
        young = frame.nlargest(1, "child_dependency_ratio").iloc[0]
        cards.append(
            (
                t("analytics.mix"),
                str(dense["county_label"]),
                t("analytics.mix_sub"),
                t(
                    "analytics.mix_body",
                    name=young["county_label"],
                    value=f"{young['child_dependency_ratio']:.1f}",
                ),
            )
        )
    return cards


def _table_row(rank: str, name: str, mapped: str, people: str, children: str, elderly: str, dep: str, css: str) -> str:
    klass = f" class='{css}'" if css else ""
    return (
        f"<tr{klass}>"
        f"<td class='num'>{html.escape(rank)}</td>"
        f"<td>{html.escape(name)}</td>"
        f"<td class='num'>{html.escape(mapped)}</td>"
        f"<td class='num'>{html.escape(people)}</td>"
        f"<td class='num'>{html.escape(children)}</td>"
        f"<td class='num'>{html.escape(elderly)}</td>"
        f"<td class='num'>{html.escape(dep)}</td>"
        "</tr>"
    )


def county_table_html(
    frame: pd.DataFrame,
    column: str,
    indicator_label: str,
    highlight: str | None = None,
    national: pd.Series | None = None,
) -> str:
    ordered = frame.sort_values(column, ascending=False)
    rows = []
    if national is not None:
        rows.append(
            _table_row(
                "—",
                "Kenya",
                format_value(national[column], column),
                f"{national['total_population']:,.0f}",
                f"{national['pct_children']:.1f}%",
                f"{national['pct_elderly']:.1f}%",
                f"{national['child_dependency_ratio']:.1f}",
                "is-kenya",
            )
        )
    for i, row in enumerate(ordered.itertuples(), start=1):
        css = "is-pinned" if highlight and row.county == highlight else ""
        rows.append(
            _table_row(
                str(i),
                str(row.county_label),
                format_value(getattr(row, column), column),
                f"{row.total_population:,.0f}",
                f"{row.pct_children:.1f}%",
                f"{row.pct_elderly:.1f}%",
                f"{row.child_dependency_ratio:.1f}",
                css,
            )
        )
    return (
        "<div class='table-wrap'>"
        "<table class='county-table'>"
        "<thead><tr>"
        "<th class='num'>#</th>"
        f"<th>{html.escape(t('table.county'))}</th>"
        f"<th class='num'>{html.escape(indicator_label)}</th>"
        f"<th class='num'>{html.escape(t('table.people'))}</th>"
        f"<th class='num'>{html.escape(t('table.under5'))}</th>"
        f"<th class='num'>{html.escape(t('table.old'))}</th>"
        f"<th class='num'>{html.escape(t('table.dep'))}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def cards_html(cards: list[tuple]) -> str:
    parts = ["<div class='cards'>"]
    for card in cards:
        if len(card) == 2:
            title, body = card
            hero = sub = ""
        else:
            title, hero, sub, body = card
        hero_html = f"<p class='card-hero'>{html.escape(hero)}</p>" if hero else ""
        sub_html = f"<p class='card-sub'>{html.escape(sub)}</p>" if sub else ""
        parts.append(
            "<article class='card'>"
            f"<p class='kicker'>{html.escape(title)}</p>"
            f"{hero_html}"
            f"{sub_html}"
            f"<p>{html.escape(body)}</p>"
            "</article>"
        )
    parts.append("</div>")
    return "".join(parts)


def inspector_html(
    row: pd.Series | None,
    column: str,
    indicator_label: str,
    year: int,
    rank: str,
    national: pd.Series | None = None,
    baseline_label: str = "Kenya",
) -> str:
    if row is None or str(row.get("county", "Kenya")) == "Kenya":
        return (
            "<aside class='peek peek-empty'>"
            f"<p class='kicker'>{html.escape(t('county_card'))}</p>"
            f"<p class='place-name'>{html.escape(t('click_map'))}</p>"
            f"<p class='peek-hint'>{html.escape(t('click_hint'))}</p>"
            "</aside>"
        )
    name = html.escape(str(row["county_label"]))
    hero = html.escape(format_value(row[column], column))
    vs = ""
    if national is not None:
        vs = (
            f"<p class='peek-vs'>{html.escape(baseline_label)} "
            f"{html.escape(format_value(national[column], column))}</p>"
            f"<p class='peek-vs'><strong>{row['pct_children']:.1f}%</strong> {html.escape(t('who.under5'))} · "
            f"{html.escape(baseline_label)} {national['pct_children']:.1f}%</p>"
        )
    return (
        "<aside class='peek'>"
        f"<p class='kicker'>{html.escape(t('county'))} · {year}</p>"
        f"<p class='place-name'>{name}</p>"
        f"<p class='rankline'>{html.escape(rank)}</p>"
        f"<p class='peek-hero'>{hero}<span>{html.escape(indicator_label)}</span></p>"
        f"{vs}"
        "<dl>"
        f"<div><dt>{html.escape(t('peek.people'))}</dt><dd>{row['total_population']:,.0f}</dd></div>"
        f"<div><dt>{html.escape(t('peek.under5'))}</dt><dd>{row['children_under_5']:,.0f} · {row['pct_children']:.1f}%</dd></div>"
        f"<div><dt>{html.escape(t('peek.old'))}</dt><dd>{row['elderly_65plus']:,.0f} · {row['pct_elderly']:.1f}%</dd></div>"
        f"<div><dt>{html.escape(t('peek.dep'))}</dt><dd>{row['child_dependency_ratio']:.1f}</dd></div>"
        "</dl>"
        "</aside>"
    )


def rank_line(frame: pd.DataFrame, county: str, column: str, indicator_label: str) -> str:
    rank, n = county_rank(frame, county, column)
    if rank == 1:
        return t("rank.highest", indicator=indicator_label.lower(), n=n)
    if rank == n:
        return t("rank.lowest", indicator=indicator_label.lower(), n=n)
    return t("rank.mid", rank=ordinal(rank), n=n, indicator=indicator_label.lower())


def extremes_line(high: list[tuple[str, str]], low: list[tuple[str, str]]) -> str:
    top = ", ".join(name for name, _ in high[:3])
    bottom = ", ".join(name for name, _ in low[:3])
    return t("extremes", top=top, bottom=bottom)


def fault_copy(exc: BaseException) -> tuple[str, str]:
    """Headline and what to do. Dry on purpose."""
    name = type(exc).__name__
    text = str(exc)
    if "WidgetAlreadyInstantiated" in name or "cannot be modified after the widget" in text:
        return t("fault.widget"), t("fault.widget_advice")
    if isinstance(exc, ImportError):
        return t("fault.import"), t("fault.import_advice")
    if isinstance(exc, FileNotFoundError) or "Processed data is missing" in text:
        return t("fault.missing"), t("fault.missing_advice")
    return t("fault.generic"), t("fault.generic_advice")
