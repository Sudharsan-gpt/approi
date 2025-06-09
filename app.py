import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.interpolate import make_interp_spline

# Set layout
st.set_page_config(layout="wide")

# 💡 Styling
st.markdown("""
<style>
/* Input fields bold */
div[data-baseweb="input"] input {
    font-weight: bold;
}

/* KPI Cards */
[data-testid="metric-container"] {
    background-color: #f0f4f8;
    border-radius: 10px;
    padding: 20px;
    border: 1px solid #ccc;
}
[data-testid="metric-container"] > div:nth-child(2) {
    color: #007bff;
    font-size: 24px;
    font-weight: bold;
}

/* Table styles */
thead tr th {
    font-weight: bold;
    background-color: #e3e3e3;
}
tbody tr:nth-child(even) {
    background-color: #f9f9f9;
}
</style>
""", unsafe_allow_html=True)

# === Input Section ===
st.markdown("### Input Parameters")
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

with col1:
    years = st.slider("Contract Duration (Years)", 1, 5, 3)
    months = years * 12
    fleet_size = st.number_input("Fleet Size", min_value=1, value=10)
    fuel_price = st.number_input("Fuel Price ($/MT)", value=550.0)
    daily_fuel = st.number_input("Daily Fuel Consumption (MT)", value=20.0)
    op_days = st.number_input("Operating Days per Year", value=200)

with col2:
    saving_hull = st.select_slider("Hull & Performance Saving (%)", options=np.arange(0, 6, 0.1), value=2.0)
    saving_voyage = st.select_slider("Voyage Optimization Saving (%)", options=np.arange(0, 6, 0.1), value=1.0)
    saving_emission = st.select_slider("Emission App Avoidance (%)", options=np.arange(0, 6, 0.1), value=0.5)
    saving_scorecard = st.select_slider("Scorecard Avoidance (%)", options=np.arange(0, 6, 0.1), value=0.2)
    saving_propulsion = st.select_slider("Propulsion Pro Saving (%)", options=np.arange(0, 6, 0.1), value=0.0)

with col3:
    cost_hull = st.number_input("Hull App Cost ($)", value=250.0)
    cost_voyage = st.number_input("Voyage App Cost ($)", value=250.0)
    cost_emission = st.number_input("Emission App Cost ($)", value=250.0)
    cost_scorecard = st.number_input("Scorecard App Cost ($)", value=250.0)
    cost_propulsion = st.number_input("Propulsion Pro App Cost ($)", value=0.0)
    initial_sub_cost = sum([cost_hull, cost_voyage, cost_emission, cost_scorecard, cost_propulsion])

with col4:
    c4a, c4b = st.columns(2)
    with c4a:
        ramp_up = st.number_input("Ramp-up Delay (Months)", value=6)
        cleaning_cost = st.number_input("Hull Cleaning Cost ($)", value=15000.0)
        cleaning_frequency = st.number_input("Cleaning Frequency (Months)", value=9)
    with c4b:
        one_time_cost = st.number_input("One-time Cost ($)", value=1000.0)
        crew_cost = st.number_input("Crew Training Cost ($)", value=100.0)
        monthly_deterioration = st.number_input("Monthly Deterioration (%)", value=0.1) / 100
        yearly_sub_increase = st.number_input("Yearly Subscription Increase (%)", value=10.0) / 100
    ramp_up_saving_pct = st.number_input("Post Ramp-up Saving % of Total", value=60.0) / 100
    post_cleaning_saving_pct = st.number_input("Post-Hull Cleaning Saving %", value=100.0) / 100

# === Core Logic ===
CO2_EMISSION_FACTOR = 3.114
monthly_fuel_cost_base = fuel_price * daily_fuel * op_days / 12
total_saving_pct = saving_hull + saving_voyage + saving_emission + saving_scorecard + saving_propulsion

data = []
cumulative_sub_cost = 0
cumulative_savings = 0
cumulative_total_cost = 0
total_fuel_mt = 0
fuel_cost_current = monthly_fuel_cost_base
sub_cost = initial_sub_cost
saving_pct = 0
last_saving_pct = 0

