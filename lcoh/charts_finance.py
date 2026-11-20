"""Diagramme für den Bereich „Weitere wirtschaftliche Kennzahlen“."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lcoh.charts import de

C_H2, C_THG, C_REV = "#1f4e79", "#2e8b57", "#7fb77e"
C_INV, C_POWER, C_OPEX, C_STACK, C_CAP = "#7f7f7f", "#c0504d", "#e8a33d", "#8064a2", "#4f6d8f"
C_MARGIN = "#5ab4e5"
M = 1e6
LEGEND = dict(orientation="h", y=-0.24, yanchor="top")


def _xlabels(t):
    return [("Inv." if j == 0 else str(int(c))) for j, c in zip(t["Jahr"], t["Kalenderjahr"])]


def cashflow_figure(f, height: int = 480) -> go.Figure:
    """Jährliche Cashflows des Projekts mit Netto-Cashflow und kumuliertem Barwert."""
    t = f.table
    x = _xlabels(t)
    fig = go.Figure()
    pos = [("Erlös Wasserstoff zu Gestehungskosten [€]", f"Wasserstoffverkauf zu Gestehungskosten ({de(f.lcoh)} €/kg)", C_H2),
           ("Marge [€]", "Marge", C_MARGIN),
           ("Erlös THG-Quote [€]", "THG-Quote", C_THG), ("Weitere Erlöse [€]", "Weitere Erlöse (Strom, O₂, Wärme u. a.)", C_REV)]
    neg = [("Investition [€]", "Investition", C_INV), ("Strom [€]", "Strom", C_POWER),
           ("Betrieb (OPEX) [€]", "Betrieb (OPEX)", C_OPEX), ("Stacktausch [€]", "Stacktausch", C_STACK)]
    for col, name, c in pos + neg:
        fig.add_trace(go.Bar(x=x, y=t[col] / M, name=name, marker_color=c,
                             hovertemplate=name + " %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=t["Cashflow Projekt [€]"] / M, name="Netto-Cashflow im Jahr", mode="lines+markers",
                             line=dict(color="black", width=2), hovertemplate="Netto-Cashflow %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=t["Kumuliert abgezinst [€]"] / M, mode="lines+markers",
                             name=f"Kumulierter Barwert (abgezinst mit {de(f.wacc * 100, 1)} %)", line=dict(color="#d62728", width=2.5),
                             hovertemplate="Kumulierter Barwert %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    fig.update_layout(barmode="relative", height=height, margin=dict(l=0, r=0, t=10, b=0), separators=",.", xaxis=dict(type="category"),
                      yaxis_title="Mio. € (nominal)", legend=LEGEND)
    return fig


def cost_revenue_figure(f, height: int = 440) -> go.Figure:
    """Kosten (linker Balken) und Erlöse (rechter Balken) je Projektjahr in Mio. €."""
    t = f.table.iloc[1:]
    x = [str(int(c)) for c in t["Kalenderjahr"]]
    fig = go.Figure()
    for col, name, c in [("Strom [€]", "Kosten: Strom", C_POWER), ("Betrieb (OPEX) [€]", "Kosten: Betrieb (OPEX)", C_OPEX),
                         ("Stacktausch [€]", "Kosten: Stacktausch", C_STACK)]:
        fig.add_trace(go.Bar(x=x, y=-t[col] / M, name=name, marker_color=c, offsetgroup="k",
                             hovertemplate=name + " %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    cap = np.full(len(t), f.capital_service / M)
    fig.add_trace(go.Bar(x=x, y=cap, name=f"Kosten: Kapitaldienst (Annuität zu {de(f.wacc * 100, 1)} %)", marker_color=C_CAP,
                         offsetgroup="k", hovertemplate="Kapitaldienst %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    for col, name, c in [("Erlös Wasserstoff zu Gestehungskosten [€]", "Erlös: Wasserstoff zu Gestehungskosten", C_H2),
                         ("Marge [€]", "Erlös: Marge", C_MARGIN), ("Erlös THG-Quote [€]", "Erlös: THG-Quote", C_THG),
                         ("Weitere Erlöse [€]", "Erlös: weitere Erlöse", C_REV)]:
        fig.add_trace(go.Bar(x=x, y=t[col] / M, name=name, marker_color=c, offsetgroup="e",
                             hovertemplate=name + " %{x}: %{y:,.2f} Mio. €<extra></extra>"))
    fig.update_layout(barmode="relative", height=height, margin=dict(l=0, r=0, t=10, b=0), separators=",.", xaxis=dict(type="category"),
                      yaxis_title="Mio. € pro Jahr (nominal)", legend=LEGEND)
    return fig


def per_kg_figure(f, height: int = 460, show_price: bool = True) -> go.Figure:
    """Kosten (oben) und Nebenerlöse (unten) je kg Wasserstoff, Gestehungskosten des Jahres; optional Verkaufspreis und Marge.
    Kostenansicht: Kapitaldienst als Annuität zum Kapitalkostensatz, Stacktausch als gleichbleibender Jahresbetrag."""
    t = f.table.iloc[1:]
    x = [str(int(c)) for c in t["Kalenderjahr"]]
    h = (t["Wasserstoff [t]"] * 1000).to_numpy()
    fig = go.Figure()
    costs = [("Strom [€]", "Kosten: Strom", C_POWER), ("Betrieb (OPEX) [€]", "Kosten: Betrieb (OPEX)", C_OPEX),
             ("Stacktausch als Jahresbetrag [€]", "Kosten: Stacktausch", C_STACK)]
    tot = np.zeros(len(t))
    for col, name, c in costs:
        v = -t[col].to_numpy() / h
        tot += v
        fig.add_trace(go.Bar(x=x, y=v, name=name, marker_color=c, hovertemplate=name + " %{x}: %{y:,.2f} €/kg<extra></extra>"))
    v = f.capital_service / h
    tot += v
    fig.add_trace(go.Bar(x=x, y=v, name="Kosten: Kapitaldienst", marker_color=C_CAP,
                         hovertemplate="Kapitaldienst %{x}: %{y:,.2f} €/kg<extra></extra>"))
    for col, name, c in [("Erlös THG-Quote [€]", "Erlös: THG-Quote", C_THG), ("Weitere Erlöse [€]", "Erlös: weitere Erlöse", C_REV)]:
        v = -t[col].to_numpy() / h
        tot += v
        fig.add_trace(go.Bar(x=x, y=v, name=name, marker_color=c, hovertemplate=name + " %{x}: %{y:,.2f} €/kg<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=tot, name="Gestehungskosten im Jahr", mode="lines+markers", line=dict(color="black", width=2),
                             hovertemplate="Gestehungskosten %{x}: %{y:,.2f} €/kg<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=[f.lcoh] * len(x), name=f"LCOH₂: {de(f.lcoh)} €/kg", mode="lines",
                             line=dict(color="black", width=1.8, dash="dash"), hoverinfo="skip"))
    if show_price:
        fig.add_trace(go.Scatter(x=x, y=t["Verkaufspreis [€/kg]"], name="Verkaufspreis Wasserstoff (Fläche: Marge)", mode="lines",
                                 line=dict(color=C_H2, width=3), fill="tonexty", fillcolor="rgba(90,180,229,0.35)",
                                 hovertemplate="Verkaufspreis %{x}: %{y:,.2f} €/kg<extra></extra>"))
    fig.update_layout(barmode="relative", height=height, margin=dict(l=0, r=0, t=10, b=0), separators=",.", xaxis=dict(type="category"),
                      yaxis_title="€ pro kg Wasserstoff (nominal)", legend=LEGEND)
    return fig


def equity_figure(f, height: int = 420) -> go.Figure:
    """Eigenkapital-Cashflow je Jahr und Schuldendienstdeckungsgrad (DSCR)."""
    t = f.table
    x = _xlabels(t)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    cf = t["Cashflow Eigenkapital [€]"] / M
    fig.add_trace(go.Bar(x=x, y=cf, name="Cashflow Eigenkapital (nach Kapitaldienst)",
                         marker_color=["#3f9b4f" if v >= 0 else "#d1495b" for v in cf],
                         hovertemplate="Cashflow Eigenkapital %{x}: %{y:,.2f} Mio. €<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=x[1:], y=t["DSCR"].iloc[1:], name="DSCR (rechte Achse)", mode="lines+markers",
                             line=dict(color=C_H2, width=2), hovertemplate="DSCR %{x}: %{y:,.2f}<extra></extra>"), secondary_y=True)
    fig.add_trace(go.Scatter(x=[x[1], x[-1]], y=[1.0, 1.0], name="DSCR = 1,0", mode="lines",
                             line=dict(color="#d62728", width=1.5, dash="dash"), hoverinfo="skip"), secondary_y=True)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), separators=",.", xaxis=dict(type="category"), legend=LEGEND)
    fig.update_yaxes(title_text="Mio. € (nominal)", secondary_y=False)
    fig.update_yaxes(title_text="DSCR [–]", secondary_y=True, showgrid=False)
    return fig
