"""
╔══════════════════════════════════════════════════════════════════╗
║          S&P 500 — Dashboard de Valoración Financiera           ║
║          Desarrollado con Streamlit + yfinance                  ║
╚══════════════════════════════════════════════════════════════════╝

Uso:
    pip install streamlit yfinance pandas
    streamlit run sp500_dashboard.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GENERAL DE PÁGINA
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="S&P 500 Valoración",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personalizado: colores del semáforo y estilo general
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .metric-box {
        background: #1e2130;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .badge-green  { background:#1a4731; color:#4ade80; padding:3px 10px; border-radius:12px; font-weight:700; font-size:.85rem; }
    .badge-yellow { background:#422006; color:#fbbf24; padding:3px 10px; border-radius:12px; font-weight:700; font-size:.85rem; }
    .badge-red    { background:#4c0519; color:#f87171; padding:3px 10px; border-radius:12px; font-weight:700; font-size:.85rem; }
    .pine-block {
        background:#0d1117; color:#a3e635;
        font-family: monospace; font-size:.82rem;
        padding:14px; border-radius:8px;
        border:1px solid #2d333b;
        white-space: pre-wrap; word-break: break-all;
    }
    h1 { font-size:1.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# DICCIONARIO DE PROMEDIOS SECTORIALES DE PER
# ─────────────────────────────────────────────────────────────────
# Ajusta estos valores manualmente según las condiciones del mercado.
# Fuentes de referencia: Damodaran Online (stern.nyu.edu/~adamodar),
# Bloomberg Sector Composites, FactSet Earnings Insight.
# Última revisión sugerida: trimestral.
SECTOR_PER_PROMEDIO = {
    # ── Tecnología: valuaciones altas por crecimiento sostenido
    "Technology":               28,

    # ── Comunicaciones: mix de growth (streaming) y value (telcos)
    "Communication Services":   22,

    # ── Consumo discrecional: cíclico, sensible a tasas de interés
    "Consumer Discretionary":   25,

    # ── Consumo básico: defensivo, dividendos estables, baja volatilidad
    "Consumer Staples":         20,

    # ── Energía: valuación baja, muy dependiente del precio del crudo
    "Energy":                   12,

    # ── Financiero: bancos, seguros; PER históricamente bajo
    "Financials":               14,

    # ── Salud: mix de farmacéuticas (growth) y hospitales (estable)
    "Health Care":              22,

    # ── Industriales: cíclico, ligado al ciclo económico global
    "Industrials":              20,

    # ── Materiales: commodities, cíclico, bajo PER en recesión
    "Materials":                16,

    # ── Inmobiliario (REITs): métrica principal = FFO, PER referencial
    "Real Estate":              35,

    # ── Utilidades: defensivo, alto dividendo, PER bajo y estable
    "Utilities":                16,
}


# ─────────────────────────────────────────────────────────────────
# UNIVERSO COMPLETO DE TICKERS S&P 500 POR SECTOR (GICS)
# Clasificación GICS vigente 2024-2025.
# Fuente: S&P Dow Jones Indices + MSCI GICS.
# Nota: el S&P 500 actualiza su composición trimestralmente;
# revisa https://www.spglobal.com/spdji/en/indices/equity/sp-500/
# para incorporar altas y bajas recientes.
# ─────────────────────────────────────────────────────────────────
TICKERS_POR_SECTOR = {

    # ── TECHNOLOGY (~65 empresas) ─────────────────────────────────
    # Hardware, semiconductores, software empresarial, IT services y
    # equipos de comunicaciones clasificados bajo GICS "Information Technology".
    "Technology": [
        # Megacaps / hardware de consumo
        "AAPL", "MSFT", "NVDA", "AVGO", "ORCL",
        # Software empresarial / cloud
        "ADBE", "CRM", "NOW", "INTU", "PANW", "CRWD", "FTNT", "CDNS", "SNPS", "ANSS",
        # Semiconductores
        "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "ADI", "MCHP",
        "NXPI", "MPWR", "ON", "SWKS", "QRVO", "TER", "KEYS",
        # IT Services / Consultoría
        "ACN", "IBM", "CTSH", "IT", "EPAM", "LDOS", "SAIC", "CDAY", "PAYC", "PCTY",
        # Hardware / Networking / Almacenamiento
        "CSCO", "HPQ", "HPE", "WDC", "STX", "NTAP", "JNPR", "FFIV",
        # Conectores / componentes electrónicos
        "TEL", "APH", "GLW", "ZBRA",
        # Software / SaaS de nicho
        "GDDY", "GEN", "VRSN", "PTC", "TYL", "ROP", "AKAM",
        # Infraestructura de energía para centros de datos
        "VRT",
        # Distribución tecnológica
        "CDW",
        # Manufactura electrónica / EMS
        "MSI",
    ],

    # ── COMMUNICATION SERVICES (~25 empresas) ─────────────────────
    # Plataformas digitales, medios, entretenimiento y telecomunicaciones.
    "Communication Services": [
        # Plataformas digitales / publicidad
        "GOOGL", "GOOG", "META",
        # Streaming / entretenimiento
        "NFLX", "DIS", "CMCSA", "WBD", "PARA",
        # Telecomunicaciones
        "T", "VZ", "TMUS", "CHTR", "LUMN",
        # Videojuegos
        "EA", "TTWO",
        # Medios tradicionales / publicidad
        "OMC", "IPG", "NWS", "NWSA", "FOXA", "FOX",
        # Live entertainment / eventos
        "LYV",
        # Dating / apps sociales
        "MTCH",
    ],

    # ── CONSUMER DISCRETIONARY (~55 empresas) ─────────────────────
    # Bienes y servicios no esenciales: retail, autos, hoteles,
    # restaurantes, viajes y ocio.
    "Consumer Discretionary": [
        # E-commerce / megacap
        "AMZN",
        # Vehículos eléctricos / autos
        "TSLA", "GM", "F", "APTV", "BWA", "LEA",
        # Home improvement / construcción
        "HD", "LOW", "MHK", "WHR",
        # Constructores residenciales
        "DHI", "LEN", "PHM", "NVR", "TOL",
        # Restaurantes / foodservice
        "MCD", "SBUX", "CMG", "YUM", "DRI",
        # Viajes / hotelería
        "BKNG", "MAR", "HLT", "ABNB",
        # Cruceros
        "RCL", "CCL", "NCLH",
        # Casinos / juego
        "MGM", "CZR", "WYNN", "LVS",
        # Apuestas deportivas online
        "DKNG",
        # Calzado / apparel
        "NKE", "PVH", "RL", "TPR", "VFC", "HAS", "MAT",
        # Retail especializado
        "TJX", "ROST", "TGT", "BBY", "ULTA",
        # Descuento / valor
        "DG", "DLTR",
        # Autopartes / distribución
        "AZO", "ORLY", "GPC", "AAP",
        # Carros usados
        "KMX",
        # E-commerce / marketplace
        "ETSY", "EBAY",
    ],

    # ── CONSUMER STAPLES (~38 empresas) ───────────────────────────
    # Alimentos, bebidas, tabaco, higiene y farmacéuticos minoristas.
    "Consumer Staples": [
        # Retail masivo / clubes
        "WMT", "COST", "KR",
        # Higiene personal / hogar
        "PG", "CL", "KMB", "CHD", "CLX",
        # Bebidas
        "KO", "PEP", "STZ", "BF-B", "TAP", "MNST",
        # Tabaco
        "PM", "MO",
        # Snacks / alimentos empacados
        "MDLZ", "KHC", "GIS", "K", "CPB", "HRL", "CAG", "MKC", "SJM",
        # Productos de belleza / lujo masivo
        "EL",
        # Commodities agrícolas / procesamiento
        "ADM", "BG",
        # Farmacéutico / retail salud
        "WBA", "CVS",
        # Distribución foodservice
        "SYY",
    ],

    # ── ENERGY (~26 empresas) ─────────────────────────────────────
    # Upstream (E&P), downstream (refinación), servicios y midstream.
    "Energy": [
        # Integradas / megacaps
        "XOM", "CVX",
        # E&P (Exploración y Producción)
        "COP", "EOG", "PXD", "DVN", "HES", "FANG", "MRO", "OXY", "APA",
        # Refinación / downstream
        "MPC", "PSX", "VLO",
        # Servicios de campo petrolero
        "SLB", "HAL", "BKR", "NOV",
        # Midstream / gasoductos
        "OKE", "WMB", "KMI", "TRGP",
        # Perforación
        "HP",
    ],

    # ── FINANCIALS (~60 empresas) ─────────────────────────────────
    # Bancos, seguros, gestores de activos, mercados de capitales y
    # fintech regulado.
    "Financials": [
        # Holding diversificado
        "BRK-B",
        # Bancos universales (Bulge Bracket)
        "JPM", "BAC", "WFC", "C", "GS", "MS",
        # Bancos regionales grandes
        "USB", "PNC", "TFC", "MTB", "FITB", "RF", "HBAN", "CFG", "KEY", "ZION", "CMA",
        # Tarjetas / pagos
        "AXP", "COF", "DFS", "SYF",
        # Brokerage / wealth management
        "SCHW", "RJF",
        # Gestión de activos
        "BLK", "TROW", "BEN", "IVZ", "AMP", "LM",
        # Custodia / servicios de valores
        "BK", "STT", "NTRS",
        # Seguros de propiedad/accidentes
        "PGR", "TRV", "CB", "ALL", "HIG", "AIG", "CINF", "EG", "RNR",
        # Seguros de vida
        "MET", "PRU", "AFL", "LNC", "UNM", "GL",
        # Seguros de garantía hipotecaria / título
        "FNF", "FAF",
        # Intermediación / corretaje seguros
        "MMC", "AON",
        # Financiamiento al consumidor
        "ALLY", "SLM",
        # Bolsas / índices / datos
        "ICE", "CME", "CBOE", "NDAQ", "MSCI", "SPGI", "MCO", "FDS",
    ],

    # ── HEALTH CARE (~57 empresas) ────────────────────────────────
    # Farmacéuticas, biotecnología, dispositivos médicos, distribución
    # y managed care (seguros de salud).
    "Health Care": [
        # Farmacéuticas grandes
        "LLY", "JNJ", "ABBV", "MRK", "PFE", "BMY",
        # Biotecnología
        "AMGN", "BIIB", "REGN", "VRTX", "MRNA", "ILMN", "BIO",
        # Diagnóstico / instrumentos de laboratorio
        "TMO", "DHR", "A", "MTD", "IDXX", "TECH",
        # Dispositivos médicos
        "ABT", "MDT", "SYK", "BSX", "ISRG", "EW", "BDX", "ZBH", "COO",
        "RMD", "HOLX", "DXCM", "ALGN", "BAX", "TFX", "WST", "PODD",
        # Sterilización / servicios hospitalarios
        "STE", "GEHC",
        # CRO / servicios de ensayos clínicos
        "IQV", "CTLT",
        # Managed Care / seguros de salud
        "UNH", "ELV", "CI", "HUM", "MOH", "CNC",
        # Hospitales / instalaciones
        "HCA", "THC", "UHS", "DVA",
        # Distribución mayorista farmacéutica
        "MCK", "ABC", "CAH", "COR",
        # Retail farmacéutico y seguros combinados
        "CVS",
        # Suministros odontológicos / veterinarios
        "HSIC", "ZTS",
    ],

    # ── INDUSTRIALS (~75 empresas) ────────────────────────────────
    # Aeroespacial & defensa, transporte, maquinaria, construcción,
    # servicios comerciales y conglomerados.
    "Industrials": [
        # Aeroespacial & defensa
        "LMT", "RTX", "BA", "GD", "NOC", "LHX", "TDG", "HWM", "TXT", "HEI", "TDY",
        # Conglomerados industriales
        "GE", "HON", "MMM", "ETN", "EMR", "ITW", "PH",
        # Maquinaria / equipo pesado
        "CAT", "DE", "IR", "ROK", "AME", "FTV", "GNRC", "PNR", "XYL",
        "IDEX", "SWK", "SNA", "RRX", "TT", "SPX",
        # Materiales de construcción / productos de construcción
        "AOS", "MAS", "ALLE", "LII", "AWI", "FBIN",
        # Paquetería / logística
        "UPS", "FDX",
        # Ferroviarias
        "UNP", "CSX", "NSC", "CP", "CNI",
        # Camiones / transporte terrestre
        "ODFL", "SAIA", "XPO", "GXO", "JBHT", "CHRW",
        # Gestión de residuos / medio ambiente
        "WM", "RSG",
        # Productos químicos especializados para industria
        "ECL",
        # Servicios uniformes / limpieza
        "CTAS",
        # Distribución industrial
        "GWW", "MSC", "FAST", "AIT", "WESCO",
        # Seguridad / vigilancia
        "AXON",
        # Análisis de datos / verificación
        "VRSK",
        # Defensa cibernética / IT gobierno
        "CACI",
        # Subasta / recuperación de activos
        "CPRT",
        # Equipos de climatización / HVAC
        "WSO",
    ],

    # ── MATERIALS (~28 empresas) ──────────────────────────────────
    # Metales, minería, químicos, papel/embalaje y materiales de construcción.
    "Materials": [
        # Gases industriales
        "LIN", "APD",
        # Pinturas / recubrimientos
        "SHW", "PPG", "RPM",
        # Químicos diversificados / especialidades
        "DOW", "IFF", "EMN", "CE", "OLN",
        # Fertilizantes / agroinsumos
        "CF", "MOS", "NTR",
        # Cobre / metales base
        "FCX",
        # Oro / metales preciosos
        "NEM",
        # Acero / metales ferrosos
        "NUE", "STLD", "RS", "CMC", "CLF", "X", "ATI",
        # Aluminio
        "AA",
        # Agregados / cemento
        "VMC", "MLM",
        # Litio / materiales de baterías
        "ALB",
        # Embalaje metálico
        "CCK", "BALL",
        # Papel / embalaje de cartón
        "PKG", "IP", "WRK", "SON",
        # Embalaje plástico
        "BERY", "SEE", "SLGN",
        # Tierras raras
        "MP",
    ],

    # ── REAL ESTATE (~42 empresas) ────────────────────────────────
    # REITs de diversas categorías: industrial, retail, residencial,
    # oficinas, salud, hospedaje y almacenamiento.
    "Real Estate": [
        # Industrial / logística
        "PLD", "REXR", "EGP", "STAG",
        # Torres de telecomunicaciones / infraestructura digital
        "AMT", "CCI", "SBA",
        # Centros de datos
        "EQIX", "DLR",
        # Self-storage
        "PSA", "EXR", "CUBE", "NSA",
        # Retail / centros comerciales
        "SPG", "O", "NNN", "REG", "KIM", "BRX", "FRT", "EPRT",
        # Residencial multifamiliar (apartamentos)
        "AVB", "EQR", "ESS", "MAA", "UDR", "CPT",
        # Viviendas unifamiliares en alquiler
        "INVH", "AMH",
        # Manufactured housing / RV parks
        "SUI", "ELS",
        # Salud / senior housing
        "WELL", "VTR", "PEAK", "OHI", "MPW", "CTRE",
        # Hospitalidad / hoteles
        "HST", "RHP", "PK",
        # Ciencias biológicas / laboratorios
        "ARE",
        # Oficinas
        "BXP", "SLG", "KRC", "DEI",
        # Cannabis / industrial especializado
        "IIPR",
        # Frío / cadena de frío
        "COLD",
    ],

    # ── UTILITIES (~30 empresas) ──────────────────────────────────
    # Eléctricas, gas natural, agua y multi-utilities.
    "Utilities": [
        # Eléctricas con gran exposición a renovables
        "NEE", "AES", "EVRG",
        # Eléctricas del sur / este
        "SO", "DUK", "D", "FE", "EIX", "PCG",
        # Eléctricas del centro / oeste
        "AEP", "XEL", "SRE", "EXC", "ETR", "CNP", "NI", "WEC", "LNT",
        # Agua
        "AWK",
        # Gas natural / multi-utility
        "PEG", "ES", "ED",
        # Pequeñas y medianas eléctricas regionales
        "PPL", "OGE", "AGR", "BKH", "NWE", "POR", "AVA", "MGEE", "OTTR",
    ],
}

# Recuento orientativo de empresas por sector (mayo 2025):
# Technology: 65 | Communication Services: 21 | Consumer Discretionary: 49
# Consumer Staples: 38 | Energy: 26 | Financials: 60 | Health Care: 57
# Industrials: 75 | Materials: 28 | Real Estate: 42 | Utilities: 30
# TOTAL ≈ 491 tickers únicos


# ─────────────────────────────────────────────────────────────────
# FUNCIONES DE DATOS
# ─────────────────────────────────────────────────────────────────

def _crear_sesion() -> requests.Session:
    """
    Crea una sesión HTTP con User-Agent de navegador real.
    Streamlit Cloud comparte IPs con miles de apps; Yahoo Finance
    bloquea peticiones sin cabecera de navegador válida.
    Pasar esta sesión a yfinance evita el error 401/429.
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_datos_ticker(ticker: str, sector: str) -> dict:
    """
    Descarga métricas financieras de un ticker via yfinance.
    — Usa sesión con User-Agent real para evitar bloqueos en Streamlit Cloud.
    — Reintenta hasta 3 veces con pausa incremental ante errores de red.
    """
    vacio = {
        "Ticker":      ticker,
        "Nombre":      ticker,
        "Sector":      sector,
        "Precio ($)":  None,
        "PER":         None,
        "Forward PER": None,
        "PEG":         None,
    }

    for intento in range(3):
        try:
            sesion = _crear_sesion()
            obj    = yf.Ticker(ticker, session=sesion)
            info   = obj.info

            # info vacío o sin datos reales → reintento
            if not info or len(info) < 5:
                time.sleep(1.5 * (intento + 1))
                continue

            precio      = info.get("currentPrice") or info.get("regularMarketPrice")
            trailing_pe = info.get("trailingPE")
            forward_pe  = info.get("forwardPE")
            peg         = info.get("pegRatio")
            nombre      = info.get("shortName", ticker)

            return {
                "Ticker":      ticker,
                "Nombre":      nombre,
                "Sector":      sector,
                "Precio ($)":  round(precio, 2)      if precio      is not None else None,
                "PER":         round(trailing_pe, 2) if trailing_pe is not None else None,
                "Forward PER": round(forward_pe, 2)  if forward_pe  is not None else None,
                "PEG":         round(peg, 2)         if peg         is not None else None,
            }

        except Exception:
            # Pausa exponencial: 1 s → 2 s → 4 s entre intentos
            if intento < 2:
                time.sleep(2 ** intento)

    return vacio


