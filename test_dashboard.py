"""
Regression Testing Script for BMC Analytics Dashboard
Tests all SQL queries and data processing functions

Usage:
    python test_dashboard.py
    python test_dashboard.py /path/to/your/database.db
    
Or set environment variable:
    export BMC_DB_PATH="/path/to/your/database.db"
    python test_dashboard.py
"""

import duckdb
import pandas as pd
import sys
import os
from datetime import datetime

# Database configuration - Priority order:
# 1. Command line argument
# 2. Environment variable
# 3. Default path
DEFAULT_DB_PATH = "/Users/vivekvishe/Documents/agro/bmc_data.db"

def get_database_path():
    """Get database path from various sources"""
    # Check command line argument
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"📍 Using database path from command line: {db_path}")
        return db_path
    
    # Check environment variable
    if 'BMC_DB_PATH' in os.environ:
        db_path = os.environ['BMC_DB_PATH']
        print(f"📍 Using database path from environment variable: {db_path}")
        return db_path
    
    # Check config file
    config_file = os.path.join(os.path.dirname(__file__), 'config.txt')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('DB_PATH=') and not line.startswith('#'):
                        db_path = line.split('=', 1)[1].strip()
                        print(f"📍 Using database path from config.txt: {db_path}")
                        return db_path
        except Exception as e:
            print(f"⚠️ Warning: Could not read config file: {e}")
    
    # Use default
    print(f"📍 Using default database path: {DEFAULT_DB_PATH}")
    print(f"\n💡 Tip: You can override by:")
    print(f"   1. Update config.txt file")
    print(f"   2. Command line: python test_dashboard.py /your/path/database.db")
    print(f"   3. Environment: export BMC_DB_PATH='/your/path/database.db'")
    return DEFAULT_DB_PATH

