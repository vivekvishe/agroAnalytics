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

## Testing

The project includes a comprehensive regression testing suite to ensure data quality and application functionality.

### Test Files

- `test_agro.py` - Main regression testing script with unittest framework
- `run_tests.sh` - Bash script wrapper for easy test execution
- `smoke_test.py` - Quick smoke test for basic functionality verification

### Running Tests

#### Quick Smoke Test
```bash
python3 smoke_test.py
```
or
```bash
./run_tests.sh --quick
```

#### Full Regression Test Suite
```bash
python3 test_agro.py
```
or
```bash
./run_tests.sh
```

#### Test with Verbose Output
```bash
python3 test_agro.py --verbose
```
or
```bash
./run_tests.sh --verbose
```

#### Run Specific Test
```bash
python3 test_agro.py --test test_database_connection
```
or
```bash
./run_tests.sh --test test_database_connection
```

#### List Available Tests
```bash
python3 test_agro.py --list
```
or
```bash
./run_tests.sh --list
```

#### Generate Test Report
```bash
python3 test_agro.py --report test_report.json
```
or
```bash
./run_tests.sh --report test_report.json
```

### Test Coverage

The regression test suite covers:

1. **Database Tests**
   - Database connection validation
   - Table existence and schema verification
   - Data quality checks (null values, negative values)

2. **Query Tests**
   - Month filter query logic
   - KPI calculation queries (volume, commission, operations)
   - Monthly revenue aggregation
   - Top clients by revenue
   - Churn risk analysis
   - Cross-selling opportunities
   - Pricing anomaly detection

3. **Data Quality Tests**
   - Critical column validation
   - Negative value detection
   - Null value warnings

### Test Automation

The tests can be integrated into CI/CD pipelines. The test scripts return appropriate exit codes:
- `0` for success (all tests passed)
- `1` for failure (one or more tests failed)

### Example CI/CD Integration

```bash
#!/bin/bash
# Example CI script
cd /path/to/agroAnalytics

# Run smoke test first
if python3 smoke_test.py; then
    echo "Smoke tests passed, running full regression suite..."
    python3 test_agro.py --report test_results.json
    if [ $? -eq 0 ]; then
        echo "All tests passed!"
        exit 0
    else
        echo "Regression tests failed"
        exit 1
    fi
else
    echo "Smoke tests failed, aborting..."
    exit 1
fi
```

## Contributing

Feel free to submit issues and enhancement requests!

### Testing Contributions

When contributing code changes:
1. Run the existing test suite to ensure no regressions
2. Add new tests for any new functionality
3. Update tests when modifying existing functionality
4. Ensure all tests pass before submitting changes