def clasificar_valoracion(per, peg, per_promedio_sector) -> tuple[str, str]:
    """
    Aplica la lógica de semáforo según PER y PEG vs. el promedio sectorial.

    Retorna (etiqueta, emoji_color).

    VERDE  (Compra Potencial) : PER < promedio sectorial  AND  PEG < 1.0
    AMARILLO (Mantenimiento)  : PER dentro de ±20 % del promedio sectorial
    ROJO (Alerta Corrección)  : PER > promedio * 1.5  OR  PEG > 2.0
    """
    if per is None or per <= 0:
        return ("⚪ Sin Datos", "⚪")

    if per < per_promedio_sector and (peg is not None and peg < 1.0):
        return ("🟢 Compra Potencial", "🟢")

    if per > per_promedio_sector * 1.5 or (peg is not None and peg > 2.0):
        return ("🔴 Alerta Corrección", "🔴")

    # Rango ≈ promedio (±20 %)
    if abs(per - per_promedio_sector) / per_promedio_sector <= 0.20:
        return ("🟡 Mantenimiento", "🟡")

    # PER alto pero PEG aceptable → amarillo moderado
    return ("🟡 Mantenimiento", "🟡")


def cargar_datos_sector(sector: str) -> pd.DataFrame:
    """Carga todos los tickers de un sector y ensambla el DataFrame final."""
    tickers = TICKERS_POR_SECTOR.get(sector, [])
    per_ref = SECTOR_PER_PROMEDIO.get(sector, 20)
    registros = []

    progress_bar = st.progress(0, text=f"Descargando datos de {sector}…")
    for i, ticker in enumerate(tickers):
        datos = obtener_datos_ticker(ticker, sector)
        valoracion, _ = clasificar_valoracion(datos["PER"], datos["PEG"], per_ref)
        datos["Valoración"] = valoracion
        datos["PER Ref. Sector"] = per_ref
        registros.append(datos)
        progress_bar.progress((i + 1) / len(tickers),
                              text=f"Procesando {ticker} ({i+1}/{len(tickers)})…")
        time.sleep(0.4)   # pausa anti-rate-limit para Streamlit Cloud

    progress_bar.empty()
    return pd.DataFrame(registros)


