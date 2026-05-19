import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import os
import tempfile
import uuid
import threading
import unicodedata
import re
from datetime import datetime, timedelta
import hashlib

pio.templates.default = "plotly_white"

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
# Establezca ADMIN_USERNAME y PASSWORD_HASH en st.secrets (Streamlit Cloud) o como
# variables de entorno. Si no se definen, se usan los valores predeterminados.
#
# Para generar el hash de una nueva contraseña, ejecute en Python:
#   import hashlib; hashlib.sha256("SuContraseña".encode()).hexdigest()

def _get_secret(env_key: str, default: str) -> str:
    """Lee env var → st.secrets → default (en ese orden de prioridad)."""
    val = os.environ.get(env_key)
    if val:
        return val
    try:
        return st.secrets.get(env_key, default)
    except Exception:
        return default

ADMIN_USERNAME = _get_secret("ADMIN_USERNAME", "admin")
PASSWORD_HASH  = _get_secret(
    "PASSWORD_HASH",
    "e0bd631724a4fb17f0fc7c19ac460ef1838cdf4c4d0a922e63c09d92b90922d8"
)

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
/* ── Base ───────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
.main .block-container {
    padding-top: 1.25rem;
    padding-bottom: 2rem;
    max-width: 1280px;
}

/* ── KPI metrics ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 14px;
    padding: 1.1rem 1.3rem 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-top: 4px solid #16A34A;
}
/* Per-card accent colours (cards 2-5 override the default green) */
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-top-color: #2563EB; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-top-color: #7C3AED; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { border-top-color: #D97706; }
[data-testid="stHorizontalBlock"] > div:nth-child(5) [data-testid="stMetric"] { border-top-color: #0891B2; }
[data-testid="stMetric"] label {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.07em !important;
    color: #6b7280 !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    color: #111827 !important;
}

/* ── Tabs ────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f1f5f9;
    padding: 5px 6px;
    border-radius: 12px;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    padding: 7px 18px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #64748b !important;
    background: transparent !important;
    border: none !important;
    outline: none !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.10) !important;
}

/* ── Charts ──────────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {
    background: white;
    border-radius: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    padding: 2rem 0.5rem 0.25rem;
    margin-bottom: 0.75rem;
    overflow: visible !important;
}
/* Keep the inner iframe/div from clipping the modebar */
[data-testid="stPlotlyChart"] > div {
    overflow: visible !important;
}

/* ── DataFrames ──────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}

/* ── Alerts / info boxes ─────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.88rem !important;
}

/* ── Expanders ───────────────────────────────────────────── */
.streamlit-expanderHeader {
    font-size: 0.86rem !important;
    color: #64748b !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
}

/* ── Subheaders / section titles ─────────────────────────── */
h2 {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
h3 {
    font-size: 1.0rem !important;
    font-weight: 650 !important;
    color: #1e293b !important;
}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    color: #e2e8f0 !important;
    border-radius: 8px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.16);
}

/* ── Section dividers ────────────────────────────────────── */
hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.25rem 0; }
</style>
""", unsafe_allow_html=True)

# DB path resolution:
# The database is stored ONLY on the user's local machine (downloaded as .db file).
# On the server, a session-specific temp file is used so nothing persists after the session ends.
# If DB_PATH env var is set (custom deployment), that path is used instead.
if "db_temp_path" not in st.session_state:
    # uuid-based name: no file created, no race condition
    _tmp_name = f"bmc_{uuid.uuid4().hex}.db"
    st.session_state["db_temp_path"] = os.path.join(tempfile.gettempdir(), _tmp_name)

DB_PATH = os.environ.get("DB_PATH", st.session_state["db_temp_path"])

# If the database temp file is not found, prompt the user to load data
if not os.path.exists(DB_PATH):
    st.markdown("""
        <div style='text-align: center; padding: 40px 0;'>
            <h2>🗄️ Base de Datos No Encontrada</h2>
            <p style='color: #666;'>No hay base de datos activa en esta sesión.</p>
            <p>Restaure su base de datos guardada <strong>(.db)</strong> o cree una nueva desde un archivo <strong>CSV/Excel</strong>.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:

        # ── Opción 1: Restaurar archivo .db descargado previamente ─────────────
        st.markdown("### 💾 Opción 1 – Restaurar base de datos existente")
        st.caption("Si ya tiene un archivo **bmc_data.db** descargado anteriormente, súbalo aquí para restaurar su base de datos completa.")

        db_restore_file = st.file_uploader(
            "📁 Subir bmc_data.db (sesión anterior)",
            type=["db"],
            key="restore_db",
            help="Suba el archivo .db que descargó en una sesión anterior"
        )

        if db_restore_file is not None:
            with st.spinner("⏳ Restaurando base de datos…"):
                try:
                    # Write the file BEFORE clearing the cache.
                    # If we cleared first and the write failed the session would be
                    # stuck with no connection and no file.
                    with open(DB_PATH, "wb") as _f:
                        _f.write(db_restore_file.read())
                    st.cache_resource.clear()
                except Exception:
                    st.error("❌ Error al restaurar la base de datos. Intente de nuevo.")
                    st.stop()
            st.success("✅ Base de datos restaurada correctamente. Cargando tablero…")
            st.rerun()

        st.markdown("---")

        # ── Opción 2: Crear desde CSV / Excel ──────────────────────────────────
        st.markdown("### 📊 Opción 2 – Crear desde CSV o Excel")
        st.caption("Suba su archivo de datos y la base de datos se creará automáticamente. Podrá descargarla para guardarla en su PC.")

        init_file = st.file_uploader(
            "📂 Seleccione su archivo de datos (CSV o Excel)",
            type=["csv", "xlsx", "xls"],
            key="init_csv",
            help="Se creará bmc_data.db a partir de este archivo"
        )

        if init_file is not None:
            with st.spinner("⏳ Creando base de datos, por favor espere…"):
                _csv_tmp = None
                try:
                    st.cache_resource.clear()

                    # Remove stale temp DB from a previous failed attempt
                    if os.path.exists(DB_PATH):
                        try:
                            os.unlink(DB_PATH)
                        except Exception:
                            pass

                    if init_file.name.lower().endswith(".csv"):
                        # Write the upload to a temp CSV file so DuckDB can read it
                        # directly from disk — avoids loading a large file into a
                        # pandas DataFrame (which can use 3-5× the raw file size in RAM)
                        _csv_tmp = os.path.join(
                            tempfile.gettempdir(),
                            f"bmc_upload_{uuid.uuid4().hex}.csv"
                        )
                        with open(_csv_tmp, "wb") as _cf:
                            _cf.write(init_file.read())

                        # Detect encoding: try UTF-8 first, fall back to latin-1.
                        # Files from Colombian/Spanish financial systems are often
                        # ISO-8859 / latin-1 (e.g. names with Ñ, á, é).
                        # DuckDB's sampling phase breaks on non-UTF-8 bytes and also
                        # misdetects the delimiter as a side-effect, so we normalise
                        # to UTF-8 first using 64 KB chunks (memory-efficient).
                        _src_enc = "utf-8"
                        for _enc in ("utf-8", "latin-1", "cp1252"):
                            try:
                                with open(_csv_tmp, "r", encoding=_enc, errors="strict") as _t:
                                    _t.read(65536)
                                _src_enc = _enc
                                break
                            except (UnicodeDecodeError, LookupError):
                                continue

                        if _src_enc != "utf-8":
                            _utf8_tmp = _csv_tmp + ".utf8.csv"
                            with open(_csv_tmp, "r", encoding=_src_enc, errors="replace") as _src, \
                                 open(_utf8_tmp, "w", encoding="utf-8") as _dst:
                                while True:
                                    _chunk = _src.read(65536)
                                    if not _chunk:
                                        break
                                    _dst.write(_chunk)
                            os.unlink(_csv_tmp)
                            _csv_tmp = _utf8_tmp

                        _csv_sql = _csv_tmp.replace("\\", "/")  # safe on Windows too
                        bootstrap_con = duckdb.connect(DB_PATH, read_only=False)
                        bootstrap_con.execute(
                            f"CREATE OR REPLACE TABLE operaciones_bmc AS "
                            f"SELECT * FROM read_csv_auto('{_csv_sql}', header=true)"
                        )
                        # Strip whitespace from column names
                        _cols = [r[0] for r in bootstrap_con.execute(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'operaciones_bmc' ORDER BY ordinal_position"
                        ).fetchall()]
                        for _col in _cols:
                            if _col != _col.strip():
                                bootstrap_con.execute(
                                    f'ALTER TABLE operaciones_bmc RENAME COLUMN '
                                    f'"{_col}" TO "{_col.strip()}"'
                                )
                        _created_rows = bootstrap_con.execute(
                            "SELECT COUNT(*) FROM operaciones_bmc"
                        ).fetchone()[0]
                        _created_cols = len(_cols)
                        bootstrap_con.close()

                    else:
                        # Excel files are typically small; pandas is fine here
                        init_df = pd.read_excel(init_file)
                        init_df.columns = init_df.columns.str.strip()
                        bootstrap_con = duckdb.connect(DB_PATH, read_only=False)
                        bootstrap_con.register("_init_data", init_df)
                        bootstrap_con.execute(
                            "CREATE OR REPLACE TABLE operaciones_bmc AS "
                            "SELECT * FROM _init_data"
                        )
                        _created_rows = len(init_df)
                        _created_cols = len(init_df.columns)
                        bootstrap_con.close()
                        del init_df  # free memory immediately

                except Exception as e:
                    # Reset temp path so the next attempt gets a fresh unique path
                    st.session_state.pop("db_temp_path", None)
                    st.error(f"❌ Error al crear la base de datos: {str(e)}")
                    st.caption("Intente subir el archivo nuevamente. Si el error persiste, verifique que el archivo no esté dañado.")
                    st.stop()
                finally:
                    # Always clean up the temporary CSV upload file
                    if _csv_tmp and os.path.exists(_csv_tmp):
                        try:
                            os.unlink(_csv_tmp)
                        except Exception:
                            pass

            # ── DB created — offer download before loading dashboard ──────────
            st.success(
                f"✅ Base de datos creada con **{_created_rows:,} registros** "
                f"y **{_created_cols} columnas**."
            )

            st.markdown("#### ⬇️ Guarde la base de datos en su PC")
            st.info(
                "**Importante:** Descargue este archivo y guárdelo en su computadora.\n\n"
                "La próxima vez que abra la app, suba el archivo **.db** (Opción 1) "
                "para restaurar su base de datos sin necesidad de re-subir el CSV."
            )

            with open(DB_PATH, "rb") as _dl_f:
                st.download_button(
                    label="⬇️ Descargar bmc_data.db (recomendado)",
                    data=_dl_f.read(),
                    file_name="bmc_data.db",
                    mime="application/octet-stream",
                    type="primary",
                    use_container_width=True,
                    help="Guarde este archivo en su PC para restaurarlo en futuras sesiones"
                )
            st.caption("💡 Al hacer clic en **Descargar**, el tablero también se cargará automáticamente.")
            st.stop()

        else:
            st.info(
                "💡 El archivo debe contener las columnas de operaciones del BMC "
                "(OPERACION, CLIENTE, COMISION, VALOR NEGOCIO, etc.).\n\n"
                "La base de datos se crea temporalmente en el servidor solo para esta sesión. "
                "**Descárguela a su PC** para guardarla de forma permanente."
            )
            st.stop()

@st.cache_resource
def get_connection(db_path):
    """Crea conexión de solo-lectura a la base de datos."""
    try:
        return duckdb.connect(db_path, read_only=True)
    except Exception:
        st.error("❌ No se pudo conectar a la base de datos. Intente resetear la sesión.")
        st.stop()

con = get_connection(DB_PATH)

# True when the referenciadores lookup table has been loaded
_ref_lookup_exists = False
try:
    con.execute("SELECT 1 FROM referenciadores LIMIT 0")
    _ref_lookup_exists = True
except Exception:
    pass

def safe_query(query, description="consulta", params=None):
    """Ejecuta consulta SQL con manejo de errores. params es una lista de valores para consultas parametrizadas."""
    try:
        if params:
            return con.execute(query, params).df()
        return con.execute(query).df()
    except Exception:
        st.error(f"❌ Error al cargar {description}.")
        return pd.DataFrame()

# Serialises all write operations so concurrent reruns never deadlock on the DB file
_db_write_lock = threading.Lock()

def upsert_to_db(db_path, new_df, existing_con=None):
    """
    Upsert (insert or update) records into operaciones_bmc.
    Records with an existing OPERACION value are updated; new ones are inserted.
    Returns (rows_affected, error_message).
    """
    with _db_write_lock:
        # Close the read-only connection BEFORE clearing cache so DuckDB allows
        # a write connection to the same file (DuckDB: one writer at a time).
        if existing_con is not None:
            try:
                existing_con.close()
            except Exception:
                pass
        get_connection.clear()

        write_con = None
        try:
            write_con = duckdb.connect(db_path, read_only=False)
            write_con.execute("BEGIN")

            # Discover columns that exist in the target table
            existing_cols = write_con.execute(
                "SELECT * FROM operaciones_bmc LIMIT 0"
            ).df().columns.tolist()

            # Keep only columns present in both the file and the table
            valid_cols = [c for c in new_df.columns if c in existing_cols]
            if not valid_cols:
                write_con.execute("ROLLBACK")
                return 0, "Ninguna columna del archivo coincide con la tabla. Verifique el formato."

            upload_df = new_df[valid_cols].copy()

            # Convert date/timestamp columns to proper datetime objects so DuckDB
            # doesn't reject strings like "2/01/2025" when inserting into DATE cols.
            date_cols = write_con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'operaciones_bmc' "
                "AND data_type IN ('DATE', 'TIMESTAMP', 'TIMESTAMP WITH TIME ZONE')"
            ).fetchdf()["column_name"].tolist()
            for col in date_cols:
                if col in upload_df.columns:
                    upload_df[col] = pd.to_datetime(
                        upload_df[col], dayfirst=True, errors="coerce"
                    )

            # Register the dataframe as a temporary view
            write_con.register("_staging", upload_df)

            if "OPERACION" in valid_cols:
                # Delete rows whose OPERACION already exists → replaced by incoming data
                existing_ops = write_con.execute(
                    "SELECT OPERACION FROM _staging WHERE OPERACION IN "
                    "(SELECT OPERACION FROM operaciones_bmc)"
                ).fetchdf()
                if not existing_ops.empty:
                    write_con.execute(
                        "DELETE FROM operaciones_bmc WHERE OPERACION IN "
                        "(SELECT OPERACION FROM _staging)"
                    )

            col_list = ", ".join(f'"{c}"' for c in valid_cols)
            write_con.execute(
                f"INSERT INTO operaciones_bmc ({col_list}) "
                f"SELECT {col_list} FROM _staging"
            )
            write_con.execute("COMMIT")
            write_con.execute("CHECKPOINT")
            write_con.unregister("_staging")
            return len(upload_df), None

        except Exception as e:
            try:
                if write_con:
                    write_con.execute("ROLLBACK")
            except Exception:
                pass
            return 0, str(e)
        finally:
            if write_con:
                write_con.close()

