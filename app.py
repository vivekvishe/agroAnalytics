import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import hashlib

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

# Page Configuration
st.set_page_config(
    page_title="Agro Analytics Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SECURE LOGIN AUTHENTICATION
# ============================================

# SECURITY NOTE: Password is stored as SHA-256 hash, not plain text
# The actual password is: 
# To generate hash for a new password, run in Python:
#   import hashlib
#   hashlib.sha256("YourNewPassword".encode()).hexdigest()

ADMIN_USERNAME = "admin"
PASSWORD_HASH = "e0bd631724a4fb17f0fc7c19ac460ef1838cdf4c4d0a922e63c09d92b90922d8"

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Compare hashed passwords instead of plain text
        if (st.session_state["username"] == ADMIN_USERNAME and 
            hash_password(st.session_state["password"]) == PASSWORD_HASH):
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
    - **Performance Metrics**: Commission, volume, and operational efficiency
    - **Strategic Insights**: AI-powered business opportunities and risks
    - **Operational Analysis**: Daily patterns and resource optimization
    - **Risk Management**: Financial exposure and compliance monitoring
    
    ### 🔍 **Navigation**
    1. **📊 Performance Dashboard**: KPIs and commission trends
    2. **💡 Strategic Insights**: Growth opportunities and risk detection
    3. **🔗 Buyer-Seller Network**: Network analysis and potential clients
    4. **👥 Client Insights**: Client value demonstration
    5. **🔍 Operational Deep-Dive**: Daily operations and efficiency
    6. **🛡️ Risk & Audit**: Concentration risk and anomaly detection
    
    ### 💡 **Usage Tips**
    - Use sidebar filters to focus on specific periods
    - Hover over charts for detailed information
    - **Click "🔍 View SQL Query" below each chart** to see the underlying query
    - Export data using download buttons
    - Check tooltips for metric explanations
    
    ### 🔍 **SQL Query Transparency**
    Every chart and table has a collapsible "🔍 View SQL Query" section that shows:
    - The exact SQL query used to generate the data
    - How filters are applied
    - What calculations are performed
    - Complete transparency into our analytics
    """)

# Quick Stats Overview
st.markdown("---")
st.subheader("🚀 Business Overview - Your Commission Earnings at a Glance")

col1, col2, col3, col4, col5 = st.columns(5)

# Get overview metrics
overview_query = f"""
    SELECT 
        COUNT(DISTINCT CLIENTE) as unique_clients,
        COUNT(DISTINCT "NOMBRE PRODUCTO") as unique_products,
        SUM("VALOR NEGOCIO") as total_volume,
        SUM(COMISION) as total_commission,
        COUNT(*) as total_ops,
        AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
    FROM operaciones_bmc 
    {filter_query}
"""

with st.expander("🔍 View Overview SQL Query", expanded=False):
    st.code(overview_query, language="sql")

overview_data = safe_query(overview_query, "overview metrics")

if not overview_data.empty:
    with col1:
        st.metric(
            "💰 Your Commission Earnings", 
            f"${overview_data['total_commission'][0]:,.0f}",
            help="Total commission earned - this is YOUR company's earnings!"
        )
    with col2:
        st.metric(
            "📊 Client Volume", 
            f"${overview_data['total_volume'][0]:,.0f}",
            help="Total value of client transactions (not your commission earnings)"
        )
    with col3:
        st.metric(
            "📈 Avg Commission Rate", 
            f"{overview_data['avg_commission_rate'][0]:.2f}%",
            help="Average percentage you earn on each transaction"
        )
    with col4:
        st.metric(
            "👥 Active Clients", 
            f"{int(overview_data['unique_clients'][0]):,}",
            help="Number of clients generating commission earnings for you"
        )
    with col5:
        st.metric(
            "✅ Transactions", 
            f"{int(overview_data['total_ops'][0]):,}",
            help="Total operations processed"
        )

# Define Tabs
tabs = st.tabs([
    "📊 Performance Dashboard", 
    "💡 Strategic Insights",
    "🔗 Buyer-Seller Network",
    "👥 Client Insights",
    "🔍 Operational Analysis",
    "🛡️ Risk & Audit"
])

# --- TAB 1: PERFORMANCE DASHBOARD ---
with tabs[0]:
    st.markdown("### 💰 Commission Performance - Your Commission Earnings")
    st.info("💡 **Remember:** Commissions are YOUR earnings - this is what your company makes!")
    
    # Monthly trend
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Monthly Commission Earnings Trend")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** How much commission is YOUR company earning each month?
            
            **What we're measuring:**
            - **Total commission earned each month** = Your actual income/earnings
            - Total business volume processed (client transactions - NOT your commission earnings)
            - Number of transactions per month
            
            **Why it matters:** This is YOUR bottom line!
            - Identify your best and worst earning months
            - Track growth trends - are you making more commission over time?
            - Spot seasonal patterns to plan cash flow
            
            **How to use it:** 
            - Compare current month to previous - are commissions growing?
            - Investigate dips - why did commission earnings drop?
            - Plan expenses based on expected commission income
            
            **Important:** The commission line shows YOUR company's actual earnings, not client transaction values.
            """)
        
        monthly_query = f"""
            SELECT 
                MES,
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as client_volume,
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
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(monthly_query, language="sql")
        
        monthly_df = safe_query(monthly_query, "monthly trend")
        
        if not monthly_df.empty:
            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Scatter(
                x=monthly_df['MES'],
                y=monthly_df['commission_earnings'],
                mode='lines+markers',
                name='Your Commission Earnings',
                line=dict(color='#27AE60', width=4),
                marker=dict(size=10, color='#27AE60'),
                hovertemplate='<b>%{x}</b><br>💰 Your Earnings: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.update_layout(
                title="Your Monthly Commission Earnings",
                xaxis_title="Month",
                yaxis_title="Commission Earnings ($) - YOUR INCOME",
                hovermode='x unified',
                plot_bgcolor='rgba(39,174,96,0.1)'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            st.caption("💰 This shows YOUR company's actual earnings from commissions")
        else:
            st.info("No data available for monthly trend")
    
    with col_right:
        st.subheader("🏆 Top 10 Clients by Commission Earnings")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** Which clients are generating the most commission for YOU?
            
            **What we're measuring:**
            - **Total commission generated by each client** = How much each client pays YOU
            - Number of transactions per client
            - Total transaction volume (their business, not your earnings)
            
            **Why it matters:**
            - These are YOUR cash cows - the clients who pay your bills!
            - They deserve VIP treatment to keep them happy
            - Losing one of these clients would hurt your commission earnings significantly
            
            **How to use it:** 
            - Call these clients regularly to maintain relationships
            - Give them priority service and special attention
            - Offer them incentives to do MORE business with you
            - If any appear on the "Churn Risk" list - URGENT action needed!
            
            **Bottom line:** These clients = Your biggest paychecks. Keep them happy!
            """)
        
        clients_query = f"""
            SELECT 
                CLIENTE,
                SUM(COMISION) as commission_earnings,
                COUNT(*) as transactions,
                SUM("VALOR NEGOCIO") as transaction_volume,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc 
            {filter_query}
            GROUP BY CLIENTE
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(clients_query, language="sql")
        
        clients_df = safe_query(clients_query, "top clients")
        
        if not clients_df.empty:
            fig_clients = px.bar(
                clients_df,
                x='commission_earnings',
                y='CLIENTE',
                orientation='h',
                title="Top Commission Generators - YOUR Biggest Earners",
                labels={'commission_earnings': 'Commission Earnings ($) - YOUR INCOME', 'CLIENTE': 'Client'},
                color='commission_earnings',
                color_continuous_scale='Greens'
            )
            fig_clients.update_traces(
                hovertemplate='<b>%{y}</b><br>💰 Pays YOU: $%{x:,.0f}<br>Transactions: %{customdata[0]}<br>Avg Rate: %{customdata[1]:.2f}%<extra></extra>',
                customdata=clients_df[['transactions', 'avg_commission_rate']]
            )
            st.plotly_chart(fig_clients, use_container_width=True)
            st.caption("💰 These clients generate the most commission earnings for YOUR company")
        else:
            st.info("No client data available")
    
    # Referenciador Performance
    st.markdown("---")
    st.subheader("🤝 All Referenciadores - Your commission drivers")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Which referenciadores are bringing in the most commission earnings for YOUR company?
        
        **What we're measuring:**
        - **Total commission volume** each referenciador has generated = Commission they brought YOU
        - Number of operations they've facilitated
        - Average commission per operation
        - **Estimated earnings for each referenciador** (what YOU pay them from commissions)
        
        **Why it matters:**
        - These people are directly responsible for YOUR commission earnings!
        - Top performers deserve bonuses and recognition
        - They're incentivized by commission, so they're motivated to bring more business
        
        **How to use it:**
        - **Reward top performers** - Give them bonuses, public recognition, better territories
        - **Learn from them** - What are they doing right? Teach others their methods
        - **Motivate others** - Show the team what top performers earn
        - **Retention** - Don't lose your best commission generators to competitors!
        
        **Key insight:** Your top referenciadores = Your money-makers. Invest in keeping them happy and productive!
        """)
    
    col_ref1, col_ref2 = st.columns(2)
    
    with col_ref1:
        referenciador_where = filter_query + (" AND " if filter_query else "WHERE ") + "REFERENCIADOR IS NOT NULL AND REFERENCIADOR != 0"
        referenciador_query = f"""
            SELECT 
                REFERENCIADOR,
                COUNT(*) as total_operations,
                SUM(COMISION) as total_commission,
                SUM("VALOR NEGOCIO") as total_volume,
                AVG(COMISION) as avg_commission_per_op,
                SUM(COMISION * ("% REF VENTA" / 100.0)) + SUM(COMISION * ("% REF COMPRA" / 100.0)) as referenciador_earnings
            FROM operaciones_bmc
            {referenciador_where}
            GROUP BY REFERENCIADOR
            ORDER BY total_commission DESC
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(referenciador_query, language="sql")
        
        referenciador_df = safe_query(referenciador_query, "all referenciadores")
        
        if not referenciador_df.empty:
            # Show chart for top 10 for visualization clarity
            top_10_ref_df = referenciador_df.head(10).copy()
            
            # Convert REFERENCIADOR to string for better display
            top_10_ref_df['REFERENCIADOR'] = top_10_ref_df['REFERENCIADOR'].astype(str)
            
            fig_ref = go.Figure()
            
            # Add vertical bar chart
            fig_ref.add_trace(go.Bar(
                x=top_10_ref_df['REFERENCIADOR'],
                y=top_10_ref_df['total_commission'],
                marker=dict(
                    color=top_10_ref_df['total_commission'],
                    colorscale='Greens',
                    showscale=False,
                    line=dict(color='darkgreen', width=1)
                ),
                text=top_10_ref_df['total_commission'],
                texttemplate='$%{text:,.0f}',
                textposition='outside',
                hovertemplate='<b>Ref Code: %{x}</b><br>' +
                             'Total Commission: $%{y:,.0f}<br>' +
                             'Operations: %{customdata[0]:,.0f}<br>' +
                             'Avg per Op: $%{customdata[1]:,.0f}<br>' +
                             'Est. Earnings: $%{customdata[2]:,.0f}<extra></extra>',
                customdata=top_10_ref_df[['total_operations', 'avg_commission_per_op', 'referenciador_earnings']]
            ))
            
            fig_ref.update_layout(
                title={
                    'text': "Top 10 commission drivers - Commission Volume Generated",
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis_title="Referenciador Code",
                yaxis_title="Total Commission Earnings ($) - Generated for YOU",
                height=500,
                margin=dict(l=80, r=40, t=80, b=80),
                plot_bgcolor='rgba(240,240,240,0.3)',
                paper_bgcolor='white',
                font=dict(size=12),
                xaxis=dict(
                    showgrid=False,
                    tickangle=-45  # Angle the labels for better readability
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='lightgray',
                    tickformat='$,.0f'
                )
            )
            
            st.plotly_chart(fig_ref, use_container_width=True)
            st.caption("💡 Chart shows top 10 for clarity - full list in table below")
        else:
            st.info("No referenciador data available")
    
    with col_ref2:
        if not referenciador_df.empty:
            st.markdown(f"**Complete Performance Metrics - All {len(referenciador_df)} Referenciadores**")
            
            # Prepare display dataframe
            display_df = referenciador_df.copy()
            display_df['REFERENCIADOR'] = display_df['REFERENCIADOR'].astype(str)
            display_df = display_df[['REFERENCIADOR', 'total_operations', 'total_commission', 'total_volume', 'referenciador_earnings']]
            
            st.dataframe(
                display_df.style.format({
                    'total_operations': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'total_volume': '${:,.0f}',
                    'referenciador_earnings': '${:,.0f}'
                }),
                use_container_width=True,
                height=500
            )
            
            # Summary stats
            total_commission = referenciador_df['total_commission'].sum()
            total_earnings = referenciador_df['referenciador_earnings'].sum()
            
            st.info(f"""
            📊 **Summary:**
            - Total Referenciadores: {len(referenciador_df)}
            - Total Commission Generated: ${total_commission:,.0f}
            - Total Referenciador Earnings: ${total_earnings:,.0f}
            """)
            
            st.caption("💰 Scroll through the complete list - estimated referenciador earnings based on commission percentages")
        else:
            st.info("No referenciador data available")
    
    # Product Performance
    st.markdown("---")
    st.subheader("📦 Product Performance - Which Products Make YOU the Most Money")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Which products generate the most commission earnings for YOUR company?
        
        **What we're measuring:**
        - **Total commission earnings per product** = How much each product pays YOU
        - Transaction volume per product (client business, not your earnings)
        - Number of transactions per product
        - **Average commission rate** - which products have the best margins for YOU
        
        **Why it matters:**
        - Focus on promoting products with highest commission earnings
        - Products with high commission rates = more profitable for YOU
        - Understanding product mix helps plan commission growth
        
        **How to use it:**
        - **Push high-margin products** - Train referenciadores to sell products with better commission rates
        - **Bundle strategically** - Combine popular products with high-margin ones
        - **Pricing strategy** - Consider if low-margin products should have higher rates
        
        **Treemap guide:** 
        - Bigger boxes = more commission earnings for YOU
        - Greener color = higher commission rate (better margins)
        - Focus on big + green boxes = your most profitable products!
        """)
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        products_query = f"""
            SELECT 
                "NOMBRE PRODUCTO",
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as volume,
                COUNT(*) as transactions,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc 
            {filter_query}
            GROUP BY "NOMBRE PRODUCTO"
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(products_query, language="sql")
        
        products_df = safe_query(products_query, "top products")
        
        if not products_df.empty:
            fig_products = px.treemap(
                products_df,
                path=['NOMBRE PRODUCTO'],
                values='commission_earnings',
                title="Commission by Product (Treemap)",
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
                    'commission_earnings': '${:,.0f}',
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
        st.subheader("🚨 Churn Risk Analysis - Protect Your Commission Earnings!")
        st.markdown("**High-value clients who haven't paid you recently (60+ days)**")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** Which clients used to pay YOU good commissions but have stopped?
            
            **What we're measuring:**
            - Clients who haven't had a transaction in over 60 days
            - How many days since they last generated commission earnings for YOU
            - **Their lifetime commission value** = Total money they've paid YOU historically
            - Total number of transactions they've done
            
            **Why it matters - THIS IS CRITICAL:**
            - These clients USED TO pay you money - now they're not!
            - You're losing recurring commission earnings
            - They may have switched to a competitor
            - Every day they're inactive = lost income for YOUR company
            
            **How to use it - URGENT ACTIONS:**
            1. **Call the top 5 TODAY** - These are high-value commission sources you're losing
            2. **Find out why** - Did they switch? Are they unhappy? Do they have a problem?
            3. **Win them back** - Offer special deals, better service, personal attention
            4. **Calculate the loss** - If they don't come back, how much annual commission do you lose?
            
            **Example:** If a client who used to pay you $50,000/year in commissions is inactive for 60 days, you've already lost ~$8,000!
            """)
        
        churn_query = f"""
            SELECT 
                CLIENTE,
                MAX("FECHA REGISTRO") as last_transaction,
                DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) as days_inactive,
                SUM(COMISION) as lifetime_commission,
                COUNT(*) as total_transactions
            FROM operaciones_bmc
            {filter_query}
            GROUP BY CLIENTE
            HAVING DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) > 60
            ORDER BY lifetime_commission DESC
            LIMIT 15
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(churn_query, language="sql")
        
        churn_df = safe_query(churn_query, "churn analysis")
        
        if not churn_df.empty:
            st.dataframe(
                churn_df.style.format({
                    'days_inactive': '{:.0f}',
                    'lifetime_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}'
                }),
                use_container_width=True
            )
            total_at_risk = churn_df['lifetime_commission'].sum()
            st.error(f"🚨 **URGENT:** {len(churn_df)} high-value clients at risk! They've paid YOU ${total_at_risk:,.0f} in total commissions historically!")
            st.markdown("**Action Required:** Contact these clients immediately to prevent permanent commission loss!")
        else:
            st.success("✅ No high-value clients at churn risk")
    
    with col_strat2:
        st.subheader("🎯 Cross-Selling Opportunities")
        st.markdown("**Products frequently bought together**")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** Which products do clients often buy together?
            
            **What we're measuring:**
            - Product pairs that the same clients purchase
            - Number of shared clients between product pairs
            - Market penetration percentage (what % of clients buy both)
            
            **Why it matters:**
            - Create bundled product offers
            - Train sales team on natural product combinations
            - Increase commission per client by suggesting complementary products
            
            **How to use it:**
            - When a client buys Product A, suggest Product B
            - Create promotional bundles of frequently paired products
            - Design marketing campaigns highlighting these combinations
            """)
        
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
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(cross_sell_query, language="sql")
        
        cross_sell_df = safe_query(cross_sell_query, "cross-sell analysis")
        
        if not cross_sell_df.empty:
            st.dataframe(cross_sell_df, use_container_width=True)
            st.info("💡 Create bundled offers for top product pairs")
        else:
            st.info("Not enough data for cross-sell analysis")
    
    # Client Segmentation
    st.markdown("---")
    st.subheader("👥 Client Segmentation by Commission Value - Who Pays YOU the Most")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** How should we prioritize clients based on how much commission earnings they generate for US?
        
        **What we're measuring:**
        - Clients grouped into 4 segments based on **commission earnings** they pay YOU:
          - **VIP (Top 20%)**: Clients who pay YOU the most in commissions - your cash cows!
          - **High Value (50-80%)**: Solid commission payers - important commission sources
          - **Medium Value (20-50%)**: Regular commission payers - moderate commission
          - **Low Value (Bottom 20%)**: Small commission payers - newer or occasional clients
        
        **Why it matters - This is YOUR money segmentation:**
        - VIP clients = Your biggest paychecks - treat them like gold!
        - Different service levels = allocate resources where YOU make the most money
        - Growth strategy = move clients up to higher commission tiers
        
        **How to use it:**
        - **VIP Clients**: Dedicated account managers, priority service, personal attention
          - *They pay your bills - don't lose them!*
        - **High Value**: Regular check-ins, special offers to increase their business
          - *Potential to become VIP - invest in them*
        - **Medium Value**: Standard service, opportunities to upsell
          - *Can they do more volume? Better commission rates?*
        - **Low Value**: Efficient service, identify growth potential
          - *Can they grow or are they just small accounts?*
        
        **Key insight:** The more commission earnings a client generates, the more attention they deserve from YOUR team!
        """)
    
    segment_query = f"""
        WITH client_stats AS (
            SELECT 
                CLIENTE,
                SUM(COMISION) as total_commission,
                COUNT(*) as transaction_count,
                AVG(COMISION) as avg_commission_per_transaction,
                SUM("VALOR NEGOCIO") as total_volume
            FROM operaciones_bmc
            {filter_query}
            GROUP BY CLIENTE
        )
        SELECT 
            CASE 
                WHEN total_commission >= (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_commission) FROM client_stats) 
                    THEN 'VIP (Top 20%)'
                WHEN total_commission >= (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_commission) FROM client_stats)
                    THEN 'High Value (50-80%)'
                WHEN total_commission >= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY total_commission) FROM client_stats)
                    THEN 'Medium Value (20-50%)'
                ELSE 'Low Value (Bottom 20%)'
            END as segment,
            COUNT(*) as client_count,
            SUM(total_commission) as segment_commission,
            AVG(transaction_count) as avg_transactions,
            AVG(avg_commission_per_transaction) as avg_commission_per_deal
        FROM client_stats
        GROUP BY segment
        ORDER BY segment_commission DESC
    """
    
    with st.expander("🔍 View SQL Query", expanded=False):
        st.code(segment_query, language="sql")
    
    segment_df = safe_query(segment_query, "client segmentation")
    
    if not segment_df.empty:
        col_seg1, col_seg2 = st.columns(2)
        
        with col_seg1:
            fig_segment = px.pie(
                segment_df,
                values='client_count',
                names='segment',
                title='Client Distribution by Commission Value Segment',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            fig_segment.update_traces(
                hovertemplate='<b>%{label}</b><br>Clients: %{value}<br>commission earnings: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=segment_df[['segment_commission']]
            )
            st.plotly_chart(fig_segment, use_container_width=True)
            st.caption("📊 Distribution of clients across value segments")
        
        with col_seg2:
            fig_commission = px.bar(
                segment_df,
                x='segment',
                y='segment_commission',
                title='Commission Contribution by Segment - YOUR Earnings',
                labels={'segment_commission': 'Commission ($) - YOUR EARNINGS', 'segment': 'Client Segment'},
                color='segment_commission',
                color_continuous_scale='Greens',
                text='segment_commission'
            )
            fig_commission.update_traces(
                texttemplate='$%{text:,.0f}',
                textposition='outside'
            )
            st.plotly_chart(fig_commission, use_container_width=True)
            st.caption("💰 How much commission earnings each segment pays YOU")
        
        # Add summary table
        st.markdown("**Detailed Segment Breakdown**")
        display_segment_df = segment_df.copy()
        st.dataframe(
            display_segment_df.style.format({
                'client_count': '{:,.0f}',
                'segment_commission': '${:,.0f}',
                'avg_transactions': '{:,.1f}',
                'avg_commission_per_deal': '${:,.0f}'
            }),
            use_container_width=True
        )
        
        # Calculate VIP percentage
        vip_commission = segment_df[segment_df['segment'] == 'VIP (Top 20%)']['segment_commission'].sum()
        total_commission = segment_df['segment_commission'].sum()
        vip_percentage = (vip_commission / total_commission * 100) if total_commission > 0 else 0
        
        st.info(f"💎 **VIP Insight:** Your top 20% of clients generate **${vip_commission:,.0f}** ({vip_percentage:.1f}%) of your total commission earnings!")

# --- TAB 3: BUYER-SELLER NETWORK ---
with tabs[2]:
    st.header("🔗 Buyer-Seller Network Analysis")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
    <b>💡 Understanding the Business Model:</b><br>
    • <b>The Transaction Flow:</b> Seller generates bill → Buyer receives goods → Your company registers the bill at BMC<br>
    • <b>Registration Benefits:</b> Either buyer OR seller gets tax benefits from government<br>
    • <b>Your Role:</b> You earn commission for facilitating the registration<br>
    • <b>Principal:</b> Whoever pays for registration (buyer or seller) is marked as "PRINCIPAL"
    </div>
    """, unsafe_allow_html=True)
    
    # Network Insights Section
    st.markdown("---")
    st.subheader("🕸️ Network Insights & Key Relationships")
    
    col_net1, col_net2 = st.columns(2)
    
    with col_net1:
        st.markdown("#### 🔄 Hub Analysis - Who Connects the Most?")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** Who are the key players connecting buyers and sellers?
            
            **What we're measuring:**
            - **Sellers with most unique buyers** - These are your distribution hubs
            - **Buyers with most unique sellers** - These are your aggregators/retailers
            - Commission earned from each hub
            
            **Why it matters:**
            - Hub sellers = Large producers/distributors with wide reach
            - Hub buyers = Large retailers/aggregators sourcing from many suppliers
            - Losing a hub affects many relationships and commission streams
            
            **How to use it:**
            - Protect hub relationships - they're critical to your network
            - Offer volume discounts or incentives to hubs
            - If a hub churns, you lose multiple commission opportunities
            """)
        
        # Top Seller Hubs
        seller_hub_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE VENDEDOR" IS NOT NULL AND "NIT COMPRADOR" IS NOT NULL'
        seller_hub_query = f"""
            SELECT 
                "NOMBRE VENDEDOR" as seller,
                COUNT(DISTINCT "NIT COMPRADOR") as unique_buyers,
                SUM(COMISION) as total_commission,
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume
            FROM operaciones_bmc
            {seller_hub_where}
            GROUP BY "NOMBRE VENDEDOR"
            HAVING COUNT(DISTINCT "NIT COMPRADOR") >= 2
            ORDER BY unique_buyers DESC, total_commission DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(seller_hub_query, language="sql")
        
        seller_hubs_df = safe_query(seller_hub_query, "seller hubs")
        
        if not seller_hubs_df.empty:
            st.markdown("**🏭 Top Seller Hubs (Most Connected Sellers)**")
            
            fig_seller_hub = px.bar(
                seller_hubs_df,
                x='unique_buyers',
                y='seller',
                orientation='h',
                title='Sellers with Most Unique Buyers',
                labels={'unique_buyers': 'Number of Unique Buyers', 'seller': 'Seller'},
                color='total_commission',
                color_continuous_scale='Oranges',
                hover_data=['total_commission', 'total_transactions']
            )
            fig_seller_hub.update_traces(
                hovertemplate='<b>%{y}</b><br>Unique Buyers: %{x}<br>Commission: $%{customdata[0]:,.0f}<br>Transactions: %{customdata[1]:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_seller_hub, use_container_width=True)
            
            st.dataframe(
                seller_hubs_df.style.format({
                    'unique_buyers': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}',
                    'total_volume': '${:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No seller hub data available")
    
    with col_net2:
        # Top Buyer Hubs
        buyer_hub_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE COMPRADOR" IS NOT NULL AND "NIT VENDEDOR" IS NOT NULL'
        buyer_hub_query = f"""
            SELECT 
                "NOMBRE COMPRADOR" as buyer,
                COUNT(DISTINCT "NIT VENDEDOR") as unique_sellers,
                SUM(COMISION) as total_commission,
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume
            FROM operaciones_bmc
            {buyer_hub_where}
            GROUP BY "NOMBRE COMPRADOR"
            HAVING COUNT(DISTINCT "NIT VENDEDOR") >= 2
            ORDER BY unique_sellers DESC, total_commission DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(buyer_hub_query, language="sql")
        
        buyer_hubs_df = safe_query(buyer_hub_query, "buyer hubs")
        
        if not buyer_hubs_df.empty:
            st.markdown("**🏪 Top Buyer Hubs (Most Connected Buyers)**")
            
            fig_buyer_hub = px.bar(
                buyer_hubs_df,
                x='unique_sellers',
                y='buyer',
                orientation='h',
                title='Buyers with Most Unique Sellers',
                labels={'unique_sellers': 'Number of Unique Sellers', 'buyer': 'Buyer'},
                color='total_commission',
                color_continuous_scale='Greens',
                hover_data=['total_commission', 'total_transactions']
            )
            fig_buyer_hub.update_traces(
                hovertemplate='<b>%{y}</b><br>Unique Sellers: %{x}<br>Commission: $%{customdata[0]:,.0f}<br>Transactions: %{customdata[1]:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_buyer_hub, use_container_width=True)
            
            st.dataframe(
                buyer_hubs_df.style.format({
                    'unique_sellers': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}',
                    'total_volume': '${:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No buyer hub data available")
    
    # Registration Principal Analysis
    st.markdown("---")
    st.subheader("💼 Registration Principal Analysis - Who Pays for Registration?")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Who typically pays for BMC registration - buyers or sellers?
        
        **What we're measuring:**
        - PRINCIPAL field = 'V' (Vendedor/Seller pays) or 'C' (Comprador/Buyer pays)
        - Commission earned from buyer-paid vs seller-paid registrations
        - Number of transactions by principal type
        
        **Why it matters:**
        - Understand which side of the market drives your business
        - Different pricing strategies for buyer vs seller registrations
        - Identify if one side is more price-sensitive
        
        **Strategic insights:**
        - If sellers pay more → Focus marketing on sellers, they value the tax benefit
        - If buyers pay more → Buyers see more value, target buyer acquisition
        - Balanced split → Both sides value the service equally
        """)
    
    principal_where = filter_query + (" AND " if filter_query else "WHERE ") + "PRINCIPAL IS NOT NULL"
    principal_query = f"""
        SELECT 
            CASE 
                WHEN PRINCIPAL = 'V' THEN 'Seller Pays (Vendedor)'
                WHEN PRINCIPAL = 'C' THEN 'Buyer Pays (Comprador)'
                ELSE 'Unknown'
            END as principal_type,
            COUNT(*) as transactions,
            SUM(COMISION) as total_commission,
            AVG(COMISION) as avg_commission,
            SUM("VALOR NEGOCIO") as total_volume,
            AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
        FROM operaciones_bmc
        {principal_where}
        GROUP BY principal_type
        ORDER BY total_commission DESC
    """
    
    with st.expander("🔍 View SQL Query", expanded=False):
        st.code(principal_query, language="sql")
    
    principal_df = safe_query(principal_query, "principal analysis")
    
    if not principal_df.empty:
        col_prin1, col_prin2 = st.columns(2)
        
        with col_prin1:
            fig_principal = px.pie(
                principal_df,
                values='total_commission',
                names='principal_type',
                title='Commission Distribution by Principal',
                hole=0.4,
                color_discrete_sequence=['#E74C3C', '#3498DB']
            )
            fig_principal.update_traces(
                hovertemplate='<b>%{label}</b><br>Commission: $%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
            )
            st.plotly_chart(fig_principal, use_container_width=True)
        
        with col_prin2:
            st.markdown("**Detailed Principal Breakdown**")
            st.dataframe(
                principal_df.style.format({
                    'transactions': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'avg_commission': '${:,.0f}',
                    'total_volume': '${:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            # Calculate insights
            if len(principal_df) >= 2:
                seller_comm = principal_df[principal_df['principal_type'] == 'Seller Pays (Vendedor)']['total_commission'].sum()
                buyer_comm = principal_df[principal_df['principal_type'] == 'Buyer Pays (Comprador)']['total_commission'].sum()
                total = seller_comm + buyer_comm
                
                if seller_comm > buyer_comm:
                    st.success(f"💡 **Insight:** Sellers pay for {(seller_comm/total*100):.1f}% of registrations. Focus on seller acquisition!")
                else:
                    st.success(f"💡 **Insight:** Buyers pay for {(buyer_comm/total*100):.1f}% of registrations. Focus on buyer acquisition!")
    
    # Mutual Relationships
    st.markdown("---")
    st.subheader("🎯 Potential Client Opportunities")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Who should we target as new clients?
        
        **The Strategy:**
        - If a **Seller is YOUR client**, their **Buyers** are potential clients
        - If a **Buyer is YOUR client**, their **Sellers** are potential clients
        - These entities already do agricultural business - they just need to register with YOU!
        
        **What we're measuring:**
        - Entities who transact with YOUR clients but aren't clients themselves
        - Transaction volume they're already doing (market size)
        - Number of YOUR clients they work with (warm leads)
        
        **Why it matters:**
        - **Warm leads** = They already know your clients, easier to convert
        - **Proven market** = They're already doing transactions that could be registered
        - **Network effect** = Converting them adds more connection value
        
        **How to use it:**
        - Prioritize prospects working with multiple clients (strongest leads)
        - Ask your clients for introductions
        - Show them tax benefits they're missing
        - Calculate commission opportunity = their volume × your rate
        """)
    
    # Get list of current clients (entities marked as PRINCIPAL)
    clients_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CC PPAL" IS NOT NULL AND CLIENTE IS NOT NULL'
    clients_query = f"""
        SELECT DISTINCT "CC PPAL" as client_nit, CLIENTE as client_name
        FROM operaciones_bmc
        {clients_where}
    """
    
    clients_df = safe_query(clients_query, "current clients list")
    
    if not clients_df.empty:
        client_nits = set(clients_df['client_nit'].unique())
        
        # Find potential clients - buyers who work with our seller clients
        # First, get seller clients
        seller_clients_where = filter_query + (" AND " if filter_query else "WHERE ") + "PRINCIPAL = 'V'"
        
        potential_buyers_query = f"""
            WITH our_seller_clients AS (
                SELECT DISTINCT "NIT VENDEDOR" as client_nit
                FROM operaciones_bmc
                {seller_clients_where}
            ),
            buyer_opportunities AS (
                SELECT 
                    o."NIT COMPRADOR" as prospect_nit,
                    o."NOMBRE COMPRADOR" as prospect_name,
                    COUNT(DISTINCT o."NIT VENDEDOR") as num_connections_to_clients,
                    SUM(o."VALOR NEGOCIO") as total_volume,
                    COUNT(*) as total_transactions,
                    AVG(o.COMISION / NULLIF(o."VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
                FROM operaciones_bmc o
                INNER JOIN our_seller_clients osc ON o."NIT VENDEDOR" = osc.client_nit
                WHERE o."NIT COMPRADOR" IS NOT NULL AND o."NOMBRE COMPRADOR" IS NOT NULL
                GROUP BY o."NIT COMPRADOR", o."NOMBRE COMPRADOR"
            )
            SELECT 
                prospect_nit,
                prospect_name,
                num_connections_to_clients,
                total_volume,
                total_transactions,
                avg_commission_rate,
                ROUND(total_volume * (avg_commission_rate / 100), 0) as commission_opportunity
            FROM buyer_opportunities
            ORDER BY num_connections_to_clients DESC, total_volume DESC
            LIMIT 20
        """
        
        potential_buyers_df = safe_query(potential_buyers_query, "potential buyer clients")
        
        # Filter out existing clients
        if not potential_buyers_df.empty:
            potential_buyers_df = potential_buyers_df[~potential_buyers_df['prospect_nit'].isin(client_nits)]
        
        # Find potential clients - sellers who work with our buyer clients
        # First, get buyer clients
        buyer_clients_where = filter_query + (" AND " if filter_query else "WHERE ") + "PRINCIPAL = 'C'"
        
        potential_sellers_query = f"""
            WITH our_buyer_clients AS (
                SELECT DISTINCT "NIT COMPRADOR" as client_nit
                FROM operaciones_bmc
                {buyer_clients_where}
            ),
            seller_opportunities AS (
                SELECT 
                    o."NIT VENDEDOR" as prospect_nit,
                    o."NOMBRE VENDEDOR" as prospect_name,
                    COUNT(DISTINCT o."NIT COMPRADOR") as num_connections_to_clients,
                    SUM(o."VALOR NEGOCIO") as total_volume,
                    COUNT(*) as total_transactions,
                    AVG(o.COMISION / NULLIF(o."VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
                FROM operaciones_bmc o
                INNER JOIN our_buyer_clients obc ON o."NIT COMPRADOR" = obc.client_nit
                WHERE o."NIT VENDEDOR" IS NOT NULL AND o."NOMBRE VENDEDOR" IS NOT NULL
                GROUP BY o."NIT VENDEDOR", o."NOMBRE VENDEDOR"
            )
            SELECT 
                prospect_nit,
                prospect_name,
                num_connections_to_clients,
                total_volume,
                total_transactions,
                avg_commission_rate,
                ROUND(total_volume * (avg_commission_rate / 100), 0) as commission_opportunity
            FROM seller_opportunities
            ORDER BY num_connections_to_clients DESC, total_volume DESC
            LIMIT 20
        """
        
        potential_sellers_df = safe_query(potential_sellers_query, "potential seller clients")
        
        # Filter out existing clients
        if not potential_sellers_df.empty:
            potential_sellers_df = potential_sellers_df[~potential_sellers_df['prospect_nit'].isin(client_nits)]
        
        # Display results
        col_opp1, col_opp2 = st.columns(2)
        
        with col_opp1:
            st.markdown("### 🔵 Potential Buyer Clients")
            st.markdown("*Buyers who purchase from YOUR seller clients*")
            
            if not potential_buyers_df.empty:
                st.success(f"🎯 Found {len(potential_buyers_df)} potential buyer clients!")
                
                # Summary metrics
                total_opp = potential_buyers_df['commission_opportunity'].sum()
                st.metric("💰 Total Commission Opportunity", f"${total_opp:,.0f}", 
                         help="Potential commission if all these buyers become clients")
                
                # Show top opportunities
                display_buyers = potential_buyers_df[['prospect_name', 'num_connections_to_clients', 
                                                       'total_volume', 'total_transactions', 
                                                       'commission_opportunity']].copy()
                display_buyers.columns = ['Prospect Name', 'Connections to Clients', 'Volume', 'Transactions', 'Commission Opp.']
                
                st.dataframe(
                    display_buyers.style.format({
                        'Connections to Clients': '{:.0f}',
                        'Volume': '${:,.0f}',
                        'Transactions': '{:.0f}',
                        'Commission Opp.': '${:,.0f}'
                    }),
                    use_container_width=True,
                    height=400
                )
                
                # Top prospect detail
                if len(potential_buyers_df) > 0:
                    top_prospect = potential_buyers_df.iloc[0]
                    with st.expander(f"🌟 Top Prospect: {top_prospect['prospect_name']}", expanded=False):
                        st.markdown(f"""
                        **Why this is a hot lead:**
                        - Works with **{int(top_prospect['num_connections_to_clients'])}** of YOUR clients
                        - **${top_prospect['total_volume']:,.0f}** in transaction volume
                        - **${top_prospect['commission_opportunity']:,.0f}** commission opportunity
                        - **{int(top_prospect['total_transactions'])}** total transactions
                        
                        **Action:** Contact your seller clients to get an introduction to this buyer!
                        """)
            else:
                st.info("No potential buyer clients found. This could mean:\n- All buyers already registered\n- Need more seller clients\n- Try expanding date filters")
        
        with col_opp2:
            st.markdown("### 🔴 Potential Seller Clients")
            st.markdown("*Sellers who sell to YOUR buyer clients*")
            
            if not potential_sellers_df.empty:
                st.success(f"🎯 Found {len(potential_sellers_df)} potential seller clients!")
                
                # Summary metrics
                total_opp = potential_sellers_df['commission_opportunity'].sum()
                st.metric("💰 Total Commission Opportunity", f"${total_opp:,.0f}",
                         help="Potential commission if all these sellers become clients")
                
                # Show top opportunities
                display_sellers = potential_sellers_df[['prospect_name', 'num_connections_to_clients', 
                                                        'total_volume', 'total_transactions', 
                                                        'commission_opportunity']].copy()
                display_sellers.columns = ['Prospect Name', 'Connections to Clients', 'Volume', 'Transactions', 'Commission Opp.']
                
                st.dataframe(
                    display_sellers.style.format({
                        'Connections to Clients': '{:.0f}',
                        'Volume': '${:,.0f}',
                        'Transactions': '{:.0f}',
                        'Commission Opp.': '${:,.0f}'
                    }),
                    use_container_width=True,
                    height=400
                )
                
                # Top prospect detail
                if len(potential_sellers_df) > 0:
                    top_prospect = potential_sellers_df.iloc[0]
                    with st.expander(f"🌟 Top Prospect: {top_prospect['prospect_name']}", expanded=False):
                        st.markdown(f"""
                        **Why this is a hot lead:**
                        - Works with **{int(top_prospect['num_connections_to_clients'])}** of YOUR clients
                        - **${top_prospect['total_volume']:,.0f}** in transaction volume
                        - **${top_prospect['commission_opportunity']:,.0f}** commission opportunity
                        - **{int(top_prospect['total_transactions'])}** total transactions
                        
                        **Action:** Contact your buyer clients to get an introduction to this seller!
                        """)
            else:
                st.info("No potential seller clients found. This could mean:\n- All sellers already registered\n- Need more buyer clients\n- Try expanding date filters")
        
        # Combined priority list
        st.markdown("---")
        st.markdown("### 🏆 Top 10 Priority Prospects (Combined)")
        
        # Combine both lists
        all_prospects = []
        
        if not potential_buyers_df.empty:
            buyers_list = potential_buyers_df.copy()
            buyers_list['type'] = '🔵 Buyer'
            all_prospects.append(buyers_list)
        
        if not potential_sellers_df.empty:
            sellers_list = potential_sellers_df.copy()
            sellers_list['type'] = '🔴 Seller'
            all_prospects.append(sellers_list)
        
        if all_prospects:
            combined_df = pd.concat(all_prospects, ignore_index=True)
            combined_df = combined_df.sort_values('num_connections_to_clients', ascending=False).head(10)
            
            priority_display = combined_df[['prospect_name', 'type', 'num_connections_to_clients', 
                                           'commission_opportunity', 'total_volume']].copy()
            priority_display.columns = ['Prospect', 'Type', 'Client Connections', 'Commission Opp.', 'Volume']
            
            st.dataframe(
                priority_display.style.format({
                    'Client Connections': '{:.0f}',
                    'Commission Opp.': '${:,.0f}',
                    'Volume': '${:,.0f}'
                }),
                use_container_width=True
            )
            
            st.info(f"""
            💡 **Sales Strategy:**
            - Start with prospects connected to **multiple clients** (stronger referrals)
            - Approach them through your **existing clients** (warm introduction)
            - Highlight the **tax benefits** they're currently missing
            - Show them the **commission opportunity** represents their potential savings
            """)
    else:
        st.warning('⚠️ Unable to determine current clients. Check if "CC PPAL" field is populated.')
    
    # Mutual Relationships
    st.markdown("---")
    st.subheader("🤝 Mutual Business Relationships")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Which buyer-seller pairs do the most business together?
        
        **What we're measuring:**
        - Top buyer-seller pairs by transaction frequency
        - Commission earned from each relationship
        - Whether it's a one-way or mutual registration pattern
        
        **Why it matters:**
        - **Strong relationships** = Predictable commission stream
        - **Exclusive relationships** = Risk if one party switches
        - **New relationships** = Growth opportunities
        
        **How to use it:**
        - Nurture strong pairs with relationship manager support
        - Cross-sell to established relationships (they trust each other)
        - Monitor if exclusive pairs should diversify
        """)
    
    relationships_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL'
    relationships_query = f"""
        SELECT 
            "NOMBRE VENDEDOR" as seller,
            "NOMBRE COMPRADOR" as buyer,
            COUNT(*) as transactions,
            SUM(COMISION) as total_commission,
            SUM("VALOR NEGOCIO") as total_volume,
            COUNT(CASE WHEN PRINCIPAL = 'V' THEN 1 END) as seller_paid,
            COUNT(CASE WHEN PRINCIPAL = 'C' THEN 1 END) as buyer_paid
        FROM operaciones_bmc
        {relationships_where}
        GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
        HAVING COUNT(*) >= 3
        ORDER BY total_commission DESC
        LIMIT 20
    """
    
    with st.expander("🔍 View SQL Query", expanded=False):
        st.code(relationships_query, language="sql")
    
    relationships_df = safe_query(relationships_query, "mutual relationships")
    
    if not relationships_df.empty:
        st.markdown("**Top 20 Buyer-Seller Relationships**")
        
        # Add relationship strength indicator
        relationships_df['relationship_type'] = relationships_df.apply(
            lambda row: '🔄 Mutual' if (row['seller_paid'] > 0 and row['buyer_paid'] > 0) 
            else ('🔴 Seller Pays' if row['seller_paid'] > 0 else '🔵 Buyer Pays'),
            axis=1
        )
        
        display_cols = ['seller', 'buyer', 'transactions', 'total_commission', 'relationship_type', 'seller_paid', 'buyer_paid']
        st.dataframe(
            relationships_df[display_cols].style.format({
                'transactions': '{:,.0f}',
                'total_commission': '${:,.0f}',
                'seller_paid': '{:,.0f}',
                'buyer_paid': '{:,.0f}'
            }),
            use_container_width=True,
            height=600
        )
        
        # Summary insights
        mutual_count = len(relationships_df[relationships_df['relationship_type'] == '🔄 Mutual'])
        total_relationships = len(relationships_df)
        
        st.info(f"""
        📊 **Relationship Insights:**
        - Total Top Relationships: {total_relationships}
        - Mutual Relationships (both parties pay): {mutual_count}
        - One-Way Relationships: {total_relationships - mutual_count}
        - Total Commission from Top 20 Pairs: ${relationships_df['total_commission'].sum():,.0f}
        """)
    else:
        st.info("Not enough data for relationship analysis (need at least 3 transactions per pair)")
    
    # Interactive Network Visualization
    st.markdown("---")
    st.subheader("🗺️ Interactive Network Visualization Map")
    
    with st.expander("ℹ️ How to interact with the network map", expanded=False):
        st.markdown("""
        **Interactive Features:**
        
        **Mouse Controls:**
        - 🖱️ **Hover** over nodes/lines to see details
        - 🔍 **Zoom** with scroll wheel or pinch
        - ✋ **Pan** by clicking and dragging on empty space
        - 🎯 **Click** nodes to highlight connections
        
        **Nodes (circles):**
        - 🔴 **Red nodes** = Sellers (vendors)
        - 🔵 **Blue nodes** = Buyers (compradores)
        - **Size** = Commission generated (bigger = more commission)
        
        **Lines (edges):**
        - Connect buyers to sellers who do business together
        - **Thickness** = Number of transactions (thicker = more frequent)
        - **Color intensity** = Commission value (darker = more $$)
        
        **What to look for:**
        - **Hub nodes** (many connections) = Critical players in your network
        - **Isolated pairs** = Exclusive relationships (risk if one leaves)
        - **Clusters** = Business ecosystems or regional groups
        - **Bridge nodes** = Entities connecting different clusters
        """)
    
    # Control panel
    st.markdown("### 🎛️ Visualization Controls")
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns(4)
    
    with col_ctrl1:
        top_n_relationships = st.slider(
            "Relationships to display",
            min_value=10,
            max_value=100,
            value=30,
            step=10,
            help="More relationships = more detailed but cluttered map"
        )
    
    with col_ctrl2:
        layout_type = st.selectbox(
            "Layout Algorithm",
            options=["spring", "circular", "fruchterman_reingold", "shell"],
            index=0,
            help="Spring=Balanced clusters, Circular=Equal spacing, Fruchterman-Reingold=Force-directed premium, Shell=Buyer/Seller rings"
        )
    
    with col_ctrl3:
        node_size_metric = st.selectbox(
            "Node Size Based On",
            options=["Commission", "Connections"],
            index=0,
            help="What should determine node size?"
        )
    
    with col_ctrl4:
        show_labels = st.checkbox(
            "Show Node Labels",
            value=False,
            help="Display names on nodes (can be cluttered with many nodes)"
        )
    
    # Get network data
    network_data_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL'
    network_data_query = f"""
        SELECT 
            "NOMBRE VENDEDOR" as seller,
            "NOMBRE COMPRADOR" as buyer,
            COUNT(*) as transactions,
            SUM(COMISION) as total_commission
        FROM operaciones_bmc
        {network_data_where}
        GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
        HAVING COUNT(*) >= 1
        ORDER BY total_commission DESC
        LIMIT {top_n_relationships}
    """
    
    network_data_df = safe_query(network_data_query, "network data")
    
    if not NETWORKX_AVAILABLE:
        st.warning("""
        ⚠️ **NetworkX not installed.** To see the interactive network map, install it:
        ```bash
        pip install networkx --break-system-packages
        ```
        After installation, restart the dashboard.
        """)
    elif not network_data_df.empty and len(network_data_df) > 0:
        # Create network graph
        G = nx.Graph()
        
        # Add edges (relationships)
        for _, row in network_data_df.iterrows():
            G.add_edge(
                f"S:{row['seller']}", 
                f"B:{row['buyer']}", 
                weight=row['transactions'],
                commission=row['total_commission']
            )
        
        # Calculate node positions based on selected layout
        try:
            if layout_type == "spring":
                pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
            elif layout_type == "circular":
                pos = nx.circular_layout(G)
            elif layout_type == "fruchterman_reingold":
                # Fruchterman-Reingold is a premium force-directed layout
                # More evenly distributed than spring
                pos = nx.spring_layout(G, k=3, iterations=100, seed=42)  # Using enhanced spring parameters
            elif layout_type == "shell":
                # Separate sellers and buyers into shells
                sellers = [n for n in G.nodes() if n.startswith("S:")]
                buyers = [n for n in G.nodes() if n.startswith("B:")]
                if len(sellers) > 0 and len(buyers) > 0:
                    pos = nx.shell_layout(G, nlist=[sellers, buyers])
                else:
                    st.warning("⚠️ Shell layout requires both sellers and buyers. Using Spring layout instead.")
                    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        except Exception as e:
            st.warning(f"⚠️ Error with {layout_type} layout: {str(e)}. Using Spring layout instead.")
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Prepare node data
        node_x = []
        node_y = []
        node_text = []
        node_hover_text = []
        node_color = []
        node_size = []
        
        # Calculate metrics per node
        node_commission = {}
        node_connections = {}
        
        for _, row in network_data_df.iterrows():
            seller_key = f"S:{row['seller']}"
            buyer_key = f"B:{row['buyer']}"
            
            node_commission[seller_key] = node_commission.get(seller_key, 0) + row['total_commission']
            node_commission[buyer_key] = node_commission.get(buyer_key, 0) + row['total_commission']
        
        for node in G.nodes():
            node_connections[node] = len(list(G.neighbors(node)))
        
        # Scale for node sizes
        max_commission = max(node_commission.values()) if node_commission else 1
        max_connections = max(node_connections.values()) if node_connections else 1
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Determine node type and details
            node_type = "Seller" if node.startswith("S:") else "Buyer"
            node_name = node[2:]  # Remove prefix
            commission = node_commission.get(node, 0)
            connections = node_connections.get(node, 0)
            
            # Short label for display
            short_name = node_name[:15] + "..." if len(node_name) > 15 else node_name
            node_text.append(short_name if show_labels else "")
            
            # Detailed hover text
            node_hover_text.append(
                f"<b>{node_name}</b><br>"
                f"Type: {node_type}<br>"
                f"Commission: ${commission:,.0f}<br>"
                f"Connections: {connections}<br>"
                f"Click to highlight"
            )
            
            # Color
            if node.startswith("S:"):
                node_color.append('#E74C3C')  # Red for sellers
            else:
                node_color.append('#3498DB')  # Blue for buyers
            
            # Size based on selected metric
            if node_size_metric == "Commission":
                size_value = commission / max_commission if max_commission > 0 else 0.5
            else:  # Connections
                size_value = connections / max_connections if max_connections > 0 else 0.5
            
            node_size.append(max(15, min(70, size_value * 70)))
        
        # Prepare edge data with varying thickness and opacity
        edge_traces = []
        max_weight = max([d['weight'] for u, v, d in G.edges(data=True)]) if G.edges() else 1
        max_edge_commission = max([d['commission'] for u, v, d in G.edges(data=True)]) if G.edges() else 1
        
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            weight = edge[2]['weight']
            edge_commission = edge[2]['commission']
            
            # Line properties based on metrics
            line_width = max(0.5, min(6, (weight / max_weight) * 6))
            opacity = max(0.2, min(0.8, (edge_commission / max_edge_commission)))
            
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(
                    width=line_width,
                    color=f'rgba(149, 165, 166, {opacity})'
                ),
                hoverinfo='text',
                text=f"<b>Relationship</b><br>"
                     f"Transactions: {weight}<br>"
                     f"Commission: ${edge_commission:,.0f}",
                showlegend=False
            )
            edge_traces.append(edge_trace)
        
        # Create node trace
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text' if show_labels else 'markers',
            hoverinfo='text',
            text=node_text,
            hovertext=node_hover_text,
            marker=dict(
                color=node_color,
                size=node_size,
                line=dict(width=2, color='white'),
                opacity=0.9
            ),
            textposition="top center",
            textfont=dict(size=8, color='black'),
            showlegend=False
        )
        
        # Create figure
        fig_network = go.Figure(data=edge_traces + [node_trace])
        
        fig_network.update_layout(
            title=dict(
                text=f"🔗 Interactive Buyer-Seller Network (Top {top_n_relationships} Relationships)",
                font=dict(size=18, color='#2c3e50'),
                x=0.5,
                xanchor='center'
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=60),
            xaxis=dict(
                showgrid=False, 
                zeroline=False, 
                showticklabels=False,
                fixedrange=False  # Allow zooming
            ),
            yaxis=dict(
                showgrid=False, 
                zeroline=False, 
                showticklabels=False,
                fixedrange=False  # Allow zooming
            ),
            plot_bgcolor='#F8F9FA',
            paper_bgcolor='white',
            height=750,
            dragmode='pan',  # Enable panning
        )
        
        # Add zoom buttons
        fig_network.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[{"xaxis.range": None, "yaxis.range": None}],
                            label="Reset Zoom",
                            method="relayout"
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=False,
                    x=0.0,
                    xanchor="left",
                    y=1.1,
                    yanchor="top"
                ),
            ]
        )
        
        st.plotly_chart(fig_network, use_container_width=True)
        
        # Network insights below the map
        st.markdown("### 📊 Network Analysis")
        col_ni1, col_ni2, col_ni3, col_ni4 = st.columns(4)
        
        with col_ni1:
            total_nodes = len(G.nodes())
            sellers = len([n for n in G.nodes() if n.startswith("S:")])
            buyers = len([n for n in G.nodes() if n.startswith("B:")])
            st.info(f"""
            **Network Size**
            
            Total Entities: **{total_nodes}**
            
            🔴 Sellers: **{sellers}**
            
            🔵 Buyers: **{buyers}**
            """)
        
        with col_ni2:
            # Find most connected nodes
            degrees = dict(G.degree())
            most_connected = max(degrees, key=degrees.get)
            most_connected_name = most_connected[2:][:30]
            most_connected_type = "Seller" if most_connected.startswith("S:") else "Buyer"
            
            st.success(f"""
            **Biggest Hub** 🌟
            
            Name: **{most_connected_name}**
            
            Type: **{most_connected_type}**
            
            Connections: **{degrees[most_connected]}**
            """)
        
        with col_ni3:
            # Calculate network density
            density = nx.density(G)
            total_commission = network_data_df['total_commission'].sum()
            
            st.warning(f"""
            **Network Health** 💪
            
            Density: **{density:.1%}**
            
            Total Commission: **${total_commission:,.0f}**
            
            Avg Trans/Pair: **{network_data_df['transactions'].mean():.1f}**
            """)
        
        with col_ni4:
            # Find potential bridge nodes (high betweenness centrality)
            if len(G.nodes()) > 2:
                betweenness = nx.betweenness_centrality(G)
                bridge_node = max(betweenness, key=betweenness.get)
                bridge_name = bridge_node[2:][:30]
                bridge_type = "Seller" if bridge_node.startswith("S:") else "Buyer"
                
                st.error(f"""
                **Key Bridge** 🌉
                
                Name: **{bridge_name}**
                
                Type: **{bridge_type}**
                
                Centrality: **{betweenness[bridge_node]:.3f}**
                """)
            else:
                st.error("**Key Bridge** 🌉\n\nNeed more nodes for analysis")
        
        # Top Hubs Table
        st.markdown("### 🎯 Top Network Hubs")
        hub_data = []
        for node in G.nodes():
            node_type = "Seller" if node.startswith("S:") else "Buyer"
            node_name = node[2:]
            commission = node_commission.get(node, 0)
            connections = node_connections.get(node, 0)
            
            hub_data.append({
                'Name': node_name,
                'Type': node_type,
                'Connections': connections,
                'Commission': commission
            })
        
        hub_df = pd.DataFrame(hub_data).sort_values('Connections', ascending=False).head(10)
        
        st.dataframe(
            hub_df.style.format({
                'Connections': '{:.0f}',
                'Commission': '${:,.0f}'
            }),
            use_container_width=True
        )
        
    else:
        st.info("Not enough relationship data to create network visualization. Need at least 10 buyer-seller relationships.")
    
    # Simple network metrics
    network_metrics_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL'
    network_metrics_query = f"""
        SELECT 
            COUNT(DISTINCT "NOMBRE VENDEDOR") as unique_sellers,
            COUNT(DISTINCT "NOMBRE COMPRADOR") as unique_buyers,
            COUNT(DISTINCT "NOMBRE VENDEDOR" || '-' || "NOMBRE COMPRADOR") as unique_relationships,
            AVG(transaction_count) as avg_transactions_per_relationship
        FROM (
            SELECT 
                "NOMBRE VENDEDOR",
                "NOMBRE COMPRADOR",
                COUNT(*) as transaction_count
            FROM operaciones_bmc
            {network_metrics_where}
            GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
        ) relationships
    """
    
    network_metrics_df = safe_query(network_metrics_query, "network metrics")
    
    if not network_metrics_df.empty:
        col_nm1, col_nm2, col_nm3, col_nm4 = st.columns(4)
        
        with col_nm1:
            st.metric("Unique Sellers", f"{int(network_metrics_df['unique_sellers'][0]):,}")
        with col_nm2:
            st.metric("Unique Buyers", f"{int(network_metrics_df['unique_buyers'][0]):,}")
        with col_nm3:
            st.metric("Unique Relationships", f"{int(network_metrics_df['unique_relationships'][0]):,}")
        with col_nm4:
            st.metric("Avg Trans/Relationship", f"{network_metrics_df['avg_transactions_per_relationship'][0]:.1f}")

# --- TAB 4: CLIENT INSIGHTS ---
with tabs[3]:
    st.header("👥 Client Value Insights - How This Data Helps YOUR Clients")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h3>💡 Why Clients Pay You Commissions</h3>
    <p><b>Clients don't just pay for registration - they pay for INSIGHTS and VALUE!</b></p>
    <p>This tab shows how the data YOU collect helps YOUR clients make better business decisions, 
    justifying the commissions they pay you. Use these insights in client meetings to demonstrate your value.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Client selector
    st.markdown("### 🎯 Select a Client to Analyze")
    
    # Get list of clients
    client_list_where = filter_query + (" AND " if filter_query else "WHERE ") + 'CLIENTE IS NOT NULL AND "CC PPAL" IS NOT NULL'
    client_list_query = f"""
        SELECT DISTINCT CLIENTE as client_name, "CC PPAL" as client_nit
        FROM operaciones_bmc
        {client_list_where}
        ORDER BY CLIENTE
    """
    
    with st.expander("🔍 View Client List SQL Query", expanded=False):
        st.code(client_list_query, language="sql")
        st.caption("This query retrieves all unique clients who can be analyzed")
    
    client_list_df = safe_query(client_list_query, "client list")
    
    if not client_list_df.empty:
        selected_client = st.selectbox(
            "Choose a client to see their insights:",
            options=client_list_df['client_name'].tolist(),
            help="Select a client to see how the data benefits them"
        )
        
        # Get client NIT
        client_nit = client_list_df[client_list_df['client_name'] == selected_client]['client_nit'].values[0]
        
        # Client Overview
        st.markdown(f"## 📊 Insights for: {selected_client}")
        
        # Get client stats
        client_stats_query = f"""
            SELECT 
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume,
                SUM(COMISION) as total_commission_paid,
                MIN("FECHA REGISTRO") as first_transaction,
                MAX("FECHA REGISTRO") as last_transaction,
                COUNT(DISTINCT CASE WHEN PRINCIPAL = 'V' THEN "NIT COMPRADOR" END) as unique_buyers,
                COUNT(DISTINCT CASE WHEN PRINCIPAL = 'C' THEN "NIT VENDEDOR" END) as unique_sellers,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc
            WHERE "CC PPAL" = '{client_nit}'
        """
        
        with st.expander("🔍 View Client Stats SQL Query", expanded=False):
            st.code(client_stats_query, language="sql")
            st.caption("This query retrieves comprehensive statistics for the selected client")
        
        client_stats_df = safe_query(client_stats_query, "client stats")
        
        if not client_stats_df.empty:
            stats = client_stats_df.iloc[0]
            
            col_cs1, col_cs2, col_cs3, col_cs4 = st.columns(4)
            
            with col_cs1:
                st.metric("Total Transactions", f"{int(stats['total_transactions']):,}")
            with col_cs2:
                st.metric("Business Volume", f"${stats['total_volume']:,.0f}")
            with col_cs3:
                st.metric("Commission Paid", f"${stats['total_commission_paid']:,.0f}")
            with col_cs4:
                st.metric("Avg Rate", f"{stats['avg_commission_rate']:.2f}%")
            
            # Value Propositions
            st.markdown("---")
            st.markdown("### 💎 Value YOU Provide to This Client")
            
            tab_val1, tab_val2, tab_val3, tab_val4 = st.tabs([
                "🎯 Market Intelligence",
                "📈 Performance Tracking", 
                "🤝 Partner Analysis",
                "💰 Cost Optimization"
            ])
            
            # TAB 1: Market Intelligence
            with tab_val1:
                st.subheader("🎯 Market Intelligence Insights")
                st.markdown("""
                **What you provide:** Real-time market data and benchmarking
                
                **Client benefits:**
                - See industry pricing trends
                - Compare their rates to market averages
                - Identify competitive advantages
                """)
                
                # Market comparison
                market_comparison_query = f"""
                    SELECT 
                        "NOMBRE PRODUCTO",
                        COUNT(*) as client_transactions,
                        AVG(CASE WHEN "CC PPAL" = '{client_nit}' THEN COMISION / NULLIF("VALOR NEGOCIO", 0) END) * 100 as client_rate,
                        AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as market_avg_rate,
                        SUM(CASE WHEN "CC PPAL" = '{client_nit}' THEN "VALOR NEGOCIO" ELSE 0 END) as client_volume
                    FROM operaciones_bmc
                    {filter_query}
                    GROUP BY "NOMBRE PRODUCTO"
                    HAVING SUM(CASE WHEN "CC PPAL" = '{client_nit}' THEN 1 ELSE 0 END) > 0
                    ORDER BY client_volume DESC
                    LIMIT 10
                """
                
                with st.expander("🔍 View Market Comparison SQL Query", expanded=False):
                    st.code(market_comparison_query, language="sql")
                    st.caption("Compares client's commission rates vs market averages by product")
                
                market_comp_df = safe_query(market_comparison_query, "market comparison")
                
                if not market_comp_df.empty:
                    st.markdown("**📊 Your Product Performance vs Market**")
                    
                    # Add comparison indicator
                    market_comp_df['vs_market'] = market_comp_df.apply(
                        lambda row: '🟢 Below Market' if row['client_rate'] < row['market_avg_rate'] 
                        else '🔴 Above Market' if row['client_rate'] > row['market_avg_rate']
                        else '🟡 At Market', axis=1
                    )
                    
                    st.dataframe(
                        market_comp_df[['NOMBRE PRODUCTO', 'client_transactions', 'client_rate', 'market_avg_rate', 'vs_market']].style.format({
                            'client_transactions': '{:.0f}',
                            'client_rate': '{:.2f}%',
                            'market_avg_rate': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    st.success("""
                    💡 **Value Delivered:** 
                    - Client can see if they're paying competitive rates
                    - Identify products where they can negotiate better prices
                    - Spot market trends before competitors
                    """)
            
            # TAB 2: Performance Tracking
            with tab_val2:
                st.subheader("📈 Performance Tracking")
                st.markdown("""
                **What you provide:** Historical data and trend analysis
                
                **Client benefits:**
                - Track business growth over time
                - Identify seasonal patterns
                - Make data-driven decisions
                """)
                
                # Monthly trend for client
                client_trend_query = f"""
                    SELECT 
                        MES,
                        COUNT(*) as transactions,
                        SUM("VALOR NEGOCIO") as volume,
                        SUM(COMISION) as commission_paid
                    FROM operaciones_bmc
                    WHERE "CC PPAL" = '{client_nit}'
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
                
                with st.expander("🔍 View Client Trend SQL Query", expanded=False):
                    st.code(client_trend_query, language="sql")
                    st.caption("Shows client's monthly business activity over time")
                
                client_trend_df = safe_query(client_trend_query, "client trend")
                
                if not client_trend_df.empty:
                    fig_client_trend = go.Figure()
                    
                    fig_client_trend.add_trace(go.Scatter(
                        x=client_trend_df['MES'],
                        y=client_trend_df['volume'],
                        mode='lines+markers',
                        name='Business Volume',
                        line=dict(color='#3498DB', width=3),
                        yaxis='y'
                    ))
                    
                    fig_client_trend.add_trace(go.Bar(
                        x=client_trend_df['MES'],
                        y=client_trend_df['transactions'],
                        name='Transactions',
                        marker_color='#95A5A6',
                        yaxis='y2'
                    ))
                    
                    fig_client_trend.update_layout(
                        title="Your Business Activity Over Time",
                        xaxis_title="Month",
                        yaxis=dict(title="Business Volume ($)", side='left'),
                        yaxis2=dict(title="Number of Transactions", overlaying='y', side='right'),
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig_client_trend, use_container_width=True)
                    
                    st.success("""
                    💡 **Value Delivered:**
                    - Clear visibility into business growth/decline
                    - Identify peak seasons for better planning
                    - Historical data for financial forecasting
                    """)
            
            # TAB 3: Partner Analysis
            with tab_val3:
                st.subheader("🤝 Trading Partner Analysis")
                st.markdown("""
                **What you provide:** Detailed partner relationship insights
                
                **Client benefits:**
                - Identify most important trading partners
                - Spot relationship risks
                - Discover new partnership opportunities
                """)
                
                # Top partners
                if stats['unique_buyers'] > 0:
                    st.markdown("**🔵 Your Top Buyers**")
                    top_buyers_query = f"""
                        SELECT 
                            "NOMBRE COMPRADOR" as partner,
                            COUNT(*) as transactions,
                            SUM("VALOR NEGOCIO") as total_volume,
                            MAX("FECHA REGISTRO") as last_transaction
                        FROM operaciones_bmc
                        WHERE "CC PPAL" = '{client_nit}' AND PRINCIPAL = 'V'
                        GROUP BY "NOMBRE COMPRADOR"
                        ORDER BY total_volume DESC
                        LIMIT 10
                    """
                    
                    with st.expander("🔍 View Top Buyers SQL Query", expanded=False):
                        st.code(top_buyers_query, language="sql")
                        st.caption("Shows client's top buyers when they act as seller")
                    
                    top_buyers_df = safe_query(top_buyers_query, "top buyers")
                    
                    if not top_buyers_df.empty:
                        st.dataframe(
                            top_buyers_df.style.format({
                                'transactions': '{:.0f}',
                                'total_volume': '${:,.0f}'
                            }),
                            use_container_width=True
                        )
                
                if stats['unique_sellers'] > 0:
                    st.markdown("**🔴 Your Top Suppliers**")
                    top_sellers_query = f"""
                        SELECT 
                            "NOMBRE VENDEDOR" as partner,
                            COUNT(*) as transactions,
                            SUM("VALOR NEGOCIO") as total_volume,
                            MAX("FECHA REGISTRO") as last_transaction
                        FROM operaciones_bmc
                        WHERE "CC PPAL" = '{client_nit}' AND PRINCIPAL = 'C'
                        GROUP BY "NOMBRE VENDEDOR"
                        ORDER BY total_volume DESC
                        LIMIT 10
                    """
                    
                    with st.expander("🔍 View Top Sellers SQL Query", expanded=False):
                        st.code(top_sellers_query, language="sql")
                        st.caption("Shows client's top suppliers when they act as buyer")
                    
                    top_sellers_df = safe_query(top_sellers_query, "top sellers")
                    
                    if not top_sellers_df.empty:
                        st.dataframe(
                            top_sellers_df.style.format({
                                'transactions': '{:.0f}',
                                'total_volume': '${:,.0f}'
                            }),
                            use_container_width=True
                        )
                
                st.success("""
                💡 **Value Delivered:**
                - Know who your most important partners are
                - Track partner reliability and consistency
                - Identify concentration risk (too dependent on one partner)
                """)
            
            # TAB 4: Cost Optimization
            with tab_val4:
                st.subheader("💰 Cost Optimization Opportunities")
                st.markdown("""
                **What you provide:** Tax benefit maximization insights
                
                **Client benefits:**
                - Understand registration costs vs benefits
                - Identify cost-saving opportunities
                - Maximize tax deductions
                """)
                
                # Cost breakdown
                cost_breakdown_query = f"""
                    SELECT 
                        YEAR,
                        SUM(COMISION) as commission_paid,
                        SUM("VALOR NEGOCIO") as volume,
                        COUNT(*) as transactions,
                        AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as effective_rate
                    FROM operaciones_bmc
                    WHERE "CC PPAL" = '{client_nit}'
                    GROUP BY YEAR
                    ORDER BY YEAR DESC
                """
                
                with st.expander("🔍 View Cost Breakdown SQL Query", expanded=False):
                    st.code(cost_breakdown_query, language="sql")
                    st.caption("Shows annual commission costs and ROI analysis for the client")
                
                cost_breakdown_df = safe_query(cost_breakdown_query, "cost breakdown")
                
                if not cost_breakdown_df.empty:
                    st.markdown("**📊 Annual Cost Analysis**")
                    st.dataframe(
                        cost_breakdown_df.style.format({
                            'commission_paid': '${:,.0f}',
                            'volume': '${:,.0f}',
                            'transactions': '{:.0f}',
                            'effective_rate': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    total_commission = cost_breakdown_df['commission_paid'].sum()
                    total_volume = cost_breakdown_df['volume'].sum()
                    
                    # Tax benefit estimation (simplified)
                    estimated_tax_benefit = total_volume * 0.15  # Assuming 15% tax savings
                    net_benefit = estimated_tax_benefit - total_commission
                    
                    col_cb1, col_cb2, col_cb3 = st.columns(3)
                    
                    with col_cb1:
                        st.metric("Total Paid", f"${total_commission:,.0f}")
                    with col_cb2:
                        st.metric("Est. Tax Benefit", f"${estimated_tax_benefit:,.0f}")
                    with col_cb3:
                        st.metric("Net Benefit", f"${net_benefit:,.0f}", 
                                 delta=f"{((net_benefit/total_commission)*100):.0f}% ROI")
                    
                    st.success("""
                    💡 **Value Delivered:**
                    - Clear ROI on registration costs
                    - Track commission payments vs tax savings
                    - Justify registration expenses to finance team
                    - Historical data for tax filing
                    """)
            
            # Summary Value Proposition
            st.markdown("---")
            st.markdown("### 🎁 Complete Value Package")
            
            st.markdown("""
            <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745;'>
            <h4>Why Clients Should Keep Paying Commissions:</h4>
            
            <p><b>1. Market Intelligence</b> 💹<br>
            → Real-time pricing data worth thousands in consulting fees<br>
            → Competitive benchmarking unavailable elsewhere</p>
            
            <p><b>2. Business Analytics</b> 📊<br>
            → Historical tracking and trend analysis<br>
            → Performance dashboards for better decisions<br>
            → Data-driven insights for growth</p>
            
            <p><b>3. Relationship Management</b> 🤝<br>
            → Partner performance tracking<br>
            → Risk identification (concentration, churn)<br>
            → Network effect from ecosystem insights</p>
            
            <p><b>4. Cost Savings</b> 💰<br>
            → Tax benefits far exceed commission costs<br>
            → ROI tracking and documentation<br>
            → Compliance and audit trail</p>
            
            <p><b>5. Time Savings</b> ⏰<br>
            → You handle all BMC paperwork<br>
            → Automated reporting<br>
            → One-stop solution</p>
            
            <hr>
            
            <p><b>Bottom Line:</b> Clients pay ~{stats['avg_commission_rate']:.2f}% commission but receive:</p>
            <ul>
            <li>✅ 15%+ tax benefits</li>
            <li>✅ Market intelligence worth $$$</li>
            <li>✅ Business analytics platform</li>
            <li>✅ Complete compliance management</li>
            </ul>
            
            <p style='font-size: 18px; font-weight: bold; color: #28a745;'>
            Net Value: 10x-20x the commission cost!
            </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("""
            💡 **How to use this tab:**
            1. Select client before meetings
            2. Review their specific insights
            3. Show them the value THEY receive
            4. Use data to justify commission rates
            5. Demonstrate continuous value delivery
            """)
        
        else:
            st.warning("No data found for this client.")
    else:
        st.info("No clients found in selected date range.")

# --- TAB 5: OPERATIONAL ANALYSIS ---
with tabs[4]:
    st.header("🔍 Operational Deep-Dive")
    
    # Day of week analysis
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        st.subheader("📅 Daily Operation Patterns")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** Which days of the week are busiest?
            
            **What we're measuring:**
            - Number of operations per day of the week
            - Commission earned each day
            - Average commission per day
            
            **Why it matters:**
            - Plan staffing levels for busy days
            - Schedule maintenance during slow days
            - Understand weekly business rhythms
            
            **How to use it:**
            - Ensure adequate staff on high-volume days
            - Plan meetings and training on slower days
            - Adjust working hours based on demand patterns
            """)
        
        dow_query = f"""
            SELECT 
                DAYNAME("FECHA REGISTRO") as day_of_week,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings,
                AVG(COMISION) as avg_commission
            FROM operaciones_bmc
            {filter_query}
            GROUP BY day_of_week
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(dow_query, language="sql")
        
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
                hovertemplate='<b>%{x}</b><br>Operations: %{y}<br>Commission: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=dow_df[['commission_earnings']]
            )
            st.plotly_chart(fig_dow, use_container_width=True)
            st.caption("💡 Optimize staffing based on peak days")
        else:
            st.info("No data for day of week analysis")
    
    with col_op2:
        st.subheader("🏭 Operations by Type")
        
        with st.expander("ℹ️ What does this show?", expanded=False):
            st.markdown("""
            **Business Question:** What types of operations are we processing?
            
            **What we're measuring:**
            - Distribution of operation types:
              - **RSG**: Registro sin incentivo (Registration without incentive)
              - **REX**: Registro exportación (Export registration)
              - **RGC**: Registro con incentivo (Registration with incentive)
            - Number of operations per type
            - Commission earned per type
            
            **Why it matters:**
            - Understand your business mix
            - Identify which operation types are most profitable
            - Plan resources for different operation types
            
            **How to use it:** Focus on growing the most profitable operation types while ensuring you have capacity for all types.
            """)
        
        op_type_query = f"""
            SELECT 
                "TIPO OPERACION",
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as volume
            FROM operaciones_bmc
            {filter_query}
            GROUP BY "TIPO OPERACION"
            ORDER BY operations DESC
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(op_type_query, language="sql")
        
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
                hovertemplate='<b>%{label}</b><br>Operations: %{value}<br>Commission: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=op_type_df[['commission_earnings']]
            )
            st.plotly_chart(fig_op_type, use_container_width=True)
        else:
            st.info("No operation type data available")
    
    # Geographic analysis
    st.markdown("---")
    st.subheader("🗺️ Geographic Distribution")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Where are our buyers and sellers located?
        
        **What we're measuring:**
        - Top cities where buyers are located
        - Top cities where sellers are located
        - Number of operations per city
        - Commission earned per city
        
        **Why it matters:**
        - Identify strong and weak geographic markets
        - Plan regional expansion strategies
        - Allocate field sales resources geographically
        - Understand regional business patterns
        
        **How to use it:**
        - Increase presence in high-commission cities
        - Investigate why some regions perform better
        - Plan targeted marketing campaigns by region
        """)
    
    col_geo1, col_geo2 = st.columns(2)
    
    with col_geo1:
        st.markdown("**Top Cities - Buyers**")
        buyer_cities_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CIUDAD COMPRADOR" IS NOT NULL'
        buyer_cities_query = f"""
            SELECT 
                "CIUDAD COMPRADOR" as city,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings
            FROM operaciones_bmc
            {buyer_cities_where}
            GROUP BY city
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(buyer_cities_query, language="sql")
        
        buyer_cities_df = safe_query(buyer_cities_query, "buyer cities")
        
        if not buyer_cities_df.empty:
            st.dataframe(
                buyer_cities_df.style.format({
                    'operations': '{:,.0f}',
                    'commission_earnings': '${:,.0f}'
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
                SUM(COMISION) as commission_earnings
            FROM operaciones_bmc
            {seller_cities_where}
            GROUP BY city
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(seller_cities_query, language="sql")
        
        seller_cities_df = safe_query(seller_cities_query, "seller cities")
        
        if not seller_cities_df.empty:
            st.dataframe(
                seller_cities_df.style.format({
                    'operations': '{:,.0f}',
                    'commission_earnings': '${:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No seller city data")

# --- TAB 6: RISK & AUDIT ---
with tabs[5]:
    st.header("🛡️ Risk & Audit Dashboard")
    
    # commission concentration (Pareto)
    st.subheader("1. commission concentration Analysis (Pareto)")
    st.markdown("_Monitor dependency on key clients_")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Are we too dependent on a small number of clients?
        
        **What we're measuring:**
        - The famous "80/20 rule" - do 20% of clients generate 80% of commission?
        - Commission from each client
        - Cumulative commission percentage (red line showing running total)
        
        **Why it matters:**
        - **High concentration = High risk**: If a few clients leave, you lose significant commission
        - **Balanced distribution = Lower risk**: Commission spread across many clients is healthier
        
        **How to use it:**
        - **If the red line reaches 80% quickly**: You're highly dependent on few clients - RISK!
          - Action: Diversify client base, acquire new clients
        - **If the red line rises gradually**: Healthy distribution - GOOD!
          
        **Example:** If 3 clients generate 80% of commission, losing one client could be devastating.
        """)
    
    pareto_query = f"""
        SELECT 
            CLIENTE,
            SUM(COMISION) as commission_earnings
        FROM operaciones_bmc
        {filter_query}
        GROUP BY CLIENTE
        ORDER BY commission_earnings DESC
        LIMIT 50
    """
    
    with st.expander("🔍 View SQL Query", expanded=False):
        st.code(pareto_query, language="sql")
    
    pareto_df = safe_query(pareto_query, "pareto analysis")
    
    if not pareto_df.empty:
        pareto_df['cumulative_commission'] = pareto_df['commission_earnings'].cumsum()
        pareto_df['cumulative_pct'] = (pareto_df['cumulative_commission'] / pareto_df['commission_earnings'].sum()) * 100
        
        fig_pareto = go.Figure()
        
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['CLIENTE'],
            y=pareto_df['commission_earnings'],
            name='Commission',
            marker_color='lightblue',
            hovertemplate='<b>%{x}</b><br>Commission: $%{y:,.0f}<extra></extra>'
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
            title='commission concentration (Pareto Chart)',
            xaxis_title='Client',
            yaxis_title='Commission ($)',
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
        top_20_commission_pct = pareto_df.iloc[:top_20_pct_count]['commission_earnings'].sum() / pareto_df['commission_earnings'].sum() * 100
        
        st.info(f"📊 Top 20% of clients ({top_20_pct_count} clients) generate {top_20_commission_pct:.1f}% of commission")
        
        if top_20_commission_pct > 80:
            st.warning("⚠️ High commission concentration risk detected")
        else:
            st.success("✅ Healthy commission distribution")
    else:
        st.info("No data for Pareto analysis")
    
    # Pricing anomalies
    st.markdown("---")
    st.subheader("2. Pricing Anomaly Detection")
    st.markdown("_Transactions with significantly lower commission rates_")
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** Are there transactions where we charged unusually low commissions?
        
        **What we're measuring:**
        - Transactions where commission rate is 30% or more below the product average
        - The actual commission rate charged
        - The normal market average rate for that product
        - The discount percentage given
        
        **Why it matters:**
        - **Detect pricing errors**: Someone may have entered wrong rates
        - **Identify special deals**: Understand which clients got discounts
        - **Commission leakage**: Are we leaving money on the table?
        
        **How to use it:**
        - Review each transaction on this list
        - Verify if the low rate was intentional (approved discount) or an error
        - If error: Correct it and retrain staff
        - If intentional: Ensure it's documented and justified
        
        **Example:** If normal rate is 5% but you charged 2%, you're losing 60% of potential commission on that deal.
        """)
    
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
        WHERE (t.COMISION / NULLIF(t."VALOR NEGOCIO", 0)) * 100 < (p.avg_rate * 0.7)
        {(" AND " + filter_query.replace("WHERE ", "")) if filter_query else ""}
        ORDER BY discount_pct DESC
        LIMIT 20
    """
    
    with st.expander("🔍 View SQL Query", expanded=False):
        st.code(anomaly_query, language="sql")
    
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
    
    with st.expander("ℹ️ What does this show?", expanded=False):
        st.markdown("""
        **Business Question:** What's the typical size of our transactions?
        
        **What we're measuring:**
        - Transactions grouped by value:
          - **Small**: Less than $1 million
          - **Medium**: $1M to $10M
          - **Large**: $10M to $50M
          - **Very Large**: Over $50M
        - Count of transactions in each category
        - Total commission from each category
        - Average commission rate by size
        
        **Why it matters:**
        - Understand your business composition
        - Large deals may need special handling or approval
        - Different sizes may require different processes
        - Plan resources based on typical deal sizes
        
        **How to use it:**
        - If most transactions are small: Focus on efficiency and volume
        - If dominated by large deals: Ensure quality control and risk management
        - Set up different approval workflows for different sizes
        """)
    
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
                SUM(COMISION) as total_commission,
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
        
        with st.expander("🔍 View SQL Query", expanded=False):
            st.code(size_query, language="sql")
        
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
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Commission: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=size_df[['total_commission']]
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
                    'total_commission': '${:,.0f}',
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