def cargar_todos_los_sectores() -> pd.DataFrame:
    """
    Carga el S&P 500 completo (~491 tickers) sector por sector.
    Cada acción es comparada contra el PER de referencia de SU propio sector,
    no contra un único valor global.
    """
    sectores = list(TICKERS_POR_SECTOR.keys())
    total_tickers = sum(len(v) for v in TICKERS_POR_SECTOR.values())
    procesados   = 0
    dfs_sectores = []

    barra_global  = st.progress(0, text="Iniciando carga del S&P 500 completo…")
    texto_estado  = st.empty()

    for sector in sectores:
        tickers = TICKERS_POR_SECTOR[sector]
        per_ref = SECTOR_PER_PROMEDIO.get(sector, 20)
        registros = []

        texto_estado.markdown(
            f"📂 **Sector actual:** `{sector}` "
            f"({len(tickers)} empresas) — "
            f"Total procesado: **{procesados}/{total_tickers}**"
        )

        for ticker in tickers:
            datos = obtener_datos_ticker(ticker, sector)
            valoracion, _ = clasificar_valoracion(datos["PER"], datos["PEG"], per_ref)
            datos["Valoración"]      = valoracion
            datos["PER Ref. Sector"] = per_ref
            registros.append(datos)
            procesados += 1
            barra_global.progress(
                procesados / total_tickers,
                text=f"[{sector}] {ticker} — {procesados}/{total_tickers} tickers"
            )
            time.sleep(0.4)   # pausa anti-rate-limit para Streamlit Cloud

        dfs_sectores.append(pd.DataFrame(registros))

    barra_global.empty()
    texto_estado.empty()
    return pd.concat(dfs_sectores, ignore_index=True)