def load_referenciadores_to_db(db_path, df, existing_con=None):
    """
    Create or replace the referenciadores table from a DataFrame.
    Expected columns: CODIGO, IDENTIFICACIÓN, NOMBRE.
    Returns (rows_loaded, error_message).
    """
    with _db_write_lock:
        if existing_con is not None:
            try:
                existing_con.close()
            except Exception:
                pass
        get_connection.clear()

        write_con = None
        try:
            write_con = duckdb.connect(db_path, read_only=False)
            df = df.copy()
            # Strip accents and whitespace from column names so IDENTIFICACIÓN,
            # IDENTIFICACI�N (corrupted encoding), etc. all become IDENTIFICACION
            def _normalize_col(s):
                s = unicodedata.normalize("NFKD", str(s))
                s = s.encode("ascii", "ignore").decode("ascii")
                s = s.strip().upper()
                # Fixes IDENTIFICACIN (accent dropped by bad encoding) and any similar variant
                s = re.sub(r"\bIDENTIFICACI.?N\b", "IDENTIFICACION", s)
                return s
            df.columns = [_normalize_col(c) for c in df.columns]
            required = {"CODIGO", "IDENTIFICACION", "NOMBRE"}
            missing = required - set(df.columns)
            if missing:
                return 0, f"Faltan columnas requeridas: {', '.join(sorted(missing))}"
            df = df[["CODIGO", "IDENTIFICACION", "NOMBRE"]]
            df["CODIGO"] = pd.to_numeric(df["CODIGO"], errors="coerce").astype("Int64")
            df["IDENTIFICACION"] = df["IDENTIFICACION"].astype(str).str.strip()
            df["NOMBRE"] = df["NOMBRE"].astype(str).str.strip()
            write_con.register("_ref_staging", df)
            write_con.execute("""
                CREATE OR REPLACE TABLE referenciadores AS
                SELECT CODIGO, IDENTIFICACION, NOMBRE
                FROM _ref_staging
            """)
            write_con.unregister("_ref_staging")
            rows = write_con.execute("SELECT COUNT(*) FROM referenciadores").fetchone()[0]
            write_con.execute("CHECKPOINT")
            return rows, None
        except Exception as e:
            return 0, str(e)
        finally:
            if write_con:
                write_con.close()

# Panel Lateral con Filtros
st.sidebar.header("🔍 Filtrar Análisis")

if st.sidebar.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
    st.session_state.pop("password_correct", None)
    st.rerun()

if st.sidebar.button("🔄 Resetear Sesión", type="secondary", use_container_width=True,
                     help="Borra la base de datos de la sesión y vuelve a la pantalla de carga"):
    # Delete the temp DB file from the server if it exists
    _temp_path = st.session_state.get("db_temp_path")
    if _temp_path and os.path.exists(_temp_path):
        try:
            os.unlink(_temp_path)
        except Exception:
            pass
    # Clear all session state except login so the user returns to the load screen
    _keep = {"password_correct": st.session_state.get("password_correct")}
    st.session_state.clear()
    st.session_state.update(_keep)
    st.cache_resource.clear()
    st.rerun()

st.sidebar.markdown("---")

# Initialise filter keys to empty list on first load so no filters are pre-applied
for _key in ("filter_months", "filter_years", "filter_op_types"):
    if _key not in st.session_state:
        st.session_state[_key] = []

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
            key="filter_months",
            help="Filtrar datos por meses específicos. Sin selección = todos los meses."
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
            key="filter_years",
            help="Filtrar datos por años específicos. Sin selección = todos los años."
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
            key="filter_op_types",
            help="RSG: Sin incentivo, REX: Exportación, RGC: Con incentivo. Sin selección = todos los tipos."
        )
    else:
        selected_op_types = []
except Exception as e:
    selected_op_types = []

def _sql_str(val: str) -> str:
    """Escapes a string value for safe embedding in a SQL literal (doubles single quotes)."""
    return str(val).replace("'", "''")

def build_where_clause():
    """Construye la cláusula WHERE según los filtros seleccionados.
    Los valores de cadena se escapan con _sql_str para prevenir inyección SQL."""
    conditions = []

    if selected_months:
        month_list = "','".join(_sql_str(m) for m in selected_months)
        conditions.append(f"MES IN ('{month_list}')")

    if selected_years:
        # Cast to int — rejects any non-numeric value that could sneak in
        safe_years = []
        for y in selected_years:
            try:
                safe_years.append(int(y))
            except (ValueError, TypeError):
                pass
        if safe_years:
            year_list = ",".join(str(y) for y in safe_years)
            conditions.append(f"YEAR IN ({year_list})")

    if selected_op_types:
        op_list = "','".join(_sql_str(t) for t in selected_op_types)
        conditions.append(f"\"TIPO OPERACION\" IN ('{op_list}')")

    if conditions:
        return "WHERE " + " AND ".join(conditions)
    return ""

filter_query = build_where_clause()

# ── Sidebar: Actualizar Datos ──────────────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("📤 Actualizar Datos en BD", expanded=False):
    st.markdown("Suba un archivo **CSV o Excel** con nuevas operaciones.")
    st.caption(
        "El archivo debe tener el **mismo formato que el CSV original** "
        "(separador `;`, mismas columnas).\n\n"
        "• Registros con `OPERACION` existente → **actualizados**\n"
        "• Registros nuevos → **insertados**\n"
        "• Columnas no reconocidas son ignoradas."
    )

    # Show expected columns and offer a template download matching the DB format
    try:
        _db_cols = con.execute(
            "SELECT * FROM operaciones_bmc LIMIT 0"
        ).df().columns.tolist()
        with st.expander("📋 Formato requerido del CSV", expanded=False):
            st.caption("El archivo debe tener estas columnas (en cualquier orden):")
            st.code(", ".join(_db_cols), language=None)
            _template_csv = ",".join(_db_cols) + "\n"
            st.download_button(
                label="⬇️ Descargar plantilla CSV",
                data=_template_csv,
                file_name="plantilla_actualizacion.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_template_csv",
            )
    except Exception:
        pass

    upsert_file = st.file_uploader(
        "Seleccionar archivo",
        type=["csv", "xlsx", "xls"],
        key="upsert_file",
        label_visibility="collapsed"
    )

    if upsert_file is not None:
        try:
            if upsert_file.name.lower().endswith(".csv"):
                # sep=None + engine='python' auto-detects delimiter (comma, semicolon, tab, etc.)
                upload_df = pd.read_csv(upsert_file, sep=None, engine="python", encoding_errors="replace")
            else:
                upload_df = pd.read_excel(upsert_file)
            # Strip leading/trailing spaces from all column names
            upload_df.columns = upload_df.columns.str.strip()

            st.success(f"📊 **{len(upload_df):,} registros** listos para cargar")

            # Column match validation against DB
            try:
                _expected = con.execute(
                    "SELECT * FROM operaciones_bmc LIMIT 0"
                ).df().columns.tolist()
                _matched = [c for c in upload_df.columns if c in _expected]
                _missing = [c for c in _expected if c not in upload_df.columns]
                _extra = [c for c in upload_df.columns if c not in _expected]
                st.markdown(
                    f"Columnas coincidentes: **{len(_matched)}/{len(_expected)}**"
                )
                if _missing:
                    st.warning(f"Columnas faltantes (se dejarán vacías): `{', '.join(_missing)}`")
                if _extra:
                    st.caption(f"Columnas ignoradas: `{', '.join(_extra)}`")
            except Exception:
                st.markdown(f"Columnas detectadas: `{len(upload_df.columns)}`")

            with st.expander("🔍 Vista previa (5 filas)", expanded=False):
                st.dataframe(upload_df.head(5), width="stretch")

            if st.button("💾 Confirmar y Actualizar BD", type="primary", key="confirm_upsert", use_container_width=True):
                with st.spinner("Actualizando base de datos…"):
                    rows_affected, error = upsert_to_db(DB_PATH, upload_df, existing_con=con)
                if error:
                    st.error(f"❌ Error: {error}")
                else:
                    st.success(f"✅ {rows_affected:,} registros procesados")
                    st.info("🔄 Recargando tablero…")
                    st.cache_resource.clear()
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Error al leer archivo: {str(e)}")

# ── Sidebar: Cargar Referenciadores ───────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("👥 Cargar Referenciadores", expanded=False):
    st.markdown("Suba el archivo **CSV** con la tabla de referenciadores.")
    st.caption(
        "El archivo debe tener las columnas: **CODIGO**, **IDENTIFICACIÓN**, **NOMBRE**.\n\n"
        "• `CODIGO` es la clave que se relaciona con la columna `REFERENCIADOR` de las operaciones.\n"
        "• La tabla se reemplaza completamente cada vez que sube un archivo nuevo."
    )

    # Show current table row count if it exists
    try:
        _ref_count = con.execute("SELECT COUNT(*) FROM referenciadores").fetchone()[0]
        st.info(f"Tabla actual: **{_ref_count:,} referenciadores** cargados.")
    except Exception:
        st.warning("La tabla de referenciadores aún no existe.")

    ref_file = st.file_uploader(
        "Seleccionar archivo CSV de referenciadores",
        type=["csv", "xlsx", "xls"],
        key="ref_upload_file",
        label_visibility="collapsed",
    )

    # Show persistent result message from a previous upload (survives rerun)
    if st.session_state.get("ref_upload_result"):
        result = st.session_state.pop("ref_upload_result")
        if result["ok"]:
            st.success(f"✅ {result['rows']:,} referenciadores cargados correctamente.")
        else:
            st.error(f"❌ Error al cargar referenciadores: {result['error']}")

    if ref_file is not None:
        try:
            if ref_file.name.lower().endswith(".csv"):
                ref_df = pd.read_csv(ref_file, sep=None, engine="python", encoding_errors="replace")
            else:
                ref_df = pd.read_excel(ref_file)
            ref_df.columns = ref_df.columns.str.strip()
            st.success(f"📊 **{len(ref_df):,} filas** detectadas")
            with st.expander("🔍 Vista previa (5 filas)", expanded=False):
                st.dataframe(ref_df.head(5), use_container_width=True)
            if st.button("💾 Confirmar y Cargar Referenciadores", type="primary",
                         key="confirm_ref_upload", use_container_width=True):
                with st.spinner("Cargando referenciadores…"):
                    rows_loaded, error = load_referenciadores_to_db(DB_PATH, ref_df, existing_con=con)
                if error:
                    st.session_state["ref_upload_result"] = {"ok": False, "error": error}
                else:
                    st.session_state["ref_upload_result"] = {"ok": True, "rows": rows_loaded}
                    st.cache_resource.clear()
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error al leer archivo: {str(e)}")

# ── Sidebar: Descargar Base de Datos ──────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("⬇️ Descargar Base de Datos", expanded=False):
    st.markdown("Descargue el archivo **bmc_data.db** para guardarlo en su PC.")
    st.caption(
        "Guarde este archivo después de cada actualización de datos. "
        "En la próxima sesión, suba el **.db** en la pantalla de inicio "
        "para restaurar su base de datos sin re-subir el CSV."
    )
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as _sidebar_f:
            st.download_button(
                label="⬇️ Descargar bmc_data.db",
                data=_sidebar_f.read(),
                file_name="bmc_data.db",
                mime="application/octet-stream",
                use_container_width=True,
                key="sidebar_download_db",
                help="Guarde este archivo en su PC para restaurarlo en futuras sesiones"
            )
    else:
        st.warning("Base de datos no disponible en esta sesión.")

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

overview_query = f"""
    SELECT
        COUNT(DISTINCT CLIENTE) as unique_clients,
        COUNT(DISTINCT "NOMBRE PRODUCTO") as unique_products,
        SUM("VALOR NEGOCIO") as total_volume,
        SUM(COMISION) as total_commission,
        SUM(COMISION * ("% REF VENTA" / 100.0))
            + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
        COUNT(*) as total_ops,
        SUM(COMISION) / NULLIF(SUM("VALOR NEGOCIO"), 0) * 100 as avg_commission_rate
    FROM operaciones_bmc
    {filter_query}
"""

overview_data = safe_query(overview_query, "métricas de resumen")

if not overview_data.empty:
    _tc   = overview_data['total_commission'][0]
    _rc   = overview_data['ref_commission'][0]
    _nc   = _tc - _rc
    _tv   = overview_data['total_volume'][0]
    _cr   = overview_data['avg_commission_rate'][0]
    _cl   = int(overview_data['unique_clients'][0])
    _ops  = int(overview_data['total_ops'][0])

    def _kpi_card(label, value, tooltip):
        return f"""
        <div title="{tooltip}" style="
            background:#f8f9fa; border:1px solid #e0e0e0; border-radius:8px;
            padding:10px 8px; text-align:center; height:100%; cursor:default;">
          <div style="font-size:0.72rem; color:#555; font-weight:600;
                      line-height:1.3; margin-bottom:6px;">{label}</div>
          <div style="font-size:0.95rem; font-weight:700; color:#111;
                      word-break:break-all; line-height:1.3;">{value}</div>
        </div>"""

    _cards = [
        ("💰 Comisión Total",          f"${_tc:,.0f}",  "Suma bruta de todas las comisiones generadas. Fórmula: SUM(COMISION)"),
        ("🤝 Comisión Referenciador",  f"${_rc:,.0f}",  "Total pagado a referenciadores. Fórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)"),
        ("🏢 Comisión Empresa (Neta)", f"${_nc:,.0f}",  "Lo que retiene su empresa después de pagar referenciadores. Fórmula: Comisión Total − Comisión Referenciador"),
        ("📦 Volumen Negociado",       f"${_tv:,.0f}",  "Valor total de las operaciones procesadas. Fórmula: SUM(VALOR NEGOCIO)"),
        ("👥 Clientes Activos",        f"{_cl:,}",      "Clientes con al menos una operación en el período seleccionado. Fórmula: COUNT(DISTINCT CLIENTE)"),
        ("📈 Tasa Comisión",           f"{_cr:.2f}%",   "Porcentaje de comisión sobre el volumen total negociado. Fórmula: SUM(COMISION) / SUM(VALOR NEGOCIO) × 100"),
    ]
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    for _col, (_lbl, _val, _tip) in zip([k1, k2, k3, k4, k5, k6], _cards):
        _col.markdown(_kpi_card(_lbl, _val, _tip), unsafe_allow_html=True)

tabs = st.tabs([
    "📊 Desempeño",
    "💡 Estrategia",
    "🔗 Red Comercial",
    "👥 Clientes",
    "🔍 Operaciones",
    "🛡️ Riesgo",
])

