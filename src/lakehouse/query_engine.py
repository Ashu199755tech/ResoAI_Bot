"""Query Engine for DuckDB Gold Layer.

Executes deterministic, ultra-fast analytical queries against the Gold Star Schema:
- Exact headcounts filtered by department, location, project, designation, skill
- Salary analytics (average, min, max)
- Employee and team listings
- Department and project summaries
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from src.config import settings

logger = logging.getLogger("resoai.lakehouse.query_engine")


class LakehouseQueryEngine:
    """Executes high-speed analytical queries on DuckDB Gold Star Schema."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or settings.lakehouse_db_path)

    @property
    def is_available(self) -> bool:
        """Check if the DuckDB database exists and has gold tables."""
        if not self.db_path.exists():
            return False
        try:
            con = duckdb.connect(str(self.db_path), read_only=True)
            tables = con.execute("SHOW TABLES").fetchall()
            con.close()
            table_names = [t[0] for t in tables]
            return "fact_employee_allocations" in table_names
        except Exception:
            return False

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a read-only connection to DuckDB."""
        return duckdb.connect(str(self.db_path), read_only=True)

    def execute_query(self, sql: str, params: Optional[list] = None) -> List[Dict[str, Any]]:
        """Run a parameterized SQL query and return results as list of dicts."""
        con = self.get_connection()
        try:
            res = con.execute(sql, params or [])
            cols = [desc[0] for desc in con.description] if con.description else []
            rows = res.fetchall()
            return [dict(zip(cols, row)) for row in rows]
        finally:
            con.close()

    def query_smart(self, question: str) -> Optional[Dict[str, Any]]:
        """Parse natural language question and route to optimal DuckDB Gold query."""
        if not self.is_available:
            return None

        q_lower = question.lower()
        start_time = time.monotonic()

        # Known entities & normalization
        dept_map = {
            "ai": "Artificial Intelligence",
            "artificial intelligence": "Artificial Intelligence",
            "engineering": "Engineering",
            "eng": "Engineering",
            "product": "Product & Design",
            "design": "Product & Design",
            "hr": "Human Resource",
            "human resource": "Human Resource",
            "human resources": "Human Resource",
            "devops": "DevOps & Cloud",
            "cloud": "DevOps & Cloud",
            "qa": "Quality Assurance",
            "quality assurance": "Quality Assurance",
            "sales": "Sales & Marketing",
            "marketing": "Sales & Marketing",
            "data": "Data Analytics",
            "analytics": "Data Analytics",
        }

        cities = ["jaipur", "gurgaon", "udaipur", "bengaluru", "remote"]

        # Detect target department
        target_dept = None
        for key, val in dept_map.items():
            if re.search(rf"\b{re.escape(key)}\b", q_lower):
                target_dept = val
                break

        # Detect target city
        target_city = None
        for city in cities:
            if re.search(rf"\b{city}\b", q_lower):
                target_city = city.capitalize()
                break

        # Detect intent
        is_count = any(k in q_lower for k in ["how many", "count", "number of", "total employees", "total people", "headcount"])
        is_salary = any(k in q_lower for k in ["salary", "pay", "compensation", "earn"])
        is_avg = any(k in q_lower for k in ["average", "avg", "mean"])

        # ── Case 1: Department Summary / Headcount ──────────────
        if (target_dept or target_city) and (is_count or is_salary):
            where_clauses = []
            params = []
            if target_dept:
                where_clauses.append("d.department_name = ?")
                params.append(target_dept)
            if target_city:
                where_clauses.append("e.location = ?")
                params.append(target_city)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            if is_salary and is_avg:
                sql = f"""
                    SELECT 
                        count(f.employee_key) AS count,
                        round(avg(f.salary), 2) AS avg_salary,
                        round(min(f.salary), 2) AS min_salary,
                        round(max(f.salary), 2) AS max_salary
                    FROM fact_employee_allocations f
                    JOIN dim_department d ON f.department_key = d.department_key
                    JOIN dim_employee e ON f.employee_key = e.employee_key
                    WHERE {where_sql}
                """
                results = self.execute_query(sql, params)
                elapsed = time.monotonic() - start_time
                if results and results[0]["count"] > 0:
                    r = results[0]
                    dept_str = f" in {target_dept}" if target_dept else ""
                    city_str = f" in {target_city}" if target_city else ""
                    summary = (
                        f"📊 **Salary Analytics{dept_str}{city_str}**:\n"
                        f"• Total Employees: **{r['count']}**\n"
                        f"• Average Annual Salary: **₹{r['avg_salary']:,.2f}**\n"
                        f"• Salary Range: **₹{r['min_salary']:,.2f}** to **₹{r['max_salary']:,.2f}**"
                    )
                    return {
                        "source": "duckdb_gold_lakehouse",
                        "operation": "salary_aggregation",
                        "count": r["count"],
                        "summary": summary,
                        "sql": sql.strip(),
                        "time_elapsed": round(elapsed, 4),
                    }

            # Standard Headcount Query
            sql = f"""
                SELECT 
                    e.full_name,
                    e.designation,
                    e.location,
                    d.department_name,
                    p.project_name
                FROM fact_employee_allocations f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_employee e ON f.employee_key = e.employee_key
                JOIN dim_project p ON f.project_key = p.project_key
                WHERE {where_sql}
                ORDER BY e.full_name
                LIMIT 50
            """
            results = self.execute_query(sql, params)
            count_sql = f"""
                SELECT count(f.employee_key) as total
                FROM fact_employee_allocations f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_employee e ON f.employee_key = e.employee_key
                WHERE {where_sql}
            """
            count_res = self.execute_query(count_sql, params)
            total_count = count_res[0]["total"] if count_res else len(results)
            elapsed = time.monotonic() - start_time

            dept_str = f" in **{target_dept}**" if target_dept else ""
            city_str = f" in **{target_city}**" if target_city else ""

            if is_count and not any(w in q_lower for k in ["list", "who", "names"] for w in [k]):
                summary = f"Based on live Lakehouse data, there are **{total_count}** employee(s){dept_str}{city_str}."
            else:
                summary_lines = [f"Found **{total_count}** employee(s){dept_str}{city_str}:\n"]
                for i, r in enumerate(results[:15], 1):
                    summary_lines.append(f"{i}. **{r['full_name']}** — {r['designation']} ({r['location']}) [Project: {r['project_name']}]")
                if total_count > 15:
                    summary_lines.append(f"\n_...and {total_count - 15} more records in the lakehouse._")
                summary = "\n".join(summary_lines)

            return {
                "source": "duckdb_gold_lakehouse",
                "operation": "headcount_or_list",
                "count": total_count,
                "matches": results,
                "summary": summary,
                "sql": sql.strip(),
                "time_elapsed": round(elapsed, 4),
            }

        # ── Case 2: Overall Department Headcount Summary ────────
        if any(p in q_lower for p in ["department summary", "headcount by department", "departments headcount", "list departments"]):
            sql = "SELECT * FROM gold_dept_summary"
            results = self.execute_query(sql)
            elapsed = time.monotonic() - start_time

            lines = ["🏢 **Department Headcount & Performance Summary (Gold Lakehouse)**:\n"]
            for r in results:
                lines.append(
                    f"• **{r['department_name']}** ({r['location_hub']} Hub): **{r['total_headcount']}** employees | "
                    f"Avg Salary: ₹{r['avg_salary']:,.0f} | Avg Rating: {r['avg_performance_rating']}/5.0"
                )
            return {
                "source": "duckdb_gold_lakehouse",
                "operation": "dept_summary_mart",
                "count": len(results),
                "matches": results,
                "summary": "\n".join(lines),
                "sql": sql,
                "time_elapsed": round(elapsed, 4),
            }

        # ── Case 3: Project Staffing Summary ────────────────────
        if any(p in q_lower for p in ["project staffing", "projects summary", "team size", "which project has"]):
            sql = "SELECT * FROM gold_project_staffing"
            results = self.execute_query(sql)
            elapsed = time.monotonic() - start_time

            lines = ["🚀 **Active Projects & Staffing (Gold Lakehouse)**:\n"]
            for r in results:
                lines.append(
                    f"• **{r['project_name']}** ({r['domain']}): **{r['assigned_team_size']}** members | "
                    f"Client: {r['client_name']} | Rating: {r['avg_team_rating']}/5.0"
                )
            return {
                "source": "duckdb_gold_lakehouse",
                "operation": "project_staffing_mart",
                "count": len(results),
                "matches": results,
                "summary": "\n".join(lines),
                "sql": sql,
                "time_elapsed": round(elapsed, 4),
            }

        return None