# ─────────────────────────────────────────────────────────────────
# FORMATO CONDICIONAL PARA DATAFRAME
# ─────────────────────────────────────────────────────────────────

def colorear_valoracion(val: str) -> str:
    """Devuelve el estilo CSS según la etiqueta de valoración."""
    if "Compra"  in val: return "background-color:#1a4731; color:#4ade80; font-weight:700;"
    if "Alerta"  in val: return "background-color:#4c0519; color:#f87171; font-weight:700;"
    if "Manten"  in val: return "background-color:#422006; color:#fbbf24; font-weight:700;"
    return ""

def colorear_per(val, per_ref: float):
    """Colorea la celda de PER según su relación con el promedio sectorial."""
    if pd.isna(val) or val is None:
        return ""
    if val < per_ref:
        return "color:#4ade80;"
    if val > per_ref * 1.5:
        return "color:#f87171;"
    return "color:#fbbf24;"

def colorear_per_fila(row) -> pd.Series:
    """
    Versión row-wise de colorear_per para usar con df.style.apply(axis=1).
    Necesaria en la vista 'Todas' donde cada fila tiene su propio PER Ref.
    """
    result = pd.Series("", index=row.index)
    if "PER" in row.index and "PER Ref. Sector" in row.index:
        result["PER"] = colorear_per(row["PER"], row["PER Ref. Sector"])
    return result


