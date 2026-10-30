"""Tests for DuckDB Medallion Lakehouse pipeline, Star Schema, and Query Engine."""

from __future__ import annotations

import duckdb

from src.lakehouse.generator import generate_synthetic_hr_dataset
from src.lakehouse.pipeline import LakehousePipeline
from src.lakehouse.query_engine import LakehouseQueryEngine
from src.lakehouse.vector_sync import (
    build_employee_semantic_doc,
    build_project_semantic_doc,
    build_holiday_semantic_doc,
)


def test_synthetic_data_generator():
    """Verify generator generates valid structures with expected fields."""
    data = generate_synthetic_hr_dataset(count=50, seed=123)
    assert len(data["employees"]) == 50
    assert len(data["departments"]) > 0
    assert len(data["projects"]) > 0
    assert len(data["allocations"]) == 50
    assert "holidays" in data
    assert len(data["holidays"]) > 0

    emp = data["employees"][0]
    assert "employee_id" in emp
    assert "full_name" in emp
    assert "department_name" in emp
    assert "salary" in emp
    assert emp["salary"] > 0


def test_lakehouse_medallion_pipeline(tmp_path):
    """Test full Medallion Architecture: Bronze -> Silver -> Gold."""
    db_file = tmp_path / "test_lakehouse.duckdb"
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    gold_dir = tmp_path / "gold"

    pipeline = LakehousePipeline(
        db_path=str(db_file),
        bronze_dir=str(bronze_dir),
        silver_dir=str(silver_dir),
        gold_dir=str(gold_dir),
    )

    # 1. Bronze
    bronze_file = pipeline.ingest_bronze(record_count=30)
    assert bronze_file.exists()

    # 2. Silver
    silver_stats = pipeline.process_silver(bronze_file)
    assert silver_stats["employees"] == 30
    assert (silver_dir / "silver_employees.parquet").exists()
    assert (silver_dir / "silver_projects.parquet").exists()
    assert (silver_dir / "silver_holidays.parquet").exists()

    # 3. Gold
    gold_stats = pipeline.process_gold()
    assert gold_stats["fact_records"] == 30
    assert gold_stats["dim_employees"] == 30
    assert gold_stats["dim_holidays"] > 0
    assert (gold_dir / "fact_employee_allocations.parquet").exists()
    assert (gold_dir / "dim_employee.parquet").exists()
    assert (gold_dir / "dim_holiday.parquet").exists()

    # 4. Query Gold Star Schema directly
    con = duckdb.connect(str(db_file))
    dept_summary = con.execute("SELECT * FROM gold_dept_summary").fetchall()
    assert len(dept_summary) > 0

    city_summary = con.execute("SELECT * FROM gold_city_headcount").fetchall()
    assert len(city_summary) > 0

    holidays = con.execute("SELECT * FROM company_holidays").fetchall()
    assert len(holidays) > 0
    con.close()


def test_lakehouse_query_engine(tmp_path):
    """Test natural language analytical routing on Gold Star Schema."""
    db_file = tmp_path / "test_lakehouse.duckdb"
    pipeline = LakehousePipeline(
        db_path=str(db_file),
        bronze_dir=str(tmp_path / "bronze"),
        silver_dir=str(tmp_path / "silver"),
        gold_dir=str(tmp_path / "gold"),
    )
    pipeline.run_full_pipeline(record_count=40)

    engine = LakehouseQueryEngine(db_path=str(db_file))
    assert engine.is_available is True

    # Test count query
    res_count = engine.query_smart("How many employees in Engineering?")
    assert res_count is not None
    assert "Engineering" in res_count["summary"]
    assert res_count["count"] >= 0

    # Test salary analytics
    res_salary = engine.query_smart("Average salary in Engineering")
    assert res_salary is not None
    assert "Salary Analytics" in res_salary["summary"]
    assert "₹" in res_salary["summary"]

    # Test department summary
    res_dept = engine.query_smart("Department summary")
    assert res_dept is not None
    assert "Department Headcount" in res_dept["summary"]

    # Test holiday queries
    res_hol = engine.query_smart("When is Diwali?")
    assert res_hol is not None
    assert "Diwali" in res_hol["summary"]
    assert "Date:" in res_hol["summary"]

    res_hol_month = engine.query_smart("Holidays in October")
    assert res_hol_month is not None
    assert "October" in res_hol_month["summary"]


def test_semantic_document_builders():
    """Verify DuckDB records convert to LangChain Documents for ChromaDB."""
    emp_record = {
        "employee_id": "EMP0099",
        "full_name": "Test User",
        "first_name": "Test",
        "last_name": "User",
        "email": "test.user@fiftyfivetech.io",
        "phone": "9999999999",
        "designation": "ML Specialist",
        "location": "Jaipur",
        "skills": "Python, RAG, PyTorch",
        "joining_date": "2023-01-01",
        "status": "Active",
        "department_name": "Artificial Intelligence",
        "location_hub": "Jaipur",
        "project_name": "ResoAI",
        "domain": "Enterprise AI",
        "salary": 1200000.0,
        "years_of_experience": 4.5,
        "performance_rating": 4.8,
    }

    doc = build_employee_semantic_doc(emp_record)
    assert "EMP0099" in doc.page_content
    assert "Test User" in doc.page_content
    assert doc.metadata["record_type"] == "employee"
    assert doc.metadata["employee_name"] == "Test User"

    proj_record = {
        "project_id": "PRJ99",
        "project_name": "ResoAI",
        "domain": "Enterprise AI",
        "client_name": "Internal",
        "tech_stack": "Python, DuckDB",
    }
    proj_doc = build_project_semantic_doc(proj_record)
    assert "ResoAI" in proj_doc.page_content
    assert proj_doc.metadata["record_type"] == "project"

    hol_record = {
        "holiday_id": "HOL_DIWALI_2026",
        "holiday_name": "Diwali",
        "date": "2026-11-08",
        "day": "Sunday",
        "month": "November",
        "holiday_type": "Weekend",
    }
    hol_doc = build_holiday_semantic_doc(hol_record)
    assert "Diwali" in hol_doc.page_content
    assert hol_doc.metadata["record_type"] == "holiday"
    assert hol_doc.metadata["holiday_name"] == "Diwali"
