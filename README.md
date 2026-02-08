# Agro Analytics Pro

A comprehensive Streamlit dashboard for agricultural business analytics and performance monitoring.

## Overview

Agro Analytics Pro is a data-driven dashboard that provides insights into agricultural business operations, performance metrics, and strategic opportunities. The application features interactive visualizations, AI-driven insights, and operational analytics.

## Features

- **📊 Performance Dashboard**: Real-time KPIs for traded volume, gross commission, and total operations
- **💡 Strategic AI Insights**: Churn risk detection and cross-selling opportunities
- **🔍 Operational Deep-Dive**: Daily operation volume analysis and bottleneck identification
- **🛡️ Risk & Audit**: Financial risk assessment, pricing anomaly detection, and revenue concentration analysis

## Tech Stack

- **Frontend**: Streamlit
- **Data Processing**: DuckDB, Pandas
- **Visualization**: Plotly Express, Plotly Graph Objects
- **Database**: SQLite (DuckDB compatible)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vivekvishe/agroAnalytics.git
   cd agroAnalytics
   ```

2. Create a virtual environment:
   ```bash
   python -m venv agro_env
   source agro_env/bin/activate  # On Windows: agro_env\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install streamlit duckdb pandas plotly
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
agroAnalytics/
├── app.py              # Main Streamlit application
├── README.md           # Project documentation
├── .gitignore          # Git ignore rules
├── bmc_data.db         # Database file (not tracked in git)
└── agro_env/           # Virtual environment (not tracked in git)
```

## Usage

1. Launch the application using `streamlit run app.py`
2. Use the sidebar filters to select specific months for analysis
3. Navigate through the tabs to explore different analytics sections:
   - **Performance Dashboard**: High-level metrics and trends
   - **Strategic AI Insights**: Business opportunities and risk detection
   - **Operational Deep-Dive**: Daily operations analysis
   - **Risk & Audit**: Financial risk assessment and audit tools

## Data Sources

The application connects to a DuckDB database (`bmc_data.db`) containing agricultural business transaction data with the following key fields:
- `MES`: Month of operation
- `CLIENTE`: Client name
- `VALOR NEGOCIO`: Transaction value
- `COMISION`: Commission amount
- `NOMBRE PRODUCTO`: Product name
- `FECHA REGISTRO`: Registration date

## License

This project is for demonstration and educational purposes.

## Contributing

Feel free to submit issues and enhancement requests!