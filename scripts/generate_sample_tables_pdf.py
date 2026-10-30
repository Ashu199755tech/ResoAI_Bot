#!/usr/bin/env python3
"""
Generate a clean, presentation-ready PDF containing sample table data from DuckDB.
Designed specifically for sharing with managers and stakeholders.
"""

import os
import subprocess
import duckdb

DB_PATH = "data/lakehouse/resoai_lakehouse.duckdb"
OUTPUT_HTML = "docs/duckdb_sample_data.html"
OUTPUT_PDF = "docs/duckdb_sample_data.pdf"

def format_val(val, col=""):
    if val is None:
        return '<span class="null-val">NULL</span>'
    if isinstance(val, float):
        if "salary" in col.lower():
            return f"₹{val:,.2f}"
        if "rating" in col.lower() or "score" in col.lower():
            return f"{val:.2f} ★"
        return f"{val:.2f}"
    if isinstance(val, int):
        if "salary" in col.lower():
            return f"₹{val:,}"
        return f"{val:,}"
    s = str(val)
    if "holiday_type" in col.lower() or "classification" in col.lower():
        if "fixed" in s.lower():
            return f'<span class="badge badge-fixed">{s}</span>'
        elif "floater" in s.lower():
            return f'<span class="badge badge-floater">{s}</span>'
        return f'<span class="badge badge-weekend">{s}</span>'
    if col.lower() == "status":
        return f'<span class="badge badge-active">{s}</span>'
    return s

def render_table_block(title, subtitle, columns, rows, badge_text=""):
    headers_html = "".join([f"<th>{c}</th>" for c in columns])
    data_rows_html = ""
    for r in rows:
        cells_html = "".join([f"<td>{format_val(val, c)}</td>" for val, c in zip(r, columns)])
        data_rows_html += f"<tr>{cells_html}</tr>"

    return f"""
    <div class="table-container">
      <div class="table-header-row">
        <div>
          <span class="table-title">{title}</span>
          <span class="table-subtitle">{subtitle}</span>
        </div>
        {f'<span class="badge-layer">{badge_text}</span>' if badge_text else ''}
      </div>
      <table class="data-table">
        <thead>
          <tr>{headers_html}</tr>
        </thead>
        <tbody>
          {data_rows_html}
        </tbody>
      </table>
    </div>
    """