class DashboardTester:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.test_results = []
        self.failed_tests = []
        
    def connect(self):
        """Connect to database"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Database not found at: {self.db_path}")
                return False
            self.connection = duckdb.connect(self.db_path, read_only=True)
            print(f"✅ Connected to database: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False
    
    def execute_query(self, query, test_name):
        """Execute a query and return results"""
        try:
            result = self.connection.execute(query).df()
            self.test_results.append({
                'test': test_name,
                'status': 'PASS',
                'rows': len(result),
                'error': None
            })
            print(f"✅ PASS: {test_name} - {len(result)} rows returned")
            return result
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': 'FAIL',
                'rows': 0,
                'error': str(e)
            })
            self.failed_tests.append(test_name)
            print(f"❌ FAIL: {test_name}")
            print(f"   Error: {str(e)}")
            return None
    
    def test_basic_queries(self):
        """Test basic data retrieval"""
        print("\n" + "="*80)
        print("SECTION 1: BASIC QUERIES")
        print("="*80)
        
        # Test 1: Count total records
        query = "SELECT COUNT(*) as total FROM operaciones_bmc"
        self.execute_query(query, "1.1 - Count total records")
        
        # Test 2: Get distinct months
        query = """
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
        self.execute_query(query, "1.2 - Get distinct months")
        
        # Test 3: Get distinct years
        query = "SELECT DISTINCT YEAR FROM operaciones_bmc WHERE YEAR IS NOT NULL ORDER BY YEAR DESC"
        self.execute_query(query, "1.3 - Get distinct years")
        
        # Test 4: Get operation types
        query = 'SELECT DISTINCT "TIPO OPERACION" FROM operaciones_bmc WHERE "TIPO OPERACION" IS NOT NULL'
        self.execute_query(query, "1.4 - Get operation types")
    
    def test_overview_metrics(self):
        """Test overview/KPI queries"""
        print("\n" + "="*80)
        print("SECTION 2: OVERVIEW METRICS")
        print("="*80)
        
        query = """
            SELECT 
                COUNT(DISTINCT CLIENTE) as unique_clients,
                COUNT(DISTINCT "NOMBRE PRODUCTO") as unique_products,
                SUM("VALOR NEGOCIO") as total_volume,
                SUM(COMISION) as total_commission,
                COUNT(*) as total_ops,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc
        """
        self.execute_query(query, "2.1 - Overview metrics")
    
    def test_performance_dashboard(self):
        """Test Performance Dashboard queries"""
        print("\n" + "="*80)
        print("SECTION 3: PERFORMANCE DASHBOARD")
        print("="*80)
        
        # Monthly revenue trend
        query = """
            SELECT 
                MES,
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as client_volume,
                COUNT(*) as operations
            FROM operaciones_bmc 
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
        self.execute_query(query, "3.1 - Monthly commission trend")
        
        # Top 10 clients
        query = """
            SELECT 
                CLIENTE,
                SUM(COMISION) as commission_earnings,
                COUNT(*) as transactions,
                SUM("VALOR NEGOCIO") as transaction_volume,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc 
            GROUP BY CLIENTE
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        self.execute_query(query, "3.2 - Top 10 clients")
        
        # All referenciadores
        query = """
            SELECT 
                REFERENCIADOR,
                COUNT(*) as total_operations,
                SUM(COMISION) as total_commission,
                SUM("VALOR NEGOCIO") as total_volume,
                AVG(COMISION) as avg_commission_per_op,
                SUM(COMISION * ("% REF VENTA" / 100.0)) + SUM(COMISION * ("% REF COMPRA" / 100.0)) as referenciador_earnings
            FROM operaciones_bmc
            WHERE REFERENCIADOR IS NOT NULL AND REFERENCIADOR != 0
            GROUP BY REFERENCIADOR
            ORDER BY total_commission DESC
        """
        self.execute_query(query, "3.3 - All referenciadores")
        
        # Product performance
        query = """
            SELECT 
                "NOMBRE PRODUCTO",
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as volume,
                COUNT(*) as transactions,
                AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_commission_rate
            FROM operaciones_bmc 
            GROUP BY "NOMBRE PRODUCTO"
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        self.execute_query(query, "3.4 - Product performance")
    
    def test_strategic_insights(self):
        """Test Strategic Insights queries"""
        print("\n" + "="*80)
        print("SECTION 4: STRATEGIC INSIGHTS")
        print("="*80)
        
        # Churn risk
        query = """
            SELECT 
                CLIENTE,
                MAX("FECHA REGISTRO") as last_transaction,
                DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) as days_inactive,
                SUM(COMISION) as lifetime_commission,
                COUNT(*) as total_transactions
            FROM operaciones_bmc
            GROUP BY CLIENTE
            HAVING DATE_DIFF('day', MAX("FECHA REGISTRO"), CURRENT_DATE) > 60
            ORDER BY lifetime_commission DESC
            LIMIT 15
        """
        self.execute_query(query, "4.1 - Churn risk analysis")
        
        # Cross-selling
        query = """
            WITH client_products AS (
                SELECT DISTINCT 
                    "NIT COMPRADOR" as client,
                    "NOMBRE PRODUCTO" as product
                FROM operaciones_bmc
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
        self.execute_query(query, "4.2 - Cross-selling opportunities")
        
        # Client segmentation
        query = """
            WITH client_stats AS (
                SELECT 
                    CLIENTE,
                    SUM(COMISION) as total_commission,
                    COUNT(*) as transaction_count,
                    AVG(COMISION) as avg_commission_per_transaction,
                    SUM("VALOR NEGOCIO") as total_volume
                FROM operaciones_bmc
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
        self.execute_query(query, "4.3 - Client segmentation")
    
    def test_network_analysis(self):
        """Test Buyer-Seller Network queries"""
        print("\n" + "="*80)
        print("SECTION 5: BUYER-SELLER NETWORK")
        print("="*80)
        
        # Seller hubs
        query = """
            SELECT 
                "NOMBRE VENDEDOR" as seller,
                COUNT(DISTINCT "NIT COMPRADOR") as unique_buyers,
                SUM(COMISION) as total_commission,
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume
            FROM operaciones_bmc
            WHERE "NOMBRE VENDEDOR" IS NOT NULL AND "NIT COMPRADOR" IS NOT NULL
            GROUP BY "NOMBRE VENDEDOR"
            HAVING COUNT(DISTINCT "NIT COMPRADOR") >= 2
            ORDER BY unique_buyers DESC, total_commission DESC
            LIMIT 10
        """
        self.execute_query(query, "5.1 - Seller hubs")
        
        # Buyer hubs
        query = """
            SELECT 
                "NOMBRE COMPRADOR" as buyer,
                COUNT(DISTINCT "NIT VENDEDOR") as unique_sellers,
                SUM(COMISION) as total_commission,
                COUNT(*) as total_transactions,
                SUM("VALOR NEGOCIO") as total_volume
            FROM operaciones_bmc
            WHERE "NOMBRE COMPRADOR" IS NOT NULL AND "NIT VENDEDOR" IS NOT NULL
            GROUP BY "NOMBRE COMPRADOR"
            HAVING COUNT(DISTINCT "NIT VENDEDOR") >= 2
            ORDER BY unique_sellers DESC, total_commission DESC
            LIMIT 10
        """
        self.execute_query(query, "5.2 - Buyer hubs")
        
        # Principal analysis
        query = """
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
            WHERE PRINCIPAL IS NOT NULL
            GROUP BY principal_type
            ORDER BY total_commission DESC
        """
        self.execute_query(query, "5.3 - Principal analysis")
        
        # Mutual relationships
        query = """
            SELECT 
                "NOMBRE VENDEDOR" as seller,
                "NOMBRE COMPRADOR" as buyer,
                COUNT(*) as transactions,
                SUM(COMISION) as total_commission,
                SUM("VALOR NEGOCIO") as total_volume,
                COUNT(CASE WHEN PRINCIPAL = 'V' THEN 1 END) as seller_paid,
                COUNT(CASE WHEN PRINCIPAL = 'C' THEN 1 END) as buyer_paid
            FROM operaciones_bmc
            WHERE "NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL
            GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
            HAVING COUNT(*) >= 3
            ORDER BY total_commission DESC
            LIMIT 20
        """
        self.execute_query(query, "5.4 - Mutual relationships")
        
        # Network metrics
        query = """
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
                WHERE "NOMBRE VENDEDOR" IS NOT NULL AND "NOMBRE COMPRADOR" IS NOT NULL
                GROUP BY "NOMBRE VENDEDOR", "NOMBRE COMPRADOR"
            ) relationships
        """
        self.execute_query(query, "5.5 - Network metrics")
    
    def test_potential_clients(self):
        """Test Potential Client queries"""
        print("\n" + "="*80)
        print("SECTION 6: POTENTIAL CLIENTS")
        print("="*80)
        
        # Get current clients
        query = """
            SELECT DISTINCT "CC PPAL" as client_nit, CLIENTE as client_name
            FROM operaciones_bmc
            WHERE "CC PPAL" IS NOT NULL AND CLIENTE IS NOT NULL
        """
        result = self.execute_query(query, "6.1 - Current clients list")
        
        if result is not None and len(result) > 0:
            # Potential buyer clients
            query = """
                WITH our_seller_clients AS (
                    SELECT DISTINCT "NIT VENDEDOR" as client_nit
                    FROM operaciones_bmc
                    WHERE PRINCIPAL = 'V'
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
            self.execute_query(query, "6.2 - Potential buyer clients")
            
            # Potential seller clients
            query = """
                WITH our_buyer_clients AS (
                    SELECT DISTINCT "NIT COMPRADOR" as client_nit
                    FROM operaciones_bmc
                    WHERE PRINCIPAL = 'C'
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
            self.execute_query(query, "6.3 - Potential seller clients")
    
    def test_operational_analysis(self):
        """Test Operational Analysis queries"""
        print("\n" + "="*80)
        print("SECTION 7: OPERATIONAL ANALYSIS")
        print("="*80)
        
        # Day of week
        query = """
            SELECT 
                DAYNAME("FECHA REGISTRO") as day_of_week,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings,
                AVG(COMISION) as avg_commission
            FROM operaciones_bmc
            GROUP BY day_of_week
        """
        self.execute_query(query, "7.1 - Day of week analysis")
        
        # Operations by type
        query = """
            SELECT 
                "TIPO OPERACION",
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings,
                SUM("VALOR NEGOCIO") as volume
            FROM operaciones_bmc
            GROUP BY "TIPO OPERACION"
            ORDER BY operations DESC
        """
        self.execute_query(query, "7.2 - Operations by type")
        
        # Buyer cities
        query = """
            SELECT 
                "CIUDAD COMPRADOR" as city,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings
            FROM operaciones_bmc
            WHERE "CIUDAD COMPRADOR" IS NOT NULL
            GROUP BY city
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        self.execute_query(query, "7.3 - Buyer cities")
        
        # Seller cities
        query = """
            SELECT 
                "CIUDAD VENDEDOR" as city,
                COUNT(*) as operations,
                SUM(COMISION) as commission_earnings
            FROM operaciones_bmc
            WHERE "CIUDAD VENDEDOR" IS NOT NULL
            GROUP BY city
            ORDER BY commission_earnings DESC
            LIMIT 10
        """
        self.execute_query(query, "7.4 - Seller cities")
    
    def test_risk_audit(self):
        """Test Risk & Audit queries"""
        print("\n" + "="*80)
        print("SECTION 8: RISK & AUDIT")
        print("="*80)
        
        # Pareto analysis
        query = """
            SELECT 
                CLIENTE,
                SUM(COMISION) as commission_earnings
            FROM operaciones_bmc
            GROUP BY CLIENTE
            ORDER BY commission_earnings DESC
            LIMIT 50
        """
        self.execute_query(query, "8.1 - Pareto analysis")
        
        # Pricing anomalies
        query = """
            WITH product_avg AS (
                SELECT 
                    "NOMBRE PRODUCTO",
                    AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as avg_rate
                FROM operaciones_bmc
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
            ORDER BY discount_pct DESC
            LIMIT 20
        """
        self.execute_query(query, "8.2 - Pricing anomalies")
        
        # Transaction size distribution
        query = """
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
            GROUP BY size_category
            ORDER BY 
                CASE size_category
                    WHEN 'Small (< $1M)' THEN 1
                    WHEN 'Medium ($1M-$10M)' THEN 2
                    WHEN 'Large ($10M-$50M)' THEN 3
                    ELSE 4
                END
        """
        self.execute_query(query, "8.3 - Transaction size distribution")
    
    def test_client_insights(self):
        """Test Client Insights queries"""
        print("\n" + "="*80)
        print("SECTION 9: CLIENT INSIGHTS")
        print("="*80)
        
        # Get client list
        query = """
            SELECT DISTINCT CLIENTE as client_name, "CC PPAL" as client_nit
            FROM operaciones_bmc
            WHERE CLIENTE IS NOT NULL AND "CC PPAL" IS NOT NULL
            ORDER BY CLIENTE
            LIMIT 1
        """
        result = self.execute_query(query, "9.1 - Client list")
        
        if result is not None and len(result) > 0:
            client_nit = result['client_nit'].values[0]
            
            # Client stats
            query = f"""
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
            self.execute_query(query, "9.2 - Client stats")
            
            # Market comparison
            query = f"""
                SELECT 
                    "NOMBRE PRODUCTO",
                    COUNT(*) as client_transactions,
                    AVG(CASE WHEN "CC PPAL" = '{client_nit}' THEN COMISION / NULLIF("VALOR NEGOCIO", 0) END) * 100 as client_rate,
                    AVG(COMISION / NULLIF("VALOR NEGOCIO", 0)) * 100 as market_avg_rate,
                    SUM(CASE WHEN "CC PPAL" = '{client_nit}' THEN "VALOR NEGOCIO" ELSE 0 END) as client_volume
                FROM operaciones_bmc
                GROUP BY "NOMBRE PRODUCTO"
                HAVING SUM(CASE WHEN "CC PPAL" = '{client_nit}' THEN 1 ELSE 0 END) > 0
                ORDER BY client_volume DESC
                LIMIT 10
            """
            self.execute_query(query, "9.3 - Market comparison")
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*80)
        print("TEST SUMMARY REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = sum(1 for t in self.test_results if t['status'] == 'PASS')
        failed = sum(1 for t in self.test_results if t['status'] == 'FAIL')
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print("\n" + "="*80)
            print("FAILED TESTS DETAIL")
            print("="*80)
            for test in self.test_results:
                if test['status'] == 'FAIL':
                    print(f"\n❌ {test['test']}")
                    print(f"   Error: {test['error']}")
        
        # Save report to file
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w') as f:
            f.write("BMC ANALYTICS DASHBOARD - REGRESSION TEST REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Database: {self.db_path}\n\n")
            
            f.write(f"Total Tests: {total_tests}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Success Rate: {(passed/total_tests*100):.1f}%\n\n")
            
            f.write("="*80 + "\n")
            f.write("DETAILED RESULTS\n")
            f.write("="*80 + "\n\n")
            
            for test in self.test_results:
                status_icon = "✅" if test['status'] == 'PASS' else "❌"
                f.write(f"{status_icon} {test['test']}\n")
                f.write(f"   Status: {test['status']}\n")
                f.write(f"   Rows: {test['rows']}\n")
                if test['error']:
                    f.write(f"   Error: {test['error']}\n")
                f.write("\n")
        
        print(f"\n📄 Report saved to: {report_filename}")
        
        return passed == total_tests
    
    def run_all_tests(self):
        """Run all test suites"""
        print("\n" + "="*80)
        print("BMC ANALYTICS DASHBOARD - REGRESSION TESTING")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.connect():
            return False
        
        # Run all test suites
        self.test_basic_queries()
        self.test_overview_metrics()
        self.test_performance_dashboard()
        self.test_strategic_insights()
        self.test_network_analysis()
        self.test_potential_clients()
        self.test_operational_analysis()
        self.test_risk_audit()
        self.test_client_insights()
        
        # Generate report
        success = self.generate_report()
        
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")
        
        return success

def main():
    """Main function"""
    db_path = get_database_path()
    
    # Validate path exists
    if not os.path.exists(db_path):
        print(f"\n❌ ERROR: Database file not found at: {db_path}")
        print(f"\n💡 Please provide the correct path:")
        print(f"   python test_dashboard.py /correct/path/to/bmc_data.db")
        sys.exit(1)
    
    tester = DashboardTester(db_path)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()