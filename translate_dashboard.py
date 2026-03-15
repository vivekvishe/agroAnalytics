#!/usr/bin/env python3
"""
Script de Traducción Automática - Dashboard BMC
Traduce el dashboard del inglés al español (Colombia)
"""

# Diccionario de traducción completo
TRANSLATIONS = {
    # Authentication
    "Secure Login Required": "Inicio de Sesión Seguro Requerido",
    "Username": "Usuario",
    "Password": "Contraseña",
    "Enter username": "Ingrese usuario",
    "Enter password": "Ingrese contraseña",
    "Login": "Iniciar Sesión",
    "Username or password incorrect": "Usuario o contraseña incorrectos",
    "Logout": "Cerrar Sesión",
    
    # Navigation
    "Performance Dashboard": "Panel de Desempeño",
    "Strategic Insights": "Perspectivas Estratégicas",
    "Buyer-Seller Network": "Red Compradores-Vendedores",
    "Client Insights": "Análisis de Clientes",
    "Operational Analysis": "Análisis Operacional",
    "Risk & Audit": "Riesgo y Auditoría",
    
    # Filters
    "Filter Analytics": "Filtrar Analítica",
    "Select Months": "Seleccionar Meses",
    "Select Years": "Seleccionar Años",
    "Operation Type": "Tipo de Operación",
    "Filter data by specific months": "Filtrar datos por meses específicos",
    "Filter data by specific years": "Filtrar datos por años específicos",
    
    # Days
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
    
    # Metrics
    "Your Commission Earnings": "Sus Comisiones Ganadas",
    "Client Volume": "Volumen de Clientes",
    "Avg Commission Rate": "Tasa Promedio de Comisión",
    "Active Clients": "Clientes Activos",
    "Transactions": "Transacciones",
    
    # Titles
    "Data-Driven Insights for Agricultural Business Operations": "Perspectivas Basadas en Datos para Operaciones de Negocios Agrícolas",
    "Dashboard Guide": "Guía del Panel",
    "Dashboard Purpose": "Propósito del Panel",
    "Navigation": "Navegación",
    "Usage Tips": "Consejos de Uso",
    "SQL Query Transparency": "Transparencia de Consultas SQL",
    
    # Common phrases
    "What does this show?": "¿Qué muestra esto?",
    "Business Question:": "Pregunta de Negocio:",
    "What we're measuring:": "Qué estamos midiendo:",
    "Why it matters:": "Por qué importa:",
    "How to use it:": "Cómo usarlo:",
    "Bottom line:": "Conclusión:",
    "Key insight:": "Perspectiva clave:",
    "View SQL Query": "Ver Consulta SQL",
    
    # Charts
    "Monthly Commission Earnings Trend": "Tendencia Mensual de Comisiones",
    "Top 10 Clients by Commission Earnings": "Top 10 Clientes por Comisiones",
    
    # Add more translations as needed...
}

def translate_dashboard(input_file, output_file):
    """Translate the dashboard file"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply translations
    for eng, esp in TRANSLATIONS.items():
        content = content.replace(f'"{eng}"', f'"{esp}"')
        content = content.replace(f"'{eng}'", f"'{esp}'")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Translation complete!")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    translate_dashboard("app.py", "app_es.py")