def generate_pdf():
    conn = duckdb.connect(DB_PATH, read_only=True)

    # 1. gold_dept_summary (all 8 rows)
    q_dept = """
        SELECT 
            department_name AS "Department",
            location_hub AS "Hub",
            total_headcount AS "Headcount",
            avg_salary AS "Avg Salary",
            min_salary AS "Min Salary",
            max_salary AS "Max Salary",
            avg_performance_rating AS "Avg Rating",
            avg_years_experience AS "Avg Exp (Yrs)"
        FROM gold_dept_summary
        ORDER BY total_headcount DESC
    """
    res_dept = conn.execute(q_dept).fetchall()
    cols_dept = [d[0] for d in conn.execute(q_dept).description]

    # 2. gold_city_headcount (all 5 rows)
    q_city = """
        SELECT 
            location AS "Office / Location",
            employee_count AS "Total Headcount",
            departments_present AS "Departments Active",
            avg_salary AS "Average Salary (INR)"
        FROM gold_city_headcount
        ORDER BY employee_count DESC
    """
    res_city = conn.execute(q_city).fetchall()
    cols_city = [d[0] for d in conn.execute(q_city).description]

    # 3. gold_project_staffing (all 6 rows)
    q_proj_staff = """
        SELECT 
            project_name AS "Project Name",
            domain AS "Industry Domain",
            client_name AS "Client / Engagement",
            assigned_team_size AS "Team Size",
            avg_team_rating AS "Team Rating"
        FROM gold_project_staffing
        ORDER BY assigned_team_size DESC
    """
    res_proj_staff = conn.execute(q_proj_staff).fetchall()
    cols_proj_staff = [d[0] for d in conn.execute(q_proj_staff).description]

    # 4. company_holidays (7 major holidays for clean fit)
    q_holidays = """
        SELECT 
            holiday_name AS "Holiday Name",
            date AS "Date",
            day AS "Day of Week",
            month AS "Month",
            holiday_type AS "Classification"
        FROM company_holidays
        ORDER BY date ASC
        LIMIT 7
    """
    res_holidays = conn.execute(q_holidays).fetchall()
    cols_holidays = [d[0] for d in conn.execute(q_holidays).description]

    # 5. dim_department (all 8 rows)
    q_dim_dept = """
        SELECT 
            department_id AS "Dept ID",
            department_name AS "Department Name",
            location_hub AS "Primary Operating Hub"
        FROM dim_department
        ORDER BY department_id ASC
    """
    res_dim_dept = conn.execute(q_dim_dept).fetchall()
    cols_dim_dept = [d[0] for d in conn.execute(q_dim_dept).description]

    # 6. dim_project (all 6 rows)
    q_dim_proj = """
        SELECT 
            project_id AS "Project ID",
            project_name AS "Project Name",
            domain AS "Domain",
            tech_stack AS "Tech Stack",
            client_name AS "Client"
        FROM dim_project
        ORDER BY project_id ASC
    """
    res_dim_proj = conn.execute(q_dim_proj).fetchall()
    cols_dim_proj = [d[0] for d in conn.execute(q_dim_proj).description]

    # 7. dim_employee (Sample 6 employees across roles)
    q_emp = """
        SELECT 
            employee_id AS "Emp ID",
            full_name AS "Employee Name",
            designation AS "Designation / Role",
            location AS "Location",
            skills AS "Core Skills",
            joining_date AS "Joining Date",
            status AS "Status"
        FROM dim_employee
        ORDER BY employee_key ASC
        LIMIT 6
    """
    res_emp = conn.execute(q_emp).fetchall()
    cols_emp = [d[0] for d in conn.execute(q_emp).description]

    # 8. fact_employee_allocations (Sample 6 rows joined with readable context)
    q_fact = """
        SELECT 
            f.fact_id AS "Fact ID",
            e.employee_id AS "Emp ID",
            e.full_name AS "Employee Name",
            d.department_name AS "Department",
            p.project_name AS "Project",
            f.salary AS "Salary (CTC)",
            f.years_of_experience AS "Exp (Yrs)",
            f.performance_rating AS "Rating",
            f.leave_balance AS "Leave Days",
            f.allocation_percentage AS "Alloc %"
        FROM fact_employee_allocations f
        JOIN dim_employee e ON f.employee_key = e.employee_key
        JOIN dim_department d ON f.department_key = d.department_key
        JOIN dim_project p ON f.project_key = p.project_key
        ORDER BY f.fact_id ASC
        LIMIT 6
    """
    res_fact = conn.execute(q_fact).fetchall()
    cols_fact = [d[0] for d in conn.execute(q_fact).description]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ResoAI DuckDB Sample Tables</title>