for month in range(1, months + 1):
    if month % 12 == 1 and month > 1:
        fuel_cost_current *= (1 + yearly_sub_increase)
        sub_cost *= (1 + yearly_sub_increase)

    if month < ramp_up:
        saving_pct = 0
    elif month > ramp_up and month < cleaning_frequency:
        saving_pct = total_saving_pct * ramp_up_saving_pct
    elif month % cleaning_frequency == 0 and month >= ramp_up:
        saving_pct = total_saving_pct * post_cleaning_saving_pct
        last_saving_pct = saving_pct
    else:
        last_saving_pct = max(0, last_saving_pct - (monthly_deterioration * 100))
        saving_pct = last_saving_pct

    fuel_saving_dollars = fuel_cost_current * (saving_pct / 100)
    monthly_fuel_mt = fuel_cost_current / fuel_price
    total_fuel_mt += monthly_fuel_mt
    cumulative_savings += fuel_saving_dollars
    cumulative_sub_cost += sub_cost
    hull_cleaning = cleaning_cost if (month % cleaning_frequency == 0 and month >= ramp_up) else 0
    other_cost = one_time_cost + crew_cost if month == 1 else 0
    total_monthly_cost = sub_cost + hull_cleaning + other_cost
    cumulative_total_cost += total_monthly_cost
    profit = cumulative_savings - cumulative_total_cost
    roi = (profit / cumulative_total_cost) if cumulative_total_cost > 0 else -1

    data.append({
        "Month": month,
        "Fuel Cost": round(fuel_cost_current),
        "Subscription Cost": round(sub_cost),
        "Cumulative Subscription Cost": round(cumulative_sub_cost),
        "Hull Cleaning Cost": round(hull_cleaning),
        "Savings in Fuel (%)": round(saving_pct, 2),
        "Fuel Cost Savings": round(fuel_saving_dollars),
        "Cumulative Savings": round(cumulative_savings),
        "Cumulative Total Cost": round(cumulative_total_cost),
        "Profit": round(profit),
        "Cumulative ROI": f"{roi * 100:.1f}%"
    })

df = pd.DataFrame(data)

# === KPIs ===
fuel_savings_mt = df["Cumulative Savings"].iloc[-1] / fuel_price
co2_reduction = fuel_savings_mt * CO2_EMISSION_FACTOR
fmt = lambda x: f"{x/1_000_000:.1f}M" if x > 1_000_000 else f"{x/1_000:.1f}k" if x > 1_000 else f"{x:,.0f}"

st.markdown("### 📊 Key Metrics")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("🚢 Fuel Savings (MT)", fmt(fuel_savings_mt))
col2.metric("💵 Cost Savings ($)", fmt(df["Fuel Cost Savings"].sum()))
col3.metric("🌱 CO₂ Reduction (MT)", fmt(co2_reduction))
col4.metric("💰 Profit ($)", fmt(df["Profit"].iloc[-1]))
col5.metric("📈 ROI", df["Cumulative ROI"].iloc[-1])
col6.metric("💼 Total Investment Cost ($)", fmt(df["Cumulative Total Cost"].iloc[-1]))
col7.metric("⛽ Total Fuel Used (MT)", fmt(total_fuel_mt))

# === Charts ===
def smooth_line(x, y):
    xnew = np.linspace(min(x), max(x), 300)
    spl = make_interp_spline(x, y, k=3)
    ynew = spl(xnew)
    return xnew, ynew

st.markdown("### 📈 Trends")
col_chart1, col_chart2, col_chart3 = st.columns(3)

with col_chart1:
    x = df["Month"]
    fig1, ax1 = plt.subplots()
    for y, color, label in zip(
        [df["Cumulative Total Cost"], df["Cumulative Savings"], df["Profit"]],
        ["#cfd8dc", "#a5d6a7", "#ffe082"],
        ["Total Cost", "Savings", "Profit"]):
        xs, ys = smooth_line(x, y)
        ax1.plot(xs, ys, color=color, label=label)
        ax1.fill_between(xs, ys, color=color, alpha=0.4)
    ax1.set_title("Investment, Savings, Profit")
    ax1.legend()
    ax1.grid(False)
    st.pyplot(fig1)

with col_chart2:
    roi_vals = [float(r.strip('%')) for r in df["Cumulative ROI"]]
    xs, ys = smooth_line(df["Month"], roi_vals)
    fig2, ax2 = plt.subplots()
    ax2.plot(xs, ys, color="#90caf9")
    ax2.fill_between(xs, ys, color="#90caf9", alpha=0.4)
    ax2.set_title("ROI % Trend")
    ax2.grid(False)
    st.pyplot(fig2)

with col_chart3:
    fig3, ax3 = plt.subplots()
    ax3.bar(["Savings", "Cost"], [df["Cumulative Savings"].iloc[-1], df["Cumulative Total Cost"].iloc[-1]],
            color=["#81c784", "#ef9a9a"], alpha=0.8)
    ax3.set_title("Total Savings vs Cost")
    ax3.grid(False)
    st.pyplot(fig3)

# === Table ===
st.markdown("### 📋 Monthly Table")
def highlight_profit(val): return 'color: green;' if val > 0 else 'color: red;'
def highlight_roi(val):
    try: return 'color: green;' if float(val.strip('%')) > 0 else 'color: red;'
    except: return ''

styled_df = df.style.applymap(highlight_profit, subset=["Profit"]) \
                    .applymap(highlight_roi, subset=["Cumulative ROI"])

st.write(styled_df)