# ─────────────────────────────────────────────────────────────────
# GENERADOR DE SNIPPET PINE SCRIPT
# ─────────────────────────────────────────────────────────────────

def generar_pine_snippet(df: pd.DataFrame) -> str:
    """
    Genera un bloque de texto compatible con Pine Script (TradingView)
    para cada ticker del DataFrame, listo para pegar en un indicador.
    """
    lineas = [
        "// ═══════════════════════════════════════════════════",
        f"// S&P 500 Valoración — Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "// ═══════════════════════════════════════════════════",
        "// Pega este bloque en la sección de comentarios o",
        "// tabla de tu indicador Pine Script.",
        "",
    ]

    for _, row in df.iterrows():
        per      = row.get("PER",         "N/A")
        f_per    = row.get("Forward PER", "N/A")
        peg      = row.get("PEG",         "N/A")
        val_raw  = row.get("Valoración",  "N/A")
        # Limpiamos los emojis para Pine Script
        val = val_raw.replace("🟢", "").replace("🔴", "").replace("🟡", "").strip()

        lineas.append(
            f'// [{row["Ticker"]}]  '
            f'PER={per}, F_PER={f_per}, PEG={peg}, '
            f'VAL="{val}", PRECIO={row.get("Precio ($)", "N/A")}'
        )

    lineas += [
        "",
        "// Uso sugerido en Pine Script:",
        '// var table t = table.new(position.top_right, 5, 20)',
        '// table.cell(t, 0, 0, "Ticker") ...',
    ]
    return "\n".join(lineas)


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Panel de Control")
    st.markdown("---")

    # "⭐ Todas" siempre aparece primero en la lista
    opciones_sector = ["⭐ Todas"] + list(TICKERS_POR_SECTOR.keys())

    sector_seleccionado = st.selectbox(
        "🏭 Sector",
        options=opciones_sector,
        index=0,
        help="Elige un sector específico o '⭐ Todas' para ver el S&P 500 completo.",
    )

    modo_todas = (sector_seleccionado == "⭐ Todas")

    # El control de PER manual solo aplica cuando se analiza UN sector concreto.
    # En modo "Todas" cada acción usa el PER de referencia de su propio sector.
    if modo_todas:
        per_ref_manual = None   # señal de "usar PER por sector"
        st.info(
            "🌐 **Modo S&P 500 completo**\n\n"
            "Cada acción se compara contra el PER de referencia "
            "de **su propio sector** (definido en `SECTOR_PER_PROMEDIO`).\n\n"
            "El override manual de PER no aplica en esta vista."
        )
    else:
        per_ref_manual = st.number_input(
            "📐 PER de referencia sectorial",
            min_value=1.0,
            max_value=100.0,
            value=float(SECTOR_PER_PROMEDIO[sector_seleccionado]),
            step=0.5,
            help="Sobreescribe el PER de referencia del sector para este análisis.",
        )

    st.markdown("---")
    st.markdown("### 🎯 Filtro de Semáforo")
    filtros_val = st.multiselect(
        "Mostrar solo:",
        options=["🟢 Compra Potencial", "🟡 Mantenimiento", "🔴 Alerta Corrección", "⚪ Sin Datos"],
        default=["🟢 Compra Potencial", "🟡 Mantenimiento", "🔴 Alerta Corrección", "⚪ Sin Datos"],
    )

    st.markdown("---")
    cargar = st.button("🔄 Cargar / Actualizar Datos", use_container_width=True, type="primary")

    st.markdown("---")
    if modo_todas:
        total_tickers = sum(len(v) for v in TICKERS_POR_SECTOR.values())
        segundos_est  = total_tickers * 1.2
        minutos_est   = int(segundos_est // 60)
        segs_rest     = int(segundos_est % 60)
        st.warning(
            f"⚠️ **{total_tickers} empresas** en total.\n\n"
            f"⏱️ Carga estimada: **~{minutos_est}m {segs_rest}s**\n\n"
            "Los datos se guardan en caché 1 hora tras la primera carga."
        )
    else:
        n_tickers    = len(TICKERS_POR_SECTOR.get(sector_seleccionado, []))
        segundos_est = n_tickers * 1.2
        minutos_est  = int(segundos_est // 60)
        segs_rest    = int(segundos_est % 60)
        tiempo_str   = f"{minutos_est}m {segs_rest}s" if minutos_est else f"{segs_rest}s"
        st.info(
            f"**{n_tickers} empresas** en este sector.\n\n"
            f"⏱️ Carga estimada: **~{tiempo_str}**\n\n"
            "Los datos se guardan en caché 1 hora."
        )
    st.caption(
        "Datos: [yfinance](https://github.com/ranaroussi/yfinance) · "
        "PER sectoriales: Damodaran / FactSet  \n"
        "⚠️ Solo con fines educativos. No es asesoramiento financiero."
    )


# ─────────────────────────────────────────────────────────────────
# ESTADO DE SESIÓN
# ─────────────────────────────────────────────────────────────────

if "df_actual" not in st.session_state:
    st.session_state.df_actual   = pd.DataFrame()
    st.session_state.sector_cargado = None


# ─────────────────────────────────────────────────────────────────
# ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────────────────────────

st.markdown("# 📊 S&P 500 — Dashboard de Valoración")
if modo_todas:
    st.markdown(
        f"**Vista:** `S&P 500 Completo` · "
        f"**PER:** referencia por sector · "
        f"**Actualizado:** {datetime.now().strftime('%H:%M:%S')}"
    )
else:
    st.markdown(
        f"**Sector seleccionado:** `{sector_seleccionado}` · "
        f"**PER de referencia:** `{per_ref_manual}` · "
        f"**Actualizado:** {datetime.now().strftime('%H:%M:%S')}"
    )
st.divider()


# ─────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────

if cargar or (st.session_state.sector_cargado != sector_seleccionado
              and st.session_state.df_actual.empty):
    if modo_todas:
        with st.spinner("Conectando con Yahoo Finance para el **S&P 500 completo**…"):
            df = cargar_todos_los_sectores()
            # En modo Todas cada fila ya tiene su propio PER Ref. Sector
            # → la clasificación se hizo dentro de cargar_todos_los_sectores()
            st.session_state.df_actual      = df
            st.session_state.sector_cargado = sector_seleccionado
    else:
        with st.spinner(f"Conectando con Yahoo Finance para **{sector_seleccionado}**…"):
            df = cargar_datos_sector(sector_seleccionado)
            # Re-clasificar con el PER manual del sidebar
            df[["Valoración", "_color"]] = df.apply(
                lambda r: pd.Series(clasificar_valoracion(r["PER"], r["PEG"], per_ref_manual)),
                axis=1,
            )
            df.drop(columns=["_color"], inplace=True, errors="ignore")
            df["PER Ref. Sector"] = per_ref_manual
            st.session_state.df_actual      = df
            st.session_state.sector_cargado = sector_seleccionado
else:
    df = st.session_state.df_actual
    # Re-aplicar PER manual solo en modo sector único
    if not df.empty and not modo_todas:
        df[["Valoración", "_color"]] = df.apply(
            lambda r: pd.Series(clasificar_valoracion(r["PER"], r["PEG"], per_ref_manual)),
            axis=1,
        )
        df.drop(columns=["_color"], inplace=True, errors="ignore")
        df["PER Ref. Sector"] = per_ref_manual


# ─────────────────────────────────────────────────────────────────
# BLOQUE PRINCIPAL: MÉTRICAS Y TABLA
# ─────────────────────────────────────────────────────────────────

if df.empty:
    st.info("👈 Haz clic en **Cargar / Actualizar Datos** en el panel izquierdo.")
    st.stop()

# Filtro de semáforo
df_filtrado = df[df["Valoración"].isin(filtros_val)] if filtros_val else df

# ── KPIs del sector ───────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
label_empresas = "🏢 Total S&P 500" if modo_todas else "🏢 Empresas analizadas"
n_sin_datos = len(df[df["Valoración"] == "⚪ Sin Datos"])
col1.metric(label_empresas,            len(df))
col2.metric("✅ Compra Potencial",     len(df[df["Valoración"].str.contains("Compra", na=False)]))
col3.metric("⚠️ Mantenimiento",        len(df[df["Valoración"].str.contains("Manten", na=False)]))
col4.metric("🚨 Alerta Corrección",   len(df[df["Valoración"].str.contains("Alerta", na=False)]))
col5.metric("⚪ Sin Datos",            n_sin_datos)

# Aviso si Yahoo Finance bloqueó muchas peticiones
pct_sin_datos = n_sin_datos / len(df) if len(df) > 0 else 0
if pct_sin_datos > 0.5:
    st.warning(
        f"⚠️ **{n_sin_datos} de {len(df)} tickers** devolvieron Sin Datos "
        f"({pct_sin_datos:.0%}). "
        "Yahoo Finance puede estar limitando las peticiones desde Streamlit Cloud. "
        "Espera unos minutos y pulsa **Cargar / Actualizar Datos** para reintentar. "
        "Los reintentos automáticos ya están activos (hasta 3 intentos por ticker)."
    )
elif n_sin_datos > 0:
    st.info(f"ℹ️ {n_sin_datos} ticker(s) sin datos. Puedes filtrarlos con el semáforo del sidebar.")

st.divider()

# ── Tabla principal con formato condicional ───────────────────────
st.subheader("📋 Tabla de Valoración")

columnas_mostrar = ["Ticker", "Nombre", "Sector", "Precio ($)", "PER",
                    "Forward PER", "PEG", "PER Ref. Sector", "Valoración"]
df_display = df_filtrado[columnas_mostrar].copy()

styled = (
    df_display.style
    .map(colorear_valoracion, subset=["Valoración"])
    # Usamos apply(axis=1) para que cada fila use su propio PER Ref. Sector
    .apply(colorear_per_fila, axis=1)
    .format({
        "Precio ($)":      lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A",
        "PER":             lambda x: f"{x:.1f}"   if pd.notna(x) else "N/A",
        "Forward PER":     lambda x: f"{x:.1f}"   if pd.notna(x) else "N/A",
        "PEG":             lambda x: f"{x:.2f}"   if pd.notna(x) else "N/A",
        "PER Ref. Sector": lambda x: f"{x:.0f}"   if pd.notna(x) else "N/A",
    })
    .set_properties(**{"text-align": "center"})
    .set_table_styles([
        {"selector": "th", "props": [("text-align", "center"), ("font-weight", "bold")]}
    ])
)

st.dataframe(styled, use_container_width=True, height=420)

st.divider()

# ─────────────────────────────────────────────────────────────────
# DETALLE DE ACCIÓN SELECCIONADA (st.metric)
# ─────────────────────────────────────────────────────────────────

st.subheader("🔍 Análisis Individual")

ticker_sel = st.selectbox(
    "Selecciona un ticker para ver detalle:",
    options=df_filtrado["Ticker"].tolist(),
    index=0,
)

if ticker_sel:
    fila = df_filtrado[df_filtrado["Ticker"] == ticker_sel].iloc[0]
    # Usar el PER de referencia del sector propio del ticker
    per_ref_ticker = fila["PER Ref. Sector"]

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("💵 Precio",       f"${fila['Precio ($)']:,.2f}" if pd.notna(fila["Precio ($)"]) else "N/A")
    mc2.metric("📈 PER (TTM)",    f"{fila['PER']:.1f}"         if pd.notna(fila["PER"])         else "N/A",
               delta=f"Ref sector: {per_ref_ticker:.0f}",
               delta_color="inverse" if pd.notna(fila["PER"]) and fila["PER"] > per_ref_ticker else "normal")
    mc3.metric("🔭 Forward PER",  f"{fila['Forward PER']:.1f}" if pd.notna(fila["Forward PER"]) else "N/A")
    mc4.metric("📐 PEG Ratio",    f"{fila['PEG']:.2f}"         if pd.notna(fila["PEG"])         else "N/A",
               delta="< 1.0 = Atractivo" if pd.notna(fila["PEG"]) and fila["PEG"] < 1.0 else "> 2.0 = Caro",
               delta_color="normal"      if pd.notna(fila["PEG"]) and fila["PEG"] < 1.0 else "inverse")
    mc5.metric("🚦 Valoración",    fila["Valoración"])

    st.caption(
        f"**{fila['Nombre']}** — {fila['Sector']} | "
        f"PER de referencia sectorial: **{per_ref_ticker:.0f}**"
    )

st.divider()


# ─────────────────────────────────────────────────────────────────
# EXPORTACIÓN PINE SCRIPT
# ─────────────────────────────────────────────────────────────────

st.subheader("🌲 Exportar a Pine Script (TradingView)")

with st.expander("ℹ️ ¿Cómo usar el snippet?", expanded=False):
    st.markdown("""
    1. Haz clic en **Generar Snippet** para producir el bloque de código.
    2. Copia el texto y pégalo directamente en el editor de **Pine Script** de TradingView.
    3. Úsalo como fuente de datos en una `table` de tu indicador o como comentario de referencia.

    ```pine
    // Ejemplo de uso en Pine Script
    // [AAPL]  PER=28.5, F_PER=24.1, PEG=0.9, VAL="Compra Potencial", PRECIO=189.3
    ```
    """)

col_btn1, col_btn2 = st.columns([2, 8])
with col_btn1:
    generar = st.button("⚡ Generar Snippet", type="primary", use_container_width=True)

if generar:
    snippet = generar_pine_snippet(df_filtrado)
    st.markdown('<div class="pine-block">' + snippet.replace("\n", "<br>") + "</div>",
                unsafe_allow_html=True)
    nombre_archivo = (
        "sp500_todas_valoracion.pine"
        if modo_todas
        else f"sp500_{sector_seleccionado.lower().replace(' ', '_')}_valoracion.pine"
    )
    st.download_button(
        label="⬇️ Descargar como .pine",
        data=snippet,
        file_name=nombre_archivo,
        mime="text/plain",
        use_container_width=False,
    )
    st.success("✅ Snippet generado. Copia el bloque de arriba o descárgalo.")
