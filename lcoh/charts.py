"""Diagramme: Kostenstruktur (gestapeltes Wasserfalldiagramm) und geordneter Lastverlauf."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from lcoh.waterfall import (BLOCK_CAPEX, BLOCK_INTEREST, BLOCK_OPEX, BLOCK_POWER, BLOCK_REVENUE, BLOCK_STACK,
                            BLOCK_SUBSIDY, Item)

COST_BLOCKS = [BLOCK_CAPEX, BLOCK_OPEX, BLOCK_STACK, BLOCK_POWER, BLOCK_INTEREST]
RELIEF_BLOCKS = [BLOCK_SUBSIDY, BLOCK_REVENUE]
BLOCK_COLORS = {
    BLOCK_CAPEX: "#2f6db5", BLOCK_OPEX: "#1b998b", BLOCK_STACK: "#7b5ea7", BLOCK_POWER: "#e07a1f",
    BLOCK_INTEREST: "#8d6e63", BLOCK_SUBSIDY: "#3f9b4f", BLOCK_REVENUE: "#9aae2c"}
TOTAL_COLOR = "#16324f"
GROSS_LABEL = "Gestehungskosten brutto"
NET_LABEL = "Gestehungskosten"


MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def year_axis(n: int = 8760) -> tuple[np.ndarray, dict]:
    """Zeitachse 1.1. bis 31.12. (Nicht-Schaltjahr) mit Monatsbeschriftung."""
    t0 = np.datetime64("2025-01-01T00:00")
    x = (t0 + np.arange(n) * np.timedelta64(1, "h")).astype("datetime64[ns]")
    starts = [np.datetime64(f"2025-{m:02d}-01T00:00") for m in range(1, 13)]
    axis = dict(tickmode="array", tickvals=starts, ticktext=MONTHS, range=[str(x[0]), str(x[-1])],
                ticks="outside", showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    return x, axis


def de(x: float, n: int = 2) -> str:
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mix(hex_color: str, t: float) -> str:
    """Mischt die Farbe mit Weiß (t = 0: Originalfarbe, t = 1: weiß)."""
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(v + (255 - v) * t) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _shades(block: str, n: int) -> list[str]:
    if n <= 1:
        return [BLOCK_COLORS[block]]
    return [_mix(BLOCK_COLORS[block], 0.65 * k / (n - 1)) for k in range(n)]


def cost_structure_figure(items: list[Item], lcoh: float, detail: bool, height: int = 420,
                          labels_in_bars: bool = True, subsidy_title: str | None = None,
                          gross_label: str | None = None) -> go.Figure:
    """Gestapeltes Wasserfalldiagramm.

    Übersicht (detail=False): ein Balken je Block, der Balken ist aus den Einzelposten zusammengesetzt.
    Detail (detail=True): ein Balken je Einzelposten, eingefärbt nach Block.
    """
    used = [i for i in items if abs(i.eur_per_kg) > 1e-9]
    bars: list[dict] = []  # label, segments [(label, value, color)], total (bool)

    def add_block(block: str) -> None:
        its = [i for i in used if i.block == block]
        if not its:
            return
        cols = _shades(block, len(its))
        if detail:
            for it, col in zip(its, cols):
                bars.append(dict(label=it.label, block=block, segs=[(it.label, it.eur_per_kg, col)], total=False))
        else:
            bars.append(dict(label=block, block=block,
                             segs=[(it.label, it.eur_per_kg, col) for it, col in zip(its, cols)], total=False))

    for b in COST_BLOCKS:
        add_block(b)
    gross = sum(i.eur_per_kg for i in used if i.block in COST_BLOCKS)
    gl = gross_label or GROSS_LABEL
    bars.append(dict(label=gl, block=None, segs=[(gl, gross, TOTAL_COLOR)], total=True))
    for b in RELIEF_BLOCKS:
        add_block(b)
    bars.append(dict(label=NET_LABEL, block=None, segs=[(NET_LABEL, lcoh, TOTAL_COLOR)], total=True))

    if subsidy_title and not detail:
        for bar in bars:
            if bar["block"] == BLOCK_SUBSIDY:
                bar["label"] = subsidy_title
    fig = go.Figure()
    level = 0.0
    tops: list[float] = []
    levels: list[tuple[float, float]] = []
    span = max(gross, 1e-9)
    for x, bar in enumerate(bars):
        start = 0.0 if bar["total"] else level
        cur = start
        for label, val, col in bar["segs"]:
            if val < 0 and bar["block"] in COST_BLOCKS:  # Abzug innerhalb eines Kostenblocks: grün schraffiert
                col = BLOCK_COLORS[BLOCK_SUBSIDY]
            show = labels_in_bars and (abs(val) > 0.045 * span) and not bar["total"]
            fig.add_trace(go.Bar(
                x=[x], y=[val], base=[cur], width=0.66, marker=dict(color=col, line=dict(color="white", width=1),
                            pattern=dict(shape="/", fgcolor="white", size=6) if (val < 0 and bar["block"] in COST_BLOCKS) else None),
                text=[label if (show and not detail) else ""], textposition="inside", insidetextanchor="middle",
                textfont=dict(size=10, color="white" if _dark(col) else "#222"),
                hovertemplate=f"{label}: {de(val)} €/kg<extra></extra>", showlegend=False, cliponaxis=False))
            cur += val
        end = cur if not bar["total"] else bar["segs"][0][1]
        tops.append(max(start, end))
        levels.append((start, end))
        level = end if bar["total"] else cur
    # Verbindungslinien und Summenbeschriftung
    for x, (bar, (start, end)) in enumerate(zip(bars, levels)):
        fig.add_annotation(x=x, y=tops[x], text=f"<b>{de(end - start if not bar['total'] else end)}</b>",
                           showarrow=False, yshift=11, font=dict(size=11))
        if x < len(bars) - 1:
            fig.add_shape(type="line", x0=x + 0.33, x1=x + 1 - 0.33, y0=end, y1=end,
                          line=dict(color="#999", width=1, dash="dot"))
    if detail:  # Blocknamen über den Gruppen
        pos = 0
        for b in COST_BLOCKS + [None] + RELIEF_BLOCKS + [None]:
            if b is None:
                pos += 1
                continue
            n = sum(1 for bar in bars if bar["block"] == b)
            if n:
                fig.add_annotation(x=pos + (n - 1) / 2, y=1.04, yref="paper", text=f"<b>{subsidy_title if (b == BLOCK_SUBSIDY and subsidy_title) else b}</b>", showarrow=False,
                                   font=dict(size=12, color=BLOCK_COLORS[b]))
            pos += n
    fig.update_layout(
        barmode="overlay", height=height, margin=dict(l=0, r=0, t=34 if detail else 24, b=0), showlegend=False,
        yaxis=dict(title="€ pro kg H₂", zeroline=True, zerolinecolor="#666"),
        xaxis=dict(automargin=True, tickmode="array", tickvals=list(range(len(bars))), ticktext=[b["label"] for b in bars],
                   tickangle=-50 if detail else -25),
        plot_bgcolor="rgba(0,0,0,0)", uniformtext=dict(mode="hide", minsize=8), separators=",.")
    return fig


def _dark(color: str) -> bool:
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 150


def load_duration_figure(hourly, power, height: int = 360) -> go.Figure:
    """Geordnete Jahresdauerlinien (kWh pro Stunde): Gesamtsystem, Elektrolyseur und gesamter Strombezug."""
    system = hourly["consumption_kwh"].to_numpy(dtype=float)
    ely = system * power.ely_kw / power.total_kw
    purchase = hourly["purchase_kwh"].to_numpy(dtype=float)
    x = np.arange(1, len(system) + 1)
    fig = go.Figure()
    for name, arr, col in [("Gesamtstrombezug", purchase, "#e07a1f"), ("Stromverbrauch Gesamtsystem", system, "#2f6db5"),
                           ("Stromverbrauch Elektrolyseur", ely, "#16324f")]:
        fig.add_trace(go.Scatter(x=x, y=np.sort(arr)[::-1], name=name, mode="lines", line=dict(color=col, width=2),
                                 hovertemplate="Stunde %{x}: %{y:,.0f} kWh<extra>" + name + "</extra>"))
    top = float(max(purchase.max(), system.max())) * 1.08 or 1.0
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Stunden pro Jahr (nach Höhe geordnet)",
                      yaxis_title="Energie pro Stunde [kWh]", legend=dict(orientation="h", y=-0.28, yanchor="top"),
                      yaxis=dict(range=[0, top], tickformat=",.0f"), separators=",.")
    return fig


def battery_soc_figure(hourly, power, height: int = 300) -> go.Figure:
    soc = hourly["battery_soc_kwh"].to_numpy(dtype=float)
    x, xaxis = year_axis(len(soc))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=soc, mode="lines", fill="tozeroy", line=dict(color="#7b5ea7", width=1),
                             name="Ladezustand", hovertemplate="%{x|%d.%m. %H:%M} Uhr: %{y:,.0f} kWh<extra></extra>"))
    fig.add_hline(y=power.battery_capacity_kwh, line=dict(color="#999", dash="dot"),
                  annotation_text=f"Kapazität {de(power.battery_capacity_kwh, 0)} kWh", annotation_position="top left")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), xaxis=xaxis,
                      yaxis_title="Ladezustand [kWh]", yaxis_tickformat=",.0f", separators=",.", showlegend=False)
    return fig


def spot_price_figure(market, height: int = 340) -> go.Figure:
    """Börsenpreis über das Jahr (Excel Blatt 8): Die Linie ist grün, solange der Preis unter der §7-Grenze liegt,
    gelb bis zum eigenen Maximalpreis und rot darüber."""
    raw = np.asarray(market.price_raw, dtype=float)
    lim7 = np.asarray(market.section7_limit, dtype=float)
    smax = float(market.spot_max_price)
    regime = np.where(raw < lim7, 0, np.where(raw <= smax, 1, 2))
    n = len(raw)
    xt, xaxis = year_axis(n)
    fig = go.Figure()
    for k, name, col in [(0, "Preis unter der §7-Grenze", "#3f9b4f"),
                         (1, "Preis zwischen §7-Grenze und eigenem Maximalpreis", "#ffc000"),
                         (2, "Preis über dem eigenen Maximalpreis", "#d62828")]:
        idx = np.where(regime[:-1] == k)[0]
        ys = np.full(3 * len(idx), np.nan)
        xs = np.full(3 * len(idx), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
        xs[0::3], xs[1::3] = xt[idx], xt[idx + 1]
        ys[0::3], ys[1::3] = raw[idx], raw[idx + 1]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name, line=dict(color=col, width=1.2),
                                 hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xt, y=raw, mode="markers", marker=dict(size=4, opacity=0),
                             showlegend=False, hovertemplate="%{x|%d.%m. %H:%M} Uhr: %{y:,.2f} €/MWh<extra></extra>"))
    top = max(smax * 2.5, float(np.percentile(raw, 99.8)))
    low = min(0.0, float(np.percentile(raw, 0.2)))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), xaxis=xaxis,
                      yaxis=dict(title="Preis [€/MWh]", range=[low * 1.1, top]), separators=",.",
                      legend=dict(orientation="h", y=1.12))
    return fig


def sensitivity_figure(rows, step: float, height: int = 460) -> go.Figure:
    """Tornado-Diagramm: Links steht die Wirkung von -x %, rechts die von +x % der Einflussgröße (Reihenfolge wie Blatt 7 der
    Excel, erste Zeile unten). Die Balkenlänge ist der Betrag der Kostenänderung in €/kg; Rot: Kosten steigen, grün: sinken."""
    base = rows[0].base if rows else 0.0
    pct = f"{de(step * 100, 0)} %"
    fig = go.Figure()
    for sign, attr, vattr in ((-1, "lcoh_minus", "v_minus"), (1, "lcoh_plus", "v_plus")):
        vals = [getattr(z, attr) for z in rows]
        delta = [v - base for v in vals]
        fig.add_trace(go.Bar(
            y=[z.name for z in rows], x=[sign * abs(d) for d in delta], orientation="h", width=0.55,
            marker=dict(color=["#3f9b4f" if d < 0 else "#d1495b" for d in delta]),
            text=[("+" if d > 0 else "−" if d < 0 else "") + de(abs(d)) for d in delta],
            textposition="inside", insidetextanchor="middle", textfont=dict(color="white", size=13),
            customdata=[[de(v), z.block, de(getattr(z, vattr)), de(d)] for z, v, d in zip(rows, vals, delta)],
            hovertemplate=("%{y}, " + ("−" if sign < 0 else "+") + pct + ": Gestehungskosten %{customdata[0]} €/kg "
                           "(Änderung %{customdata[3]} €/kg)<br>%{customdata[1]}: %{customdata[2]}<extra></extra>"),
            showlegend=False))
    m = max((abs(getattr(z, a) - base) for z in rows for a in ("lcoh_minus", "lcoh_plus")), default=1.0) * 1.08 or 1.0
    ticks = [m * i / 4 for i in range(-4, 5)]
    fig.add_vline(x=0, line=dict(color="#16324f", width=2))
    fig.add_annotation(x=0, y=1.07, yref="paper", text=f"Basis: {de(base)} €/kg", showarrow=False, font=dict(color="#16324f"))
    fig.add_annotation(x=-m, xanchor="left", y=1.07, yref="paper", text=f"<b>−{pct}</b> der Einflussgröße", showarrow=False)
    fig.add_annotation(x=m, xanchor="right", y=1.07, yref="paper", text=f"<b>+{pct}</b> der Einflussgröße", showarrow=False)
    fig.update_layout(barmode="overlay", height=height, margin=dict(l=0, r=0, t=34, b=0), separators=",.",
                      xaxis=dict(title="Änderung der Gestehungskosten [€/kg] (Betrag)", range=[-m, m], tickvals=ticks,
                                 ticktext=[de(abs(t), 1) for t in ticks], zeroline=False))
    return fig