<style>
  @page {{
    size: A4 landscape;
    margin: 8mm 12mm 8mm 12mm;
    @bottom-right {{
      content: "Page " counter(page) " of 3";
      font-size: 7.5pt;
      color: #64748b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    @bottom-left {{
      content: "ResoAI DuckDB Medallion Lakehouse • Live Sample Table Data • FiftyFive Technologies";
      font-size: 7.5pt;
      color: #94a3b8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    font-size: 8pt;
    line-height: 1.32;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  /* HEADER BANNER */
  .header-card {{
    background: #0f172a;
    color: #ffffff;
    padding: 9px 14px;
    border-radius: 5px;
    margin-bottom: 7px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .header-title {{
    font-size: 13pt;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.3px;
  }}

  .header-subtitle {{
    font-size: 7.8pt;
    color: #94a3b8;
  }}

  .header-badge {{
    background: #0284c7;
    color: #ffffff;
    padding: 2.5px 9px;
    border-radius: 9999px;
    font-size: 6.8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* TABLE CONTAINER */
  .table-container {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px 9px;
    margin-bottom: 7px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  }}

  .table-header-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }}

  .table-title {{
    font-size: 9pt;
    font-weight: 800;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color: #0f172a;
    margin-right: 6px;
  }}

  .table-subtitle {{
    font-size: 7.2pt;
    color: #64748b;
  }}

  .badge-layer {{
    font-size: 6.5pt;
    font-weight: 700;
    text-transform: uppercase;
    padding: 1.5px 6px;
    border-radius: 3px;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
  }}

  /* DATA TABLE */
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 6.8pt;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    overflow: hidden;
  }}

  .data-table th {{
    background: #1e293b;
    color: #f8fafc;
    padding: 3px 5px;
    font-weight: 700;
    text-align: left;
    white-space: nowrap;
    border-right: 1px solid #334155;
    font-size: 6.5pt;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}

  .data-table th:last-child {{
    border-right: none;
  }}

  .data-table td {{
    padding: 2.5px 5px;
    border-bottom: 1px solid #e2e8f0;
    border-right: 1px solid #f1f5f9;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 6.6pt;
    color: #334155;
    white-space: nowrap;
  }}

  .data-table td:last-child {{
    border-right: none;
  }}

  .data-table tr:nth-child(even) td {{
    background-color: #f8fafc;
  }}

  .badge {{
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 6pt;
    font-weight: 700;
    text-transform: uppercase;
  }}

  .badge-fixed {{
    background: #e0f2fe;
    color: #0369a1;
    border: 1px solid #bae6fd;
  }}

  .badge-floater {{
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fde68a;
  }}

  .badge-weekend {{
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
  }}

  .badge-active {{
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #bbf7d0;
  }}

  .page-break {{
    page-break-after: always;
    break-after: page;
  }}
</style>
</head>
<body>

  <!-- ==================== PAGE 1 ==================== -->
  <div class="header-card">
    <div>
      <div class="header-title">DuckDB Medallion Lakehouse — Live Sample Data</div>
      <div class="header-subtitle">Section 1: Analytical Aggregation Marts (Headcounts, Compensation & Staffing)</div>
    </div>
    <span class="header-badge">Gold Analytics Marts</span>
  </div>

  {render_table_block("gold_dept_summary", "Department Headcounts, Compensation Ranges & Experience Metrics (Full 8 Departments)", cols_dept, res_dept, "Gold Mart")}
  {render_table_block("gold_city_headcount", "Geographic Workforce Distribution & Average Salary per City Hub (Full 5 Locations)", cols_city, res_city, "Gold Mart")}
  {render_table_block("gold_project_staffing", "Enterprise Client Engagements & Engineering Team Allocations (Full 6 Projects)", cols_proj_staff, res_proj_staff, "Gold Mart")}

  <div class="page-break"></div>

  <!-- ==================== PAGE 2 ==================== -->
  <div class="header-card">
    <div>
      <div class="header-title">DuckDB Medallion Lakehouse — Live Sample Data</div>
      <div class="header-subtitle">Section 2: Company Calendar & Organizational Dimensions</div>
    </div>
    <span class="header-badge">Core Dimensions</span>
  </div>

  {render_table_block("company_holidays", "Official FiftyFive Technologies 2026 Corporate Holiday Calendar (Sample Major Holidays)", cols_holidays, res_holidays, "Holiday Dimension")}
  {render_table_block("dim_department", "Business Units & Primary Physical Operating Hubs (Full 8 Departments)", cols_dim_dept, res_dim_dept, "Dept Dimension")}
  {render_table_block("dim_project", "Innovation Initiatives, Industry Domains & Technology Stacks (Full 6 Projects)", cols_dim_proj, res_dim_proj, "Project Dimension")}

  <div class="page-break"></div>

  <!-- ==================== PAGE 3 ==================== -->
  <div class="header-card">
    <div>
      <div class="header-title">DuckDB Medallion Lakehouse — Live Sample Data</div>
      <div class="header-subtitle">Section 3: Workforce Directory & Analytical Star Schema Fact Model</div>
    </div>
    <span class="header-badge">Fact & Employee Dimension</span>
  </div>

  {render_table_block("dim_employee", "Workforce Directory with Designations, Skills Taxonomy & Locations (Sample 6 Employees)", cols_emp, res_emp, "Employee Dimension")}
  {render_table_block("fact_employee_allocations", "Quantitative Fact Table with Joined Context (Salaries, Ratings, Leaves & Allocations)", cols_fact, res_fact, "Star Schema Fact")}

</body>
</html>
"""

    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML written to: {OUTPUT_HTML}")

    abs_html = os.path.abspath(OUTPUT_HTML)
    abs_pdf = os.path.abspath(OUTPUT_PDF)
    chrome_cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={abs_pdf}",
        f"file://{abs_html}"
    ]
    subprocess.run(chrome_cmd, check=True)
    print(f"PDF generated at: {OUTPUT_PDF}")

if __name__ == "__main__":
    generate_pdf()
