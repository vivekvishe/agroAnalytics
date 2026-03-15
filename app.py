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

# Configuración de Página
st.set_page_config(
    page_title="Agro Analytics Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# AUTENTICACIÓN SEGURA DE INICIO DE SESIÓN
# ============================================

# NOTA DE SEGURIDAD: La contraseña se almacena como hash SHA-256, no en texto plano

# Para generar el hash de una nueva contraseña, ejecute en Python:
#   import hashlib
#   hashlib.sha256("SuNuevaContraseña".encode()).hexdigest()

ADMIN_USERNAME = "admin"
PASSWORD_HASH = "e0bd631724a4fb17f0fc7c19ac460ef1838cdf4c4d0a922e63c09d92b90922d8"

def hash_password(password):
    """Genera hash SHA-256 de una contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password():
    """Retorna `True` si el usuario ingresó la contraseña correcta."""
    
    def password_entered():
        """Verifica si la contraseña ingresada es correcta."""
        if (st.session_state["username"] == ADMIN_USERNAME and 
            hash_password(st.session_state["password"]) == PASSWORD_HASH):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("""
        <div style='text-align: center; padding: 50px 0;'>
            <h1>🌾 Agro Analytics BMC</h1>
            <h3>Inicio de Sesión Requerido</h3>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input("Usuario", key="username", placeholder="Ingrese su usuario")
        st.text_input("Contraseña", type="password", key="password", placeholder="Ingrese su contraseña")
        st.button("Ingresar", on_click=password_entered, type="primary", use_container_width=True)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Usuario o contraseña incorrectos")
    
    return False

if not check_password():
    st.stop()

# ============================================
# TABLERO PRINCIPAL (solo visible después del inicio de sesión)
# ============================================

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

import tempfile

# DB path resolution (in priority order):
# 1. DB_PATH environment variable
# 2. Same folder as app.py (default - works on Streamlit Cloud)
# 3. File uploader (for Windows/other users who have the db elsewhere)
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmc_data.db")
DB_PATH = os.environ.get("DB_PATH", _default_db)

# If the database is not found, show a file uploader
if not os.path.exists(DB_PATH):
    if "uploaded_db_path" not in st.session_state:
        st.markdown("""
            <div style='text-align: center; padding: 40px 0;'>
                <h2>🗄️ Base de Datos No Encontrada</h2>
                <p style='color: #666;'>El archivo <code>bmc_data.db</code> no fue encontrado automáticamente.</p>
                <p>Por favor suba el archivo de base de datos para continuar.</p>
            </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            uploaded_db = st.file_uploader(
                "📂 Seleccione el archivo bmc_data.db",
                type=["db"],
                help="Suba el archivo de base de datos DuckDB (.db)"
            )
            if uploaded_db is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
                tmp.write(uploaded_db.read())
                tmp.close()
                st.session_state["uploaded_db_path"] = tmp.name
                st.rerun()
            else:
                st.info("💡 El archivo bmc_data.db puede estar en cualquier carpeta de su computador.")
                st.stop()
    DB_PATH = st.session_state["uploaded_db_path"]

@st.cache_resource
def get_connection(db_path):
    """Crea conexión a la base de datos con manejo de errores"""
    try:
        return duckdb.connect(db_path, read_only=True)
    except Exception as e:
        st.error(f"❌ Error al conectar con la base de datos: {str(e)}")
        st.stop()

con = get_connection(DB_PATH)

def safe_query(query, description="consulta"):
    """Ejecuta consulta SQL con manejo de errores"""
    try:
        return con.execute(query).df()
    except Exception as e:
        st.error(f"❌ Error ejecutando {description}: {str(e)}")
        st.code(query, language="sql")
        return pd.DataFrame()

# Panel Lateral con Filtros
st.sidebar.header("🔍 Filtrar Análisis")

if st.sidebar.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.markdown("---")

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
    months_df = safe_query(months_query, "filtro de meses")
    
    if not months_df.empty:
        months = months_df['MES'].tolist()
        selected_months = st.sidebar.multiselect(
            "📅 Seleccionar Meses", 
            options=months, 
            default=months,
            help="Filtrar datos por meses específicos"
        )
    else:
        selected_months = []
        st.sidebar.warning("No hay datos de meses disponibles")
except Exception as e:
    st.sidebar.error(f"Error al cargar meses: {str(e)}")
    selected_months = []

try:
    years_query = "SELECT DISTINCT YEAR FROM operaciones_bmc WHERE YEAR IS NOT NULL ORDER BY YEAR DESC"
    years_df = safe_query(years_query, "filtro de años")
    
    if not years_df.empty:
        years = years_df['YEAR'].tolist()
        selected_years = st.sidebar.multiselect(
            "📆 Seleccionar Años",
            options=years,
            default=years,
            help="Filtrar datos por años específicos"
        )
    else:
        selected_years = []
except Exception as e:
    selected_years = []

try:
    op_types_query = "SELECT DISTINCT \"TIPO OPERACION\" FROM operaciones_bmc WHERE \"TIPO OPERACION\" IS NOT NULL"
    op_types_df = safe_query(op_types_query, "tipos de operación")
    
    if not op_types_df.empty:
        op_types = op_types_df['TIPO OPERACION'].tolist()
        selected_op_types = st.sidebar.multiselect(
            "📋 Tipo de Operación",
            options=op_types,
            default=op_types,
            help="RSG: Sin incentivo, REX: Exportación, RGC: Con incentivo"
        )
    else:
        selected_op_types = []
except Exception as e:
    selected_op_types = []

def build_where_clause():
    """Construye la cláusula WHERE según los filtros seleccionados"""
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

# Título Principal
st.title("🌾 Agro Analytics BMC - Tablero de Desempeño y Estrategia")
st.markdown("### Análisis Basado en Datos para Operaciones del Negocio Agrícola")

with st.expander("📋 **Guía del Tablero**", expanded=False):
    st.markdown("""
    ### 🎯 **Propósito del Tablero**
    Monitorear operaciones del negocio agrícola con análisis integrales:
    - **Métricas de Desempeño**: Comisión, volumen y eficiencia operativa
    - **Perspectivas Estratégicas**: Oportunidades de negocio impulsadas por IA y riesgos
    - **Análisis Operativo**: Patrones diarios y optimización de recursos
    - **Gestión de Riesgos**: Exposición financiera y monitoreo de cumplimiento
    
    ### 🔍 **Navegación**
    1. **📊 Tablero de Desempeño**: KPIs y tendencias de comisión
    2. **💡 Perspectivas Estratégicas**: Oportunidades de crecimiento y detección de riesgos
    3. **🔗 Red Compradores-Vendedores**: Análisis de red y clientes potenciales
    4. **👥 Perspectivas del Cliente**: Demostración de valor al cliente
    5. **🔍 Análisis Operativo**: Operaciones diarias y eficiencia
    6. **🛡️ Riesgo y Auditoría**: Riesgo de concentración y detección de anomalías
    
    ### 💡 **Consejos de Uso**
    - Use los filtros del panel lateral para enfocarse en períodos específicos
    - Pase el cursor sobre los gráficos para información detallada
    - **Haga clic en "🔍 Ver Consulta SQL" debajo de cada gráfico** para ver la consulta subyacente
    - Exporte datos usando los botones de descarga
    - Revise los tooltips para explicaciones de métricas
    
    ### 🔍 **Transparencia en Consultas SQL**
    Cada gráfico y tabla tiene una sección desplegable "🔍 Ver Consulta SQL" que muestra:
    - La consulta SQL exacta usada para generar los datos
    - Cómo se aplican los filtros
    - Qué cálculos se realizan
    - Transparencia total en nuestros análisis
    """)

st.markdown("---")
st.subheader("🚀 Resumen del Negocio - Sus Comisiones de un Vistazo")

col1, col2, col3, col4, col5 = st.columns(5)

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

with st.expander("🔍 Ver Consulta SQL del Resumen", expanded=False):
    st.code(overview_query, language="sql")

overview_data = safe_query(overview_query, "métricas de resumen")

if not overview_data.empty:
    with col1:
        st.metric(
            "💰 Sus Comisiones Ganadas", 
            f"${overview_data['total_commission'][0]:,.0f}",
            help="Total de comisiones ganadas - ¡estas son las ganancias de SU empresa!"
        )
    with col2:
        st.metric(
            "📊 Volumen de Clientes", 
            f"${overview_data['total_volume'][0]:,.0f}",
            help="Valor total de transacciones de clientes (no sus comisiones)"
        )
    with col3:
        st.metric(
            "📈 Tasa Promedio de Comisión", 
            f"{overview_data['avg_commission_rate'][0]:.2f}%",
            help="Porcentaje promedio que gana en cada transacción"
        )
    with col4:
        st.metric(
            "👥 Clientes Activos", 
            f"{int(overview_data['unique_clients'][0]):,}",
            help="Número de clientes generando comisiones para usted"
        )
    with col5:
        st.metric(
            "✅ Transacciones", 
            f"{int(overview_data['total_ops'][0]):,}",
            help="Total de operaciones procesadas"
        )

# Definir Pestañas
tabs = st.tabs([
    "📊 Tablero de Desempeño", 
    "💡 Perspectivas Estratégicas",
    "🔗 Red Compradores-Vendedores",
    "👥 Perspectivas del Cliente",
    "🔍 Análisis Operativo",
    "🛡️ Riesgo y Auditoría"
])

# --- PESTAÑA 1: TABLERO DE DESEMPEÑO ---
with tabs[0]:
    st.markdown("### 💰 Desempeño de Comisiones - Sus Ganancias")
    st.info("💡 **Recuerde:** Las comisiones son SUS ganancias - ¡esto es lo que genera su empresa!")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Tendencia Mensual de Comisiones")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Cuánta comisión está ganando SU empresa cada mes?
            
            **Qué estamos midiendo:**
            - **Total de comisión ganada cada mes** = Sus ingresos/ganancias reales
            - Volumen de negocio total procesado (transacciones de clientes - NO sus comisiones)
            - Número de transacciones por mes
            
            **Por qué importa:** ¡Esta es SU línea de fondo!
            - Identifique sus mejores y peores meses de ganancias
            - Siga tendencias de crecimiento - ¿está ganando más comisión con el tiempo?
            - Detecte patrones estacionales para planificar flujo de caja
            
            **Cómo usarlo:** 
            - Compare el mes actual con el anterior - ¿están creciendo las comisiones?
            - Investigue caídas - ¿por qué bajaron las comisiones?
            - Planifique gastos basándose en ingresos esperados de comisión
            
            **Importante:** La línea de comisión muestra las ganancias reales de SU empresa, no los valores de transacciones de clientes.
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(monthly_query, language="sql")
        
        monthly_df = safe_query(monthly_query, "tendencia mensual")
        
        if not monthly_df.empty:
            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Scatter(
                x=monthly_df['MES'],
                y=monthly_df['commission_earnings'],
                mode='lines+markers',
                name='Sus Comisiones Ganadas',
                line=dict(color='#27AE60', width=4),
                marker=dict(size=10, color='#27AE60'),
                hovertemplate='<b>%{x}</b><br>💰 Sus Ganancias: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.update_layout(
                title="Sus Comisiones Ganadas por Mes",
                xaxis_title="Mes",
                yaxis_title="Comisiones Ganadas ($) - SUS INGRESOS",
                hovermode='x unified',
                plot_bgcolor='rgba(39,174,96,0.1)'
            )
            st.plotly_chart(fig_monthly, width="stretch")
            st.caption("💰 Esto muestra las ganancias reales de SU empresa por comisiones")
        else:
            st.info("No hay datos disponibles para la tendencia mensual")
    
    with col_right:
        st.subheader("🏆 Top 10 Clientes por Comisiones Generadas")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Qué clientes están generando más comisión para USTED?
            
            **Qué estamos midiendo:**
            - **Comisión total generada por cada cliente** = Cuánto le paga cada cliente
            - Número de transacciones por cliente
            - Volumen total de transacciones
            
            **Por qué importa:**
            - ¡Estas son SUS vacas lecheras - los clientes que pagan sus cuentas!
            - Merecen tratamiento VIP para mantenerlos contentos
            - Perder uno de estos clientes afectaría significativamente sus comisiones
            
            **Cómo usarlo:** 
            - Llame a estos clientes regularmente para mantener las relaciones
            - Déles servicio prioritario y atención especial
            - Ofrézcales incentivos para hacer MÁS negocio con usted
            - Si alguno aparece en la lista de "Riesgo de Fuga" - ¡se necesita acción URGENTE!
            
            **Conclusión:** Estos clientes = Sus mayores cheques de pago. ¡Manténgalos contentos!
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(clients_query, language="sql")
        
        clients_df = safe_query(clients_query, "top clientes")
        
        if not clients_df.empty:
            fig_clients = px.bar(
                clients_df,
                x='commission_earnings',
                y='CLIENTE',
                orientation='h',
                title="Mayores Generadores de Comisión - Sus Mejores Clientes",
                labels={'commission_earnings': 'Comisiones Ganadas ($) - SUS INGRESOS', 'CLIENTE': 'Cliente'},
                color='commission_earnings',
                color_continuous_scale='Greens'
            )
            fig_clients.update_traces(
                hovertemplate='<b>%{y}</b><br>💰 Le Paga: $%{x:,.0f}<br>Transacciones: %{customdata[0]}<br>Tasa Prom: %{customdata[1]:.2f}%<extra></extra>',
                customdata=clients_df[['transactions', 'avg_commission_rate']]
            )
            st.plotly_chart(fig_clients, width="stretch")
            st.caption("💰 Estos clientes generan las mayores comisiones para SU empresa")
        else:
            st.info("No hay datos de clientes disponibles")
    
    # Desempeño de Referenciadores
    st.markdown("---")
    st.subheader("🤝 Todos los Referenciadores - Sus Impulsores de Comisión")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Qué referenciadores están trayendo más comisiones para SU empresa?
        
        **Qué estamos midiendo:**
        - **Volumen total de comisión** que cada referenciador ha generado
        - Número de operaciones que han facilitado
        - Comisión promedio por operación
        - **Ganancias estimadas para cada referenciador** (lo que USTED les paga de comisiones)
        
        **Por qué importa:**
        - ¡Estas personas son directamente responsables de SUS comisiones!
        - Los mejores merecen bonificaciones y reconocimiento
        - Están incentivados por comisión, así que están motivados a traer más negocio
        
        **Cómo usarlo:**
        - **Recompense a los mejores** - Déles bonificaciones, reconocimiento público, mejores territorios
        - **Aprenda de ellos** - ¿Qué están haciendo bien? Enseñe sus métodos a otros
        - **Motive a otros** - Muestre al equipo lo que ganan los mejores
        - **Retención** - ¡No pierda a sus mejores generadores de comisión frente a competidores!
        
        **Perspectiva clave:** Sus mejores referenciadores = Sus generadores de dinero. ¡Invierta en mantenerlos contentos y productivos!
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(referenciador_query, language="sql")
        
        referenciador_df = safe_query(referenciador_query, "todos los referenciadores")
        
        if not referenciador_df.empty:
            top_10_ref_df = referenciador_df.head(10).copy()
            top_10_ref_df['REFERENCIADOR'] = top_10_ref_df['REFERENCIADOR'].astype(str)
            
            fig_ref = go.Figure()
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
                hovertemplate='<b>Cód. Ref: %{x}</b><br>' +
                             'Comisión Total: $%{y:,.0f}<br>' +
                             'Operaciones: %{customdata[0]:,.0f}<br>' +
                             'Prom por Op: $%{customdata[1]:,.0f}<br>' +
                             'Ganancias Est.: $%{customdata[2]:,.0f}<extra></extra>',
                customdata=top_10_ref_df[['total_operations', 'avg_commission_per_op', 'referenciador_earnings']]
            ))
            
            fig_ref.update_layout(
                title={
                    'text': "Top 10 Impulsores de Comisión - Volumen Generado",
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis_title="Código Referenciador",
                yaxis_title="Total Comisiones Ganadas ($) - Generadas para USTED",
                height=500,
                margin=dict(l=80, r=40, t=80, b=80),
                plot_bgcolor='rgba(240,240,240,0.3)',
                paper_bgcolor='white',
                font=dict(size=12),
                xaxis=dict(showgrid=False, tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor='lightgray', tickformat='$,.0f')
            )
            
            st.plotly_chart(fig_ref, width="stretch")
            st.caption("💡 El gráfico muestra el top 10 para mayor claridad - lista completa en la tabla inferior")
        else:
            st.info("No hay datos de referenciadores disponibles")
    
    with col_ref2:
        if not referenciador_df.empty:
            st.markdown(f"**Métricas de Desempeño Completas - Todos los {len(referenciador_df)} Referenciadores**")
            
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
                width="stretch",
                height=500
            )
            
            total_commission = referenciador_df['total_commission'].sum()
            total_earnings = referenciador_df['referenciador_earnings'].sum()
            
            st.info(f"""
            📊 **Resumen:**
            - Total Referenciadores: {len(referenciador_df)}
            - Total Comisión Generada: ${total_commission:,.0f}
            - Total Ganancias Referenciadores: ${total_earnings:,.0f}
            """)
            
            st.caption("💰 Desplace por la lista completa - ganancias estimadas de referenciadores basadas en porcentajes de comisión")
        else:
            st.info("No hay datos de referenciadores disponibles")
    
    # Desempeño de Productos
    st.markdown("---")
    st.subheader("📦 Desempeño de Productos - Cuáles Productos Le Generan Más Dinero")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Qué productos generan más comisiones para SU empresa?
        
        **Qué estamos midiendo:**
        - **Comisión total por producto** = Cuánto le paga cada producto
        - Volumen de transacciones por producto
        - Número de transacciones por producto
        - **Tasa promedio de comisión** - qué productos tienen los mejores márgenes para USTED
        
        **Por qué importa:**
        - Enfóquese en promover productos con mayores comisiones
        - Productos con altas tasas de comisión = más rentables para USTED
        - Entender la mezcla de productos ayuda a planificar crecimiento de comisiones
        
        **Cómo usarlo:**
        - **Impulse productos de alto margen** - Entrene a referenciadores para vender con mejores tasas
        - **Agrupe estratégicamente** - Combine productos populares con los de alto margen
        - **Estrategia de precios** - Considere si productos de bajo margen deberían tener tasas más altas
        
        **Guía del mapa de árbol:** 
        - Cajas más grandes = más comisiones para USTED
        - Color más verde = tasa de comisión más alta (mejores márgenes)
        - ¡Enfóquese en cajas grandes y verdes = sus productos más rentables!
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(products_query, language="sql")
        
        products_df = safe_query(products_query, "top productos")
        
        if not products_df.empty:
            fig_products = px.treemap(
                products_df,
                path=['NOMBRE PRODUCTO'],
                values='commission_earnings',
                title="Comisión por Producto (Mapa de Árbol)",
                color='avg_commission_rate',
                color_continuous_scale='RdYlGn',
                labels={'avg_commission_rate': 'Tasa Comisión Prom %'}
            )
            st.plotly_chart(fig_products, width="stretch")
        else:
            st.info("No hay datos de productos disponibles")
    
    with col_prod2:
        if not products_df.empty:
            st.dataframe(
                products_df.style.format({
                    'commission_earnings': '${:,.0f}',
                    'volume': '${:,.0f}',
                    'transactions': '{:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                width="stretch",
                height=400
            )

# --- PESTAÑA 2: PERSPECTIVAS ESTRATÉGICAS ---
with tabs[1]:
    st.header("💡 Oportunidades de Negocio Impulsadas por IA")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
    <b>🎯 Acciones Estratégicas:</b><br>
    • <b>Prevención de Fuga</b>: Reactiva clientes inactivos<br>
    • <b>Venta Cruzada</b>: Agrupa productos frecuentemente emparejados<br>
    • <b>Oportunidades de Crecimiento</b>: Apunta a segmentos desatendidos
    </div>
    """, unsafe_allow_html=True)
    
    col_strat1, col_strat2 = st.columns(2)
    
    with col_strat1:
        st.subheader("🚨 Análisis de Riesgo de Fuga - ¡Proteja Sus Comisiones!")
        st.markdown("**Clientes de alto valor que no han pagado recientemente (60+ días)**")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Qué clientes solían pagar buenas comisiones pero han dejado de hacerlo?
            
            **Qué estamos midiendo:**
            - Clientes que no han tenido transacciones en más de 60 días
            - Cuántos días desde que generaron comisiones por última vez
            - **Su valor de comisión de por vida** = Total de dinero que le han pagado históricamente
            - Número total de transacciones realizadas
            
            **Por qué importa - ESTO ES CRÍTICO:**
            - ¡Estos clientes SOLÍAN pagarle dinero - ahora no lo hacen!
            - Está perdiendo comisiones recurrentes
            - Pueden haberse pasado a un competidor
            - Cada día inactivos = ingresos perdidos para SU empresa
            
            **Cómo usarlo - ACCIONES URGENTES:**
            1. **Llame al top 5 HOY** - Son fuentes de comisión de alto valor que está perdiendo
            2. **Averigüe por qué** - ¿Se cambiaron? ¿Están insatisfechos? ¿Tienen un problema?
            3. **Recupérelos** - Ofrezca tratos especiales, mejor servicio, atención personal
            4. **Calcule la pérdida** - Si no vuelven, ¿cuánta comisión anual pierde?
            
            **Ejemplo:** Si un cliente que solía pagarle $50.000/año en comisiones lleva 60 días inactivo, ¡ya ha perdido ~$8.000!
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(churn_query, language="sql")
        
        churn_df = safe_query(churn_query, "análisis de fuga")
        
        if not churn_df.empty:
            st.dataframe(
                churn_df.style.format({
                    'days_inactive': '{:.0f}',
                    'lifetime_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}'
                }),
                width="stretch"
            )
            total_at_risk = churn_df['lifetime_commission'].sum()
            st.error(f"🚨 **URGENTE:** ¡{len(churn_df)} clientes de alto valor en riesgo! Le han pagado ${total_at_risk:,.0f} en comisiones históricamente!")
            st.markdown("**Acción Requerida:** ¡Contacte a estos clientes de inmediato para evitar pérdida permanente de comisiones!")
        else:
            st.success("✅ No hay clientes de alto valor en riesgo de fuga")
    
    with col_strat2:
        st.subheader("🎯 Oportunidades de Venta Cruzada")
        st.markdown("**Productos frecuentemente comprados juntos**")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Qué productos compran los clientes juntos frecuentemente?
            
            **Qué estamos midiendo:**
            - Pares de productos que los mismos clientes compran
            - Número de clientes compartidos entre pares de productos
            - Porcentaje de penetración de mercado
            
            **Por qué importa:**
            - Crear ofertas de productos agrupados
            - Entrenar al equipo de ventas en combinaciones naturales
            - Aumentar comisión por cliente sugiriendo productos complementarios
            
            **Cómo usarlo:**
            - Cuando un cliente compre Producto A, sugiera Producto B
            - Cree paquetes promocionales de productos frecuentemente emparejados
            - Diseñe campañas de marketing destacando estas combinaciones
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(cross_sell_query, language="sql")
        
        cross_sell_df = safe_query(cross_sell_query, "análisis de venta cruzada")
        
        if not cross_sell_df.empty:
            st.dataframe(cross_sell_df, width="stretch")
            st.info("💡 Cree ofertas agrupadas para los mejores pares de productos")
        else:
            st.info("No hay suficientes datos para el análisis de venta cruzada")
    
    # Segmentación de Clientes
    st.markdown("---")
    st.subheader("👥 Segmentación de Clientes por Valor de Comisión - Quién le Paga Más")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Cómo debemos priorizar clientes según las comisiones que generan para NOSOTROS?
        
        **Qué estamos midiendo:**
        - Clientes agrupados en 4 segmentos según **comisiones** que le pagan:
          - **VIP (Top 20%)**: Clientes que le pagan MÁS comisiones - ¡sus vacas lecheras!
          - **Alto Valor (50-80%)**: Buenos pagadores de comisión - fuentes importantes
          - **Valor Medio (20-50%)**: Pagadores regulares de comisión - comisión moderada
          - **Bajo Valor (Inferior 20%)**: Pequeños pagadores - clientes nuevos u ocasionales
        
        **Por qué importa - Esta es SU segmentación de dinero:**
        - Clientes VIP = Sus mayores cheques de pago - ¡trátelos como oro!
        - Diferentes niveles de servicio = asigne recursos donde USTED gana más
        - Estrategia de crecimiento = mueva clientes a niveles de comisión más altos
        
        **Cómo usarlo:**
        - **Clientes VIP**: Gestores de cuenta dedicados, servicio prioritario, atención personal
        - **Alto Valor**: Revisiones regulares, ofertas especiales para aumentar su negocio
        - **Valor Medio**: Servicio estándar, oportunidades de venta adicional
        - **Bajo Valor**: Servicio eficiente, identificar potencial de crecimiento
        
        **Perspectiva clave:** ¡Cuantas más comisiones genera un cliente, más atención merece de SU equipo!
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
                    THEN 'Alto Valor (50-80%)'
                WHEN total_commission >= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY total_commission) FROM client_stats)
                    THEN 'Valor Medio (20-50%)'
                ELSE 'Bajo Valor (Inferior 20%)'
            END as segment,
            COUNT(*) as client_count,
            SUM(total_commission) as segment_commission,
            AVG(transaction_count) as avg_transactions,
            AVG(avg_commission_per_transaction) as avg_commission_per_deal
        FROM client_stats
        GROUP BY segment
        ORDER BY segment_commission DESC
    """
    
    with st.expander("🔍 Ver Consulta SQL", expanded=False):
        st.code(segment_query, language="sql")
    
    segment_df = safe_query(segment_query, "segmentación de clientes")
    
    if not segment_df.empty:
        col_seg1, col_seg2 = st.columns(2)
        
        with col_seg1:
            fig_segment = px.pie(
                segment_df,
                values='client_count',
                names='segment',
                title='Distribución de Clientes por Segmento de Valor',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            fig_segment.update_traces(
                hovertemplate='<b>%{label}</b><br>Clientes: %{value}<br>Comisiones: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=segment_df[['segment_commission']]
            )
            st.plotly_chart(fig_segment, width="stretch")
            st.caption("📊 Distribución de clientes por segmento de valor")
        
        with col_seg2:
            fig_commission = px.bar(
                segment_df,
                x='segment',
                y='segment_commission',
                title='Contribución de Comisión por Segmento - SUS Ganancias',
                labels={'segment_commission': 'Comisión ($) - SUS GANANCIAS', 'segment': 'Segmento de Cliente'},
                color='segment_commission',
                color_continuous_scale='Greens',
                text='segment_commission'
            )
            fig_commission.update_traces(
                texttemplate='$%{text:,.0f}',
                textposition='outside'
            )
            st.plotly_chart(fig_commission, width="stretch")
            st.caption("💰 Cuánto le paga en comisiones cada segmento")
        
        st.markdown("**Desglose Detallado por Segmento**")
        display_segment_df = segment_df.copy()
        st.dataframe(
            display_segment_df.style.format({
                'client_count': '{:,.0f}',
                'segment_commission': '${:,.0f}',
                'avg_transactions': '{:,.1f}',
                'avg_commission_per_deal': '${:,.0f}'
            }),
            width="stretch"
        )
        
        vip_commission = segment_df[segment_df['segment'] == 'VIP (Top 20%)']['segment_commission'].sum()
        total_commission = segment_df['segment_commission'].sum()
        vip_percentage = (vip_commission / total_commission * 100) if total_commission > 0 else 0
        
        st.info(f"💎 **Perspectiva VIP:** Su top 20% de clientes genera **${vip_commission:,.0f}** ({vip_percentage:.1f}%) de sus comisiones totales!")

# --- PESTAÑA 3: RED COMPRADORES-VENDEDORES ---
with tabs[2]:
    st.header("🔗 Análisis de Red Compradores-Vendedores")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
    <b>💡 Entendiendo el Modelo de Negocio:</b><br>
    • <b>Flujo de Transacción:</b> El vendedor genera factura → El comprador recibe mercancía → Su empresa registra la factura en BMC<br>
    • <b>Beneficios del Registro:</b> El comprador O el vendedor obtienen beneficios tributarios del gobierno<br>
    • <b>Su Rol:</b> Usted gana comisión por facilitar el registro<br>
    • <b>Principal:</b> Quien paga por el registro (comprador o vendedor) se marca como "PRINCIPAL"
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🕸️ Perspectivas de la Red y Relaciones Clave")
    
    col_net1, col_net2 = st.columns(2)
    
    with col_net1:
        st.markdown("#### 🔄 Análisis de Nodos Centrales - ¿Quién Conecta Más?")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Quiénes son los actores clave que conectan compradores y vendedores?
            
            **Qué estamos midiendo:**
            - **Vendedores con más compradores únicos** - Estos son sus centros de distribución
            - **Compradores con más vendedores únicos** - Estos son sus agregadores/minoristas
            - Comisión ganada de cada nodo central
            
            **Por qué importa:**
            - Vendedores centrales = Grandes productores/distribuidores con amplio alcance
            - Compradores centrales = Grandes minoristas/agregadores comprando de muchos proveedores
            - Perder un nodo central afecta muchas relaciones y flujos de comisión
            
            **Cómo usarlo:**
            - Proteja las relaciones centrales - son críticas para su red
            - Ofrezca descuentos por volumen o incentivos a nodos centrales
            - Si un nodo central abandona, pierde múltiples oportunidades de comisión
            """)
        
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(seller_hub_query, language="sql")
        
        seller_hubs_df = safe_query(seller_hub_query, "nodos vendedores")
        
        if not seller_hubs_df.empty:
            st.markdown("**🏭 Principales Nodos de Vendedores (Más Conectados)**")
            
            fig_seller_hub = px.bar(
                seller_hubs_df,
                x='unique_buyers',
                y='seller',
                orientation='h',
                title='Vendedores con Más Compradores Únicos',
                labels={'unique_buyers': 'Número de Compradores Únicos', 'seller': 'Vendedor'},
                color='total_commission',
                color_continuous_scale='Oranges',
                hover_data=['total_commission', 'total_transactions']
            )
            fig_seller_hub.update_traces(
                hovertemplate='<b>%{y}</b><br>Compradores Únicos: %{x}<br>Comisión: $%{customdata[0]:,.0f}<br>Transacciones: %{customdata[1]:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_seller_hub, width="stretch")
            
            st.dataframe(
                seller_hubs_df.style.format({
                    'unique_buyers': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}',
                    'total_volume': '${:,.0f}'
                }),
                width="stretch"
            )
        else:
            st.info("No hay datos de nodos de vendedores disponibles")
    
    with col_net2:
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(buyer_hub_query, language="sql")
        
        buyer_hubs_df = safe_query(buyer_hub_query, "nodos compradores")
        
        if not buyer_hubs_df.empty:
            st.markdown("**🏪 Principales Nodos de Compradores (Más Conectados)**")
            
            fig_buyer_hub = px.bar(
                buyer_hubs_df,
                x='unique_sellers',
                y='buyer',
                orientation='h',
                title='Compradores con Más Vendedores Únicos',
                labels={'unique_sellers': 'Número de Vendedores Únicos', 'buyer': 'Comprador'},
                color='total_commission',
                color_continuous_scale='Greens',
                hover_data=['total_commission', 'total_transactions']
            )
            fig_buyer_hub.update_traces(
                hovertemplate='<b>%{y}</b><br>Vendedores Únicos: %{x}<br>Comisión: $%{customdata[0]:,.0f}<br>Transacciones: %{customdata[1]:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_buyer_hub, width="stretch")
            
            st.dataframe(
                buyer_hubs_df.style.format({
                    'unique_sellers': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'total_transactions': '{:,.0f}',
                    'total_volume': '${:,.0f}'
                }),
                width="stretch"
            )
        else:
            st.info("No hay datos de nodos de compradores disponibles")
    
    st.markdown("---")
    st.subheader("💼 Análisis del Principal de Registro - ¿Quién Paga el Registro?")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Quién paga típicamente el registro en BMC - compradores o vendedores?
        
        **Qué estamos midiendo:**
        - Campo PRINCIPAL = 'V' (Vendedor paga) o 'C' (Comprador paga)
        - Comisión ganada por registros pagados por compradores vs vendedores
        - Número de transacciones por tipo de principal
        
        **Por qué importa:**
        - Entender qué lado del mercado impulsa su negocio
        - Diferentes estrategias de precios para registros de compradores vs vendedores
        - Identificar si un lado es más sensible al precio
        
        **Perspectivas estratégicas:**
        - Si los vendedores pagan más → Enfoque marketing en vendedores, valoran el beneficio tributario
        - Si los compradores pagan más → Los compradores ven más valor, apunte a adquisición de compradores
        - División equilibrada → Ambos lados valoran el servicio por igual
        """)
    
    principal_where = filter_query + (" AND " if filter_query else "WHERE ") + "PRINCIPAL IS NOT NULL"
    principal_query = f"""
        SELECT 
            CASE 
                WHEN PRINCIPAL = 'V' THEN 'Vendedor Paga'
                WHEN PRINCIPAL = 'C' THEN 'Comprador Paga'
                ELSE 'Desconocido'
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
    
    with st.expander("🔍 Ver Consulta SQL", expanded=False):
        st.code(principal_query, language="sql")
    
    principal_df = safe_query(principal_query, "análisis de principal")
    
    if not principal_df.empty:
        col_prin1, col_prin2 = st.columns(2)
        
        with col_prin1:
            fig_principal = px.pie(
                principal_df,
                values='total_commission',
                names='principal_type',
                title='Distribución de Comisión por Principal',
                hole=0.4,
                color_discrete_sequence=['#E74C3C', '#3498DB']
            )
            fig_principal.update_traces(
                hovertemplate='<b>%{label}</b><br>Comisión: $%{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>'
            )
            st.plotly_chart(fig_principal, width="stretch")
        
        with col_prin2:
            st.markdown("**Desglose Detallado por Principal**")
            st.dataframe(
                principal_df.style.format({
                    'transactions': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'avg_commission': '${:,.0f}',
                    'total_volume': '${:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                width="stretch"
            )
            
            if len(principal_df) >= 2:
                seller_comm = principal_df[principal_df['principal_type'] == 'Vendedor Paga']['total_commission'].sum()
                buyer_comm = principal_df[principal_df['principal_type'] == 'Comprador Paga']['total_commission'].sum()
                total = seller_comm + buyer_comm
                
                if seller_comm > buyer_comm:
                    st.success(f"💡 **Perspectiva:** Los vendedores pagan el {(seller_comm/total*100):.1f}% de los registros. ¡Enfóquese en adquisición de vendedores!")
                else:
                    st.success(f"💡 **Perspectiva:** Los compradores pagan el {(buyer_comm/total*100):.1f}% de los registros. ¡Enfóquese en adquisición de compradores!")
    
    st.markdown("---")
    st.subheader("🎯 Oportunidades de Clientes Potenciales")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿A quién debemos apuntar como nuevos clientes?
        
        **La Estrategia:**
        - Si un **Vendedor es SU cliente**, sus **Compradores** son clientes potenciales
        - Si un **Comprador es SU cliente**, sus **Vendedores** son clientes potenciales
        - ¡Estas entidades ya hacen negocio agrícola - solo necesitan registrarse con USTED!
        
        **Qué estamos midiendo:**
        - Entidades que transaccionan con SUS clientes pero no son clientes
        - Volumen de transacciones que ya están realizando
        - Número de SUS clientes con quienes trabajan (prospectos cálidos)
        
        **Por qué importa:**
        - **Prospectos cálidos** = Ya conocen a sus clientes, más fáciles de convertir
        - **Mercado probado** = Ya están haciendo transacciones que podrían registrarse
        - **Efecto de red** = Convertirlos añade más valor de conexión
        
        **Cómo usarlo:**
        - Priorice prospectos que trabajan con múltiples clientes (mejores referencias)
        - Pida a sus clientes introducciones
        - Muéstreles beneficios tributarios que están perdiendo
        - Calcule oportunidad de comisión = su volumen × su tasa
        """)
    
    clients_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CC PPAL" IS NOT NULL AND CLIENTE IS NOT NULL'
    clients_query = f"""
        SELECT DISTINCT "CC PPAL" as client_nit, CLIENTE as client_name
        FROM operaciones_bmc
        {clients_where}
    """
    
    clients_df = safe_query(clients_query, "lista de clientes actuales")
    
    if not clients_df.empty:
        client_nits = set(clients_df['client_nit'].unique())
        
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
        
        potential_buyers_df = safe_query(potential_buyers_query, "compradores potenciales")
        
        if not potential_buyers_df.empty:
            potential_buyers_df = potential_buyers_df[~potential_buyers_df['prospect_nit'].isin(client_nits)]
        
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
        
        potential_sellers_df = safe_query(potential_sellers_query, "vendedores potenciales")
        
        if not potential_sellers_df.empty:
            potential_sellers_df = potential_sellers_df[~potential_sellers_df['prospect_nit'].isin(client_nits)]
        
        col_opp1, col_opp2 = st.columns(2)
        
        with col_opp1:
            st.markdown("### 🔵 Compradores Potenciales como Clientes")
            st.markdown("*Compradores que compran a SUS clientes vendedores*")
            
            if not potential_buyers_df.empty:
                st.success(f"🎯 ¡Se encontraron {len(potential_buyers_df)} compradores potenciales como clientes!")
                
                total_opp = potential_buyers_df['commission_opportunity'].sum()
                st.metric("💰 Oportunidad Total de Comisión", f"${total_opp:,.0f}", 
                         help="Comisión potencial si todos estos compradores se convierten en clientes")
                
                display_buyers = potential_buyers_df[['prospect_name', 'num_connections_to_clients', 
                                                       'total_volume', 'total_transactions', 
                                                       'commission_opportunity']].copy()
                display_buyers.columns = ['Nombre del Prospecto', 'Conexiones con Clientes', 'Volumen', 'Transacciones', 'Oportunidad de Comisión']
                
                st.dataframe(
                    display_buyers.style.format({
                        'Conexiones con Clientes': '{:.0f}',
                        'Volumen': '${:,.0f}',
                        'Transacciones': '{:.0f}',
                        'Oportunidad de Comisión': '${:,.0f}'
                    }),
                    width="stretch",
                    height=400
                )
                
                if len(potential_buyers_df) > 0:
                    top_prospect = potential_buyers_df.iloc[0]
                    with st.expander(f"🌟 Mejor Prospecto: {top_prospect['prospect_name']}", expanded=False):
                        st.markdown(f"""
                        **Por qué es un prospecto caliente:**
                        - Trabaja con **{int(top_prospect['num_connections_to_clients'])}** de SUS clientes
                        - **${top_prospect['total_volume']:,.0f}** en volumen de transacciones
                        - **${top_prospect['commission_opportunity']:,.0f}** de oportunidad de comisión
                        - **{int(top_prospect['total_transactions'])}** transacciones totales
                        
                        **Acción:** ¡Contacte a sus clientes vendedores para que le presenten a este comprador!
                        """)
            else:
                st.info("No se encontraron compradores potenciales. Esto podría significar:\n- Todos los compradores ya están registrados\n- Se necesitan más clientes vendedores\n- Intente ampliar los filtros de fechas")
        
        with col_opp2:
            st.markdown("### 🔴 Vendedores Potenciales como Clientes")
            st.markdown("*Vendedores que venden a SUS clientes compradores*")
            
            if not potential_sellers_df.empty:
                st.success(f"🎯 ¡Se encontraron {len(potential_sellers_df)} vendedores potenciales como clientes!")
                
                total_opp = potential_sellers_df['commission_opportunity'].sum()
                st.metric("💰 Oportunidad Total de Comisión", f"${total_opp:,.0f}",
                         help="Comisión potencial si todos estos vendedores se convierten en clientes")
                
                display_sellers = potential_sellers_df[['prospect_name', 'num_connections_to_clients', 
                                                        'total_volume', 'total_transactions', 
                                                        'commission_opportunity']].copy()
                display_sellers.columns = ['Nombre del Prospecto', 'Conexiones con Clientes', 'Volumen', 'Transacciones', 'Oportunidad de Comisión']
                
                st.dataframe(
                    display_sellers.style.format({
                        'Conexiones con Clientes': '{:.0f}',
                        'Volumen': '${:,.0f}',
                        'Transacciones': '{:.0f}',
                        'Oportunidad de Comisión': '${:,.0f}'
                    }),
                    width="stretch",
                    height=400
                )
                
                if len(potential_sellers_df) > 0:
                    top_prospect = potential_sellers_df.iloc[0]
                    with st.expander(f"🌟 Mejor Prospecto: {top_prospect['prospect_name']}", expanded=False):
                        st.markdown(f"""
                        **Por qué es un prospecto caliente:**
                        - Trabaja con **{int(top_prospect['num_connections_to_clients'])}** de SUS clientes
                        - **${top_prospect['total_volume']:,.0f}** en volumen de transacciones
                        - **${top_prospect['commission_opportunity']:,.0f}** de oportunidad de comisión
                        - **{int(top_prospect['total_transactions'])}** transacciones totales
                        
                        **Acción:** ¡Contacte a sus clientes compradores para que le presenten a este vendedor!
                        """)
            else:
                st.info("No se encontraron vendedores potenciales. Esto podría significar:\n- Todos los vendedores ya están registrados\n- Se necesitan más clientes compradores\n- Intente ampliar los filtros de fechas")
        
        st.markdown("---")
        st.markdown("### 🏆 Top 10 Prospectos Prioritarios (Combinados)")
        
        all_prospects = []
        
        if not potential_buyers_df.empty:
            buyers_list = potential_buyers_df.copy()
            buyers_list['type'] = '🔵 Comprador'
            all_prospects.append(buyers_list)
        
        if not potential_sellers_df.empty:
            sellers_list = potential_sellers_df.copy()
            sellers_list['type'] = '🔴 Vendedor'
            all_prospects.append(sellers_list)
        
        if all_prospects:
            combined_df = pd.concat(all_prospects, ignore_index=True)
            combined_df = combined_df.sort_values('num_connections_to_clients', ascending=False).head(10)
            
            priority_display = combined_df[['prospect_name', 'type', 'num_connections_to_clients', 
                                           'commission_opportunity', 'total_volume']].copy()
            priority_display.columns = ['Prospecto', 'Tipo', 'Conexiones con Clientes', 'Oportunidad de Comisión', 'Volumen']
            
            st.dataframe(
                priority_display.style.format({
                    'Conexiones con Clientes': '{:.0f}',
                    'Oportunidad de Comisión': '${:,.0f}',
                    'Volumen': '${:,.0f}'
                }),
                width="stretch"
            )
            
            st.info(f"""
            💡 **Estrategia Comercial:**
            - Comience con prospectos conectados a **múltiples clientes** (referencias más fuertes)
            - Acérquese a ellos a través de sus **clientes existentes** (introducción cálida)
            - Destaque los **beneficios tributarios** que actualmente están perdiendo
            - Muéstreles que la **oportunidad de comisión** representa sus ahorros potenciales
            """)
    else:
        st.warning('⚠️ No se pueden determinar los clientes actuales. Verifique si el campo "CC PPAL" está poblado.')
    
    st.markdown("---")
    st.subheader("🤝 Relaciones Comerciales Mutuas")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Qué pares comprador-vendedor hacen más negocio juntos?
        
        **Qué estamos midiendo:**
        - Principales pares comprador-vendedor por frecuencia de transacciones
        - Comisión ganada de cada relación
        - Si es un patrón de registro unilateral o mutuo
        
        **Por qué importa:**
        - **Relaciones fuertes** = Flujo de comisión predecible
        - **Relaciones exclusivas** = Riesgo si una parte se cambia
        - **Nuevas relaciones** = Oportunidades de crecimiento
        
        **Cómo usarlo:**
        - Nutra pares fuertes con soporte de gestores de relaciones
        - Venta cruzada a relaciones establecidas (ya confían el uno en el otro)
        - Monitoree si los pares exclusivos deberían diversificarse
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
    
    with st.expander("🔍 Ver Consulta SQL", expanded=False):
        st.code(relationships_query, language="sql")
    
    relationships_df = safe_query(relationships_query, "relaciones mutuas")
    
    if not relationships_df.empty:
        st.markdown("**Top 20 Relaciones Comprador-Vendedor**")
        
        relationships_df['relationship_type'] = relationships_df.apply(
            lambda row: '🔄 Mutua' if (row['seller_paid'] > 0 and row['buyer_paid'] > 0) 
            else ('🔴 Vendedor Paga' if row['seller_paid'] > 0 else '🔵 Comprador Paga'),
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
            width="stretch",
            height=600
        )
        
        mutual_count = len(relationships_df[relationships_df['relationship_type'] == '🔄 Mutua'])
        total_relationships = len(relationships_df)
        
        st.info(f"""
        📊 **Perspectivas de Relaciones:**
        - Total Principales Relaciones: {total_relationships}
        - Relaciones Mutuas (ambas partes pagan): {mutual_count}
        - Relaciones Unilaterales: {total_relationships - mutual_count}
        - Comisión Total de los 20 Mejores Pares: ${relationships_df['total_commission'].sum():,.0f}
        """)
    else:
        st.info("No hay suficientes datos para el análisis de relaciones (se necesitan al menos 3 transacciones por par)")
    
    # Visualización Interactiva de Red
    st.markdown("---")
    st.subheader("🗺️ Mapa Interactivo de Visualización de Red")
    
    with st.expander("ℹ️ Cómo interactuar con el mapa de red", expanded=False):
        st.markdown("""
        **Funciones Interactivas:**
        
        **Controles del Ratón:**
        - 🖱️ **Pase el cursor** sobre nodos/líneas para ver detalles
        - 🔍 **Amplíe** con la rueda del ratón o pellizco
        - ✋ **Desplace** haciendo clic y arrastrando en espacio vacío
        - 🎯 **Haga clic** en nodos para resaltar conexiones
        
        **Nodos (círculos):**
        - 🔴 **Nodos rojos** = Vendedores
        - 🔵 **Nodos azules** = Compradores
        - **Tamaño** = Comisión generada (más grande = más comisión)
        
        **Líneas (aristas):**
        - Conectan compradores con vendedores que hacen negocios juntos
        - **Grosor** = Número de transacciones (más grueso = más frecuente)
        - **Intensidad del color** = Valor de comisión (más oscuro = más $$$)
        
        **Qué buscar:**
        - **Nodos centrales** (muchas conexiones) = Actores críticos en su red
        - **Pares aislados** = Relaciones exclusivas (riesgo si uno se va)
        - **Clústeres** = Ecosistemas de negocio o grupos regionales
        - **Nodos puente** = Entidades conectando diferentes clústeres
        """)
    
    st.markdown("### 🎛️ Controles de Visualización")
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns(4)
    
    with col_ctrl1:
        top_n_relationships = st.slider(
            "Relaciones a mostrar",
            min_value=10,
            max_value=100,
            value=30,
            step=10,
            help="Más relaciones = mapa más detallado pero más aglomerado"
        )
    
    with col_ctrl2:
        layout_type = st.selectbox(
            "Algoritmo de Diseño",
            options=["spring", "circular", "fruchterman_reingold", "shell"],
            index=0,
            help="Spring=Clústeres equilibrados, Circular=Espaciado igual, Fruchterman-Reingold=Dirigido por fuerza, Shell=Anillos Comprador/Vendedor"
        )
    
    with col_ctrl3:
        node_size_metric = st.selectbox(
            "Tamaño de Nodo Basado En",
            options=["Comisión", "Conexiones"],
            index=0,
            help="¿Qué debe determinar el tamaño del nodo?"
        )
    
    with col_ctrl4:
        show_labels = st.checkbox(
            "Mostrar Etiquetas de Nodo",
            value=False,
            help="Mostrar nombres en nodos (puede ser confuso con muchos nodos)"
        )
    
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
    
    network_data_df = safe_query(network_data_query, "datos de red")
    
    if not NETWORKX_AVAILABLE:
        st.warning("""
        ⚠️ **NetworkX no está instalado.** Para ver el mapa de red interactivo, instálelo:
        ```bash
        pip install networkx --break-system-packages
        ```
        Después de la instalación, reinicie el tablero.
        """)
    elif not network_data_df.empty and len(network_data_df) > 0:
        G = nx.Graph()
        
        for _, row in network_data_df.iterrows():
            G.add_edge(
                f"S:{row['seller']}", 
                f"B:{row['buyer']}", 
                weight=row['transactions'],
                commission=row['total_commission']
            )
        
        try:
            if layout_type == "spring":
                pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
            elif layout_type == "circular":
                pos = nx.circular_layout(G)
            elif layout_type == "fruchterman_reingold":
                pos = nx.spring_layout(G, k=3, iterations=100, seed=42)
            elif layout_type == "shell":
                sellers = [n for n in G.nodes() if n.startswith("S:")]
                buyers = [n for n in G.nodes() if n.startswith("B:")]
                if len(sellers) > 0 and len(buyers) > 0:
                    pos = nx.shell_layout(G, nlist=[sellers, buyers])
                else:
                    st.warning("⚠️ El diseño Shell requiere vendedores y compradores. Usando diseño Spring.")
                    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        except Exception as e:
            st.warning(f"⚠️ Error con diseño {layout_type}: {str(e)}. Usando diseño Spring.")
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        node_x, node_y, node_text, node_hover_text, node_color, node_size = [], [], [], [], [], []
        node_commission = {}
        node_connections = {}
        
        for _, row in network_data_df.iterrows():
            seller_key = f"S:{row['seller']}"
            buyer_key = f"B:{row['buyer']}"
            node_commission[seller_key] = node_commission.get(seller_key, 0) + row['total_commission']
            node_commission[buyer_key] = node_commission.get(buyer_key, 0) + row['total_commission']
        
        for node in G.nodes():
            node_connections[node] = len(list(G.neighbors(node)))
        
        max_commission = max(node_commission.values()) if node_commission else 1
        max_connections = max(node_connections.values()) if node_connections else 1
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            node_type = "Vendedor" if node.startswith("S:") else "Comprador"
            node_name = node[2:]
            commission = node_commission.get(node, 0)
            connections = node_connections.get(node, 0)
            
            short_name = node_name[:15] + "..." if len(node_name) > 15 else node_name
            node_text.append(short_name if show_labels else "")
            
            node_hover_text.append(
                f"<b>{node_name}</b><br>"
                f"Tipo: {node_type}<br>"
                f"Comisión: ${commission:,.0f}<br>"
                f"Conexiones: {connections}<br>"
                f"Haga clic para resaltar"
            )
            
            node_color.append('#E74C3C' if node.startswith("S:") else '#3498DB')
            
            if node_size_metric == "Comisión":
                size_value = commission / max_commission if max_commission > 0 else 0.5
            else:
                size_value = connections / max_connections if max_connections > 0 else 0.5
            
            node_size.append(max(15, min(70, size_value * 70)))
        
        edge_traces = []
        max_weight = max([d['weight'] for u, v, d in G.edges(data=True)]) if G.edges() else 1
        max_edge_commission = max([d['commission'] for u, v, d in G.edges(data=True)]) if G.edges() else 1
        
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            weight = edge[2]['weight']
            edge_commission = edge[2]['commission']
            line_width = max(0.5, min(6, (weight / max_weight) * 6))
            opacity = max(0.2, min(0.8, (edge_commission / max_edge_commission)))
            
            edge_trace = go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                mode='lines',
                line=dict(width=line_width, color=f'rgba(149, 165, 166, {opacity})'),
                hoverinfo='text',
                text=f"<b>Relación</b><br>Transacciones: {weight}<br>Comisión: ${edge_commission:,.0f}",
                showlegend=False
            )
            edge_traces.append(edge_trace)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if show_labels else 'markers',
            hoverinfo='text',
            text=node_text,
            hovertext=node_hover_text,
            marker=dict(color=node_color, size=node_size, line=dict(width=2, color='white'), opacity=0.9),
            textposition="top center",
            textfont=dict(size=8, color='black'),
            showlegend=False
        )
        
        fig_network = go.Figure(data=edge_traces + [node_trace])
        fig_network.update_layout(
            title=dict(
                text=f"🔗 Red Interactiva Compradores-Vendedores (Top {top_n_relationships} Relaciones)",
                font=dict(size=18, color='#2c3e50'), x=0.5, xanchor='center'
            ),
            showlegend=False, hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=False),
            plot_bgcolor='#F8F9FA', paper_bgcolor='white', height=750, dragmode='pan',
        )
        
        fig_network.update_layout(
            updatemenus=[dict(
                type="buttons", direction="left",
                buttons=[dict(args=[{"xaxis.range": None, "yaxis.range": None}], label="Restablecer Zoom", method="relayout")],
                pad={"r": 10, "t": 10}, showactive=False, x=0.0, xanchor="left", y=1.1, yanchor="top"
            )]
        )
        
        st.plotly_chart(fig_network, width="stretch")
        
        st.markdown("### 📊 Análisis de Red")
        col_ni1, col_ni2, col_ni3, col_ni4 = st.columns(4)
        
        with col_ni1:
            total_nodes = len(G.nodes())
            sellers = len([n for n in G.nodes() if n.startswith("S:")])
            buyers = len([n for n in G.nodes() if n.startswith("B:")])
            st.info(f"""
            **Tamaño de la Red**
            
            Total Entidades: **{total_nodes}**
            
            🔴 Vendedores: **{sellers}**
            
            🔵 Compradores: **{buyers}**
            """)
        
        with col_ni2:
            degrees = dict(G.degree())
            most_connected = max(degrees, key=degrees.get)
            most_connected_name = most_connected[2:][:30]
            most_connected_type = "Vendedor" if most_connected.startswith("S:") else "Comprador"
            
            st.success(f"""
            **Mayor Nodo Central** 🌟
            
            Nombre: **{most_connected_name}**
            
            Tipo: **{most_connected_type}**
            
            Conexiones: **{degrees[most_connected]}**
            """)
        
        with col_ni3:
            density = nx.density(G)
            total_commission = network_data_df['total_commission'].sum()
            
            st.warning(f"""
            **Salud de la Red** 💪
            
            Densidad: **{density:.1%}**
            
            Comisión Total: **${total_commission:,.0f}**
            
            Prom Trans/Par: **{network_data_df['transactions'].mean():.1f}**
            """)
        
        with col_ni4:
            if len(G.nodes()) > 2:
                betweenness = nx.betweenness_centrality(G)
                bridge_node = max(betweenness, key=betweenness.get)
                bridge_name = bridge_node[2:][:30]
                bridge_type = "Vendedor" if bridge_node.startswith("S:") else "Comprador"
                
                st.error(f"""
                **Nodo Puente Clave** 🌉
                
                Nombre: **{bridge_name}**
                
                Tipo: **{bridge_type}**
                
                Centralidad: **{betweenness[bridge_node]:.3f}**
                """)
            else:
                st.error("**Nodo Puente Clave** 🌉\n\nSe necesitan más nodos para el análisis")
        
        st.markdown("### 🎯 Principales Nodos Centrales de la Red")
        hub_data = []
        for node in G.nodes():
            node_type = "Vendedor" if node.startswith("S:") else "Comprador"
            node_name = node[2:]
            commission = node_commission.get(node, 0)
            connections = node_connections.get(node, 0)
            hub_data.append({'Nombre': node_name, 'Tipo': node_type, 'Conexiones': connections, 'Comisión': commission})
        
        hub_df = pd.DataFrame(hub_data).sort_values('Conexiones', ascending=False).head(10)
        st.dataframe(hub_df.style.format({'Conexiones': '{:.0f}', 'Comisión': '${:,.0f}'}), width="stretch")
        
    else:
        st.info("No hay suficientes datos de relaciones para crear la visualización de red. Se necesitan al menos 10 relaciones comprador-vendedor.")
    
    network_metrics_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL'
    network_metrics_query = f"""
        SELECT 
            COUNT(DISTINCT "NOMBRE VENDEDOR") as unique_sellers,
            COUNT(DISTINCT "NOMBRE COMPRADOR") as unique_buyers,
            COUNT(DISTINCT "NOMBRE VENDEDOR" || '-' || "NOMBRE COMPRADOR") as unique_relationships,
            AVG(transaction_count) as avg_transactions_per_relationship
        FROM (
            SELECT "NOMBRE VENDEDOR", "NOMBRE COMPRADOR", COUNT(*) as transaction_count
            FROM operaciones_bmc
            {network_metrics_where}
            GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
        ) relationships
    """
    
    network_metrics_df = safe_query(network_metrics_query, "métricas de red")
    
    if not network_metrics_df.empty:
        col_nm1, col_nm2, col_nm3, col_nm4 = st.columns(4)
        with col_nm1:
            st.metric("Vendedores Únicos", f"{int(network_metrics_df['unique_sellers'][0]):,}")
        with col_nm2:
            st.metric("Compradores Únicos", f"{int(network_metrics_df['unique_buyers'][0]):,}")
        with col_nm3:
            st.metric("Relaciones Únicas", f"{int(network_metrics_df['unique_relationships'][0]):,}")
        with col_nm4:
            st.metric("Prom Trans/Relación", f"{network_metrics_df['avg_transactions_per_relationship'][0]:.1f}")

# --- PESTAÑA 4: PERSPECTIVAS DEL CLIENTE ---
with tabs[3]:
    st.header("👥 Perspectivas del Cliente - Cómo Estos Datos Ayudan a SUS Clientes")
    
    st.markdown("""
    <div style='background-color: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h3>💡 Por Qué los Clientes le Pagan Comisiones</h3>
    <p><b>¡Los clientes no solo pagan por el registro - pagan por PERSPECTIVAS y VALOR!</b></p>
    <p>Esta pestaña muestra cómo los datos que USTED recopila ayudan a SUS clientes a tomar mejores decisiones,
    justificando las comisiones que le pagan. Use estas perspectivas en reuniones con clientes para demostrar su valor.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎯 Seleccione un Cliente para Analizar")
    
    client_list_where = filter_query + (" AND " if filter_query else "WHERE ") + 'CLIENTE IS NOT NULL AND "CC PPAL" IS NOT NULL'
    client_list_query = f"""
        SELECT DISTINCT CLIENTE as client_name, "CC PPAL" as client_nit
        FROM operaciones_bmc
        {client_list_where}
        ORDER BY CLIENTE
    """
    
    with st.expander("🔍 Ver Consulta SQL de Lista de Clientes", expanded=False):
        st.code(client_list_query, language="sql")
        st.caption("Esta consulta recupera todos los clientes únicos que pueden ser analizados")
    
    client_list_df = safe_query(client_list_query, "lista de clientes")
    
    if not client_list_df.empty:
        selected_client = st.selectbox(
            "Elija un cliente para ver sus perspectivas:",
            options=client_list_df['client_name'].tolist(),
            help="Seleccione un cliente para ver cómo los datos le benefician"
        )
        
        client_nit = client_list_df[client_list_df['client_name'] == selected_client]['client_nit'].values[0]
        
        st.markdown(f"## 📊 Perspectivas para: {selected_client}")
        
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
        
        with st.expander("🔍 Ver Consulta SQL de Estadísticas del Cliente", expanded=False):
            st.code(client_stats_query, language="sql")
            st.caption("Esta consulta recupera estadísticas completas para el cliente seleccionado")
        
        client_stats_df = safe_query(client_stats_query, "estadísticas del cliente")
        
        if not client_stats_df.empty:
            stats = client_stats_df.iloc[0]
            
            col_cs1, col_cs2, col_cs3, col_cs4 = st.columns(4)
            
            with col_cs1:
                st.metric("Total Transacciones", f"{int(stats['total_transactions']):,}")
            with col_cs2:
                st.metric("Volumen de Negocio", f"${stats['total_volume']:,.0f}")
            with col_cs3:
                st.metric("Comisión Pagada", f"${stats['total_commission_paid']:,.0f}")
            with col_cs4:
                st.metric("Tasa Promedio", f"{stats['avg_commission_rate']:.2f}%")
            
            st.markdown("---")
            st.markdown("### 💎 Valor que USTED Aporta a Este Cliente")
            
            tab_val1, tab_val2, tab_val3, tab_val4 = st.tabs([
                "🎯 Inteligencia de Mercado",
                "📈 Seguimiento de Desempeño", 
                "🤝 Análisis de Socios",
                "💰 Optimización de Costos"
            ])
            
            with tab_val1:
                st.subheader("🎯 Perspectivas de Inteligencia de Mercado")
                st.markdown("""
                **Lo que usted provee:** Datos de mercado en tiempo real y comparativas
                
                **Beneficios para el cliente:**
                - Ver tendencias de precios de la industria
                - Comparar sus tarifas con promedios del mercado
                - Identificar ventajas competitivas
                """)
                
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
                
                with st.expander("🔍 Ver Consulta SQL de Comparativa de Mercado", expanded=False):
                    st.code(market_comparison_query, language="sql")
                    st.caption("Compara las tarifas de comisión del cliente vs promedios del mercado por producto")
                
                market_comp_df = safe_query(market_comparison_query, "comparativa de mercado")
                
                if not market_comp_df.empty:
                    st.markdown("**📊 Desempeño de Sus Productos vs Mercado**")
                    
                    market_comp_df['vs_market'] = market_comp_df.apply(
                        lambda row: '🟢 Por Debajo del Mercado' if row['client_rate'] < row['market_avg_rate'] 
                        else '🔴 Por Encima del Mercado' if row['client_rate'] > row['market_avg_rate']
                        else '🟡 En el Mercado', axis=1
                    )
                    
                    st.dataframe(
                        market_comp_df[['NOMBRE PRODUCTO', 'client_transactions', 'client_rate', 'market_avg_rate', 'vs_market']].style.format({
                            'client_transactions': '{:.0f}',
                            'client_rate': '{:.2f}%',
                            'market_avg_rate': '{:.2f}%'
                        }),
                        width="stretch"
                    )
                    
                    st.success("""
                    💡 **Valor Entregado:** 
                    - El cliente puede ver si está pagando tarifas competitivas
                    - Identificar productos donde puede negociar mejores precios
                    - Detectar tendencias del mercado antes que los competidores
                    """)
            
            with tab_val2:
                st.subheader("📈 Seguimiento de Desempeño")
                st.markdown("""
                **Lo que usted provee:** Datos históricos y análisis de tendencias
                
                **Beneficios para el cliente:**
                - Seguir el crecimiento del negocio en el tiempo
                - Identificar patrones estacionales
                - Tomar decisiones basadas en datos
                """)
                
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
                            WHEN MES LIKE 'ene%' THEN 1 WHEN MES LIKE 'feb%' THEN 2
                            WHEN MES LIKE 'mar%' THEN 3 WHEN MES LIKE 'abr%' THEN 4
                            WHEN MES LIKE 'may%' THEN 5 WHEN MES LIKE 'jun%' THEN 6
                            WHEN MES LIKE 'jul%' THEN 7 WHEN MES LIKE 'ago%' THEN 8
                            WHEN MES LIKE 'sep%' THEN 9 WHEN MES LIKE 'oct%' THEN 10
                            WHEN MES LIKE 'nov%' THEN 11 WHEN MES LIKE 'dic%' THEN 12
                            ELSE 0
                        END
                """
                
                with st.expander("🔍 Ver Consulta SQL de Tendencia del Cliente", expanded=False):
                    st.code(client_trend_query, language="sql")
                    st.caption("Muestra la actividad comercial mensual del cliente en el tiempo")
                
                client_trend_df = safe_query(client_trend_query, "tendencia del cliente")
                
                if not client_trend_df.empty:
                    fig_client_trend = go.Figure()
                    fig_client_trend.add_trace(go.Scatter(
                        x=client_trend_df['MES'], y=client_trend_df['volume'],
                        mode='lines+markers', name='Volumen de Negocio',
                        line=dict(color='#3498DB', width=3), yaxis='y'
                    ))
                    fig_client_trend.add_trace(go.Bar(
                        x=client_trend_df['MES'], y=client_trend_df['transactions'],
                        name='Transacciones', marker_color='#95A5A6', yaxis='y2'
                    ))
                    fig_client_trend.update_layout(
                        title="Su Actividad Comercial en el Tiempo",
                        xaxis_title="Mes",
                        yaxis=dict(title="Volumen de Negocio ($)", side='left'),
                        yaxis2=dict(title="Número de Transacciones", overlaying='y', side='right'),
                        hovermode='x unified', height=400
                    )
                    st.plotly_chart(fig_client_trend, width="stretch")
                    
                    st.success("""
                    💡 **Valor Entregado:**
                    - Visibilidad clara del crecimiento/declive del negocio
                    - Identificar temporadas pico para mejor planificación
                    - Datos históricos para proyecciones financieras
                    """)
            
            with tab_val3:
                st.subheader("🤝 Análisis de Socios Comerciales")
                st.markdown("""
                **Lo que usted provee:** Perspectivas detalladas de relaciones con socios
                
                **Beneficios para el cliente:**
                - Identificar los socios comerciales más importantes
                - Detectar riesgos en las relaciones
                - Descubrir nuevas oportunidades de alianza
                """)
                
                if stats['unique_buyers'] > 0:
                    st.markdown("**🔵 Sus Principales Compradores**")
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
                    
                    with st.expander("🔍 Ver Consulta SQL de Principales Compradores", expanded=False):
                        st.code(top_buyers_query, language="sql")
                        st.caption("Muestra los principales compradores del cliente cuando actúa como vendedor")
                    
                    top_buyers_df = safe_query(top_buyers_query, "principales compradores")
                    
                    if not top_buyers_df.empty:
                        st.dataframe(
                            top_buyers_df.style.format({'transactions': '{:.0f}', 'total_volume': '${:,.0f}'}),
                            width="stretch"
                        )
                
                if stats['unique_sellers'] > 0:
                    st.markdown("**🔴 Sus Principales Proveedores**")
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
                    
                    with st.expander("🔍 Ver Consulta SQL de Principales Proveedores", expanded=False):
                        st.code(top_sellers_query, language="sql")
                        st.caption("Muestra los principales proveedores del cliente cuando actúa como comprador")
                    
                    top_sellers_df = safe_query(top_sellers_query, "principales proveedores")
                    
                    if not top_sellers_df.empty:
                        st.dataframe(
                            top_sellers_df.style.format({'transactions': '{:.0f}', 'total_volume': '${:,.0f}'}),
                            width="stretch"
                        )
                
                st.success("""
                💡 **Valor Entregado:**
                - Conozca quiénes son sus socios más importantes
                - Siga la confiabilidad y consistencia de los socios
                - Identifique el riesgo de concentración (demasiada dependencia de un socio)
                """)
            
            with tab_val4:
                st.subheader("💰 Oportunidades de Optimización de Costos")
                st.markdown("""
                **Lo que usted provee:** Perspectivas de maximización de beneficios tributarios
                
                **Beneficios para el cliente:**
                - Entender costos de registro vs beneficios
                - Identificar oportunidades de ahorro
                - Maximizar deducciones tributarias
                """)
                
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
                
                with st.expander("🔍 Ver Consulta SQL de Desglose de Costos", expanded=False):
                    st.code(cost_breakdown_query, language="sql")
                    st.caption("Muestra costos anuales de comisión y análisis de ROI para el cliente")
                
                cost_breakdown_df = safe_query(cost_breakdown_query, "desglose de costos")
                
                if not cost_breakdown_df.empty:
                    st.markdown("**📊 Análisis Anual de Costos**")
                    st.dataframe(
                        cost_breakdown_df.style.format({
                            'commission_paid': '${:,.0f}',
                            'volume': '${:,.0f}',
                            'transactions': '{:.0f}',
                            'effective_rate': '{:.2f}%'
                        }),
                        width="stretch"
                    )
                    
                    total_commission = cost_breakdown_df['commission_paid'].sum()
                    total_volume = cost_breakdown_df['volume'].sum()
                    estimated_tax_benefit = total_volume * 0.15
                    net_benefit = estimated_tax_benefit - total_commission
                    
                    col_cb1, col_cb2, col_cb3 = st.columns(3)
                    with col_cb1:
                        st.metric("Total Pagado", f"${total_commission:,.0f}")
                    with col_cb2:
                        st.metric("Beneficio Tributario Est.", f"${estimated_tax_benefit:,.0f}")
                    with col_cb3:
                        st.metric("Beneficio Neto", f"${net_benefit:,.0f}", 
                                 delta=f"{((net_benefit/total_commission)*100):.0f}% ROI")
                    
                    st.success("""
                    💡 **Valor Entregado:**
                    - ROI claro sobre los costos de registro
                    - Seguimiento de pagos de comisión vs ahorro tributario
                    - Justificar gastos de registro al equipo financiero
                    - Datos históricos para declaración de impuestos
                    """)
            
            st.markdown("---")
            st.markdown("### 🎁 Paquete Completo de Valor")
            
            st.markdown(f"""
            <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745;'>
            <h4>Por Qué los Clientes Deberían Seguir Pagando Comisiones:</h4>
            
            <p><b>1. Inteligencia de Mercado</b> 💹<br>
            → Datos de precios en tiempo real por valor de miles en honorarios de consultoría<br>
            → Comparativas competitivas no disponibles en otro lugar</p>
            
            <p><b>2. Analítica de Negocio</b> 📊<br>
            → Seguimiento histórico y análisis de tendencias<br>
            → Tableros de desempeño para mejores decisiones<br>
            → Perspectivas basadas en datos para el crecimiento</p>
            
            <p><b>3. Gestión de Relaciones</b> 🤝<br>
            → Seguimiento del desempeño de socios<br>
            → Identificación de riesgos (concentración, fuga)<br>
            → Efecto de red de perspectivas del ecosistema</p>
            
            <p><b>4. Ahorro de Costos</b> 💰<br>
            → Los beneficios tributarios superan ampliamente los costos de comisión<br>
            → Seguimiento y documentación del ROI<br>
            → Trazabilidad de cumplimiento y auditoría</p>
            
            <p><b>5. Ahorro de Tiempo</b> ⏰<br>
            → Usted maneja todos los trámites de BMC<br>
            → Reportes automatizados<br>
            → Solución integral</p>
            
            <hr>
            
            <p><b>Conclusión:</b> Los clientes pagan ~{stats['avg_commission_rate']:.2f}% de comisión pero reciben:</p>
            <ul>
            <li>✅ Beneficios tributarios del 15%+</li>
            <li>✅ Inteligencia de mercado por valor de $$$</li>
            <li>✅ Plataforma de analítica de negocio</li>
            <li>✅ Gestión integral de cumplimiento</li>
            </ul>
            
            <p style='font-size: 18px; font-weight: bold; color: #28a745;'>
            ¡Valor Neto: 10x-20x el costo de la comisión!
            </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("""
            💡 **Cómo usar esta pestaña:**
            1. Seleccione el cliente antes de las reuniones
            2. Revise sus perspectivas específicas
            3. Muéstreles el valor que ELLOS reciben
            4. Use datos para justificar las tarifas de comisión
            5. Demuestre la entrega continua de valor
            """)
        
        else:
            st.warning("No se encontraron datos para este cliente.")
    else:
        st.info("No se encontraron clientes en el rango de fechas seleccionado.")

# --- PESTAÑA 5: ANÁLISIS OPERATIVO ---
with tabs[4]:
    st.header("🔍 Análisis Operativo Detallado")
    
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        st.subheader("📅 Patrones de Operaciones Diarias")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Qué días de la semana están más ocupados?
            
            **Qué estamos midiendo:**
            - Número de operaciones por día de la semana
            - Comisión ganada cada día
            - Comisión promedio por día
            
            **Por qué importa:**
            - Planificar niveles de personal para días ocupados
            - Programar mantenimiento durante días lentos
            - Entender los ritmos semanales del negocio
            
            **Cómo usarlo:**
            - Asegure personal adecuado en días de alto volumen
            - Planifique reuniones y capacitaciones en días más lentos
            - Ajuste los horarios según los patrones de demanda
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(dow_query, language="sql")
        
        dow_df = safe_query(dow_query, "análisis por día de semana")
        
        if not dow_df.empty:
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            # Use a temporary sort key to order by day of week, then drop it
            dow_df['_sort_key'] = pd.Categorical(dow_df['day_of_week'].astype(str), categories=day_order, ordered=True)
            dow_df = dow_df.sort_values('_sort_key').drop(columns=['_sort_key'])
            
            day_translation = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            # Convert to plain string before mapping to avoid Categorical assignment error
            dow_df['day_of_week'] = dow_df['day_of_week'].astype(str).map(day_translation).fillna(dow_df['day_of_week'].astype(str))
            
            fig_dow = px.bar(
                dow_df,
                x='day_of_week',
                y='operations',
                title='Operaciones por Día de la Semana',
                labels={'operations': 'Número de Operaciones', 'day_of_week': 'Día'},
                color='operations',
                color_continuous_scale='Viridis'
            )
            fig_dow.update_traces(
                hovertemplate='<b>%{x}</b><br>Operaciones: %{y}<br>Comisión: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=dow_df[['commission_earnings']]
            )
            st.plotly_chart(fig_dow, width="stretch")
            st.caption("💡 Optimice el personal según los días pico")
        else:
            st.info("No hay datos para el análisis por día de semana")
    
    with col_op2:
        st.subheader("🏭 Operaciones por Tipo")
        
        with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
            st.markdown("""
            **Pregunta de Negocio:** ¿Qué tipos de operaciones estamos procesando?
            
            **Qué estamos midiendo:**
            - Distribución de tipos de operación:
              - **RSG**: Registro sin incentivo
              - **REX**: Registro exportación
              - **RGC**: Registro con incentivo
            - Número de operaciones por tipo
            - Comisión ganada por tipo
            
            **Por qué importa:**
            - Entender la mezcla de negocios
            - Identificar qué tipos son más rentables
            - Planificar recursos para diferentes tipos
            
            **Cómo usarlo:** Enfóquese en crecer los tipos más rentables mientras asegura capacidad para todos.
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(op_type_query, language="sql")
        
        op_type_df = safe_query(op_type_query, "análisis por tipo de operación")
        
        if not op_type_df.empty:
            fig_op_type = px.pie(
                op_type_df,
                values='operations',
                names='TIPO OPERACION',
                title='Distribución por Tipo de Operación',
                hole=0.3
            )
            fig_op_type.update_traces(
                hovertemplate='<b>%{label}</b><br>Operaciones: %{value}<br>Comisión: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=op_type_df[['commission_earnings']]
            )
            st.plotly_chart(fig_op_type, width="stretch")
        else:
            st.info("No hay datos de tipo de operación disponibles")
    
    st.markdown("---")
    st.subheader("🗺️ Distribución Geográfica")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Dónde están ubicados nuestros compradores y vendedores?
        
        **Qué estamos midiendo:**
        - Principales ciudades donde están ubicados los compradores
        - Principales ciudades donde están ubicados los vendedores
        - Número de operaciones por ciudad
        - Comisión ganada por ciudad
        
        **Por qué importa:**
        - Identificar mercados geográficos fuertes y débiles
        - Planificar estrategias de expansión regional
        - Asignar recursos de ventas de campo geográficamente
        - Entender patrones de negocio regionales
        
        **Cómo usarlo:**
        - Aumente presencia en ciudades de alta comisión
        - Investigue por qué algunas regiones tienen mejor desempeño
        - Planifique campañas de marketing por región
        """)
    
    col_geo1, col_geo2 = st.columns(2)
    
    with col_geo1:
        st.markdown("**Principales Ciudades - Compradores**")
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(buyer_cities_query, language="sql")
        
        buyer_cities_df = safe_query(buyer_cities_query, "ciudades compradores")
        
        if not buyer_cities_df.empty:
            st.dataframe(
                buyer_cities_df.style.format({'operations': '{:,.0f}', 'commission_earnings': '${:,.0f}'}),
                width="stretch"
            )
        else:
            st.info("No hay datos de ciudades de compradores")
    
    with col_geo2:
        st.markdown("**Principales Ciudades - Vendedores**")
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
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(seller_cities_query, language="sql")
        
        seller_cities_df = safe_query(seller_cities_query, "ciudades vendedores")
        
        if not seller_cities_df.empty:
            st.dataframe(
                seller_cities_df.style.format({'operations': '{:,.0f}', 'commission_earnings': '${:,.0f}'}),
                width="stretch"
            )
        else:
            st.info("No hay datos de ciudades de vendedores")

# --- PESTAÑA 6: RIESGO Y AUDITORÍA ---
with tabs[5]:
    st.header("🛡️ Tablero de Riesgo y Auditoría")
    
    st.subheader("1. Análisis de Concentración de Comisiones (Pareto)")
    st.markdown("_Monitorear dependencia de clientes clave_")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Somos demasiado dependientes de un pequeño número de clientes?
        
        **Qué estamos midiendo:**
        - La famosa "regla 80/20" - ¿el 20% de los clientes genera el 80% de la comisión?
        - Comisión de cada cliente
        - Porcentaje acumulado de comisión (línea roja mostrando total acumulado)
        
        **Por qué importa:**
        - **Alta concentración = Alto riesgo**: Si pocos clientes se van, pierde comisión significativa
        - **Distribución equilibrada = Menor riesgo**: Comisión repartida entre muchos clientes es más saludable
        
        **Cómo usarlo:**
        - **Si la línea roja llega al 80% rápido**: Depende mucho de pocos clientes - ¡RIESGO!
          - Acción: Diversifique la base de clientes, adquiera nuevos clientes
        - **Si la línea roja sube gradualmente**: Distribución saludable - ¡BIEN!
          
        **Ejemplo:** Si 3 clientes generan el 80% de la comisión, perder uno podría ser devastador.
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
    
    with st.expander("🔍 Ver Consulta SQL", expanded=False):
        st.code(pareto_query, language="sql")
    
    pareto_df = safe_query(pareto_query, "análisis de Pareto")
    
    if not pareto_df.empty:
        pareto_df['cumulative_commission'] = pareto_df['commission_earnings'].cumsum()
        pareto_df['cumulative_pct'] = (pareto_df['cumulative_commission'] / pareto_df['commission_earnings'].sum()) * 100
        
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['CLIENTE'],
            y=pareto_df['commission_earnings'],
            name='Comisión',
            marker_color='lightblue',
            hovertemplate='<b>%{x}</b><br>Comisión: $%{y:,.0f}<extra></extra>'
        ))
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df['CLIENTE'],
            y=pareto_df['cumulative_pct'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            marker=dict(color='red', size=6),
            line=dict(color='red', width=2),
            hovertemplate='<b>%{x}</b><br>Acumulado: %{y:.1f}%<extra></extra>'
        ))
        fig_pareto.update_layout(
            title='Concentración de Comisiones (Gráfico de Pareto)',
            xaxis_title='Cliente',
            yaxis_title='Comisión ($)',
            yaxis2=dict(title='Porcentaje Acumulado (%)', overlaying='y', side='right', range=[0, 100]),
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig_pareto, width="stretch")
        
        top_20_pct_count = int(len(pareto_df) * 0.2)
        top_20_commission_pct = pareto_df.iloc[:top_20_pct_count]['commission_earnings'].sum() / pareto_df['commission_earnings'].sum() * 100
        
        st.info(f"📊 El top 20% de clientes ({top_20_pct_count} clientes) genera el {top_20_commission_pct:.1f}% de la comisión")
        
        if top_20_commission_pct > 80:
            st.warning("⚠️ Alto riesgo de concentración de comisiones detectado")
        else:
            st.success("✅ Distribución saludable de comisiones")
    else:
        st.info("No hay datos para el análisis de Pareto")
    
    st.markdown("---")
    st.subheader("2. Detección de Anomalías de Precios")
    st.markdown("_Transacciones con tasas de comisión significativamente bajas_")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Hay transacciones donde cobramos comisiones inusualmente bajas?
        
        **Qué estamos midiendo:**
        - Transacciones donde la tasa de comisión está 30% o más por debajo del promedio del producto
        - La tasa de comisión real cobrada
        - La tasa promedio normal del mercado para ese producto
        - El porcentaje de descuento dado
        
        **Por qué importa:**
        - **Detectar errores de precios**: Alguien puede haber ingresado tarifas incorrectas
        - **Identificar tratos especiales**: Entender qué clientes obtuvieron descuentos
        - **Fuga de comisión**: ¿Estamos dejando dinero sobre la mesa?
        
        **Cómo usarlo:**
        - Revise cada transacción en esta lista
        - Verifique si la tasa baja fue intencional (descuento aprobado) o un error
        - Si es error: Corríjalo y reentrene al personal
        - Si fue intencional: Asegúrese de que esté documentado y justificado
        
        **Ejemplo:** Si la tasa normal es del 5% pero cobró el 2%, está perdiendo el 60% de la comisión potencial en ese negocio.
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
    
    with st.expander("🔍 Ver Consulta SQL", expanded=False):
        st.code(anomaly_query, language="sql")
    
    anomaly_df = safe_query(anomaly_query, "anomalías de precios")
    
    if not anomaly_df.empty:
        st.dataframe(
            anomaly_df.style.format({
                'transaction_value': '${:,.0f}',
                'actual_rate': '{:.2f}%',
                'market_avg_rate': '{:.2f}%',
                'discount_pct': '{:.1f}%'
            }),
            width="stretch"
        )
        st.warning(f"⚠️ Se encontraron {len(anomaly_df)} transacciones con tasas de comisión inusualmente bajas")
        st.markdown("**Acción:** Revise estas transacciones para detectar errores de precios o acuerdos especiales")
    else:
        st.success("✅ No se detectaron anomalías de precios significativas")
    
    st.markdown("---")
    st.subheader("3. Distribución del Tamaño de Transacciones")
    
    with st.expander("ℹ️ ¿Qué muestra esto?", expanded=False):
        st.markdown("""
        **Pregunta de Negocio:** ¿Cuál es el tamaño típico de nuestras transacciones?
        
        **Qué estamos midiendo:**
        - Transacciones agrupadas por valor:
          - **Pequeña**: Menos de $1 millón
          - **Mediana**: $1M a $10M
          - **Grande**: $10M a $50M
          - **Muy Grande**: Más de $50M
        - Conteo de transacciones en cada categoría
        - Comisión total por categoría
        - Tasa promedio de comisión por tamaño
        
        **Por qué importa:**
        - Entender la composición de su negocio
        - Los negocios grandes pueden necesitar manejo o aprobación especial
        - Diferentes tamaños pueden requerir diferentes procesos
        - Planificar recursos según tamaños típicos de negocio
        
        **Cómo usarlo:**
        - Si la mayoría son pequeñas: Enfóquese en eficiencia y volumen
        - Si dominan los negocios grandes: Asegure control de calidad y gestión de riesgos
        - Configure flujos de aprobación diferentes según tamaños
        """)
    
    col_size1, col_size2 = st.columns(2)
    
    with col_size1:
        size_query = f"""
            SELECT 
                CASE 
                    WHEN "VALOR NEGOCIO" < 1000000 THEN 'Pequeña (< $1M)'
                    WHEN "VALOR NEGOCIO" < 10000000 THEN 'Mediana ($1M-$10M)'
                    WHEN "VALOR NEGOCIO" < 50000000 THEN 'Grande ($10M-$50M)'
                    ELSE 'Muy Grande (> $50M)'
                END as size_category,
                COUNT(*) as transaction_count,
                SUM(COMISION) as total_commission,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc
            {filter_query}
            GROUP BY size_category
            ORDER BY 
                CASE size_category
                    WHEN 'Pequeña (< $1M)' THEN 1
                    WHEN 'Mediana ($1M-$10M)' THEN 2
                    WHEN 'Grande ($10M-$50M)' THEN 3
                    ELSE 4
                END
        """
        
        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(size_query, language="sql")
        
        size_df = safe_query(size_query, "tamaño de transacciones")
        
        if not size_df.empty:
            fig_size = px.pie(
                size_df,
                values='transaction_count',
                names='size_category',
                title='Conteo de Transacciones por Tamaño',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues
            )
            fig_size.update_traces(
                hovertemplate='<b>%{label}</b><br>Conteo: %{value}<br>Comisión: $%{customdata[0]:,.0f}<extra></extra>',
                customdata=size_df[['total_commission']]
            )
            st.plotly_chart(fig_size, width="stretch")
        else:
            st.info("No hay datos de tamaño de transacciones")
    
    with col_size2:
        if not size_df.empty:
            st.markdown("**Desglose por Tamaño de Transacciones**")
            st.dataframe(
                size_df.style.format({
                    'transaction_count': '{:,.0f}',
                    'total_commission': '${:,.0f}',
                    'avg_commission_rate': '{:.2f}%'
                }),
                width="stretch"
            )
            st.caption("💡 Las transacciones grandes pueden requerir manejo especial")

# Pie de página
st.markdown("---")
st.markdown(f"""
### 📊 **Resumen del Tablero**

**Características Mejoradas:**
- ✅ Manejo de errores y validación de datos mejorados
- ✅ Mejores consultas SQL con manejo adecuado de valores nulos
- ✅ Visualizaciones mejoradas con tooltips
- ✅ Opciones de filtrado integrales
- ✅ Gestión de riesgos y detección de anomalías
- ✅ Perspectivas geográficas y operativas

**Próximos Pasos:**
1. Configurar alertas automatizadas para métricas clave
2. Exportar informes para reuniones con partes interesadas
3. Programar revisiones regulares del tablero
4. Integrar con CRM para gestión de clientes

---
*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
""")

# con.close()  # No cerrar aquí - dejar que la caché de Streamlit lo maneje
