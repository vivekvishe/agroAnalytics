import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(
    page_title="Agro Analytics Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# LOGIN AUTHENTICATION
# ============================================
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (st.session_state["username"] == "admin" and 
            st.session_state["password"] == "Aguacate78)"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
            del st.session_state["username"]  # Don't store username
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.markdown("""
        <div style='text-align: center; padding: 50px 0;'>
            <h1>🌾 Agro Analytics BMC</h1>
            <h3>Secure Login Required</h3>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input("Username", key="username", placeholder="Enter username")
        st.text_input("Password", type="password", key="password", placeholder="Enter password")
        st.button("Login", on_click=password_entered, type="primary", use_container_width=True)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Username or password incorrect")
    
    return False

# Check authentication before showing dashboard
if not check_password():
    st.stop()  # Don't continue if not authenticated

# ============================================
# MAIN DASHBOARD (only shown after login)
# ============================================

# Custom CSS for better styling
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 1. Database Connection with Error Handling
DB_PATH = "/Users/vivekvishe/Documents/agro/bmc_data.db"

@st.cache_resource
def get_connection():
    """Create database connection with error handling"""
    if not os.path.exists(DB_PATH):
        st.error(f"❌ Database file not found at: {DB_PATH}")
        st.info("💡 Please update the DB_PATH variable with your database location")
        st.stop()
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        st.error(f"❌ Error connecting to database: {str(e)}")
        st.stop()

con = get_connection()

# Helper function to execute queries safely
def safe_query(query, description="query"):
    """Execute SQL query with error handling"""
    try:
        return con.execute(query).df()
    except Exception as e:
        st.error(f"❌ Error executing {description}: {str(e)}")
        st.code(query, language="sql")
        return pd.DataFrame()

# 2. Sidebar Filters with Improved Logic
st.sidebar.header("🔍 Filter Analytics")

# Logout button
if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.markdown("---")

# Month filter with better ordering
try:
    months_query = """
        SELECT DISTINCT MES 
        FROM operaciones_bmc 
        WHERE MES IS NOT NULL
        ORDER BY 
            CASE 
                WHEN MES LIKE 'ene%' THEN 1
                WHEN MES LIKE 'feb%' THEN 2
                WHEN MES LIKE 'mar%' THEN 3
                WHEN MES LIKE 'abr%' THEN 4
                WHEN MES LIKE 'may%' THEN 5
                WHEN MES LIKE 'jun%' THEN 6
                WHEN MES LIKE 'jul%' THEN 7
                WHEN MES LIKE 'ago%' THEN 8
                WHEN MES LIKE 'sep%' THEN 9
                WHEN MES LIKE 'oct%' THEN 10
                WHEN MES LIKE 'nov%' THEN 11
                WHEN MES LIKE 'dic%' THEN 12
                ELSE 0
            END
    """
    months_df = safe_query(months_query, "months filter")
    
    if not months_df.empty:
        months = months_df['MES'].tolist()
        selected_months = st.sidebar.multiselect(
            "📅 Select Months", 
            options=months, 
            default=months,
            help="Filter data by specific months"
        )
    else:
        selected_months = []
        st.sidebar.warning("No month data available")
except Exception as e:
    st.sidebar.error(f"Error loading months: {str(e)}")
    selected_months = []

# Year filter
try:
    years_query = "SELECT DISTINCT YEAR FROM operaciones_bmc WHERE YEAR IS NOT NULL ORDER BY YEAR DESC"
    years_df = safe_query(years_query, "years filter")
    
    if not years_df.empty:
        years = years_df['YEAR'].tolist()
        selected_years = st.sidebar.multiselect(
            "📆 Select Years",
            options=years,
            default=years,
            help="Filter data by specific years"
        )
    else:
        selected_years = []
except Exception as e:
    selected_years = []

# Operation type filter
try:
    op_types_query = "SELECT DISTINCT \"TIPO OPERACION\" FROM operaciones_bmc WHERE \"TIPO OPERACION\" IS NOT NULL"
    op_types_df = safe_query(op_types_query, "operation types")
    
    if not op_types_df.empty:
        op_types = op_types_df['TIPO OPERACION'].tolist()
        selected_op_types = st.sidebar.multiselect(
            "📋 Operation Type",
            options=op_types,
            default=op_types,
            help="RSG: Sin incentivo, REX: Exportación, RGC: Con incentivo"
        )
    else:
        selected_op_types = []
except Exception as e:
    selected_op_types = []

# Build WHERE clause
def build_where_clause():
    """Build WHERE clause based on selected filters"""
    conditions = []
    
    if selected_months:
        month_list = "','".join(selected_months)
        conditions.append(f"MES IN ('{month_list}')")
    
    if selected_years:
        year_list = ",".join(map(str, selected_years))
        conditions.append(f"YEAR IN ({year_list})")
    
    if selected_op_types:
        op_list = "','".join(selected_op_types)
        conditions.append(f"\"TIPO OPERACION\" IN ('{op_list}')")
    
    if conditions:
        return "WHERE " + " AND ".join(conditions)
    return ""

filter_query = build_where_clause()

# Title and Logo
st.title("🌾 Agro Analytics BMC - Performance & Strategy Dashboard")
st.markdown("### Data-Driven Insights for Agricultural Business Operations")

# Dashboard Overview
with st.expander("📋 **Dashboard Guide**", expanded=False):
    st.markdown("""
    ### 🎯 **Dashboard Purpose**
    Monitor agricultural business operations with comprehensive analytics:
    - **Performance Metrics**: Revenue, volume, and operational efficiency
    - **Strategic Insights**: AI-powered business opportunities and risks
    - **Operational Analysis**: Daily patterns and resource optimization
    - **Risk Management**: Financial exposure and compliance monitoring
    
    ### 🔍 **Navigation**
    1. **📊 Performance Dashboard**: KPIs and revenue trends
    2. **💡 Strategic Insights**: Growth opportunities and risk detection
    3. **🔍 Operational Deep-Dive**: Daily operations and efficiency
    4. **🛡️ Risk & Audit**: Concentration risk and anomaly detection
    
    ### 💡 **Usage Tips**
    - Use sidebar filters to focus on specific periods
    - Hover over charts for detailed information
    - Export data using download buttons
    - Check tooltips for metric explanations
    """)

# Quick Stats Overview
st.markdown("---")
st.subheader("🚀 Business Overview")

col1, col2, col3, col4, col5 = st.columns(5)

# Get overview metrics
overview_query = f"""
    SELECT 
        COUNT(DISTINCT CLIENTE) as unique_clients,
        COUNT(DISTINCT "NOMBRE PRODUCTO") as unique_products,
        SUM("VALOR NEGOCIO") as total_volume,
        SUM(COMISION) as total_commission,
        COUNT(*) as total_ops
    FROM operaciones_bmc 
    {filter_query}
"""
overview_data = safe_query(overview_query, "overview metrics")

if not overview_data.empty:
    with col1:
        st.metric(
            "Active Clients", 
            f"{int(overview_data['unique_clients'][0]):,}",
            help="Number of distinct clients in selected period"
        )
    with col2:
        st.metric(
            "Products Traded", 
            f"{int(overview_data['unique_products'][0]):,}",
            help="Number of distinct products"
        )
    with col3:
        st.metric(
            "Total Volume", 
            f"${overview_data['total_volume'][0]:,.0f}",
            help="Sum of all transaction values"
        )
    with col4:
        st.metric(
            "Commission Revenue", 
            f"${overview_data['total_commission'][0]:,.0f}",
            help="Total commission earned"
        )
    with col5:
        st.metric(
            "Transactions", 
            f"{int(overview_data['total_ops'][0]):,}",
            help="Total number of operations"
        )

# Define Tabs
tabs = st.tabs([
    "📊 Performance Dashboard", 
    "💡 Strategic Insights", 
    "🔍 Operational Analysis",
    "🛡️ Risk & Audit"
])

# --- TAB 1: PERFORMANCE DASHBOARD ---
with tabs[0]:
    st.markdown("### 📈 Key Performance Indicators")
    
    # Monthly trend
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Monthly Revenue Trend")
        monthly_query = f"""
            SELECT 
                MES,
                SUM(COMISION) as revenue,
                SUM("VALOR NEGOCIO") as volume,
                COUNT(*) as operations
            FROM operaciones_bmc 
            {filter_query}
            GROUP BY MES
            ORDER BY 
                CASE 
                    WHEN MES LIKE 'ene%' THEN 1
                    WHEN MES LIKE 'feb%' THEN 2
                    WHEN MES LIKE 'mar%' THEN 3
                    WHEN MES LIKE 'abr%' THEN 4
                    WHEN MES LIKE 'may%' THEN 5
                    WHEN MES LIKE 'jun%' THEN 6
                    WHEN MES LIKE 'jul%' THEN 7
                    WHEN MES LIKE 'ago%' THEN 8
                    WHEN MES LIKE 'sep%' THEN 9
                    WHEN MES LIKE 'oct%' THEN 10
                    WHEN MES LIKE 'nov%' THEN 11
                    WHEN MES LIKE 'dic%' THEN 12
                    ELSE 0
                END
        """
        monthly_df = safe_query(monthly_query, "monthly trend")
        
        if not monthly_df.empty:
            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Scatter(
                x=monthly_df['MES'],
                y=monthly_df['revenue'],
                mode='lines+markers',
                name='Revenue',
                line=dict(color='#2E86AB', width=3),
                marker=dict(size=8),
                hovertemplate='<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.update_layout(
                title="Monthly Commission Revenue",
                xaxis_title="Month",
                yaxis_title="Revenue ($)",
                hovermode='x unified'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            st.caption("💡 Track revenue performance across months")
        else:
            st.info("No data available for monthly trend")
    
    with col_right:
        st.subheader("🏆 Top 10 Clients by Revenue")
        clients_query = f"""
            SELECT 
                CLIENTE,
                SUM(COMISION) as revenue,
                COUNT(*) as transactions,
                SUM("VALOR NEGOCIO") as volume
            FROM operaciones_bmc 
            {filter_query}
            GROUP BY CLIENTE
            ORDER BY revenue DESC
            LIMIT 10
        """
        clients_df = safe_query(clients_query, "top clients")
        
        if not clients_df.empty:
            fig_clients = px.bar(
                clients_df,
                x='revenue',
                y='CLIENTE',
                orientation='h',
                title="Top Revenue Generators",
                labels={'revenue': 'Revenue ($)', 'CLIENTE': 'Client'},
                color='revenue',
                color_continuous_scale='Blues'
            )
            fig_clients.update_traces(
                hovertemplate='<b>%{y}</b><br>Revenue: $%{x:,.0f}<br>Transactions: %{customdata[0]}<extra></extra>',
                customdata=clients_df[['transactions']]
            )
            st.plotly_chart(fig_clients, use_container_width=True)
            st.caption("💡 Focus on high-value client relationships")
        else:
            st.info("No client data available")
    
    # Product Performance
    st.markdown("---")
    st.subheader("📦 Product Performance Analysis")
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        products_query = f"""
            SELECT 
                "NOMBRE PRODUCTO",
                SUM(COMISION) as revenue,
                SUM("VALOR NEGOCIO") as volume,
                COUNT(*) as transactions,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc 
            {filter_query}
            GROUP BY "NOMBRE PRODUCTO"
            ORDER BY revenue DESC
            LIMIT 10
        """
        products_df = safe_query(products_query, "top products")
        
        if not products_df.empty:
            fig_products = px.treemap(
                products_df,
                path=['NOMBRE PRODUCTO'],
                values='revenue',
                title="Revenue by Product (Treemap)",
                color='avg_commission_rate',
                color_continuous_scale='RdYlGn',
                labels={'avg_commission_rate': 'Avg Commission %'}
            )
            st.plotly_chart(fig_products, use_container_width=True)
        else:
            st.info("No product data available")
    
    with col_prod2:
        if not products_df.empty:
            st.dataframe(
                products_df.style.format({
                    'revenue': '${:,.0f}',
                    'volume': '${:,.0f}',
                    'transactions': '{:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                use_container_width=True,
                height=400
            )

# --- TAB 2: STRATEGIC INSIGHTS ---
with tabs[1]:
    st.header("💡 AI-Driven Business Opportunities")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
    <b>🎯 Strategic Actions:</b><br>
    • <b>Churn Prevention</b>: Re-engage inactive clients<br>
    • <b>Cross-Selling</b>: Bundle frequently paired products<br>
    • <b>Growth Opportunities</b>: Target underserved segments
    </div>
    """, unsafe_allow_html=True)
    
    col_strat1, col_strat2 = st.columns(2)
    
    with col_strat1:
        st.subheader("🚨 Churn Risk Analysis")
        st.markdown("**Clients inactive for 60+ days**")
        
        churn_query = f"""
            SELECT 
                CLIENTE,
                MAX("FECHA REGISTRO") as last_transaction,
                DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) as days_inactive,
                SUM(COMISION) as lifetime_revenue,
                COUNT(*) as total_transactions
            FROM operaciones_bmc
            {filter_query}
            GROUP BY CLIENTE
            HAVING DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) > 60
            ORDER BY lifetime_revenue DESC
            LIMIT 15
        """
        churn_df = safe_query(churn_query, "churn analysis")
        
        if not churn_df.empty:
            st.dataframe(
                churn_df.style.format({
                    'days_inactive': '{:.0f}',
                    'lifetime_revenue': '${:,.0f}',
                    'total_transactions': '{:,.0f}'
                }),
                use_container_width=True
            )
            st.warning(f"⚠️ {len(churn_df)} high-value clients at risk")
            st.markdown("**Action:** Schedule re-engagement calls with top 5 clients")
        else:
            st.success("✅ No high-value clients at churn risk")
    
    with col_strat2:
        st.subheader("🎯 Cross-Selling Opportunities")
        st.markdown("**Products frequently bought together**")
        
        cross_sell_query = f"""
            WITH client_products AS (
                SELECT DISTINCT 
                    "NIT COMPRADOR" as client,
                    "NOMBRE PRODUCTO" as product
                FROM operaciones_bmc
                {filter_query}
            )
            SELECT 
                p1.product as product_a,
                p2.product as product_b,
                COUNT(DISTINCT p1.client) as shared_clients,
                ROUND(COUNT(DISTINCT p1.client) * 100.0 / 
                    (SELECT COUNT(DISTINCT client) FROM client_products), 2) as market_penetration
            FROM client_products p1
            JOIN client_products p2 
                ON p1.client = p2.client 
                AND p1.product < p2.product
            GROUP BY p1.product, p2.product
            HAVING COUNT(DISTINCT p1.client) >= 3
            ORDER BY shared_clients DESC
            LIMIT 10
        """
        cross_sell_df = safe_query(cross_sell_query, "cross-sell analysis")
        
        if not cross_sell_df.empty:
            st.dataframe(cross_sell_df, use_container_width=True)
            st.info("💡 Create bundled offers for top product pairs")
        else:
            st.info("Not enough data for cross-sell analysis")
    
    # Client Segmentation
    st.markdown("---")
    st.subheader("👥 Client Segmentation by Value")
    
    segment_query = f"""
        WITH client_stats AS (
            SELECT 
                CLIENTE,
                SUM(COMISION) as total_revenue,
                COUNT(*) as transaction_count,
                AVG(COMISION) as avg_transaction_value
            FROM operaciones_bmc
            {filter_query}
            GROUP BY CLIENTE
        )
        SELECT 
            CASE 
                WHEN total_revenue >= (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_revenue) FROM client_stats) 
                    THEN 'VIP (Top 20%)'
                WHEN total_revenue >= (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_revenue) FROM client_stats)
                    THEN 'High Value (50-80%)'
                WHEN total_revenue >= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY total_revenue) FROM client_stats)
                    THEN 'Medium Value (20-50%)'
                ELSE 'Low Value (Bottom 20%)'
            END as segment,
            COUNT(*) as client_count,
            SUM(total_revenue) as segment_revenue,
            AVG(transaction_count) as avg_transactions
        FROM client_stats
        GROUP BY segment
        ORDER BY segment_revenue DESC
    """
    segment_df = safe_query(segment_query, "client segmentation")
    
    if not segment_df.empty:
        col_seg1, col_seg2 = st.columns(2)
        
        with col_seg1:
            fig_segment = px.pie(
                segment_df,
                values='client_count',
                names='segment',
                title='Client Distribution by Segment',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_segment, use_container_width=True)
        
        with col_seg2:
            fig_revenue = px.bar(
                segment_df,
                x='segment',
                y='segment_revenue',
                title='Revenue Contribution by Segment',
                labels={'segment_revenue': 'Revenue ($)', 'segment': 'Client Segment'},
                color='segment_revenue',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)

# --- TAB 3: OPERATIONAL ANALYSIS ---
with tabs[2]:
    st.header("🔍 Operational Deep-Dive")
    
    # Day of week analysis
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        st.subheader("📅 Daily Operation Patterns")
        
        dow_query = f"""
            SELECT 
                DAYNAME("FECHA REGISTRO") as day_of_week,
                COUNT(*) as operations,
                SUM(COMISION) as revenue,
                AVG(COMISION) as avg_commission
            FROM operaciones_bmc
            {filter_query}
            GROUP BY day_of_week
        """
        dow_df = safe_query(dow_query, "day of week analysis")
        
        if not dow_df.empty:
            # Order days properly
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_df['day_of_week'] = pd.Categorical(dow_df['day_of_week'], categories=day_order, ordered=True)
            dow_df = dow_df.sort_values('day_of_week')
            
            fig_dow = px.bar(
                dow_df,
                x='day_of_week',
                y='operations',
                title='Operations by Day of Week',
                labels={'operations': 'Number of Operations', 'day_of_week': 'Day'},
                color='operations',
                color_continuous_scale='Viridis'
            )
            fig_dow.update_traces(
                hovertemplate='<b>%{x}</b><br>Operations: %{y}<br>Revenue: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=dow_df[['revenue']]
            )
            st.plotly_chart(fig_dow, use_container_width=True)
            st.caption("💡 Optimize staffing based on peak days")
        else:
            st.info("No data for day of week analysis")
    
    with col_op2:
        st.subheader("🏭 Operations by Type")
        
        op_type_query = f"""
            SELECT 
                "TIPO OPERACION",
                COUNT(*) as operations,
                SUM(COMISION) as revenue,
                SUM("VALOR NEGOCIO") as volume
            FROM operaciones_bmc
            {filter_query}
            GROUP BY "TIPO OPERACION"
            ORDER BY operations DESC
        """
        op_type_df = safe_query(op_type_query, "operation type analysis")
        
        if not op_type_df.empty:
            fig_op_type = px.pie(
                op_type_df,
                values='operations',
                names='TIPO OPERACION',
                title='Distribution by Operation Type',
                hole=0.3
            )
            fig_op_type.update_traces(
                hovertemplate='<b>%{label}</b><br>Operations: %{value}<br>Revenue: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=op_type_df[['revenue']]
            )
            st.plotly_chart(fig_op_type, use_container_width=True)
        else:
            st.info("No operation type data available")
    
    # Geographic analysis
    st.markdown("---")
    st.subheader("🗺️ Geographic Distribution")
    
    col_geo1, col_geo2 = st.columns(2)
    
    with col_geo1:
        st.markdown("**Top Cities - Buyers**")
        buyer_cities_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CIUDAD COMPRADOR" IS NOT NULL'
        buyer_cities_query = f"""
            SELECT 
                "CIUDAD COMPRADOR" as city,
                COUNT(*) as operations,
                SUM(COMISION) as revenue
            FROM operaciones_bmc
            {buyer_cities_where}
            GROUP BY city
            ORDER BY revenue DESC
            LIMIT 10
        """
        buyer_cities_df = safe_query(buyer_cities_query, "buyer cities")
        
        if not buyer_cities_df.empty:
            st.dataframe(
                buyer_cities_df.style.format({
                    'operations': '{:,.0f}',
                    'revenue': '${:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No buyer city data")
    
    with col_geo2:
        st.markdown("**Top Cities - Sellers**")
        seller_cities_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CIUDAD VENDEDOR" IS NOT NULL'
        seller_cities_query = f"""
            SELECT 
                "CIUDAD VENDEDOR" as city,
                COUNT(*) as operations,
                SUM(COMISION) as revenue
            FROM operaciones_bmc
            {seller_cities_where}
            GROUP BY city
            ORDER BY revenue DESC
            LIMIT 10
        """
        seller_cities_df = safe_query(seller_cities_query, "seller cities")
        
        if not seller_cities_df.empty:
            st.dataframe(
                seller_cities_df.style.format({
                    'operations': '{:,.0f}',
                    'revenue': '${:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No seller city data")

# --- TAB 4: RISK & AUDIT ---
with tabs[3]:
    st.header("🛡️ Risk & Audit Dashboard")
    
    # Revenue concentration (Pareto)
    st.subheader("1. Revenue Concentration Analysis (Pareto)")
    st.markdown("_Monitor dependency on key clients_")
    
    pareto_query = f"""
        SELECT 
            CLIENTE,
            SUM(COMISION) as revenue
        FROM operaciones_bmc
        {filter_query}
        GROUP BY CLIENTE
        ORDER BY revenue DESC
        LIMIT 50
    """
    pareto_df = safe_query(pareto_query, "pareto analysis")
    
    if not pareto_df.empty:
        pareto_df['cumulative_revenue'] = pareto_df['revenue'].cumsum()
        pareto_df['cumulative_pct'] = (pareto_df['cumulative_revenue'] / pareto_df['revenue'].sum()) * 100
        
        fig_pareto = go.Figure()
        
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['CLIENTE'],
            y=pareto_df['revenue'],
            name='Revenue',
            marker_color='lightblue',
            hovertemplate='<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>'
        ))
        
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df['CLIENTE'],
            y=pareto_df['cumulative_pct'],
            name='Cumulative %',
            yaxis='y2',
            mode='lines+markers',
            marker=dict(color='red', size=6),
            line=dict(color='red', width=2),
            hovertemplate='<b>%{x}</b><br>Cumulative: %{y:.1f}%<extra></extra>'
        ))
        
        fig_pareto.update_layout(
            title='Revenue Concentration (Pareto Chart)',
            xaxis_title='Client',
            yaxis_title='Revenue ($)',
            yaxis2=dict(
                title='Cumulative Percentage (%)',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig_pareto, use_container_width=True)
        
        # Calculate 80-20 rule
        top_20_pct_count = int(len(pareto_df) * 0.2)
        top_20_revenue_pct = pareto_df.iloc[:top_20_pct_count]['revenue'].sum() / pareto_df['revenue'].sum() * 100
        
        st.info(f"📊 Top 20% of clients ({top_20_pct_count} clients) generate {top_20_revenue_pct:.1f}% of revenue")
        
        if top_20_revenue_pct > 80:
            st.warning("⚠️ High revenue concentration risk detected")
        else:
            st.success("✅ Healthy revenue distribution")
    else:
        st.info("No data for Pareto analysis")
    
    # Pricing anomalies
    st.markdown("---")
    st.subheader("2. Pricing Anomaly Detection")
    st.markdown("_Transactions with significantly lower commission rates_")
    
    anomaly_query = f"""
        WITH product_avg AS (
            SELECT 
                "NOMBRE PRODUCTO",
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_rate
            FROM operaciones_bmc
            {filter_query}
            GROUP BY "NOMBRE PRODUCTO"
            HAVING AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) > 0
        )
        SELECT 
            t.OPERACION,
            t.CLIENTE,
            t."NOMBRE PRODUCTO",
            t."VALOR NEGOCIO" as transaction_value,
            (t.COMISION / NULLIF(t."VALOR NEGOCIO", 0)) * 100 as actual_rate,
            p.avg_rate as market_avg_rate,
            ROUND(((p.avg_rate - (t.COMISION / NULLIF(t."VALOR NEGOCIO", 0)) * 100) / p.avg_rate) * 100, 1) as discount_pct
        FROM operaciones_bmc t
        JOIN product_avg p ON t."NOMBRE PRODUCTO" = p."NOMBRE PRODUCTO"
        {filter_query.replace('WHERE', 'AND') if filter_query else ''}
        WHERE (t.COMISION / NULLIF(t."VALOR NEGOCIO", 0)) * 100 < (p.avg_rate * 0.7)
        ORDER BY discount_pct DESC
        LIMIT 20
    """
    anomaly_df = safe_query(anomaly_query, "pricing anomalies")
    
    if not anomaly_df.empty:
        st.dataframe(
            anomaly_df.style.format({
                'transaction_value': '${:,.0f}',
                'actual_rate': '{:.2f}%',
                'market_avg_rate': '{:.2f}%',
                'discount_pct': '{:.1f}%'
            }),
            use_container_width=True
        )
        st.warning(f"⚠️ Found {len(anomaly_df)} transactions with unusually low commission rates")
        st.markdown("**Action:** Review these transactions for pricing errors or special agreements")
    else:
        st.success("✅ No significant pricing anomalies detected")
    
    # Transaction size distribution
    st.markdown("---")
    st.subheader("3. Transaction Size Distribution")
    
    col_size1, col_size2 = st.columns(2)
    
    with col_size1:
        size_query = f"""
            SELECT 
                CASE 
                    WHEN "VALOR NEGOCIO" < 1000000 THEN 'Small (< $1M)'
                    WHEN "VALOR NEGOCIO" < 10000000 THEN 'Medium ($1M-$10M)'
                    WHEN "VALOR NEGOCIO" < 50000000 THEN 'Large ($10M-$50M)'
                    ELSE 'Very Large (> $50M)'
                END as size_category,
                COUNT(*) as transaction_count,
                SUM(COMISION) as total_revenue,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc
            {filter_query}
            GROUP BY size_category
            ORDER BY 
                CASE size_category
                    WHEN 'Small (< $1M)' THEN 1
                    WHEN 'Medium ($1M-$10M)' THEN 2
                    WHEN 'Large ($10M-$50M)' THEN 3
                    ELSE 4
                END
        """
        size_df = safe_query(size_query, "transaction size")
        
        if not size_df.empty:
            fig_size = px.pie(
                size_df,
                values='transaction_count',
                names='size_category',
                title='Transaction Count by Size',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues
            )
            fig_size.update_traces(
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Revenue: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=size_df[['total_revenue']]
            )
            st.plotly_chart(fig_size, use_container_width=True)
        else:
            st.info("No transaction size data")
    
    with col_size2:
        if not size_df.empty:
            st.markdown("**Transaction Size Breakdown**")
            st.dataframe(
                size_df.style.format({
                    'transaction_count': '{:,.0f}',
                    'total_revenue': '${:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            st.caption("💡 Large transactions may require special handling")

# Footer
st.markdown("---")
st.markdown("""
### 📊 **Dashboard Summary**

**Enhanced Features:**
- ✅ Improved error handling and data validation
- ✅ Better SQL queries with proper NULL handling
- ✅ Enhanced visualizations with tooltips
- ✅ Comprehensive filtering options
- ✅ Risk management and anomaly detection
- ✅ Geographic and operational insights

**Next Steps:**
1. Set up automated alerts for key metrics
2. Export reports for stakeholder meetings
3. Schedule regular dashboard reviews
4. Integrate with CRM for client management

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
""")

# Close connection when done
# con.close()  # Don't close here - let Streamlit cache handle it