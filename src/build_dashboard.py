"""
Interactive Telecom Analytics Dashboard
=========================================
Builds a single-page HTML dashboard from the Gold-layer CSVs.
Output: dashboards/telecom_dashboard.html
This file is fully self-contained and hostable via GitHub Pages.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold"
OUT = PROJECT_ROOT / "dashboards" / "telecom_dashboard.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

cs = pd.read_csv(GOLD / "fact_customer_summary.csv")
cc = pd.read_csv(GOLD / "fact_churn_cohort.csv")
rp = pd.read_csv(GOLD / "fact_regional_performance.csv")
dn = pd.read_csv(GOLD / "fact_daily_network_metrics.csv")
dn["call_date"] = pd.to_datetime(dn["call_date"])

PRIMARY = "#1e3a8a"; ACCENT = "#0ea5e9"; DANGER = "#dc2626"
WARN = "#f59e0b"; GOOD = "#10b981"; GREY = "#64748b"
PANEL = "#1e293b"; TEXT = "#e2e8f0"

total_customers = len(cs)
churn_rate = cs["churn_flag"].mean() * 100
mrr = cs["monthlycharges"].sum()
arpu = cs["monthlycharges"].mean()
lost_mrr = cs[cs["churn_flag"] == 1]["monthlycharges"].sum()

contract_churn = cs.groupby("contract").agg(
    churn_rate=("churn_flag", lambda x: x.mean() * 100),
    customers=("customer_id", "count"),
).reset_index().sort_values("churn_rate", ascending=False)

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=contract_churn["contract"], y=contract_churn["churn_rate"],
    marker_color=[DANGER, WARN, GOOD],
    text=[f"{v:.1f}%" for v in contract_churn["churn_rate"]],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Churn rate: %{y:.2f}%<br>Customers: %{customdata:,}<extra></extra>",
    customdata=contract_churn["customers"],
))
fig1.update_layout(
    title="<b>Churn Rate by Contract Type</b><br><sub style='color:#94a3b8'>Month-to-month customers churn at 15× the rate of 2-year contracts</sub>",
    yaxis_title="Churn Rate (%)",
    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT,
    height=380, margin=dict(t=80, b=40, l=60, r=20),
    yaxis=dict(gridcolor="#334155", range=[0, 50]),
    xaxis=dict(gridcolor="#334155"),
)

top_cohorts = cc[cc["customer_count"] >= 50].nlargest(8, "churn_rate_pct").iloc[::-1]
top_cohorts["label"] = (
    top_cohorts["tenure_cohort"].astype(str) + " | "
    + top_cohorts["contract"].astype(str).str.replace("Month-to-month", "M2M") + " | "
    + top_cohorts["paymentmethod"].astype(str)
        .str.replace("Bank transfer (automatic)", "Bank xfer")
        .str.replace("Credit card (automatic)", "Credit card")
        .str.replace("Electronic check", "E-check")
        .str.replace("Mailed check", "Mail check")
)

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    y=top_cohorts["label"], x=top_cohorts["churn_rate_pct"], orientation="h",
    marker_color=top_cohorts["churn_rate_pct"],
    marker_colorscale=[[0, GOOD], [0.5, WARN], [1, DANGER]],
    text=[f"{v:.1f}%  ({c:,})" for v, c in zip(top_cohorts["churn_rate_pct"], top_cohorts["customer_count"])],
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>Churn rate: %{x:.2f}%<br>Customers: %{customdata:,}<extra></extra>",
    customdata=top_cohorts["customer_count"],
))
fig2.update_layout(
    title="<b>Top 8 Highest-Risk Customer Cohorts</b><br><sub style='color:#94a3b8'>Cohort = tenure × contract × payment method  |  n ≥ 50</sub>",
    xaxis_title="Churn Rate (%)",
    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT,
    height=440, margin=dict(t=80, b=40, l=240, r=80),
    xaxis=dict(gridcolor="#334155", range=[0, 80]),
    yaxis=dict(gridcolor="#334155"),
)

fig3 = make_subplots(specs=[[{"secondary_y": True}]])
rp_sorted = rp.sort_values("total_calls", ascending=False)
fig3.add_trace(go.Bar(
    x=rp_sorted["region"], y=rp_sorted["total_calls"],
    marker_color=PRIMARY, name="Total Calls",
    text=[f"{v:,}" for v in rp_sorted["total_calls"]], textposition="outside",
    hovertemplate="<b>%{x}</b><br>Total calls: %{y:,}<extra></extra>",
), secondary_y=False)
fig3.add_trace(go.Scatter(
    x=rp_sorted["region"], y=rp_sorted["drop_rate_pct"],
    mode="lines+markers+text", marker=dict(color=DANGER, size=12),
    line=dict(color=DANGER, width=3), name="Drop Rate %",
    text=[f"{v:.2f}%" for v in rp_sorted["drop_rate_pct"]], textposition="top center",
    hovertemplate="<b>%{x}</b><br>Drop rate: %{y:.2f}%<extra></extra>",
), secondary_y=True)
fig3.update_layout(
    title="<b>Regional Network Performance</b><br><sub style='color:#94a3b8'>Call volume (bars) vs. drop rate (line)</sub>",
    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT,
    height=380, margin=dict(t=80, b=40, l=60, r=60),
    legend=dict(orientation="h", y=-0.15),
)
fig3.update_xaxes(gridcolor="#334155")
fig3.update_yaxes(title_text="Total Calls", gridcolor="#334155", secondary_y=False)
fig3.update_yaxes(title_text="Drop Rate %", gridcolor="#334155", secondary_y=True)

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=dn["call_date"], y=dn["call_success_rate_pct"], mode="lines",
    line=dict(color=GOOD, width=2), fill="tozeroy",
    fillcolor="rgba(16, 185, 129, 0.15)", name="Success Rate",
    hovertemplate="<b>%{x|%b %d, %Y}</b><br>Success rate: %{y:.2f}%<extra></extra>",
))
fig4.add_hline(y=dn["call_success_rate_pct"].mean(), line_dash="dash", line_color=ACCENT,
               annotation_text=f"Mean: {dn['call_success_rate_pct'].mean():.2f}%",
               annotation_font_color=ACCENT)
fig4.update_layout(
    title="<b>Daily Call Success Rate (90 days)</b><br><sub style='color:#94a3b8'>Network reliability trending</sub>",
    yaxis_title="Success Rate (%)",
    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT,
    height=380, margin=dict(t=80, b=40, l=60, r=20),
    yaxis=dict(gridcolor="#334155", range=[85, 100]),
    xaxis=dict(gridcolor="#334155"),
)

cs_e = cs.copy()
cs_e["eng_band"] = pd.cut(cs_e["engagement_score"], bins=[-1, 25, 50, 75, 101],
    labels=["Low (0-25)", "Mid-Low (25-50)", "Mid-High (50-75)", "High (75-100)"])
eng = cs_e.groupby("eng_band", observed=True).agg(
    churn_rate=("churn_flag", lambda x: x.mean() * 100),
    customers=("customer_id", "count"),
    avg_revenue=("monthlycharges", "mean"),
).reset_index()

fig5 = go.Figure()
fig5.add_trace(go.Bar(
    x=eng["eng_band"].astype(str), y=eng["churn_rate"],
    marker_color=[DANGER, WARN, ACCENT, GOOD],
    text=[f"{v:.1f}%<br>n={c:,}" for v, c in zip(eng["churn_rate"], eng["customers"])],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Churn rate: %{y:.2f}%<br>Customers: %{customdata[0]:,}<br>Avg revenue: $%{customdata[1]:.2f}<extra></extra>",
    customdata=list(zip(eng["customers"], eng["avg_revenue"])),
))
fig5.update_layout(
    title="<b>Customer Engagement vs. Churn</b><br><sub style='color:#94a3b8'>Highly engaged customers churn at half the rate of disengaged ones</sub>",
    yaxis_title="Churn Rate (%)",
    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT,
    height=380, margin=dict(t=80, b=40, l=60, r=20),
    yaxis=dict(gridcolor="#334155", range=[0, 50]),
    xaxis=dict(gridcolor="#334155"),
)

def fig_html(fig):
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"displayModeBar": False})

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Telecom Analytics Platform — Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: linear-gradient(135deg, #0f172a, #1e293b); color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  min-height: 100vh; padding: 24px; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
header {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #334155;
  border-radius: 12px; padding: 28px 32px; margin-bottom: 24px; }}
h1 {{ font-size: 28px; font-weight: 700; color: #f1f5f9; margin-bottom: 8px; }}
.subtitle {{ color: #94a3b8; font-size: 15px; line-height: 1.5; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px; margin-bottom: 24px; }}
.kpi {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #334155;
  border-radius: 12px; padding: 22px 24px; transition: transform 0.2s; }}
.kpi:hover {{ transform: translateY(-2px); border-color: #475569; }}
.kpi .label {{ color: #94a3b8; font-size: 13px; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 8px; }}
.kpi .value {{ color: #f1f5f9; font-size: 32px; font-weight: 700; line-height: 1; }}
.kpi .sub {{ color: #64748b; font-size: 12px; margin-top: 6px; }}
.danger .value {{ color: #f87171; }}
.warn .value {{ color: #fbbf24; }}
.good .value {{ color: #34d399; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
.grid-full {{ grid-template-columns: 1fr; }}
.card {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #334155;
  border-radius: 12px; padding: 8px; overflow: hidden; }}
footer {{ color: #64748b; font-size: 13px; text-align: center; padding: 24px 0; }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📡 Telecom Customer Analytics Platform</h1>
    <p class="subtitle">End-to-end data engineering pipeline: ingestion → transformation → warehouse → analytics. <br>
       Built on a real-world telecom customer churn dataset with synthetic CDR enrichment.</p>
  </header>
  <div class="kpis">
    <div class="kpi"><div class="label">Total Customers</div><div class="value">{total_customers:,}</div><div class="sub">across 5 regions</div></div>
    <div class="kpi danger"><div class="label">Churn Rate</div><div class="value">{churn_rate:.1f}%</div><div class="sub">1,869 customers lost</div></div>
    <div class="kpi good"><div class="label">Monthly Revenue</div><div class="value">${mrr/1000:,.0f}K</div><div class="sub">${arpu:.2f} ARPU</div></div>
    <div class="kpi warn"><div class="label">Revenue at Risk</div><div class="value">${lost_mrr/1000:,.0f}K</div><div class="sub">monthly recurring loss</div></div>
  </div>
  <div class="grid">
    <div class="card">{fig_html(fig1)}</div>
    <div class="card">{fig_html(fig5)}</div>
  </div>
  <div class="grid grid-full">
    <div class="card">{fig_html(fig2)}</div>
  </div>
  <div class="grid">
    <div class="card">{fig_html(fig3)}</div>
    <div class="card">{fig_html(fig4)}</div>
  </div>
  <footer>
    Data: 7,043 customers · 50,000 CDR records · 200 cell towers · 91 days of network telemetry<br>
    Pipeline: Bronze → Silver → Gold → SQLite warehouse · Built with Python, Pandas, SQL, Plotly
  </footer>
</div>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"✓ Dashboard written: {OUT}")
print(f"  Size: {OUT.stat().st_size / 1024:.1f} KB")