# --- PESTAÑA 1: TABLERO DE DESEMPEÑO ---
with tabs[0]:
    
    col_left = st.container()
    col_right = st.container()
    
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
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                SUM(COMISION)
                    - SUM(COMISION * ("% REF VENTA" / 100.0))
                    - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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
                x=monthly_df['MES'], y=monthly_df['commission_earnings'],
                mode='lines+markers', name='Comisión Total',
                line=dict(color='#16A34A', width=3),
                marker=dict(size=8, color='#16A34A', line=dict(color='white', width=2)),
                fill='tozeroy', fillcolor='rgba(22,163,74,0.08)',
                hovertemplate='Comisión Total: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.add_trace(go.Scatter(
                x=monthly_df['MES'], y=monthly_df['ref_commission'],
                mode='lines+markers', name='Comisión Referenciador',
                line=dict(color='#F59E0B', width=2, dash='dot'),
                marker=dict(size=6, color='#F59E0B'),
                hovertemplate='Comisión Referenciador: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.add_trace(go.Scatter(
                x=monthly_df['MES'], y=monthly_df['net_commission'],
                mode='lines+markers', name='Comisión Empresa (Neta)',
                line=dict(color='#3B82F6', width=2, dash='dash'),
                marker=dict(size=6, color='#3B82F6'),
                hovertemplate='Comisión Empresa: $%{y:,.0f}<extra></extra>'
            ))
            fig_monthly.update_layout(
                title=dict(text="Comisiones por Mes — Total · Referenciador · Empresa", font=dict(size=15, color='#0f172a')),
                xaxis=dict(title="", showgrid=False, tickfont=dict(size=12)),
                yaxis=dict(title="Comisiones ($)", tickformat='$,.0f', gridcolor='#f1f5f9'),
                hovermode='x unified',
                margin=dict(l=60, r=20, t=50, b=40),
                height=380,
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            )
            st.plotly_chart(fig_monthly, width="stretch")
        else:
            st.info("No hay datos disponibles para la tendencia mensual")
    
    with col_right:
        st.subheader("🏆 Mejores Clientes por Comisión")
        st.caption("Los 10 clientes que más ingresos generan. El color identifica su referenciador.")

        if _ref_lookup_exists:
            clients_query = f"""
                SELECT
                    sub.CLIENTE,
                    sub.commission_earnings,
                    sub.ref_earnings,
                    sub.commission_earnings - sub.ref_earnings AS company_commission,
                    sub.transactions,
                    sub.transaction_volume,
                    sub.avg_commission_rate,
                    sub.main_referenciador,
                    COALESCE(r.NOMBRE, CAST(sub.main_referenciador AS VARCHAR)) AS nombre_ref
                FROM (
                    SELECT
                        CLIENTE,
                        SUM(COMISION) AS commission_earnings,
                        SUM(COMISION * ("% REF VENTA" / 100.0))
                            + SUM(COMISION * ("% REF COMPRA" / 100.0)) AS ref_earnings,
                        COUNT(*) AS transactions,
                        SUM("VALOR NEGOCIO") AS transaction_volume,
                        AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 AS avg_commission_rate,
                        mode(REFERENCIADOR) AS main_referenciador
                    FROM operaciones_bmc
                    {filter_query}
                    GROUP BY CLIENTE
                    ORDER BY commission_earnings DESC
                    LIMIT 10
                ) sub
                LEFT JOIN referenciadores r ON sub.main_referenciador = r.CODIGO
            """
        else:
            clients_query = f"""
                SELECT
                    CLIENTE,
                    SUM(COMISION) AS commission_earnings,
                    SUM(COMISION * ("% REF VENTA" / 100.0))
                        + SUM(COMISION * ("% REF COMPRA" / 100.0)) AS ref_earnings,
                    SUM(COMISION)
                        - SUM(COMISION * ("% REF VENTA" / 100.0))
                        - SUM(COMISION * ("% REF COMPRA" / 100.0)) AS company_commission,
                    COUNT(*) AS transactions,
                    SUM("VALOR NEGOCIO") AS transaction_volume,
                    AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 AS avg_commission_rate,
                    NULL AS main_referenciador,
                    NULL AS nombre_ref
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
            has_ref = _ref_lookup_exists and clients_df['nombre_ref'].notna().any()

            # ── Chart ──────────────────────────────────────────────────────────
            plot_df = clients_df.sort_values('commission_earnings', ascending=True).copy()

            if has_ref:
                fig_clients = px.bar(
                    plot_df,
                    x='commission_earnings',
                    y='CLIENTE',
                    orientation='h',
                    color='nombre_ref',
                    text='commission_earnings',
                    labels={
                        'commission_earnings': 'Comisión ($)',
                        'CLIENTE': '',
                        'nombre_ref': 'Referenciador',
                    },
                    color_discrete_sequence=px.colors.qualitative.Safe,
                )
            else:
                fig_clients = px.bar(
                    plot_df,
                    x='commission_earnings',
                    y='CLIENTE',
                    orientation='h',
                    text='commission_earnings',
                    color='commission_earnings',
                    color_continuous_scale='Greens',
                    labels={'commission_earnings': 'Comisión ($)', 'CLIENTE': ''},
                )
                fig_clients.update_coloraxes(showscale=False)

            fig_clients.update_traces(
                texttemplate='$%{text:,.0f}',
                textposition='outside',
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Comisión: $%{x:,.0f}<br>'
                    + ('Referenciador: %{customdata[2]}<br>' if has_ref else '')
                    + 'Operaciones: %{customdata[0]:,.0f}<br>'
                    'Tasa prom: %{customdata[1]:.2f}%<extra></extra>'
                ),
                customdata=plot_df[['transactions', 'avg_commission_rate', 'nombre_ref']]
                           if has_ref else
                           plot_df[['transactions', 'avg_commission_rate']],
            )
            fig_clients.update_layout(
                title=None,
                xaxis=dict(title='Comisión generada ($)', tickformat='$,.0f',
                           showgrid=True, gridcolor='#f1f5f9'),
                yaxis=dict(title='', tickfont=dict(size=12)),
                legend=dict(title='Referenciador', orientation='h',
                            yanchor='bottom', y=1.02, xanchor='left', x=0),
                margin=dict(l=10, r=120, t=40, b=40),
                height=420,
            )
            st.plotly_chart(fig_clients, width="stretch")

            # ── Ranked summary table ───────────────────────────────────────────
            table_df = clients_df.copy().reset_index(drop=True)
            table_df.insert(0, '#', range(1, len(table_df) + 1))
            for col in ('commission_earnings', 'ref_earnings', 'company_commission', 'transaction_volume'):
                if col in table_df.columns:
                    table_df[col] = table_df[col].apply(lambda v: f"${v:,.0f}" if pd.notna(v) else "$0")
            table_df['transactions']        = table_df['transactions'].apply(lambda v: f"{v:,.0f}")
            table_df['avg_commission_rate'] = table_df['avg_commission_rate'].apply(lambda v: f"{v:.2f}%")

            col_map = {
                '#': '#',
                'CLIENTE': 'Cliente',
                'nombre_ref': 'Referenciador',
                'commission_earnings': 'Comisión Total',
                'ref_earnings': 'Comisión Referenciador',
                'company_commission': 'Comisión Empresa',
                'transactions': 'Operaciones',
                'avg_commission_rate': 'Tasa Prom',
            }
            show_cols = ['#', 'CLIENTE', 'nombre_ref', 'commission_earnings',
                         'ref_earnings', 'company_commission',
                         'transactions', 'avg_commission_rate'] if has_ref else \
                        ['#', 'CLIENTE', 'commission_earnings',
                         'ref_earnings', 'company_commission',
                         'transactions', 'avg_commission_rate']
            table_df = table_df[show_cols].rename(columns=col_map)

            _cc = st.column_config
            col_cfg = {
                '#': _cc.NumberColumn(
                    '#',
                    help='Posición en el ranking. El #1 es el cliente que más comisión genera para su empresa.',
                    format='%d',
                ),
                'Cliente': _cc.TextColumn(
                    'Cliente',
                    help='Nombre del cliente registrado en las operaciones.',
                ),
                'Referenciador': _cc.TextColumn(
                    'Referenciador',
                    help='Referenciador que más operaciones aportó para este cliente '
                         '(calculado como la moda de REFERENCIADOR en sus operaciones).',
                ),
                'Comisión Total': _cc.TextColumn(
                    'Comisión Total',
                    help='Suma de todas las comisiones generadas por este cliente.\n'
                         'Fórmula: SUM(COMISION)',
                ),
                'Comisión Referenciador': _cc.TextColumn(
                    'Comisión Referenciador',
                    help='Monto que se paga al referenciador por las operaciones de este cliente.\n'
                         'Fórmula: SUM(COMISION × "% REF VENTA" / 100) + SUM(COMISION × "% REF COMPRA" / 100)',
                ),
                'Comisión Empresa': _cc.TextColumn(
                    'Comisión Empresa',
                    help='Lo que su empresa retiene después de pagar al referenciador.\n'
                         'Fórmula: Comisión Total − Comisión Referenciador',
                ),
                'Operaciones': _cc.TextColumn(
                    'Operaciones',
                    help='Número total de operaciones registradas para este cliente en el período seleccionado.',
                ),
                'Tasa Prom': _cc.TextColumn(
                    'Tasa Prom',
                    help='Tasa promedio de comisión cobrada sobre el valor de negocio.\n'
                         'Fórmula: AVG(COMISION / VALOR NEGOCIO) × 100',
                ),
            }
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                column_config={k: v for k, v in col_cfg.items() if k in table_df.columns},
            )

            # ── Referenciador breakdown (only when loaded) ─────────────────────
            if has_ref:
                ref_summary = (
                    clients_df.groupby('nombre_ref')
                    .agg(
                        clientes=('CLIENTE', 'count'),
                        comision_total=('commission_earnings', 'sum'),
                        comision_ref=('ref_earnings', 'sum'),
                        comision_empresa=('company_commission', 'sum'),
                    )
                    .sort_values('comision_total', ascending=False)
                    .reset_index()
                )
                st.markdown("**Aporte por referenciador — de estos 10 clientes**")
                st.caption(
                    "Cada tarjeta muestra cuánto retiene su empresa gracias a los clientes "
                    "que trajo ese referenciador. Pase el cursor sobre el ícono **?** para ver el detalle."
                )
                rcols = st.columns(min(len(ref_summary), 4))
                for i, row in ref_summary.iterrows():
                    with rcols[i % len(rcols)]:
                        st.metric(
                            label=row['nombre_ref'],
                            value=f"${row['comision_empresa']:,.0f}",
                            delta=f"Ref: ${row['comision_ref']:,.0f}  ·  {int(row['clientes'])} cliente{'s' if row['clientes'] > 1 else ''}",
                            help=(
                                f"**{row['nombre_ref']}**\n\n"
                                f"**Comisión Empresa** (valor principal)\n"
                                f"Lo que su empresa retiene después de pagar al referenciador.\n"
                                f"Fórmula: Comisión Total − Comisión Referenciador\n"
                                f"= ${row['comision_total']:,.0f} − ${row['comision_ref']:,.0f} "
                                f"= ${row['comision_empresa']:,.0f}\n\n"
                                f"**Comisión Referenciador** (flecha)\n"
                                f"Monto pagado al referenciador por sus clientes.\n"
                                f"Fórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)\n"
                                f"= ${row['comision_ref']:,.0f}\n\n"
                                f"**Comisión Total generada**\n"
                                f"Suma bruta de comisiones de sus {int(row['clientes'])} "
                                f"cliente{'s' if row['clientes'] > 1 else ''} en el top 10.\n"
                                f"= ${row['comision_total']:,.0f}"
                            ),
                        )
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
    
    col_ref1 = st.container()
    col_ref2 = st.container()
    
    with col_ref1:
        referenciador_where = filter_query + (" AND " if filter_query else "WHERE ") + "REFERENCIADOR IS NOT NULL AND REFERENCIADOR != 0"

        if _ref_lookup_exists:
            referenciador_query = f"""
                SELECT sub.REFERENCIADOR,
                    COALESCE(r.NOMBRE, CAST(sub.REFERENCIADOR AS VARCHAR)) AS NOMBRE_REF,
                    sub.total_operations, sub.total_commission, sub.total_volume,
                    sub.avg_commission_per_op, sub.referenciador_earnings
                FROM (
                    SELECT REFERENCIADOR,
                        COUNT(*) as total_operations,
                        SUM(COMISION) as total_commission,
                        SUM("VALOR NEGOCIO") as total_volume,
                        AVG(COMISION) as avg_commission_per_op,
                        SUM(COMISION * ("% REF VENTA" / 100.0))
                            + SUM(COMISION * ("% REF COMPRA" / 100.0)) as referenciador_earnings
                    FROM operaciones_bmc
                    {referenciador_where}
                    GROUP BY REFERENCIADOR
                ) sub
                LEFT JOIN referenciadores r ON sub.REFERENCIADOR = r.CODIGO
                ORDER BY sub.total_commission DESC
            """
        else:
            referenciador_query = f"""
                SELECT
                    CAST(REFERENCIADOR AS VARCHAR) AS NOMBRE_REF,
                    COUNT(*) as total_operations,
                    SUM(COMISION) as total_commission,
                    SUM("VALOR NEGOCIO") as total_volume,
                    AVG(COMISION) as avg_commission_per_op,
                    SUM(COMISION * ("% REF VENTA" / 100.0))
                        + SUM(COMISION * ("% REF COMPRA" / 100.0)) as referenciador_earnings
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

            fig_ref = go.Figure()
            fig_ref.add_trace(go.Bar(
                x=top_10_ref_df['NOMBRE_REF'],
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
                hovertemplate='<b>%{x}</b><br>' +
                             'Comisión Total: $%{y:,.0f}<br>' +
                             'Volumen Total: $%{customdata[4]:,.0f}<br>' +
                             'Operaciones: %{customdata[0]:,.0f}<br>' +
                             'Prom por Op: $%{customdata[1]:,.0f}<br>' +
                             'Ganancias Referenciador: $%{customdata[2]:,.0f}<br>' +
                             'Código: %{customdata[3]}<extra></extra>',
                customdata=top_10_ref_df[['total_operations', 'avg_commission_per_op', 'referenciador_earnings', 'REFERENCIADOR', 'total_volume']]
            ))

            fig_ref.update_layout(
                title={
                    'text': "Top 10 Referenciadores por Comisión Generada",
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis_title="Referenciador",
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
            display_df = display_df[['REFERENCIADOR', 'NOMBRE_REF', 'total_operations',
                                     'total_commission', 'total_volume', 'referenciador_earnings']]
            display_df = display_df.rename(columns={'NOMBRE_REF': 'Nombre', 'REFERENCIADOR': 'Código'})

            # Pre-format so column_config tooltips can be added
            display_df['total_operations']      = display_df['total_operations'].apply(lambda v: f"{v:,.0f}")
            display_df['total_commission']       = display_df['total_commission'].apply(lambda v: f"${v:,.0f}")
            display_df['total_volume']           = display_df['total_volume'].apply(lambda v: f"${v:,.0f}")
            display_df['referenciador_earnings'] = display_df['referenciador_earnings'].apply(lambda v: f"${v:,.0f}")

            _cc = st.column_config
            st.dataframe(
                display_df,
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    'Código': _cc.TextColumn(
                        'Código',
                        help='Código interno que identifica al referenciador en el sistema.',
                    ),
                    'Nombre': _cc.TextColumn(
                        'Referenciador',
                        help='Nombre o razón social del referenciador.',
                    ),
                    'total_operations': _cc.TextColumn(
                        'Operaciones',
                        help='Número total de operaciones en las que participó este referenciador '
                             'dentro del período filtrado.\n'
                             'Fórmula: COUNT(*)',
                    ),
                    'total_commission': _cc.TextColumn(
                        'Comisión Total',
                        help='Suma de todas las comisiones generadas en las operaciones '
                             'donde este referenciador participó.\n'
                             'Fórmula: SUM(COMISION)',
                    ),
                    'total_volume': _cc.TextColumn(
                        'Volumen Total',
                        help='Valor total de negocio (monto operado) en las operaciones '
                             'asociadas a este referenciador.\n'
                             'Fórmula: SUM(VALOR NEGOCIO)',
                    ),
                    'referenciador_earnings': _cc.TextColumn(
                        'Ganancia Referenciador',
                        help='Estimación de lo que su empresa paga a este referenciador '
                             'por concepto de comisión sobre ventas y compras.\n'
                             'Fórmula: SUM(COMISION × "% REF VENTA" / 100) '
                             '+ SUM(COMISION × "% REF COMPRA" / 100)',
                    ),
                },
            )

            total_commission = referenciador_df['total_commission'].sum()
            total_earnings   = referenciador_df['referenciador_earnings'].sum()

            st.info(
                f"📊 **Resumen:** {len(referenciador_df)} referenciadores · "
                f"Comisión total: ${total_commission:,.0f} · "
                f"Pagado a referenciadores: ${total_earnings:,.0f}"
            )
        else:
            st.info("No hay datos de referenciadores disponibles")

    # Pivot by referenciador name
    st.markdown("---")
    st.subheader("📋 Pivot por Nombre de Referenciador")
    st.caption("Agrupa todos los códigos que comparten el mismo nombre en una sola fila.")

    if not referenciador_df.empty and _ref_lookup_exists:
        pivot_df = referenciador_df.copy()
        pivot_df['REFERENCIADOR'] = pivot_df['REFERENCIADOR'].astype(str)

        pivot_grouped = (
            pivot_df
            .groupby('NOMBRE_REF', sort=False)
            .agg(
                Códigos=('REFERENCIADOR', lambda x: ', '.join(sorted(x.unique()))),
                total_commission=('total_commission', 'sum'),
                referenciador_earnings=('referenciador_earnings', 'sum'),
                total_volume=('total_volume', 'sum'),
                total_operations=('total_operations', 'sum'),
            )
            .reset_index()
            .sort_values('total_commission', ascending=False)
            .rename(columns={'NOMBRE_REF': 'Nombre'})
        )

        pivot_display = pivot_grouped.copy()
        pivot_display['total_commission']       = pivot_display['total_commission'].apply(lambda v: f"${v:,.0f}")
        pivot_display['referenciador_earnings'] = pivot_display['referenciador_earnings'].apply(lambda v: f"${v:,.0f}")
        pivot_display['total_volume']           = pivot_display['total_volume'].apply(lambda v: f"${v:,.0f}")
        pivot_display['total_operations']       = pivot_display['total_operations'].apply(lambda v: f"{v:,.0f}")

        _cc2 = st.column_config
        st.dataframe(
            pivot_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Nombre': _cc2.TextColumn(
                    'Referenciador',
                    help='Nombre o razón social del referenciador.',
                ),
                'Códigos': _cc2.TextColumn(
                    'Código(s)',
                    help='Código(s) asociados a este nombre. Si hay más de uno, están separados por coma.',
                ),
                'total_commission': _cc2.TextColumn(
                    'Comisión Total',
                    help='Suma de comisiones generadas por todas las operaciones de este referenciador.\n'
                         'Fórmula: SUM(COMISION)',
                ),
                'referenciador_earnings': _cc2.TextColumn(
                    'Comisión Referenciador',
                    help='Estimación de lo que su empresa paga al referenciador.\n'
                         'Fórmula: SUM(COMISION × "% REF VENTA" / 100) + SUM(COMISION × "% REF COMPRA" / 100)',
                ),
                'total_volume': _cc2.TextColumn(
                    'Volumen Total',
                    help='Valor total de negocio operado.\n'
                         'Fórmula: SUM(VALOR NEGOCIO)',
                ),
                'total_operations': _cc2.TextColumn(
                    'Operaciones',
                    help='Número total de operaciones asociadas a este referenciador.\n'
                         'Fórmula: COUNT(*)',
                ),
            },
        )
    elif not _ref_lookup_exists:
        st.info("Cargue el archivo de referenciadores para ver esta tabla.")
    else:
        st.info("No hay datos de referenciadores disponibles.")

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
    
    col_prod1 = st.container()
    col_prod2 = st.container()
    
    with col_prod1:
        products_query = f"""
            SELECT
                "NOMBRE PRODUCTO",
                SUM(COMISION) as commission_earnings,
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                SUM(COMISION)
                    - SUM(COMISION * ("% REF VENTA" / 100.0))
                    - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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
                labels={'avg_commission_rate': 'Tasa Comisión Prom %'},
                custom_data=['ref_commission', 'net_commission']
            )
            fig_products.update_traces(
                hovertemplate='<b>%{label}</b><br>'
                              'Comisión Total: $%{value:,.0f}<br>'
                              'Comisión Referenciador: $%{customdata[0]:,.0f}<br>'
                              'Comisión Empresa: $%{customdata[1]:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_products, width="stretch")
        else:
            st.info("No hay datos de productos disponibles")

    with col_prod2:
        if not products_df.empty:
            prod_display = products_df.copy()
            prod_display['commission_earnings'] = prod_display['commission_earnings'].apply(lambda v: f"${v:,.0f}")
            prod_display['ref_commission']       = prod_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            prod_display['net_commission']       = prod_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            prod_display['volume']               = prod_display['volume'].apply(lambda v: f"${v:,.0f}")
            prod_display['transactions']         = prod_display['transactions'].apply(lambda v: f"{v:,.0f}")
            prod_display['avg_commission_rate']  = prod_display['avg_commission_rate'].apply(lambda v: f"{v:.2f}%")
            st.dataframe(
                prod_display,
                use_container_width=True, hide_index=True, height=400,
                column_config={
                    'NOMBRE PRODUCTO':      st.column_config.TextColumn('Producto', help='Nombre del producto agrícola negociado (maíz, café, arroz, etc.).'),
                    'commission_earnings':  st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones generadas por operaciones de este producto.\nFórmula: SUM(COMISION)'),
                    'ref_commission':       st.column_config.TextColumn('Comisión Referenciador', help='Total pagado a referenciadores por operaciones de este producto.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                    'net_commission':       st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa después de pagar referenciadores, para este producto.\nFórmula: Comisión Total − Comisión Referenciador'),
                    'volume':               st.column_config.TextColumn('Volumen', help='Valor total de negocio operado en este producto.\nFórmula: SUM("VALOR NEGOCIO")'),
                    'transactions':         st.column_config.TextColumn('Operaciones', help='Número de operaciones registradas para este producto.\nFórmula: COUNT(*)'),
                    'avg_commission_rate':  st.column_config.TextColumn('Tasa Prom %', help='Porcentaje promedio de comisión sobre el valor de negocio para este producto.\nFórmula: AVG(COMISION / "VALOR NEGOCIO") × 100'),
                },
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
    
    col_strat1 = st.container()
    col_strat2 = st.container()
    
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
        
        if _ref_lookup_exists:
            churn_query = f"""
                SELECT
                    sub.CLIENTE,
                    sub.last_transaction,
                    sub.days_inactive,
                    sub.lifetime_commission,
                    sub.ref_commission,
                    sub.lifetime_commission - sub.ref_commission AS net_commission,
                    sub.total_transactions,
                    COALESCE(r.NOMBRE, CAST(sub.main_referenciador AS VARCHAR)) AS referenciador
                FROM (
                    SELECT
                        CLIENTE,
                        MAX("FECHA REGISTRO") as last_transaction,
                        DATE_DIFF('day', MAX(TRY_CAST("FECHA REGISTRO" AS DATE)), CURRENT_DATE) as days_inactive,
                        SUM(COMISION) as lifetime_commission,
                        SUM(COMISION * ("% REF VENTA" / 100.0))
                            + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                        COUNT(*) as total_transactions,
                        mode(REFERENCIADOR) as main_referenciador
                    FROM operaciones_bmc
                    {filter_query}
                    GROUP BY CLIENTE
                    HAVING DATE_DIFF('day', MAX(TRY_CAST("FECHA REGISTRO" AS DATE)), CURRENT_DATE) > 60
                    ORDER BY lifetime_commission DESC
                    LIMIT 15
                ) sub
                LEFT JOIN referenciadores r ON sub.main_referenciador = r.CODIGO
            """
        else:
            churn_query = f"""
                SELECT
                    CLIENTE,
                    MAX("FECHA REGISTRO") as last_transaction,
                    DATE_DIFF('day', MAX(TRY_CAST("FECHA REGISTRO" AS DATE)), CURRENT_DATE) as days_inactive,
                    SUM(COMISION) as lifetime_commission,
                    SUM(COMISION * ("% REF VENTA" / 100.0))
                        + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                    SUM(COMISION)
                        - SUM(COMISION * ("% REF VENTA" / 100.0))
                        - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
                    COUNT(*) as total_transactions
                FROM operaciones_bmc
                {filter_query}
                GROUP BY CLIENTE
                HAVING DATE_DIFF('day', MAX(TRY_CAST("FECHA REGISTRO" AS DATE)), CURRENT_DATE) > 60
                ORDER BY lifetime_commission DESC
                LIMIT 15
            """

        with st.expander("🔍 Ver Consulta SQL", expanded=False):
            st.code(churn_query, language="sql")

        churn_df = safe_query(churn_query, "análisis de fuga")

        if not churn_df.empty:
            churn_display = churn_df.copy()
            churn_display['days_inactive']      = churn_display['days_inactive'].apply(lambda v: f"{v:.0f}")
            churn_display['lifetime_commission'] = churn_display['lifetime_commission'].apply(lambda v: f"${v:,.0f}")
            churn_display['ref_commission']      = churn_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            churn_display['net_commission']      = churn_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            churn_display['total_transactions']  = churn_display['total_transactions'].apply(lambda v: f"{v:,.0f}")

            churn_col_config = {
                'CLIENTE': st.column_config.TextColumn('Cliente', help='Nombre del cliente registrado en las operaciones.'),
                'last_transaction': st.column_config.TextColumn('Última Operación', help='Fecha de la última operación registrada para este cliente.'),
                'days_inactive': st.column_config.TextColumn('Días Inactivo', help='Días transcurridos desde la última operación hasta hoy.'),
                'lifetime_commission': st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones históricas.\nFórmula: SUM(COMISION)'),
                'ref_commission': st.column_config.TextColumn('Comisión Referenciador', help='Lo pagado al referenciador en comisiones.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                'net_commission': st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa.\nFórmula: Comisión Total − Comisión Referenciador'),
                'total_transactions': st.column_config.TextColumn('Operaciones', help='Número total de operaciones históricas del cliente.\nFórmula: COUNT(*)'),
            }
            if _ref_lookup_exists and 'referenciador' in churn_display.columns:
                churn_col_config['referenciador'] = st.column_config.TextColumn(
                    'Referenciador',
                    help='Referenciador responsable de la mayoría de las operaciones de este cliente.',
                )

            st.dataframe(churn_display, use_container_width=True, hide_index=True, column_config=churn_col_config)
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
            cross_sell_display = cross_sell_df.copy()
            cross_sell_display['shared_clients'] = cross_sell_display['shared_clients'].apply(lambda x: f'{int(x):,}')
            cross_sell_display['market_penetration'] = cross_sell_display['market_penetration'].apply(lambda x: f'{x:.2f}%')
            st.dataframe(
                cross_sell_display,
                width="stretch",
                hide_index=True,
                column_config={
                    'product_a': st.column_config.TextColumn('Producto A', help='Primer producto del par de venta cruzada. Los pares están ordenados alfabéticamente para evitar duplicados.'),
                    'product_b': st.column_config.TextColumn('Producto B', help='Segundo producto del par. Clientes que operan este producto también operan Producto A.'),
                    'shared_clients': st.column_config.TextColumn('Clientes Compartidos', help='Número de clientes distintos que han operado ambos productos en el período filtrado.\nFórmula: COUNT(DISTINCT cliente) — solo pares con ≥ 3 clientes compartidos'),
                    'market_penetration': st.column_config.TextColumn('Penetración de Mercado', help='Porcentaje de sus clientes totales que han operado ambos productos. Indica qué tan común es este par.\nFórmula: (Clientes Compartidos / Total Clientes) × 100'),
                }
            )
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
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
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
            SUM(ref_commission) as segment_ref_commission,
            SUM(total_commission) - SUM(ref_commission) as segment_net_commission,
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
        col_seg1 = st.container()
        col_seg2 = st.container()

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
                hovertemplate='<b>%{label}</b><br>Clientes: %{value}<br>'
                              'Comisión Total: $%{customdata[0]:,.0f}<br>'
                              'Comisión Ref.: $%{customdata[1]:,.0f}<br>'
                              'Comisión Empresa: $%{customdata[2]:,.0f}<extra></extra>',
                customdata=segment_df[['segment_commission', 'segment_ref_commission', 'segment_net_commission']]
            )
            st.plotly_chart(fig_segment, width="stretch")
            st.caption("📊 Distribución de clientes por segmento de valor")

        with col_seg2:
            fig_commission = go.Figure()
            fig_commission.add_trace(go.Bar(
                name='Comisión Empresa', x=segment_df['segment'], y=segment_df['segment_net_commission'],
                marker_color='#16A34A', text=segment_df['segment_net_commission'],
                texttemplate='$%{text:,.0f}', textposition='inside'
            ))
            fig_commission.add_trace(go.Bar(
                name='Comisión Referenciador', x=segment_df['segment'], y=segment_df['segment_ref_commission'],
                marker_color='#F59E0B', text=segment_df['segment_ref_commission'],
                texttemplate='$%{text:,.0f}', textposition='inside'
            ))
            fig_commission.update_layout(
                barmode='stack', title='Comisión por Segmento — Total · Ref · Empresa',
                xaxis_title='Segmento', yaxis=dict(title='Comisión ($)', tickformat='$,.0f'),
                height=380, margin=dict(l=60, r=20, t=50, b=40),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            )
            st.plotly_chart(fig_commission, width="stretch")
            st.caption("💰 Cuánto le paga en comisiones cada segmento")

        st.markdown("**Desglose Detallado por Segmento**")
        seg_display = segment_df.copy()
        seg_display['segment_commission']     = seg_display['segment_commission'].apply(lambda v: f"${v:,.0f}")
        seg_display['segment_ref_commission'] = seg_display['segment_ref_commission'].apply(lambda v: f"${v:,.0f}")
        seg_display['segment_net_commission'] = seg_display['segment_net_commission'].apply(lambda v: f"${v:,.0f}")
        seg_display['client_count']           = seg_display['client_count'].apply(lambda v: f"{v:,.0f}")
        seg_display['avg_transactions']       = seg_display['avg_transactions'].apply(lambda v: f"{v:,.1f}")
        seg_display['avg_commission_per_deal']= seg_display['avg_commission_per_deal'].apply(lambda v: f"${v:,.0f}")
        st.dataframe(
            seg_display,
            use_container_width=True, hide_index=True,
            column_config={
                'segment':                  st.column_config.TextColumn('Segmento', help='Categoría de valor del cliente basada en el percentil de comisiones generadas:\n• VIP (Top 20%): Los que más comisiones aportan\n• Alto Valor (50–80%): Buenos generadores de comisión\n• Valor Medio (20–50%): Aportadores moderados\n• Bajo Valor (inferior 20%): Clientes nuevos u ocasionales'),
                'client_count':             st.column_config.TextColumn('Clientes', help='Número de clientes en este segmento.\nFórmula: COUNT(DISTINCT CLIENTE)'),
                'segment_commission':       st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones generadas por todos los clientes de este segmento.\nFórmula: SUM(COMISION)'),
                'segment_ref_commission':   st.column_config.TextColumn('Comisión Referenciador', help='Total pagado a referenciadores por clientes de este segmento.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                'segment_net_commission':   st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa después de pagar referenciadores, para este segmento.\nFórmula: Comisión Total − Comisión Referenciador'),
                'avg_transactions':         st.column_config.TextColumn('Transacc. Prom.', help='Número promedio de transacciones por cliente en este segmento.\nFórmula: AVG(COUNT(*) por CLIENTE)'),
                'avg_commission_per_deal':  st.column_config.TextColumn('Comisión Prom/Op', help='Comisión promedio por operación para clientes de este segmento.\nFórmula: AVG(COMISION) por operación dentro del segmento'),
            },
        )
        
        vip_commission = segment_df[segment_df['segment'] == 'VIP (Top 20%)']['segment_commission'].sum()
        total_commission = segment_df['segment_commission'].sum()
        vip_percentage = (vip_commission / total_commission * 100) if total_commission > 0 else 0

        st.info(f"💎 **Perspectiva VIP:** Su top 20% de clientes genera **${vip_commission:,.0f}** ({vip_percentage:.1f}%) de sus comisiones totales!")

        # ── Detailed per-client report ─────────────────────────────────────────
        with st.expander("📋 Ver Informe Detallado por Cliente", expanded=False):
            if _ref_lookup_exists:
                detail_query = f"""
                    WITH client_stats AS (
                        SELECT
                            CLIENTE,
                            mode(REFERENCIADOR) AS main_ref,
                            SUM(COMISION) AS total_commission,
                            SUM(COMISION * ("% REF VENTA" / 100.0))
                                + SUM(COMISION * ("% REF COMPRA" / 100.0)) AS ref_commission,
                            COUNT(*) AS transaction_count,
                            SUM("VALOR NEGOCIO") AS total_volume
                        FROM operaciones_bmc
                        {filter_query}
                        GROUP BY CLIENTE
                    ),
                    pcts AS (
                        SELECT
                            PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_commission) AS p80,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_commission) AS p50,
                            PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY total_commission) AS p20
                        FROM client_stats
                    )
                    SELECT
                        CASE
                            WHEN cs.total_commission >= p.p80 THEN 'VIP (Top 20%)'
                            WHEN cs.total_commission >= p.p50 THEN 'Alto Valor (50-80%)'
                            WHEN cs.total_commission >= p.p20 THEN 'Valor Medio (20-50%)'
                            ELSE 'Bajo Valor (Inferior 20%)'
                        END AS segment,
                        cs.CLIENTE,
                        COALESCE(r.NOMBRE, CAST(cs.main_ref AS VARCHAR)) AS nombre_ref,
                        cs.total_commission,
                        cs.ref_commission,
                        cs.total_commission - cs.ref_commission AS net_commission,
                        cs.transaction_count,
                        cs.total_volume
                    FROM client_stats cs
                    CROSS JOIN pcts p
                    LEFT JOIN referenciadores r ON cs.main_ref = r.CODIGO
                    ORDER BY cs.total_commission DESC
                """
            else:
                detail_query = f"""
                    WITH client_stats AS (
                        SELECT
                            CLIENTE,
                            SUM(COMISION) AS total_commission,
                            SUM(COMISION * ("% REF VENTA" / 100.0))
                                + SUM(COMISION * ("% REF COMPRA" / 100.0)) AS ref_commission,
                            COUNT(*) AS transaction_count,
                            SUM("VALOR NEGOCIO") AS total_volume
                        FROM operaciones_bmc
                        {filter_query}
                        GROUP BY CLIENTE
                    ),
                    pcts AS (
                        SELECT
                            PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_commission) AS p80,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_commission) AS p50,
                            PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY total_commission) AS p20
                        FROM client_stats
                    )
                    SELECT
                        CASE
                            WHEN cs.total_commission >= p.p80 THEN 'VIP (Top 20%)'
                            WHEN cs.total_commission >= p.p50 THEN 'Alto Valor (50-80%)'
                            WHEN cs.total_commission >= p.p20 THEN 'Valor Medio (20-50%)'
                            ELSE 'Bajo Valor (Inferior 20%)'
                        END AS segment,
                        cs.CLIENTE,
                        cs.total_commission,
                        cs.ref_commission,
                        cs.total_commission - cs.ref_commission AS net_commission,
                        cs.transaction_count,
                        cs.total_volume
                    FROM client_stats cs
                    CROSS JOIN pcts p
                    ORDER BY cs.total_commission DESC
                """

            segment_order = ['VIP (Top 20%)', 'Alto Valor (50-80%)', 'Valor Medio (20-50%)', 'Bajo Valor (Inferior 20%)']
            selected_segment = st.selectbox(
                "Seleccionar segmento",
                options=segment_order,
                key="segment_detail_filter",
            )

            _seg_filter_map = {
                'VIP (Top 20%)':           'cs.total_commission >= p.p80',
                'Alto Valor (50-80%)':     'cs.total_commission >= p.p50 AND cs.total_commission < p.p80',
                'Valor Medio (20-50%)':    'cs.total_commission >= p.p20 AND cs.total_commission < p.p50',
                'Bajo Valor (Inferior 20%)': 'cs.total_commission < p.p20',
            }
            _seg_where = _seg_filter_map[selected_segment]

            if _ref_lookup_exists:
                detail_query = detail_query.replace(
                    "ORDER BY cs.total_commission DESC",
                    f"WHERE {_seg_where}\n                    ORDER BY cs.total_commission DESC"
                )
            else:
                detail_query = detail_query.replace(
                    "ORDER BY cs.total_commission DESC",
                    f"WHERE {_seg_where}\n                    ORDER BY cs.total_commission DESC"
                )

            detail_df = safe_query(detail_query, "detalle clientes por segmento")

            if not detail_df.empty:
                st.caption(f"Mostrando {len(detail_df)} cliente(s) en **{selected_segment}**")

                det_display = detail_df.copy()
                det_display['total_commission']   = det_display['total_commission'].apply(lambda v: f"${v:,.0f}")
                det_display['ref_commission']     = det_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
                det_display['net_commission']     = det_display['net_commission'].apply(lambda v: f"${v:,.0f}")
                det_display['transaction_count']  = det_display['transaction_count'].apply(lambda v: f"{int(v):,}")
                det_display['total_volume']       = det_display['total_volume'].apply(lambda v: f"${v:,.0f}")

                _seg_colors = {
                    'VIP (Top 20%)': '🥇',
                    'Alto Valor (50-80%)': '🥈',
                    'Valor Medio (20-50%)': '🥉',
                    'Bajo Valor (Inferior 20%)': '▪️',
                }
                det_display['segment'] = det_display['segment'].apply(lambda s: f"{_seg_colors.get(s, '')} {s}")

                det_col_config = {
                    'segment':          st.column_config.TextColumn('Segmento', help='Categoría asignada según el percentil de comisión total del cliente dentro del período filtrado.'),
                    'CLIENTE':          st.column_config.TextColumn('Cliente', help='Nombre del cliente registrado en las operaciones.'),
                    'total_commission': st.column_config.TextColumn('Comisión Total', help='Suma de todas las comisiones brutas generadas por este cliente.\nFórmula: SUM(COMISION)'),
                    'ref_commission':   st.column_config.TextColumn('Comisión Referenciador', help='Monto pagado al referenciador por operaciones de este cliente.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                    'net_commission':   st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa después de pagar al referenciador.\nFórmula: Comisión Total − Comisión Referenciador'),
                    'transaction_count': st.column_config.TextColumn('Operaciones', help='Número de operaciones del cliente en el período.\nFórmula: COUNT(*)'),
                    'total_volume':     st.column_config.TextColumn('Volumen', help='Valor total de negocio operado por este cliente.\nFórmula: SUM("VALOR NEGOCIO")'),
                }
                if _ref_lookup_exists and 'nombre_ref' in det_display.columns:
                    det_col_config['nombre_ref'] = st.column_config.TextColumn(
                        'Referenciador',
                        help='Referenciador más frecuente en las operaciones de este cliente (moda estadística de REFERENCIADOR).',
                    )
                    show_det_cols = ['segment', 'CLIENTE', 'nombre_ref', 'total_commission', 'ref_commission', 'net_commission', 'transaction_count', 'total_volume']
                else:
                    show_det_cols = ['segment', 'CLIENTE', 'total_commission', 'ref_commission', 'net_commission', 'transaction_count', 'total_volume']

                st.dataframe(
                    det_display[show_det_cols],
                    use_container_width=True,
                    hide_index=True,
                    height=500,
                    column_config=det_col_config,
                )
            else:
                st.info("No hay datos de clientes para mostrar.")

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
    
    col_net1 = st.container()
    col_net2 = st.container()
    
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

        if _ref_lookup_exists:
            seller_hub_query = f"""
                SELECT sub.seller, sub.unique_buyers, sub.total_commission,
                       sub.ref_commission,
                       sub.total_commission - sub.ref_commission AS net_commission,
                       sub.total_transactions, sub.total_volume,
                       COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref
                FROM (
                    SELECT "NOMBRE VENDEDOR" as seller,
                           COUNT(DISTINCT "NIT COMPRADOR") as unique_buyers,
                           SUM(COMISION) as total_commission,
                           SUM(COMISION * ("% REF VENTA" / 100.0))
                               + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                           COUNT(*) as total_transactions,
                           SUM("VALOR NEGOCIO") as total_volume,
                           mode(REFERENCIADOR) as main_ref
                    FROM operaciones_bmc
                    {seller_hub_where}
                    GROUP BY "NOMBRE VENDEDOR"
                    HAVING COUNT(DISTINCT "NIT COMPRADOR") >= 2
                    ORDER BY unique_buyers DESC, total_commission DESC
                    LIMIT 10
                ) sub
                LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
            """
        else:
            seller_hub_query = f"""
                SELECT "NOMBRE VENDEDOR" as seller,
                       COUNT(DISTINCT "NIT COMPRADOR") as unique_buyers,
                       SUM(COMISION) as total_commission,
                       SUM(COMISION * ("% REF VENTA" / 100.0))
                           + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                       SUM(COMISION)
                           - SUM(COMISION * ("% REF VENTA" / 100.0))
                           - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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

            _sh_has_ref = 'nombre_ref' in seller_hubs_df.columns
            _sh_cd_cols = ['total_commission', 'ref_commission', 'net_commission', 'total_transactions']
            if _sh_has_ref:
                _sh_cd_cols.append('nombre_ref')
            fig_seller_hub = go.Figure()
            fig_seller_hub.add_trace(go.Bar(
                x=seller_hubs_df['unique_buyers'],
                y=seller_hubs_df['seller'],
                orientation='h',
                marker=dict(color=seller_hubs_df['total_commission'], colorscale='Oranges', showscale=False),
                customdata=seller_hubs_df[_sh_cd_cols].values,
                hovertemplate=(
                    '<b>%{y}</b><br>Compradores Únicos: %{x}<br>'
                    'Comisión Total: $%{customdata[0]:,.0f}<br>'
                    'Comisión Ref.: $%{customdata[1]:,.0f}<br>'
                    'Comisión Empresa: $%{customdata[2]:,.0f}<br>'
                    'Transacciones: %{customdata[3]:,.0f}<br>'
                    + ('Referenciador: %{customdata[4]}<extra></extra>' if _sh_has_ref else '<extra></extra>')
                ),
            ))
            fig_seller_hub.update_layout(
                title='Vendedores con Más Compradores Únicos',
                xaxis_title='Número de Compradores Únicos', yaxis_title='Vendedor',
                height=400, margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_seller_hub, width="stretch")

            sh_display = seller_hubs_df.copy()
            sh_display['unique_buyers']      = sh_display['unique_buyers'].apply(lambda v: f"{v:,.0f}")
            sh_display['total_commission']   = sh_display['total_commission'].apply(lambda v: f"${v:,.0f}")
            sh_display['ref_commission']     = sh_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            sh_display['net_commission']     = sh_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            sh_display['total_transactions'] = sh_display['total_transactions'].apply(lambda v: f"{v:,.0f}")
            sh_display['total_volume']       = sh_display['total_volume'].apply(lambda v: f"${v:,.0f}")
            sh_cols = {
                'seller':           st.column_config.TextColumn('Vendedor', help='Nombre del vendedor en las operaciones de la BMC.'),
                'unique_buyers':    st.column_config.TextColumn('Compradores Únicos', help='Cuántos compradores distintos ha tenido este vendedor en el período.\nFórmula: COUNT(DISTINCT "NIT COMPRADOR")'),
                'total_commission': st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones generadas por operaciones de este vendedor.\nFórmula: SUM(COMISION)'),
                'ref_commission':   st.column_config.TextColumn('Comisión Ref.', help='Total pagado al referenciador por operaciones de este vendedor.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                'net_commission':   st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa después de pagar referenciadores.\nFórmula: Comisión Total − Comisión Referenciador'),
                'total_transactions': st.column_config.TextColumn('Transacciones', help='Número total de operaciones en que este vendedor participó.\nFórmula: COUNT(*)'),
                'total_volume':     st.column_config.TextColumn('Volumen Total', help='Valor total de negocio en operaciones de este vendedor.\nFórmula: SUM("VALOR NEGOCIO")'),
            }
            if _sh_has_ref:
                sh_cols['nombre_ref'] = st.column_config.TextColumn('Referenciador', help='Referenciador más frecuente en las operaciones de este vendedor (moda estadística).')
            st.dataframe(sh_display, use_container_width=True, hide_index=True, column_config=sh_cols)
        else:
            st.info("No hay datos de nodos de vendedores disponibles")
    
    with col_net2:
        buyer_hub_where = filter_query + (" AND " if filter_query else "WHERE ") + '"NOMBRE COMPRADOR" IS NOT NULL AND "NIT VENDEDOR" IS NOT NULL'

        if _ref_lookup_exists:
            buyer_hub_query = f"""
                SELECT sub.buyer, sub.unique_sellers, sub.total_commission,
                       sub.ref_commission,
                       sub.total_commission - sub.ref_commission AS net_commission,
                       sub.total_transactions, sub.total_volume,
                       COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref
                FROM (
                    SELECT "NOMBRE COMPRADOR" as buyer,
                           COUNT(DISTINCT "NIT VENDEDOR") as unique_sellers,
                           SUM(COMISION) as total_commission,
                           SUM(COMISION * ("% REF VENTA" / 100.0))
                               + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                           COUNT(*) as total_transactions,
                           SUM("VALOR NEGOCIO") as total_volume,
                           mode(REFERENCIADOR) as main_ref
                    FROM operaciones_bmc
                    {buyer_hub_where}
                    GROUP BY "NOMBRE COMPRADOR"
                    HAVING COUNT(DISTINCT "NIT VENDEDOR") >= 2
                    ORDER BY unique_sellers DESC, total_commission DESC
                    LIMIT 10
                ) sub
                LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
            """
        else:
            buyer_hub_query = f"""
                SELECT "NOMBRE COMPRADOR" as buyer,
                       COUNT(DISTINCT "NIT VENDEDOR") as unique_sellers,
                       SUM(COMISION) as total_commission,
                       SUM(COMISION * ("% REF VENTA" / 100.0))
                           + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                       SUM(COMISION)
                           - SUM(COMISION * ("% REF VENTA" / 100.0))
                           - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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

            _bh_has_ref = 'nombre_ref' in buyer_hubs_df.columns
            _bh_cd_cols = ['total_commission', 'ref_commission', 'net_commission', 'total_transactions']
            if _bh_has_ref:
                _bh_cd_cols.append('nombre_ref')
            fig_buyer_hub = go.Figure()
            fig_buyer_hub.add_trace(go.Bar(
                x=buyer_hubs_df['unique_sellers'],
                y=buyer_hubs_df['buyer'],
                orientation='h',
                marker=dict(color=buyer_hubs_df['total_commission'], colorscale='Greens', showscale=False),
                customdata=buyer_hubs_df[_bh_cd_cols].values,
                hovertemplate=(
                    '<b>%{y}</b><br>Vendedores Únicos: %{x}<br>'
                    'Comisión Total: $%{customdata[0]:,.0f}<br>'
                    'Comisión Ref.: $%{customdata[1]:,.0f}<br>'
                    'Comisión Empresa: $%{customdata[2]:,.0f}<br>'
                    'Transacciones: %{customdata[3]:,.0f}<br>'
                    + ('Referenciador: %{customdata[4]}<extra></extra>' if _bh_has_ref else '<extra></extra>')
                ),
            ))
            fig_buyer_hub.update_layout(
                title='Compradores con Más Vendedores Únicos',
                xaxis_title='Número de Vendedores Únicos', yaxis_title='Comprador',
                height=400, margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_buyer_hub, width="stretch")

            bh_display = buyer_hubs_df.copy()
            bh_display['unique_sellers']     = bh_display['unique_sellers'].apply(lambda v: f"{v:,.0f}")
            bh_display['total_commission']   = bh_display['total_commission'].apply(lambda v: f"${v:,.0f}")
            bh_display['ref_commission']     = bh_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            bh_display['net_commission']     = bh_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            bh_display['total_transactions'] = bh_display['total_transactions'].apply(lambda v: f"{v:,.0f}")
            bh_display['total_volume']       = bh_display['total_volume'].apply(lambda v: f"${v:,.0f}")
            bh_cols = {
                'buyer':            st.column_config.TextColumn('Comprador', help='Nombre del comprador en las operaciones de la BMC.'),
                'unique_sellers':   st.column_config.TextColumn('Vendedores Únicos', help='Cuántos vendedores distintos ha tenido este comprador en el período.\nFórmula: COUNT(DISTINCT "NIT VENDEDOR")'),
                'total_commission': st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones generadas por operaciones de este comprador.\nFórmula: SUM(COMISION)'),
                'ref_commission':   st.column_config.TextColumn('Comisión Ref.', help='Total pagado al referenciador por operaciones de este comprador.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
                'net_commission':   st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa después de pagar referenciadores.\nFórmula: Comisión Total − Comisión Referenciador'),
                'total_transactions': st.column_config.TextColumn('Transacciones', help='Número total de operaciones en que este comprador participó.\nFórmula: COUNT(*)'),
                'total_volume':     st.column_config.TextColumn('Volumen Total', help='Valor total de negocio en operaciones de este comprador.\nFórmula: SUM("VALOR NEGOCIO")'),
            }
            if _bh_has_ref:
                bh_cols['nombre_ref'] = st.column_config.TextColumn('Referenciador', help='Referenciador más frecuente en las operaciones de este comprador (moda estadística).')
            st.dataframe(bh_display, use_container_width=True, hide_index=True, column_config=bh_cols)
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
        col_prin1 = st.container()
        col_prin2 = st.container()
        
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
            prin_display = principal_df.copy()
            prin_display['transactions']        = prin_display['transactions'].apply(lambda v: f"{v:,.0f}")
            prin_display['total_commission']    = prin_display['total_commission'].apply(lambda v: f"${v:,.0f}")
            prin_display['avg_commission']      = prin_display['avg_commission'].apply(lambda v: f"${v:,.0f}")
            prin_display['total_volume']        = prin_display['total_volume'].apply(lambda v: f"${v:,.0f}")
            prin_display['avg_commission_rate'] = prin_display['avg_commission_rate'].apply(lambda v: f"{v:.2f}%")
            st.dataframe(
                prin_display, use_container_width=True, hide_index=True,
                column_config={
                    'principal_type':       st.column_config.TextColumn('Principal', help='Quién paga el registro: Vendedor (PRINCIPAL=V) o Comprador (PRINCIPAL=C).'),
                    'transactions':         st.column_config.TextColumn('Operaciones', help='Número de operaciones donde este tipo de principal pagó el registro.\nFórmula: COUNT(*)'),
                    'total_commission':     st.column_config.TextColumn('Comisión Total', help='Suma de comisiones generadas por operaciones de este tipo de principal.\nFórmula: SUM(COMISION)'),
                    'avg_commission':       st.column_config.TextColumn('Comisión Promedio', help='Comisión promedio por operación para este tipo de principal.\nFórmula: AVG(COMISION)'),
                    'total_volume':         st.column_config.TextColumn('Volumen Total', help='Valor total de negocio operado donde este tipo de principal pagó.\nFórmula: SUM(VALOR NEGOCIO)'),
                    'avg_commission_rate':  st.column_config.TextColumn('Tasa Comisión Prom.', help='Porcentaje promedio de comisión sobre el valor de negocio.\nFórmula: AVG(COMISION / VALOR NEGOCIO) × 100'),
                },
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
        
        if _ref_lookup_exists:
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
                        AVG(o.COMISION / NULLIF(o."VALOR NEGOCIO", 0)) * 100 as avg_commission_rate,
                        mode(o.REFERENCIADOR) as main_ref
                    FROM operaciones_bmc o
                    INNER JOIN our_seller_clients osc ON o."NIT VENDEDOR" = osc.client_nit
                    WHERE o."NIT COMPRADOR" IS NOT NULL AND o."NOMBRE COMPRADOR" IS NOT NULL
                    GROUP BY o."NIT COMPRADOR", o."NOMBRE COMPRADOR"
                )
                SELECT bo.prospect_nit, bo.prospect_name, bo.num_connections_to_clients,
                       bo.total_volume, bo.total_transactions, bo.avg_commission_rate,
                       ROUND(bo.total_volume * (bo.avg_commission_rate / 100), 0) as commission_opportunity,
                       COALESCE(r.NOMBRE, CAST(bo.main_ref AS VARCHAR)) AS nombre_ref
                FROM buyer_opportunities bo
                LEFT JOIN referenciadores r ON bo.main_ref = r.CODIGO
                ORDER BY bo.num_connections_to_clients DESC, bo.total_volume DESC
                LIMIT 20
            """
        else:
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
                SELECT prospect_nit, prospect_name, num_connections_to_clients,
                       total_volume, total_transactions, avg_commission_rate,
                       ROUND(total_volume * (avg_commission_rate / 100), 0) as commission_opportunity
                FROM buyer_opportunities
                ORDER BY num_connections_to_clients DESC, total_volume DESC
                LIMIT 20
            """
        
        potential_buyers_df = safe_query(potential_buyers_query, "compradores potenciales")
        
        if not potential_buyers_df.empty:
            potential_buyers_df = potential_buyers_df[~potential_buyers_df['prospect_nit'].isin(client_nits)]
        
        buyer_clients_where = filter_query + (" AND " if filter_query else "WHERE ") + "PRINCIPAL = 'C'"
        
        if _ref_lookup_exists:
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
                        AVG(o.COMISION / NULLIF(o."VALOR NEGOCIO", 0)) * 100 as avg_commission_rate,
                        mode(o.REFERENCIADOR) as main_ref
                    FROM operaciones_bmc o
                    INNER JOIN our_buyer_clients obc ON o."NIT COMPRADOR" = obc.client_nit
                    WHERE o."NIT VENDEDOR" IS NOT NULL AND o."NOMBRE VENDEDOR" IS NOT NULL
                    GROUP BY o."NIT VENDEDOR", o."NOMBRE VENDEDOR"
                )
                SELECT so.prospect_nit, so.prospect_name, so.num_connections_to_clients,
                       so.total_volume, so.total_transactions, so.avg_commission_rate,
                       ROUND(so.total_volume * (so.avg_commission_rate / 100), 0) as commission_opportunity,
                       COALESCE(r.NOMBRE, CAST(so.main_ref AS VARCHAR)) AS nombre_ref
                FROM seller_opportunities so
                LEFT JOIN referenciadores r ON so.main_ref = r.CODIGO
                ORDER BY so.num_connections_to_clients DESC, so.total_volume DESC
                LIMIT 20
            """
        else:
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
                SELECT prospect_nit, prospect_name, num_connections_to_clients,
                       total_volume, total_transactions, avg_commission_rate,
                       ROUND(total_volume * (avg_commission_rate / 100), 0) as commission_opportunity
                FROM seller_opportunities
                ORDER BY num_connections_to_clients DESC, total_volume DESC
                LIMIT 20
            """
        
        potential_sellers_df = safe_query(potential_sellers_query, "vendedores potenciales")
        
        if not potential_sellers_df.empty:
            potential_sellers_df = potential_sellers_df[~potential_sellers_df['prospect_nit'].isin(client_nits)]
        
        col_opp1 = st.container()
        col_opp2 = st.container()
        
        with col_opp1:
            st.markdown("### 🔵 Compradores Potenciales como Clientes")
            st.markdown("*Compradores que compran a SUS clientes vendedores*")
            
            if not potential_buyers_df.empty:
                st.success(f"🎯 ¡Se encontraron {len(potential_buyers_df)} compradores potenciales como clientes!")

                total_opp = potential_buyers_df['commission_opportunity'].sum()
                st.metric("💰 Oportunidad Total de Comisión", f"${total_opp:,.0f}",
                         help="Comisión potencial si todos estos compradores se convierten en clientes")

                _pb_has_ref = 'nombre_ref' in potential_buyers_df.columns
                pb_cols = ['prospect_name', 'num_connections_to_clients', 'total_volume',
                           'total_transactions', 'commission_opportunity']
                if _pb_has_ref:
                    pb_cols.insert(1, 'nombre_ref')
                pb_display = potential_buyers_df[pb_cols].copy()
                pb_display['num_connections_to_clients'] = pb_display['num_connections_to_clients'].apply(lambda v: f"{v:,.0f}")
                pb_display['total_volume']               = pb_display['total_volume'].apply(lambda v: f"${v:,.0f}")
                pb_display['total_transactions']         = pb_display['total_transactions'].apply(lambda v: f"{v:,.0f}")
                pb_display['commission_opportunity']     = pb_display['commission_opportunity'].apply(lambda v: f"${v:,.0f}")
                pb_col_config = {
                    'prospect_name': st.column_config.TextColumn('Nombre del Prospecto', help='Comprador que ya ha transaccionado con sus clientes vendedores pero que aún no es cliente directo suyo.'),
                    'num_connections_to_clients': st.column_config.TextColumn('Conexiones con Clientes', help='Cuántos de sus clientes vendedores ya han operado con este prospecto comprador.\nFórmula: COUNT(DISTINCT cliente_vendedor)'),
                    'total_volume': st.column_config.TextColumn('Volumen', help='Valor total de negocio transaccionado por este prospecto con sus clientes.\nFórmula: SUM("VALOR NEGOCIO")'),
                    'total_transactions': st.column_config.TextColumn('Transacciones', help='Número de operaciones en las que este prospecto participó como comprador junto a sus clientes.\nFórmula: COUNT(*)'),
                    'commission_opportunity': st.column_config.TextColumn('Oportunidad de Comisión', help='Comisión potencial estimada si este prospecto se convierte en cliente directo, basada en el volumen histórico y tasa promedio del mercado.\nFórmula: Volumen × Tasa Promedio de Comisión del Mercado'),
                }
                if _pb_has_ref:
                    pb_col_config['nombre_ref'] = st.column_config.TextColumn(
                        'Referenciador',
                        help='Referenciador cuyo cliente ya trabaja con este prospecto.',
                    )
                st.dataframe(pb_display, use_container_width=True, hide_index=True,
                             height=400, column_config=pb_col_config)

                if len(potential_buyers_df) > 0:
                    top_prospect = potential_buyers_df.iloc[0]
                    with st.expander(f"🌟 Mejor Prospecto: {top_prospect['prospect_name']}", expanded=False):
                        ref_line = f"\n- Referenciador vinculado: **{top_prospect['nombre_ref']}**" if _pb_has_ref else ""
                        st.markdown(f"""
                        **Por qué es un prospecto caliente:**
                        - Trabaja con **{int(top_prospect['num_connections_to_clients'])}** de SUS clientes
                        - **${top_prospect['total_volume']:,.0f}** en volumen de transacciones
                        - **${top_prospect['commission_opportunity']:,.0f}** de oportunidad de comisión
                        - **{int(top_prospect['total_transactions'])}** transacciones totales{ref_line}

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

                _ps_has_ref = 'nombre_ref' in potential_sellers_df.columns
                ps_cols = ['prospect_name', 'num_connections_to_clients', 'total_volume',
                           'total_transactions', 'commission_opportunity']
                if _ps_has_ref:
                    ps_cols.insert(1, 'nombre_ref')
                ps_display = potential_sellers_df[ps_cols].copy()
                ps_display['num_connections_to_clients'] = ps_display['num_connections_to_clients'].apply(lambda v: f"{v:,.0f}")
                ps_display['total_volume']               = ps_display['total_volume'].apply(lambda v: f"${v:,.0f}")
                ps_display['total_transactions']         = ps_display['total_transactions'].apply(lambda v: f"{v:,.0f}")
                ps_display['commission_opportunity']     = ps_display['commission_opportunity'].apply(lambda v: f"${v:,.0f}")
                ps_col_config = {
                    'prospect_name': st.column_config.TextColumn('Nombre del Prospecto', help='Vendedor que ya ha transaccionado con sus clientes compradores pero que aún no es cliente directo suyo.'),
                    'num_connections_to_clients': st.column_config.TextColumn('Conexiones con Clientes', help='Cuántos de sus clientes compradores ya han operado con este prospecto vendedor.\nFórmula: COUNT(DISTINCT cliente_comprador)'),
                    'total_volume': st.column_config.TextColumn('Volumen', help='Valor total de negocio transaccionado por este prospecto con sus clientes.\nFórmula: SUM("VALOR NEGOCIO")'),
                    'total_transactions': st.column_config.TextColumn('Transacciones', help='Número de operaciones en las que este prospecto participó como vendedor junto a sus clientes.\nFórmula: COUNT(*)'),
                    'commission_opportunity': st.column_config.TextColumn('Oportunidad de Comisión', help='Comisión potencial estimada si este prospecto se convierte en cliente directo, basada en el volumen histórico y tasa promedio del mercado.\nFórmula: Volumen × Tasa Promedio de Comisión del Mercado'),
                }
                if _ps_has_ref:
                    ps_col_config['nombre_ref'] = st.column_config.TextColumn(
                        'Referenciador',
                        help='Referenciador cuyo cliente ya trabaja con este prospecto.',
                    )
                st.dataframe(ps_display, use_container_width=True, hide_index=True,
                             height=400, column_config=ps_col_config)

                if len(potential_sellers_df) > 0:
                    top_prospect = potential_sellers_df.iloc[0]
                    with st.expander(f"🌟 Mejor Prospecto: {top_prospect['prospect_name']}", expanded=False):
                        ref_line = f"\n- Referenciador vinculado: **{top_prospect['nombre_ref']}**" if _ps_has_ref else ""
                        st.markdown(f"""
                        **Por qué es un prospecto caliente:**
                        - Trabaja con **{int(top_prospect['num_connections_to_clients'])}** de SUS clientes
                        - **${top_prospect['total_volume']:,.0f}** en volumen de transacciones
                        - **${top_prospect['commission_opportunity']:,.0f}** de oportunidad de comisión
                        - **{int(top_prospect['total_transactions'])}** transacciones totales{ref_line}

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
            
            _comb_has_ref = 'nombre_ref' in combined_df.columns
            comb_cols = ['prospect_name', 'type', 'num_connections_to_clients',
                         'commission_opportunity', 'total_volume']
            if _comb_has_ref:
                comb_cols.insert(2, 'nombre_ref')
            priority_display = combined_df[comb_cols].copy()
            priority_display['num_connections_to_clients'] = priority_display['num_connections_to_clients'].apply(lambda v: f"{v:,.0f}")
            priority_display['commission_opportunity']     = priority_display['commission_opportunity'].apply(lambda v: f"${v:,.0f}")
            priority_display['total_volume']               = priority_display['total_volume'].apply(lambda v: f"${v:,.0f}")
            comb_col_config = {
                'prospect_name': st.column_config.TextColumn('Prospecto'),
                'type': st.column_config.TextColumn('Tipo'),
                'num_connections_to_clients': st.column_config.TextColumn('Conexiones con Clientes'),
                'commission_opportunity': st.column_config.TextColumn('Oportunidad de Comisión'),
                'total_volume': st.column_config.TextColumn('Volumen'),
            }
            if _comb_has_ref:
                comb_col_config['nombre_ref'] = st.column_config.TextColumn(
                    'Referenciador',
                    help='Referenciador cuyo cliente ya trabaja con este prospecto.',
                )
            st.dataframe(priority_display, use_container_width=True, hide_index=True,
                         column_config=comb_col_config)
            
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

    if _ref_lookup_exists:
        relationships_query = f"""
            SELECT sub.seller, sub.buyer, sub.transactions, sub.total_commission,
                   sub.ref_commission,
                   sub.total_commission - sub.ref_commission AS net_commission,
                   sub.total_volume, sub.seller_paid, sub.buyer_paid,
                   COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref
            FROM (
                SELECT "NOMBRE VENDEDOR" as seller,
                       "NOMBRE COMPRADOR" as buyer,
                       COUNT(*) as transactions,
                       SUM(COMISION) as total_commission,
                       SUM(COMISION * ("% REF VENTA" / 100.0))
                           + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                       SUM("VALOR NEGOCIO") as total_volume,
                       COUNT(CASE WHEN PRINCIPAL = 'V' THEN 1 END) as seller_paid,
                       COUNT(CASE WHEN PRINCIPAL = 'C' THEN 1 END) as buyer_paid,
                       mode(REFERENCIADOR) as main_ref
                FROM operaciones_bmc
                {relationships_where}
                GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
                HAVING COUNT(*) >= 3
                ORDER BY total_commission DESC
                LIMIT 20
            ) sub
            LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
        """
    else:
        relationships_query = f"""
            SELECT "NOMBRE VENDEDOR" as seller,
                   "NOMBRE COMPRADOR" as buyer,
                   COUNT(*) as transactions,
                   SUM(COMISION) as total_commission,
                   SUM(COMISION * ("% REF VENTA" / 100.0))
                       + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                   SUM(COMISION)
                       - SUM(COMISION * ("% REF VENTA" / 100.0))
                       - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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

        _rel_has_ref = 'nombre_ref' in relationships_df.columns
        rel_display = relationships_df.copy()
        rel_display['transactions']     = rel_display['transactions'].apply(lambda v: f"{v:,.0f}")
        rel_display['total_commission'] = rel_display['total_commission'].apply(lambda v: f"${v:,.0f}")
        rel_display['ref_commission']   = rel_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
        rel_display['net_commission']   = rel_display['net_commission'].apply(lambda v: f"${v:,.0f}")
        rel_display['seller_paid']      = rel_display['seller_paid'].apply(lambda v: f"{v:,.0f}")
        rel_display['buyer_paid']       = rel_display['buyer_paid'].apply(lambda v: f"{v:,.0f}")

        display_cols = ['seller', 'buyer', 'transactions', 'total_commission', 'ref_commission', 'net_commission', 'relationship_type', 'seller_paid', 'buyer_paid']
        if _rel_has_ref:
            display_cols.insert(2, 'nombre_ref')

        rel_col_config = {
            'seller':           st.column_config.TextColumn('Vendedor', help='Nombre del vendedor en esta relación comercial.'),
            'buyer':            st.column_config.TextColumn('Comprador', help='Nombre del comprador en esta relación comercial.'),
            'transactions':     st.column_config.TextColumn('Operaciones', help='Número de operaciones entre este vendedor y comprador.\nFórmula: COUNT(*)'),
            'total_commission': st.column_config.TextColumn('Comisión Total', help='Suma bruta de comisiones de las operaciones entre este par.\nFórmula: SUM(COMISION)'),
            'ref_commission':   st.column_config.TextColumn('Comisión Ref.', help='Total pagado al referenciador por operaciones entre este par.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)'),
            'net_commission':   st.column_config.TextColumn('Comisión Empresa', help='Lo que retiene su empresa por operaciones entre este par.\nFórmula: Comisión Total − Comisión Referenciador'),
            'relationship_type': st.column_config.TextColumn('Tipo Relación', help='🔄 Mutua: ambos han pagado el registro en distintas operaciones.\n→ Unilateral: solo uno siempre paga el registro.'),
            'seller_paid':      st.column_config.TextColumn('Vend. Paga', help='Número de operaciones donde el vendedor pagó el registro (PRINCIPAL=V).'),
            'buyer_paid':       st.column_config.TextColumn('Comp. Paga', help='Número de operaciones donde el comprador pagó el registro (PRINCIPAL=C).'),
        }
        if _rel_has_ref:
            rel_col_config['nombre_ref'] = st.column_config.TextColumn(
                'Referenciador',
                help='Referenciador más frecuente en las operaciones de esta relación comprador-vendedor.',
            )

        st.dataframe(rel_display[display_cols], use_container_width=True, hide_index=True,
                     height=600, column_config=rel_col_config)
        
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

        # Build referenciador lookup for each node (seller/buyer name → ref name)
        _hub_ref_lookup = {}
        if _ref_lookup_exists:
            _hub_ref_s_df = safe_query(f"""
                SELECT sub."NOMBRE VENDEDOR" AS name,
                       COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref
                FROM (
                    SELECT "NOMBRE VENDEDOR", mode(REFERENCIADOR) AS main_ref
                    FROM operaciones_bmc
                    {network_data_where}
                    GROUP BY "NOMBRE VENDEDOR"
                ) sub
                LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
            """, "ref vendedores red")
            _hub_ref_b_df = safe_query(f"""
                SELECT sub."NOMBRE COMPRADOR" AS name,
                       COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref
                FROM (
                    SELECT "NOMBRE COMPRADOR", mode(REFERENCIADOR) AS main_ref
                    FROM operaciones_bmc
                    {network_data_where}
                    GROUP BY "NOMBRE COMPRADOR"
                ) sub
                LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
            """, "ref compradores red")
            for _, _row in _hub_ref_s_df.iterrows():
                _hub_ref_lookup[f"S:{_row['name']}"] = _row['nombre_ref']
            for _, _row in _hub_ref_b_df.iterrows():
                _hub_ref_lookup[f"B:{_row['name']}"] = _row['nombre_ref']

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_type = "Vendedor" if node.startswith("S:") else "Comprador"
            node_name = node[2:]
            commission = node_commission.get(node, 0)
            connections = node_connections.get(node, 0)
            ref_name = _hub_ref_lookup.get(node)

            short_name = node_name[:15] + "..." if len(node_name) > 15 else node_name
            node_text.append(short_name if show_labels else "")

            node_hover_text.append(
                f"<b>{node_name}</b><br>"
                f"Tipo: {node_type}<br>"
                f"Comisión: ${commission:,.0f}<br>"
                f"Conexiones: {connections}<br>"
                + (f"Referenciador: {ref_name}<br>" if ref_name else "")
                + "Haga clic para resaltar"
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
            ref_name = _hub_ref_lookup.get(node, "")
            row = {'Nombre': node_name, 'Tipo': node_type, 'Conexiones': connections, 'Comisión': commission}
            if _ref_lookup_exists:
                row['Referenciador'] = ref_name
            hub_data.append(row)

        hub_df = pd.DataFrame(hub_data).sort_values('Conexiones', ascending=False).head(10)
        hub_df['Conexiones'] = hub_df['Conexiones'].apply(lambda v: f"{v:,.0f}")
        hub_df['Comisión']   = hub_df['Comisión'].apply(lambda v: f"${v:,.0f}")
        hub_col_config = {
            'Nombre': st.column_config.TextColumn('Nombre', help='Nombre del vendedor o comprador en la red.'),
            'Tipo': st.column_config.TextColumn('Tipo', help='Vendedor o Comprador.'),
            'Conexiones': st.column_config.TextColumn('Conexiones', help='Número de contrapartes únicas con las que este nodo opera.'),
            'Comisión': st.column_config.TextColumn('Comisión', help='Total de comisiones generadas en operaciones que involucran este nodo.'),
        }
        if _ref_lookup_exists:
            hub_col_config['Referenciador'] = st.column_config.TextColumn(
                'Referenciador',
                help='Referenciador más frecuente en las operaciones de este nodo.',
            )
        st.dataframe(hub_df, use_container_width=True, hide_index=True, column_config=hub_col_config)
        
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
            st.metric("Vendedores Únicos", f"{int(network_metrics_df['unique_sellers'][0]):,}",
                      help="Número de vendedores distintos que aparecen en las operaciones del período.\nFórmula: COUNT(DISTINCT NOMBRE VENDEDOR)")
        with col_nm2:
            st.metric("Compradores Únicos", f"{int(network_metrics_df['unique_buyers'][0]):,}",
                      help="Número de compradores distintos que aparecen en las operaciones del período.\nFórmula: COUNT(DISTINCT NOMBRE COMPRADOR)")
        with col_nm3:
            st.metric("Relaciones Únicas", f"{int(network_metrics_df['unique_relationships'][0]):,}",
                      help="Pares comprador-vendedor únicos que han operado juntos al menos una vez.\nFórmula: COUNT(DISTINCT NOMBRE VENDEDOR || '-' || NOMBRE COMPRADOR)")
        with col_nm4:
            st.metric("Prom Trans/Relación", f"{network_metrics_df['avg_transactions_per_relationship'][0]:.1f}",
                      help="Promedio de transacciones por par comprador-vendedor. Valores altos indican relaciones comerciales recurrentes y estables.")

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
        
        _nit_rows = client_list_df[client_list_df['client_name'] == selected_client]['client_nit']
        if _nit_rows.empty:
            st.warning("Cliente no encontrado. Seleccione otro.")
            st.stop()
        # Escape for SQL embedding (prevents injection if data contains quotes)
        client_nit = _sql_str(str(_nit_rows.values[0]))
        
        st.markdown(f"## 📊 Perspectivas para: {selected_client}")

        if _ref_lookup_exists:
            _client_ref_query = f"""
                SELECT COALESCE(r.NOMBRE, CAST(sub.main_ref AS VARCHAR)) AS nombre_ref,
                       CAST(sub.main_ref AS VARCHAR) AS codigo_ref
                FROM (
                    SELECT mode(REFERENCIADOR) AS main_ref
                    FROM operaciones_bmc
                    WHERE "CC PPAL" = '{client_nit}'
                      AND REFERENCIADOR IS NOT NULL AND REFERENCIADOR != 0
                ) sub
                LEFT JOIN referenciadores r ON sub.main_ref = r.CODIGO
            """
            _client_ref_df = safe_query(_client_ref_query, "referenciador del cliente")
            if not _client_ref_df.empty and _client_ref_df['nombre_ref'].notna().any():
                _ref_name = _client_ref_df['nombre_ref'].values[0]
                _ref_code = _client_ref_df['codigo_ref'].values[0]
                st.info(f"👥 **Referenciador:** {_ref_name}  ·  Código: {_ref_code}")

        client_stats_query = f"""
            SELECT
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume,
                SUM(COMISION) as total_commission_paid,
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
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
            _cs_net = stats['total_commission_paid'] - stats['ref_commission']

            col_cs1, col_cs2, col_cs3, col_cs4, col_cs5 = st.columns(5)

            with col_cs1:
                st.metric("Total Transacciones", f"{int(stats['total_transactions']):,}",
                          help="Número total de operaciones registradas para este cliente en todos los períodos.\nFórmula: COUNT(*)")
            with col_cs2:
                st.metric("Comisión Total", f"${stats['total_commission_paid']:,.0f}",
                          help="Suma bruta de todas las comisiones generadas por este cliente.\nFórmula: SUM(COMISION)")
            with col_cs3:
                st.metric("Comisión Referenciador", f"${stats['ref_commission']:,.0f}",
                          help="Lo que su empresa paga al referenciador por las operaciones de este cliente.\nFórmula: SUM(COMISION × % REF VENTA/100) + SUM(COMISION × % REF COMPRA/100)")
            with col_cs4:
                st.metric("Comisión Empresa", f"${_cs_net:,.0f}",
                          help="Comisión neta que retiene su empresa después de pagar al referenciador.\nFórmula: Comisión Total − Comisión Referenciador")
            with col_cs5:
                st.metric("Tasa Promedio", f"{stats['avg_commission_rate']:.2f}%",
                          help="Porcentaje promedio de comisión sobre el valor de negocio de este cliente.\nFórmula: AVG(COMISION / VALOR NEGOCIO) × 100")
            
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
                    
                    mc_display = market_comp_df[['NOMBRE PRODUCTO', 'client_transactions', 'client_rate', 'market_avg_rate', 'vs_market']].copy()
                    mc_display['client_transactions'] = mc_display['client_transactions'].apply(lambda v: f"{v:.0f}")
                    mc_display['client_rate']         = mc_display['client_rate'].apply(lambda v: f"{v:.2f}%")
                    mc_display['market_avg_rate']     = mc_display['market_avg_rate'].apply(lambda v: f"{v:.2f}%")
                    st.dataframe(
                        mc_display, use_container_width=True, hide_index=True,
                        column_config={
                            'NOMBRE PRODUCTO':    st.column_config.TextColumn('Producto', help='Nombre del producto agrícola operado.'),
                            'client_transactions': st.column_config.TextColumn('Operaciones del Cliente', help='Número de operaciones que este cliente realizó en este producto.\nFórmula: COUNT donde CC PPAL = cliente'),
                            'client_rate':        st.column_config.TextColumn('Tasa del Cliente', help='Porcentaje de comisión promedio pagado por este cliente en este producto.\nFórmula: AVG(COMISION/VALOR NEGOCIO × 100) solo para este cliente'),
                            'market_avg_rate':    st.column_config.TextColumn('Promedio Mercado', help='Tasa de comisión promedio del mercado para este producto (todos los clientes).\nFórmula: AVG(COMISION/VALOR NEGOCIO × 100) todos los clientes'),
                            'vs_market':          st.column_config.TextColumn('vs. Mercado', help='Comparación de la tasa del cliente con el promedio del mercado. 🟢 Por debajo = paga menos que el mercado. 🔴 Por encima = paga más.'),
                        },
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
                        tb_display = top_buyers_df.copy()
                        tb_display['transactions'] = tb_display['transactions'].apply(lambda v: f"{v:.0f}")
                        tb_display['total_volume'] = tb_display['total_volume'].apply(lambda v: f"${v:,.0f}")
                        st.dataframe(tb_display, use_container_width=True, hide_index=True, column_config={
                            'partner':          st.column_config.TextColumn('Comprador', help='Nombre del comprador que adquirió productos de este cliente.'),
                            'transactions':     st.column_config.TextColumn('Operaciones', help='Número de transacciones registradas con este comprador.\nFórmula: COUNT(*)'),
                            'total_volume':     st.column_config.TextColumn('Volumen Total', help='Valor total de negocio operado con este comprador.\nFórmula: SUM(VALOR NEGOCIO)'),
                            'last_transaction': st.column_config.TextColumn('Última Operación', help='Fecha de la operación más reciente con este comprador.'),
                        })

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
                        ts_display = top_sellers_df.copy()
                        ts_display['transactions'] = ts_display['transactions'].apply(lambda v: f"{v:.0f}")
                        ts_display['total_volume'] = ts_display['total_volume'].apply(lambda v: f"${v:,.0f}")
                        st.dataframe(ts_display, use_container_width=True, hide_index=True, column_config={
                            'partner':          st.column_config.TextColumn('Proveedor', help='Nombre del vendedor que suministró productos a este cliente.'),
                            'transactions':     st.column_config.TextColumn('Operaciones', help='Número de transacciones registradas con este proveedor.\nFórmula: COUNT(*)'),
                            'total_volume':     st.column_config.TextColumn('Volumen Total', help='Valor total de negocio operado con este proveedor.\nFórmula: SUM(VALOR NEGOCIO)'),
                            'last_transaction': st.column_config.TextColumn('Última Operación', help='Fecha de la operación más reciente con este proveedor.'),
                        })
                
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
                    cb_display = cost_breakdown_df.copy()
                    cb_display['commission_paid'] = cb_display['commission_paid'].apply(lambda v: f"${v:,.0f}")
                    cb_display['volume']          = cb_display['volume'].apply(lambda v: f"${v:,.0f}")
                    cb_display['transactions']    = cb_display['transactions'].apply(lambda v: f"{v:.0f}")
                    cb_display['effective_rate']  = cb_display['effective_rate'].apply(lambda v: f"{v:.2f}%")
                    st.dataframe(
                        cb_display, use_container_width=True, hide_index=True,
                        column_config={
                            'YEAR':            st.column_config.TextColumn('Año', help='Año de las operaciones.'),
                            'commission_paid': st.column_config.TextColumn('Comisión Pagada', help='Total de comisiones pagadas a su empresa por este cliente en el año.\nFórmula: SUM(COMISION)'),
                            'volume':          st.column_config.TextColumn('Volumen Operado', help='Valor total de negocio registrado en el año.\nFórmula: SUM(VALOR NEGOCIO)'),
                            'transactions':    st.column_config.TextColumn('Operaciones', help='Número de operaciones registradas en el año.\nFórmula: COUNT(*)'),
                            'effective_rate':  st.column_config.TextColumn('Tasa Efectiva', help='Porcentaje promedio de comisión pagado sobre el valor de negocio en el año.\nFórmula: AVG(COMISION / VALOR NEGOCIO) × 100'),
                        },
                    )

                    total_commission = cost_breakdown_df['commission_paid'].sum()
                    total_volume = cost_breakdown_df['volume'].sum()
                    estimated_tax_benefit = total_volume * 0.15
                    net_benefit = estimated_tax_benefit - total_commission

                    col_cb1, col_cb2, col_cb3 = st.columns(3)
                    with col_cb1:
                        st.metric("Total Pagado", f"${total_commission:,.0f}",
                                  help="Total de comisiones pagadas a su empresa por este cliente en todos los años.\nFórmula: SUM(COMISION)")
                    with col_cb2:
                        st.metric("Beneficio Tributario Est.", f"${estimated_tax_benefit:,.0f}",
                                  help="Estimación del beneficio tributario obtenido al registrar operaciones en BMC.\nFórmula: Volumen Total × 15% (tasa estimada de deducciones fiscales)")
                    with col_cb3:
                        st.metric("Beneficio Neto", f"${net_benefit:,.0f}",
                                  delta=f"{((net_benefit/total_commission)*100):.0f}% ROI",
                                  help="Diferencia entre el beneficio tributario estimado y las comisiones pagadas.\nFórmula: Beneficio Tributario − Total Pagado")
                    
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
    
    col_op1 = st.container()
    col_op2 = st.container()
    
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
                CASE EXTRACT(ISODOW FROM TRY_CAST("FECHA REGISTRO" AS DATE))
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                    WHEN 7 THEN 'Sunday'
                END AS day_of_week,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings,
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                SUM(COMISION)
                    - SUM(COMISION * ("% REF VENTA" / 100.0))
                    - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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
            dow_df['_sort_key'] = pd.Categorical(dow_df['day_of_week'].astype(str), categories=day_order, ordered=True)
            dow_df = dow_df.sort_values('_sort_key').drop(columns=['_sort_key'])
            day_translation = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            dow_df['day_of_week'] = dow_df['day_of_week'].astype(str).map(day_translation).fillna(dow_df['day_of_week'].astype(str))

            fig_dow = px.bar(
                dow_df, x='day_of_week', y='operations',
                title='Operaciones por Día de la Semana',
                labels={'operations': 'Número de Operaciones', 'day_of_week': 'Día'},
                color='operations', color_continuous_scale='Viridis'
            )
            fig_dow.update_traces(
                hovertemplate='<b>%{x}</b><br>Operaciones: %{y}<br>'
                              'Comisión Total: $%{customdata[0]:,.0f}<br>'
                              'Comisión Ref.: $%{customdata[1]:,.0f}<br>'
                              'Comisión Empresa: $%{customdata[2]:,.0f}<extra></extra>',
                customdata=dow_df[['commission_earnings', 'ref_commission', 'net_commission']]
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
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                SUM(COMISION)
                    - SUM(COMISION * ("% REF VENTA" / 100.0))
                    - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
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
                op_type_df, values='operations', names='TIPO OPERACION',
                title='Distribución por Tipo de Operación', hole=0.3
            )
            fig_op_type.update_traces(
                hovertemplate='<b>%{label}</b><br>Operaciones: %{value}<br>'
                              'Comisión Total: $%{customdata[0]:,.0f}<br>'
                              'Comisión Ref.: $%{customdata[1]:,.0f}<br>'
                              'Comisión Empresa: $%{customdata[2]:,.0f}<extra></extra>',
                customdata=op_type_df[['commission_earnings', 'ref_commission', 'net_commission']]
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
    
    col_geo1 = st.container()
    col_geo2 = st.container()
    
    with col_geo1:
        st.markdown("**Principales Ciudades - Compradores**")
        buyer_cities_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CIUDAD COMPRADOR" IS NOT NULL'
        buyer_cities_query = f"""
            SELECT "CIUDAD COMPRADOR" as city,
                   COUNT(*) as operations,
                   SUM(COMISION) as commission_earnings,
                   SUM(COMISION * ("% REF VENTA" / 100.0))
                       + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                   SUM(COMISION)
                       - SUM(COMISION * ("% REF VENTA" / 100.0))
                       - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission
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
            bc_display = buyer_cities_df.copy()
            bc_display['operations']         = bc_display['operations'].apply(lambda v: f"{v:,.0f}")
            bc_display['commission_earnings'] = bc_display['commission_earnings'].apply(lambda v: f"${v:,.0f}")
            bc_display['ref_commission']      = bc_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            bc_display['net_commission']      = bc_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            st.dataframe(bc_display, use_container_width=True, hide_index=True, column_config={
                'city': st.column_config.TextColumn('Ciudad'),
                'operations': st.column_config.TextColumn('Operaciones'),
                'commission_earnings': st.column_config.TextColumn('Comisión Total'),
                'ref_commission': st.column_config.TextColumn('Comisión Ref.'),
                'net_commission': st.column_config.TextColumn('Comisión Empresa'),
            })
        else:
            st.info("No hay datos de ciudades de compradores")

    with col_geo2:
        st.markdown("**Principales Ciudades - Vendedores**")
        seller_cities_where = filter_query + (" AND " if filter_query else "WHERE ") + '"CIUDAD VENDEDOR" IS NOT NULL'
        seller_cities_query = f"""
            SELECT "CIUDAD VENDEDOR" as city,
                   COUNT(*) as operations,
                   SUM(COMISION) as commission_earnings,
                   SUM(COMISION * ("% REF VENTA" / 100.0))
                       + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                   SUM(COMISION)
                       - SUM(COMISION * ("% REF VENTA" / 100.0))
                       - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission
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
            sc_display = seller_cities_df.copy()
            sc_display['operations']         = sc_display['operations'].apply(lambda v: f"{v:,.0f}")
            sc_display['commission_earnings'] = sc_display['commission_earnings'].apply(lambda v: f"${v:,.0f}")
            sc_display['ref_commission']      = sc_display['ref_commission'].apply(lambda v: f"${v:,.0f}")
            sc_display['net_commission']      = sc_display['net_commission'].apply(lambda v: f"${v:,.0f}")
            st.dataframe(sc_display, use_container_width=True, hide_index=True, column_config={
                'city': st.column_config.TextColumn('Ciudad'),
                'operations': st.column_config.TextColumn('Operaciones'),
                'commission_earnings': st.column_config.TextColumn('Comisión Total'),
                'ref_commission': st.column_config.TextColumn('Comisión Ref.'),
                'net_commission': st.column_config.TextColumn('Comisión Empresa'),
            })
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
    
    if _ref_lookup_exists:
        pareto_query = f"""
            SELECT
                sub.CLIENTE,
                sub.commission_earnings,
                sub.ref_commission,
                sub.commission_earnings - sub.ref_commission AS net_commission,
                COALESCE(r.NOMBRE, CAST(sub.main_referenciador AS VARCHAR)) AS nombre_ref
            FROM (
                SELECT
                    CLIENTE,
                    SUM(COMISION) as commission_earnings,
                    SUM(COMISION * ("% REF VENTA" / 100.0))
                        + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                    mode(REFERENCIADOR) as main_referenciador
                FROM operaciones_bmc
                {filter_query}
                GROUP BY CLIENTE
                ORDER BY commission_earnings DESC
                LIMIT 50
            ) sub
            LEFT JOIN referenciadores r ON sub.main_referenciador = r.CODIGO
        """
    else:
        pareto_query = f"""
            SELECT
                CLIENTE,
                SUM(COMISION) as commission_earnings,
                SUM(COMISION * ("% REF VENTA" / 100.0))
                    + SUM(COMISION * ("% REF COMPRA" / 100.0)) as ref_commission,
                SUM(COMISION)
                    - SUM(COMISION * ("% REF VENTA" / 100.0))
                    - SUM(COMISION * ("% REF COMPRA" / 100.0)) as net_commission,
                NULL as nombre_ref
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

        _pareto_has_ref = 'nombre_ref' in pareto_df.columns and pareto_df['nombre_ref'].notna().any()
        _pareto_cd_cols = ['ref_commission', 'net_commission']
        if _pareto_has_ref:
            _pareto_cd_cols.append('nombre_ref')

        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['CLIENTE'],
            y=pareto_df['commission_earnings'],
            name='Comisión',
            marker_color='lightblue',
            customdata=pareto_df[_pareto_cd_cols],
            hovertemplate=(
                '<b>%{x}</b><br>Comisión Total: $%{y:,.0f}<br>'
                'Comisión Ref.: $%{customdata[0]:,.0f}<br>'
                'Comisión Empresa: $%{customdata[1]:,.0f}<br>'
                + ('Referenciador: %{customdata[2]}<extra></extra>' if _pareto_has_ref else '<extra></extra>')
            )
        ))
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df['CLIENTE'],
            y=pareto_df['cumulative_pct'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            marker=dict(color='red', size=6),
            line=dict(color='red', width=2),
            customdata=pareto_df[_pareto_cd_cols],
            hovertemplate=(
                '<b>%{x}</b><br>Acumulado: %{y:.1f}%<br>'
                + ('Referenciador: %{customdata[2]}<extra></extra>' if _pareto_has_ref else '<extra></extra>')
            )
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
        anomaly_display = anomaly_df.copy()
        anomaly_display['transaction_value'] = anomaly_display['transaction_value'].apply(lambda x: f'${x:,.0f}')
        anomaly_display['actual_rate'] = anomaly_display['actual_rate'].apply(lambda x: f'{x:.2f}%')
        anomaly_display['market_avg_rate'] = anomaly_display['market_avg_rate'].apply(lambda x: f'{x:.2f}%')
        anomaly_display['discount_pct'] = anomaly_display['discount_pct'].apply(lambda x: f'{x:.1f}%')
        st.dataframe(
            anomaly_display,
            width="stretch",
            hide_index=True,
            column_config={
                'OPERACION': st.column_config.TextColumn('Operación', help='Identificador único de la operación en el sistema BMC.'),
                'CLIENTE': st.column_config.TextColumn('Cliente', help='Nombre del cliente que realizó esta transacción.'),
                'NOMBRE PRODUCTO': st.column_config.TextColumn('Producto', help='Producto agrícola negociado en esta operación.'),
                'transaction_value': st.column_config.TextColumn('Valor Negocio', help='Valor total de la transacción.\nFórmula: SUM("VALOR NEGOCIO")'),
                'actual_rate': st.column_config.TextColumn('Tasa Real', help='Tasa de comisión cobrada en esta operación específica.\nFórmula: (COMISION / VALOR NEGOCIO) × 100'),
                'market_avg_rate': st.column_config.TextColumn('Tasa Promedio Mercado', help='Tasa promedio de comisión para este producto en todas las operaciones del período filtrado.\nFórmula: AVG(COMISION / VALOR NEGOCIO) × 100 — agrupado por producto'),
                'discount_pct': st.column_config.TextColumn('Descuento %', help='Cuánto por debajo del promedio está la tasa real. Valores altos indican mayor descuento o posible error.\nFórmula: ((Tasa Promedio − Tasa Real) / Tasa Promedio) × 100'),
            }
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
    
    col_size1 = st.container()
    col_size2 = st.container()
    
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
            size_display = size_df.copy()
            size_display['transaction_count'] = size_display['transaction_count'].apply(lambda x: f'{int(x):,}')
            size_display['total_commission'] = size_display['total_commission'].apply(lambda x: f'${x:,.0f}')
            size_display['avg_commission_rate'] = size_display['avg_commission_rate'].apply(lambda x: f'{x:.2f}%')
            st.dataframe(
                size_display,
                width="stretch",
                hide_index=True,
                column_config={
                    'size_category': st.column_config.TextColumn('Categoría', help='Rango de valor de la transacción:\n• Pequeña: < $1M\n• Mediana: $1M–$10M\n• Grande: $10M–$50M\n• Muy Grande: > $50M'),
                    'transaction_count': st.column_config.TextColumn('Operaciones', help='Número de transacciones en este rango de tamaño.\nFórmula: COUNT(*)'),
                    'total_commission': st.column_config.TextColumn('Comisión Total', help='Suma de comisiones brutas cobradas en transacciones de este tamaño.\nFórmula: SUM(COMISION)'),
                    'avg_commission_rate': st.column_config.TextColumn('Tasa Prom. Comisión', help='Tasa de comisión promedio para transacciones de este tamaño.\nFórmula: AVG(COMISION / VALOR NEGOCIO) × 100'),
                }
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
