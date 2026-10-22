"""Dual-Sync Bridge: Syncs DuckDB Gold Dimensional Records into ChromaDB Vector Store.

Converts structured relational employee and project entities into rich semantic text profiles
and embeds them in ChromaDB so semantic search and conceptual queries work seamlessly alongside SQL.
"""

from __future__ import annotations

import logging
from typing import List

from langchain_core.documents import Document

from src.lakehouse.pipeline import LakehousePipeline
from src.rag.store import get_vector_store

logger = logging.getLogger("resoai.lakehouse.vector_sync")


def build_employee_semantic_doc(record: dict) -> Document:
    """Build a rich, semantically dense Document from an employee record."""
    content = (
        f"Employee Profile: {record['full_name']} ({record['employee_id']})\n"
        f"Designation: {record['designation']}\n"
        f"Department: {record['department_name']} ({record['location_hub']} Hub)\n"
        f"Current Work Location: {record['location']}\n"
        f"Current Project: {record['project_name']} (Domain: {record.get('domain', 'Enterprise')})\n"
        f"Core Technical Skills: {record['skills']}\n"
        f"Experience Level: {record['years_of_experience']} years\n"
        f"Performance Rating: {record['performance_rating']} / 5.0\n"
        f"Employment Status: {record['status']}\n"
        f"Email Address: {record['email']}\n"
        f"Contact Phone: {record['phone']}"
    )

    metadata = {
        "record_type": "employee",
        "record_id": record["employee_id"],
        "employee_name": record["full_name"],
        "department": record["department_name"],
        "location": record["location"],
        "designation": record["designation"],
        "project_name": record["project_name"],
        "source": "duckdb_gold_lakehouse",
    }
    return Document(page_content=content, metadata=metadata)


def build_project_semantic_doc(record: dict) -> Document:
    """Build a rich semantic Document from a project record."""
    content = (
        f"Project Profile: {record['project_name']} ({record['project_id']})\n"
        f"Domain / Industry: {record['domain']}\n"
        f"Client: {record['client_name']}\n"
        f"Technology Stack: {record['tech_stack']}\n"
        f"Overview: Enterprise project delivered by FiftyFive Technologies focusing on {record['domain']}."
    )

    metadata = {
        "record_type": "project",
        "record_id": record["project_id"],
        "project_name": record["project_name"],
        "domain": record["domain"],
        "source": "duckdb_gold_lakehouse",
    }
    return Document(page_content=content, metadata=metadata)


def sync_lakehouse_to_vector_store(pipeline: LakehousePipeline | None = None, limit: int | None = None) -> int:
    """Read Gold layer records from DuckDB, convert to semantic documents, and insert into ChromaDB."""
    pipeline = pipeline or LakehousePipeline()
    con = pipeline.get_connection()

    try:
        # 1. Fetch joined employee records
        query = """
            SELECT 
                e.employee_id,
                e.full_name,
                e.first_name,
                e.last_name,
                e.email,
                e.phone,
                e.designation,
                e.location,
                e.skills,
                e.joining_date,
                e.status,
                d.department_name,
                d.location_hub,
                p.project_name,
                p.domain,
                f.salary,
                f.years_of_experience,
                f.performance_rating
            FROM dim_employee e
            JOIN fact_employee_allocations f ON e.employee_key = f.employee_key
            JOIN dim_department d ON f.department_key = d.department_key
            JOIN dim_project p ON f.project_key = p.project_key
        """
        if limit:
            query += f" LIMIT {limit}"

        emp_rows = con.execute(query).fetchall()
        cols = [desc[0] for desc in con.description]
        emp_records = [dict(zip(cols, row)) for row in emp_rows]

        # 2. Fetch project records
        proj_rows = con.execute("SELECT * FROM dim_project").fetchall()
        proj_cols = [desc[0] for desc in con.description]
        proj_records = [dict(zip(proj_cols, row)) for row in proj_rows]

        # 3. Create Documents
        documents: List[Document] = []
        for r in emp_records:
            documents.append(build_employee_semantic_doc(r))

        for r in proj_records:
            documents.append(build_project_semantic_doc(r))

        logger.info("Generated %d semantic profile documents from DuckDB", len(documents))

        # 4. Ingest into ChromaDB
        vector_store = get_vector_store()
        
        # Batch insert into ChromaDB (batches of 100)
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            vector_store.add_documents(batch)

        logger.info("Successfully synced %d records from DuckDB to ChromaDB", len(documents))
        return len(documents)

    finally:
        con.close()
