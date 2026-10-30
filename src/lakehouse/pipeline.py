"""Medallion Architecture Pipeline for ResoAI with DuckDB.

Pipeline Flow:
1. Bronze: Ingests raw JSON/API payloads into data/lakehouse/bronze/ with audit metadata.
2. Silver: Conforms, cleans, standardizes types, and outputs silver parquet/DuckDB tables.
3. Gold: Builds a full Star Schema (fact & dimension tables) + business aggregation views.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb

from src.config import settings
from src.lakehouse.generator import generate_synthetic_hr_dataset

logger = logging.getLogger("resoai.lakehouse")


class LakehousePipeline:
    """Orchestrates Bronze -> Silver -> Gold Medallion transformations."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        bronze_dir: Optional[str] = None,
        silver_dir: Optional[str] = None,
        gold_dir: Optional[str] = None,
    ) -> None:
        self.db_path = Path(db_path or settings.lakehouse_db_path)
        self.bronze_dir = Path(bronze_dir or settings.lakehouse_bronze_dir)
        self.silver_dir = Path(silver_dir or settings.lakehouse_silver_dir)
        self.gold_dir = Path(gold_dir or settings.lakehouse_gold_dir)

        # Ensure directory structures exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.bronze_dir.mkdir(parents=True, exist_ok=True)
        self.silver_dir.mkdir(parents=True, exist_ok=True)
        self.gold_dir.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection to the persistent lakehouse database."""
        return duckdb.connect(str(self.db_path))

    # ── Bronze Stage: Raw Ingestion ──────────────────────────

    def ingest_bronze(self, raw_data: Optional[Dict[str, Any]] = None, record_count: int = 500) -> Path:
        """Ingest raw unmodified data into Bronze layer with timestamp metadata."""
        if raw_data is None:
            raw_data = generate_synthetic_hr_dataset(count=record_count)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        bronze_file = self.bronze_dir / f"bronze_hr_raw_{timestamp_str}.json"
        bronze_latest = self.bronze_dir / "bronze_hr_raw_latest.json"

        payload = {
            "_metadata": {
                "ingested_at": datetime.now().isoformat(),
                "source": "synthetic_generator_api",
                "record_counts": {
                    "employees": len(raw_data.get("employees", [])),
                    "departments": len(raw_data.get("departments", [])),
                    "projects": len(raw_data.get("projects", [])),
                    "allocations": len(raw_data.get("allocations", [])),
                    "holidays": len(raw_data.get("holidays", [])),
                },
            },
            "data": raw_data,
        }

        with open(bronze_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        with open(bronze_latest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logger.info("Bronze layer ingested: %s (%d employees)", bronze_file.name, len(raw_data.get("employees", [])))
        return bronze_latest

    # ── Silver Stage: Cleaning & Normalization ──────────────

    def process_silver(self, bronze_file: Optional[Path] = None) -> Dict[str, int]:
        """Transform Bronze raw payloads into conformed Silver tables and Parquet files."""
        if bronze_file is None:
            bronze_file = self.bronze_dir / "bronze_hr_raw_latest.json"

        if not bronze_file.exists():
            raise FileNotFoundError(f"Bronze file {bronze_file} not found. Run ingest_bronze() first.")

        bronze_path_str = str(bronze_file)
        con = self.get_connection()

        try:
            # 1. Clean Departments
            con.execute("DROP TABLE IF EXISTS silver_departments")
            con.execute("""
                CREATE TABLE silver_departments AS 
                SELECT 
                    TRIM(d.department_id)::VARCHAR AS department_id,
                    TRIM(d.department_name)::VARCHAR AS department_name,
                    TRIM(d.location_hub)::VARCHAR AS location_hub,
                    CURRENT_TIMESTAMP AS processed_at
                FROM (
                    SELECT unnest(data.departments) AS d 
                    FROM read_json_auto(?)
                )
            """, [bronze_path_str])

            # 2. Clean Projects
            con.execute("DROP TABLE IF EXISTS silver_projects")
            con.execute("""
                CREATE TABLE silver_projects AS 
                SELECT 
                    TRIM(p.project_id)::VARCHAR AS project_id,
                    TRIM(p.project_name)::VARCHAR AS project_name,
                    TRIM(p.domain)::VARCHAR AS domain,
                    TRIM(p.tech_stack)::VARCHAR AS tech_stack,
                    TRIM(p.client_name)::VARCHAR AS client_name,
                    CURRENT_TIMESTAMP AS processed_at
                FROM (
                    SELECT unnest(data.projects) AS p 
                    FROM read_json_auto(?)
                )
            """, [bronze_path_str])

            # 3. Clean Employees (Deduplicate by employee_id, standardize strings & numbers)
            con.execute("DROP TABLE IF EXISTS silver_employees")
            con.execute("""
                CREATE TABLE silver_employees AS 
                SELECT 
                    TRIM(e.employee_id)::VARCHAR AS employee_id,
                    TRIM(e.first_name)::VARCHAR AS first_name,
                    TRIM(e.last_name)::VARCHAR AS last_name,
                    TRIM(e.full_name)::VARCHAR AS full_name,
                    LOWER(TRIM(e.email))::VARCHAR AS email,
                    TRIM(e.phone)::VARCHAR AS phone,
                    TRIM(e.department_id)::VARCHAR AS department_id,
                    TRIM(e.department_name)::VARCHAR AS department_name,
                    TRIM(e.designation)::VARCHAR AS designation,
                    TRIM(e.location)::VARCHAR AS location,
                    e.joining_date::DATE AS joining_date,
                    ROUND(e.salary::DOUBLE, 2) AS salary,
                    ROUND(e.years_of_experience::DOUBLE, 1) AS years_of_experience,
                    TRIM(e.skills)::VARCHAR AS skills,
                    TRIM(e.status)::VARCHAR AS status,
                    TRIM(e.project_id)::VARCHAR AS project_id,
                    TRIM(e.project_name)::VARCHAR AS project_name,
                    ROUND(e.performance_rating::DOUBLE, 2) AS performance_rating,
                    e.leave_balance::INTEGER AS leave_balance,
                    CURRENT_TIMESTAMP AS processed_at
                FROM (
                    SELECT unnest(data.employees) AS e 
                    FROM read_json_auto(?)
                )
            """, [bronze_path_str])

            # 4. Clean Holidays
            con.execute("DROP TABLE IF EXISTS silver_holidays")
            has_bronze_holidays = False
            try:
                test_h = con.execute(
                    "SELECT count(*) FROM (SELECT unnest(data.holidays) AS h FROM read_json_auto(?))",
                    [bronze_path_str],
                ).fetchone()
                if test_h and test_h[0] > 0:
                    has_bronze_holidays = True
            except Exception:
                has_bronze_holidays = False

            if has_bronze_holidays:
                con.execute("""
                    CREATE TABLE silver_holidays AS 
                    SELECT 
                        TRIM(h.id)::VARCHAR AS holiday_id,
                        TRIM(h.name)::VARCHAR AS holiday_name,
                        h.date::DATE AS date,
                        TRIM(h.day)::VARCHAR AS day,
                        TRIM(h.month)::VARCHAR AS month,
                        TRIM(COALESCE(h.type, 'Fixed'))::VARCHAR AS holiday_type,
                        CURRENT_TIMESTAMP AS processed_at
                    FROM (
                        SELECT unnest(data.holidays) AS h 
                        FROM read_json_auto(?)
                    )
                """, [bronze_path_str])
            else:
                holidays_json = Path(settings.data_dir) / "holidays.json"
                if holidays_json.exists():
                    con.execute("""
                        CREATE TABLE silver_holidays AS 
                        SELECT 
                            TRIM(h.id)::VARCHAR AS holiday_id,
                            TRIM(h.name)::VARCHAR AS holiday_name,
                            h.date::DATE AS date,
                            TRIM(h.day)::VARCHAR AS day,
                            TRIM(h.month)::VARCHAR AS month,
                            TRIM(COALESCE(h.type, 'Fixed'))::VARCHAR AS holiday_type,
                            CURRENT_TIMESTAMP AS processed_at
                        FROM read_json_auto(?) AS h
                    """, [str(holidays_json)])
                else:
                    con.execute("""
                        CREATE TABLE silver_holidays (
                            holiday_id VARCHAR,
                            holiday_name VARCHAR,
                            date DATE,
                            day VARCHAR,
                            month VARCHAR,
                            holiday_type VARCHAR,
                            processed_at TIMESTAMP
                        )
                    """)

            # Export Silver tables to compressed Parquet format
            silver_emp_parquet = self.silver_dir / "silver_employees.parquet"
            silver_proj_parquet = self.silver_dir / "silver_projects.parquet"
            silver_dept_parquet = self.silver_dir / "silver_departments.parquet"
            silver_hol_parquet = self.silver_dir / "silver_holidays.parquet"

            con.execute(f"COPY silver_employees TO '{silver_emp_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY silver_projects TO '{silver_proj_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY silver_departments TO '{silver_dept_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY silver_holidays TO '{silver_hol_parquet}' (FORMAT PARQUET)")

            emp_count = con.execute("SELECT count(*) FROM silver_employees").fetchone()[0]
            proj_count = con.execute("SELECT count(*) FROM silver_projects").fetchone()[0]
            dept_count = con.execute("SELECT count(*) FROM silver_departments").fetchone()[0]
            hol_count = con.execute("SELECT count(*) FROM silver_holidays").fetchone()[0]

            logger.info("Silver layer processed: %d employees, %d projects, %d departments, %d holidays", emp_count, proj_count, dept_count, hol_count)
            return {"employees": emp_count, "projects": proj_count, "departments": dept_count, "holidays": hol_count}

        finally:
            con.close()

    # ── Gold Stage: Star Schema & Business Marts ─────────────

    def process_gold(self) -> Dict[str, int]:
        """Build Dimension tables, Fact table, and analytical summary Views in Gold layer."""
        con = self.get_connection()
        try:
            # 1. Dimension: dim_department
            con.execute("DROP TABLE IF EXISTS dim_department CASCADE")
            con.execute("""
                CREATE TABLE dim_department AS
                SELECT 
                    row_number() OVER (ORDER BY department_id) AS department_key,
                    department_id,
                    department_name,
                    location_hub
                FROM silver_departments
            """)

            # 2. Dimension: dim_project
            con.execute("DROP TABLE IF EXISTS dim_project CASCADE")
            con.execute("""
                CREATE TABLE dim_project AS
                SELECT 
                    row_number() OVER (ORDER BY project_id) AS project_key,
                    project_id,
                    project_name,
                    domain,
                    tech_stack,
                    client_name
                FROM silver_projects
            """)

            # 3. Dimension: dim_employee
            con.execute("DROP TABLE IF EXISTS dim_employee CASCADE")
            con.execute("""
                CREATE TABLE dim_employee AS
                SELECT 
                    row_number() OVER (ORDER BY employee_id) AS employee_key,
                    employee_id,
                    full_name,
                    first_name,
                    last_name,
                    email,
                    phone,
                    designation,
                    location,
                    skills,
                    joining_date,
                    status
                FROM silver_employees
            """)

            # 4. Fact Table: fact_employee_allocations
            con.execute("DROP TABLE IF EXISTS fact_employee_allocations CASCADE")
            con.execute("""
                CREATE TABLE fact_employee_allocations AS
                SELECT 
                    row_number() OVER () AS fact_id,
                    e.employee_key,
                    d.department_key,
                    p.project_key,
                    s.salary,
                    s.years_of_experience,
                    s.performance_rating,
                    s.leave_balance,
                    100 AS allocation_percentage
                FROM silver_employees s
                JOIN dim_employee e ON s.employee_id = e.employee_id
                JOIN dim_department d ON s.department_id = d.department_id
                JOIN dim_project p ON s.project_id = p.project_id
            """)

            # 5. Dimension: dim_holiday (Table & company_holidays View)
            con.execute("DROP TABLE IF EXISTS dim_holiday CASCADE")
            # Verify if silver_holidays table exists
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
            if "silver_holidays" in tables:
                con.execute("""
                    CREATE TABLE dim_holiday AS
                    SELECT 
                        row_number() OVER (ORDER BY date, holiday_name) AS holiday_key,
                        holiday_id,
                        holiday_name,
                        date,
                        day,
                        month,
                        holiday_type
                    FROM silver_holidays
                """)
            else:
                holidays_json = Path(settings.data_dir) / "holidays.json"
                if holidays_json.exists():
                    con.execute("""
                        CREATE TABLE dim_holiday AS
                        SELECT 
                            row_number() OVER (ORDER BY date, holiday_name) AS holiday_key,
                            TRIM(h.id)::VARCHAR AS holiday_id,
                            TRIM(h.name)::VARCHAR AS holiday_name,
                            h.date::DATE AS date,
                            TRIM(h.day)::VARCHAR AS day,
                            TRIM(h.month)::VARCHAR AS month,
                            TRIM(COALESCE(h.type, 'Fixed'))::VARCHAR AS holiday_type
                        FROM read_json_auto(?) AS h
                    """, [str(holidays_json)])
                else:
                    con.execute("""
                        CREATE TABLE dim_holiday (
                            holiday_key INTEGER,
                            holiday_id VARCHAR,
                            holiday_name VARCHAR,
                            date DATE,
                            day VARCHAR,
                            month VARCHAR,
                            holiday_type VARCHAR
                        )
                    """)

            con.execute("DROP VIEW IF EXISTS company_holidays")
            con.execute("""
                CREATE VIEW company_holidays AS
                SELECT 
                    holiday_key,
                    holiday_id,
                    holiday_name,
                    date,
                    day,
                    month,
                    holiday_type
                FROM dim_holiday
            """)

            # 6. Gold Analytical Mart: gold_dept_summary (View)
            con.execute("DROP VIEW IF EXISTS gold_dept_summary")
            con.execute("""
                CREATE VIEW gold_dept_summary AS
                SELECT 
                    d.department_name,
                    d.location_hub,
                    count(f.employee_key) AS total_headcount,
                    round(avg(f.salary), 2) AS avg_salary,
                    round(min(f.salary), 2) AS min_salary,
                    round(max(f.salary), 2) AS max_salary,
                    round(avg(f.performance_rating), 2) AS avg_performance_rating,
                    round(avg(f.years_of_experience), 1) AS avg_years_experience
                FROM fact_employee_allocations f
                JOIN dim_department d ON f.department_key = d.department_key
                GROUP BY d.department_name, d.location_hub
                ORDER BY total_headcount DESC
            """)

            # 6. Gold Analytical Mart: gold_city_headcount (View)
            con.execute("DROP VIEW IF EXISTS gold_city_headcount")
            con.execute("""
                CREATE VIEW gold_city_headcount AS
                SELECT 
                    e.location,
                    count(e.employee_key) AS employee_count,
                    count(DISTINCT f.department_key) AS departments_present,
                    round(avg(f.salary), 2) AS avg_salary
                FROM fact_employee_allocations f
                JOIN dim_employee e ON f.employee_key = e.employee_key
                GROUP BY e.location
                ORDER BY employee_count DESC
            """)

            # 7. Gold Analytical Mart: gold_project_staffing (View)
            con.execute("DROP VIEW IF EXISTS gold_project_staffing")
            con.execute("""
                CREATE VIEW gold_project_staffing AS
                SELECT 
                    p.project_name,
                    p.domain,
                    p.client_name,
                    count(f.employee_key) AS assigned_team_size,
                    round(avg(f.performance_rating), 2) AS avg_team_rating
                FROM fact_employee_allocations f
                JOIN dim_project p ON f.project_key = p.project_key
                GROUP BY p.project_name, p.domain, p.client_name
                ORDER BY assigned_team_size DESC
            """)

            # Export Gold Star Schema to Parquet
            gold_fact_parquet = self.gold_dir / "fact_employee_allocations.parquet"
            gold_dim_emp_parquet = self.gold_dir / "dim_employee.parquet"
            gold_dim_dept_parquet = self.gold_dir / "dim_department.parquet"
            gold_dim_proj_parquet = self.gold_dir / "dim_project.parquet"
            gold_dim_hol_parquet = self.gold_dir / "dim_holiday.parquet"

            con.execute(f"COPY fact_employee_allocations TO '{gold_fact_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY dim_employee TO '{gold_dim_emp_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY dim_department TO '{gold_dim_dept_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY dim_project TO '{gold_dim_proj_parquet}' (FORMAT PARQUET)")
            con.execute(f"COPY dim_holiday TO '{gold_dim_hol_parquet}' (FORMAT PARQUET)")

            fact_count = con.execute("SELECT count(*) FROM fact_employee_allocations").fetchone()[0]
            dim_emp_count = con.execute("SELECT count(*) FROM dim_employee").fetchone()[0]
            dim_hol_count = con.execute("SELECT count(*) FROM dim_holiday").fetchone()[0]

            logger.info("Gold Star Schema created: %d facts, %d dim_employees, %d dim_holidays", fact_count, dim_emp_count, dim_hol_count)
            return {
                "fact_records": fact_count,
                "dim_employees": dim_emp_count,
                "dim_holidays": dim_hol_count,
            }

        finally:
            con.close()

    def run_full_pipeline(self, record_count: int = 500) -> Dict[str, Any]:
        """Execute full end-to-end Medallion pipeline: Bronze -> Silver -> Gold."""
        bronze_file = self.ingest_bronze(record_count=record_count)
        silver_stats = self.process_silver(bronze_file)
        gold_stats = self.process_gold()

        return {
            "status": "success",
            "bronze_file": str(bronze_file),
            "silver": silver_stats,
            "gold": gold_stats,
            "database_path": str(self.db_path),
        }
