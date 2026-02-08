import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Page Configuration
st.set_page_config(page_title="Agro Analytics Pro", layout="wide")

# Title and Logo
st.title("🌾 Agro Analytics BMC - Performance & Strategy Dashboard")
st.markdown("### Data-Driven Insights & AI Business Opportunities")

# 1. Database Connection
DB_PATH = "/Users/vivekvishe/Documents/agro/bmc_data.db"

def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"❌ Database file not found at: {DB_PATH}")
        st.stop()
    return duckdb.connect(DB_PATH, read_only=True)

con = get_connection()

# 2. Sidebar Filters
st.sidebar.header("Filter Analytics")
try:
    months_df = con.execute("SELECT DISTINCT \"MES\" FROM operaciones_bmc").df()
    months = months_df['MES'].tolist()
    selected_months = st.sidebar.multiselect("Select Months", options=months, default=months)
    
    if selected_months:
        filter_query = f"WHERE \"MES\" IN {tuple(selected_months) if len(selected_months) > 1 else '(' + repr(selected_months[0]) + ')'}"
    else:
        filter_query = ""
except:
    filter_query = ""

# Define Tabs
tab_dash, tab_strat, tab_ops, tab_audit = st.tabs([
    "📊 Performance Dashboard", 
    "💡 Strategic AI Insights", 
    "🔍 Operational Deep-Dive",
    "🛡️ Risk & Audit"
])

# --- TAB 1: PERFORMANCE DASHBOARD ---
with tab_dash:
    kpi_query = f"SELECT SUM(\"VALOR NEGOCIO\") as vol, SUM(\"COMISION\") as com, COUNT(*) as ops FROM operaciones_bmc {filter_query}"
    kpi_data = con.execute(kpi_query).df()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Traded Volume", f"${kpi_data['vol'][0]:,.0f}")
    c2.metric("Gross Commission", f"${kpi_data['com'][0]:,.0f}")
    c3.metric("Total Operations", f"{kpi_data['ops'][0]:,.0f}")

    st.markdown("---")
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        st.subheader("Monthly Revenue Trend")
        df_monthly = con.execute(f"SELECT \"MES\", SUM(\"COMISION\") as Revenue FROM operaciones_bmc {filter_query} GROUP BY 1").df()
        st.plotly_chart(px.line(df_monthly, x="MES", y="Revenue", markers=True), use_container_width=True)
    with r1_c2:
        st.subheader("Top 10 Clients by Revenue")
        df_clients = con.execute(f"SELECT \"CLIENTE\", SUM(\"COMISION\") as Revenue FROM operaciones_bmc {filter_query} GROUP BY 1 ORDER BY 2 DESC LIMIT 10").df()
        st.plotly_chart(px.bar(df_clients, x="Revenue", y="CLIENTE", orientation='h'), use_container_width=True)

# --- TAB 2: STRATEGIC AI INSIGHTS ---
with tab_strat:
    st.header("AI-Driven Business Opportunities")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🛑 Churn Risk: Idle Clients")
        st.dataframe(con.execute("SELECT \"CLIENTE\", MAX(\"FECHA REGISTRO\") as \"Last Active\" FROM operaciones_bmc GROUP BY 1 HAVING MAX(\"FECHA REGISTRO\") < '2025-04-01'").df(), use_container_width=True)
    with col_b:
        st.subheader("🎯 Cross-Selling Opportunities")
        st.dataframe(con.execute("SELECT p1.\"NOMBRE PRODUCTO\" as A, p2.\"NOMBRE PRODUCTO\" as B, COUNT(*) as Freq FROM operaciones_bmc p1 JOIN operaciones_bmc p2 ON p1.\"NIT COMPRADOR\" = p2.\"NIT COMPRADOR\" AND p1.\"NOMBRE PRODUCTO\" < p2.\"NOMBRE PRODUCTO\" GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 5").df(), use_container_width=True)

# --- TAB 3: OPERATIONAL DEEP-DIVE ---
with tab_ops:
    st.header("Operational Bottlenecks")
    df_days = con.execute(f"SELECT DAYNAME(\"FECHA REGISTRO\") as Day, COUNT(*) as Ops FROM operaciones_bmc {filter_query} GROUP BY 1").df()
    st.plotly_chart(px.bar(df_days, x="Day", y="Ops", title="Daily Operation Volume"), use_container_width=True)

# --- TAB 4: RISK & AUDIT (NEW QUERIES) ---
with tab_audit:
    st.header("Financial Risk & Audit Dashboard")
    
    # 1. Pareto Concentration Chart
    st.subheader("1. Revenue Concentration (Pareto)")
    st.markdown("_Is your revenue too dependent on a few clients?_")
    pareto_df = con.execute("SELECT \"CLIENTE\", SUM(\"COMISION\") as rev FROM operaciones_bmc GROUP BY 1 ORDER BY 2 DESC").df()
    pareto_df['cum_pct'] = pareto_df['rev'].cumsum() / pareto_df['rev'].sum() * 100
    
    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(x=pareto_df['CLIENTE'], y=pareto_df['rev'], name="Revenue"))
    fig_pareto.add_trace(go.Scatter(x=pareto_df['CLIENTE'], y=pareto_df['cum_pct'], name="Cumulative %", yaxis="y2"))
    fig_pareto.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100]), showlegend=False)
    st.plotly_chart(fig_pareto, use_container_width=True)

    # 2. Pricing Outliers
    st.subheader("2. Pricing Anomaly Detection")
    st.markdown("_Transactions where the commission is >30% below the product average._")
    outlier_query = """
        WITH prod_avg AS (SELECT "NOMBRE PRODUCTO", AVG("COMISION" / NULLIF("VALOR NEGOCIO", 0)) as avg_r FROM operaciones_bmc GROUP BY 1)
        SELECT t."OPERACION", t."CLIENTE", t."NOMBRE PRODUCTO", (t."COMISION" / NULLIF(t."VALOR NEGOCIO", 0)) as actual_rate, p.avg_r as market_avg
        FROM operaciones_bmc t JOIN prod_avg p ON t."NOMBRE PRODUCTO" = p."NOMBRE PRODUCTO"
        WHERE actual_rate < (p.avg_r * 0.7) LIMIT 10
    """
    st.dataframe(con.execute(outlier_query).df(), use_container_width=True)

    # 3. Ticket Size Efficiency
    st.subheader("3. Ticket Size Distribution")
    ticket_query = """
        SELECT CASE WHEN "VALOR NEGOCIO" < 1000000 THEN 'Small' WHEN "VALOR NEGOCIO" < 10000000 THEN 'Medium' ELSE 'Large' END as size,
        COUNT(*) as count, SUM("COMISION") as rev FROM operaciones_bmc GROUP BY 1
    """
    st.plotly_chart(px.pie(con.execute(ticket_query).df(), values="count", names="size", hole=0.4), use_container_width=True)

# 7. Raw Data Explorer
st.markdown("---")
if st.checkbox("Show Raw Data Table"):
    st.write(con.execute(f"SELECT * FROM operaciones_bmc {filter_query} LIMIT 100").df())

con.close()