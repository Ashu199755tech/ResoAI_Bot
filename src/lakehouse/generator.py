"""Synthetic HR Data Generator for ResoAI Medallion Lakehouse.

Uses Faker with a deterministic seed to generate rich, realistic enterprise HR datasets:
- Departments & Hubs
- Projects & Tech Stacks
- Employees (demographics, designations, salaries, skills, tenure)
- Project Allocations
- Performance & Leaves
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

from faker import Faker
from src.config import settings

DEFAULT_COMPANY_HOLIDAYS = [
    {"id": "HOL_NEW_YEAR__2026_2026", "name": "New Year - 2026", "date": "2026-01-01", "day": "Thursday", "month": "January", "type": "Fixed"},
    {"id": "HOL_REPUBLIC_DAY_2026", "name": "Republic Day", "date": "2026-01-26", "day": "Monday", "month": "January", "type": "Fixed"},
    {"id": "HOL_HOLI_2026", "name": "Holi", "date": "2026-03-04", "day": "Wednesday", "month": "March", "type": "Fixed"},
    {"id": "HOL_INDEPENDENCE_DAY_2026", "name": "Independence Day", "date": "2026-08-15", "day": "Saturday", "month": "August", "type": "Weekend"},
    {"id": "HOL_MAHATMA_GANDHI_JAYANTI_2026", "name": "Mahatma Gandhi Jayanti", "date": "2026-10-02", "day": "Friday", "month": "October", "type": "Fixed"},
    {"id": "HOL_DUSSHERA_2026", "name": "Dusshera", "date": "2026-10-20", "day": "Tuesday", "month": "October", "type": "Fixed"},
    {"id": "HOL_DIWALI_2026", "name": "Diwali", "date": "2026-11-08", "day": "Sunday", "month": "November", "type": "Weekend"},
    {"id": "HOL_CHRISTMAS_DAY_2026", "name": "Christmas Day", "date": "2026-12-25", "day": "Friday", "month": "December", "type": "Fixed"},
    {"id": "HOL_MAKAR_SANKRANTI__PONGAL_2026", "name": "Makar Sankranti / Pongal", "date": "2026-01-14", "day": "Wednesday", "month": "January", "type": "Floater Leave"},
    {"id": "HOL_RANGPANCHMI_2026", "name": "Rangpanchmi", "date": "2026-03-08", "day": "Sunday", "month": "March", "type": "Weekend"},
    {"id": "HOL_EID_UL_FITR_2026", "name": "Eid-ul-Fitr", "date": "2026-03-21", "day": "Saturday", "month": "March", "type": "Weekend"},
    {"id": "HOL_RAM_NAVAMI_2026", "name": "Ram Navami", "date": "2026-03-26", "day": "Thursday", "month": "March", "type": "Floater Leave"},
    {"id": "HOL_MAHAVEER_JAYANTI_2026", "name": "Mahaveer Jayanti", "date": "2026-03-31", "day": "Tuesday", "month": "March", "type": "Floater Leave"},
    {"id": "HOL_GOOD_FRIDAY_2026", "name": "Good Friday", "date": "2026-04-03", "day": "Friday", "month": "April", "type": "Floater Leave"},
    {"id": "HOL_AMBEDKAR_JAYANTI_2026", "name": "Ambedkar Jayanti", "date": "2026-04-14", "day": "Tuesday", "month": "April", "type": "Floater Leave"},
    {"id": "HOL_EID_AL_ADHA_2026", "name": "Eid Al Adha", "date": "2026-05-27", "day": "Wednesday", "month": "May", "type": "Floater Leave"},
    {"id": "HOL_ONAM_2026", "name": "Onam", "date": "2026-08-26", "day": "Wednesday", "month": "August", "type": "Floater Leave"},
    {"id": "HOL_RAKSHA_BANDHAN_2026", "name": "Raksha Bandhan", "date": "2026-08-28", "day": "Friday", "month": "August", "type": "Floater Leave"},
    {"id": "HOL_JANMASHTAMI_2026", "name": "Janmashtami", "date": "2026-09-04", "day": "Friday", "month": "September", "type": "Floater Leave"},
    {"id": "HOL_GANESH_CHATURTHI_2026", "name": "Ganesh Chaturthi", "date": "2026-09-14", "day": "Monday", "month": "September", "type": "Floater Leave"},
    {"id": "HOL_MAHAV_NAVMI__DURGA_POOJA_2026", "name": "Mahav Navmi / Durga Pooja", "date": "2026-10-19", "day": "Monday", "month": "October", "type": "Floater Leave"},
    {"id": "HOL_BHAI_DOOJ_2026", "name": "Bhai Dooj", "date": "2026-11-11", "day": "Wednesday", "month": "November", "type": "Floater Leave"},
    {"id": "HOL_CHHATH_POOJA_2026", "name": "Chhath Pooja", "date": "2026-11-15", "day": "Sunday", "month": "November", "type": "Weekend"},
    {"id": "HOL_GURU_NANAK_JAYANTI_2026", "name": "Guru Nanak Jayanti", "date": "2026-11-24", "day": "Tuesday", "month": "November", "type": "Floater Leave"}
]


def get_company_holidays() -> List[Dict[str, Any]]:
    """Load official company holidays from data/holidays.json or fallback list."""
    holidays_file = Path(settings.data_dir) / "holidays.json"
    if holidays_file.exists():
        try:
            with open(holidays_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return DEFAULT_COMPANY_HOLIDAYS


LOCATIONS = ["Jaipur", "Gurgaon", "Udaipur", "Bengaluru", "Remote"]

DEPARTMENTS = [
    {"department_id": "DEP01", "department_name": "Artificial Intelligence", "location_hub": "Jaipur"},
    {"department_id": "DEP02", "department_name": "Engineering", "location_hub": "Jaipur"},
    {"department_id": "DEP03", "department_name": "Product & Design", "location_hub": "Gurgaon"},
    {"department_id": "DEP04", "department_name": "Human Resource", "location_hub": "Jaipur"},
    {"department_id": "DEP05", "department_name": "DevOps & Cloud", "location_hub": "Gurgaon"},
    {"department_id": "DEP06", "department_name": "Quality Assurance", "location_hub": "Jaipur"},
    {"department_id": "DEP07", "department_name": "Sales & Marketing", "location_hub": "Bengaluru"},
    {"department_id": "DEP08", "department_name": "Data Analytics", "location_hub": "Udaipur"},
]

PROJECTS = [
    {
        "project_id": "PRJ01",
        "project_name": "ResoAI",
        "domain": "Enterprise AI / NLP",
        "tech_stack": "Python, Ollama, ChromaDB, FastAPI, LangChain",
        "client_name": "FiftyFive Technologies Internal",
    },
    {
        "project_id": "PRJ02",
        "project_name": "VisionAI OCR",
        "domain": "Computer Vision",
        "tech_stack": "Python, PyTorch, OpenCV, Fastify, Docker",
        "client_name": "HealthCorp Global",
    },
    {
        "project_id": "PRJ03",
        "project_name": "CloudMigrate",
        "domain": "Cloud Infrastructure",
        "tech_stack": "AWS, Terraform, Kubernetes, Go",
        "client_name": "FinTech Alliance",
    },
    {
        "project_id": "PRJ04",
        "project_name": "RetailPulse",
        "domain": "E-Commerce Analytics",
        "tech_stack": "React, Node.js, PostgreSQL, Redis",
        "client_name": "OmniRetail Inc",
    },
    {
        "project_id": "PRJ05",
        "project_name": "FraudShield",
        "domain": "Cybersecurity & Fraud Detection",
        "tech_stack": "Python, Scikit-learn, Kafka, ClickHouse",
        "client_name": "Apex Banking Group",
    },
    {
        "project_id": "PRJ06",
        "project_name": "Phoenix HRMS",
        "domain": "HR SaaS Platform",
        "tech_stack": "Next.js, FastAPI, GraphQL, MongoDB",
        "client_name": "Keka Systems Partner",
    },
]

SKILL_SETS = {
    "Artificial Intelligence": ["Python", "PyTorch", "TensorFlow", "HuggingFace", "NLP", "LLMs", "RAG", "Computer Vision", "LangChain"],
    "Engineering": ["Python", "FastAPI", "React", "Node.js", "Java", "Go", "PostgreSQL", "Docker", "Microservices"],
    "Product & Design": ["Figma", "UI/UX", "Product Roadmap", "User Research", "Agile", "Jira"],
    "Human Resource": ["Talent Acquisition", "Employee Relations", "Payroll", "HR Analytics", "Compliance", "Keka"],
    "DevOps & Cloud": ["AWS", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Prometheus"],
    "Quality Assurance": ["Automation Testing", "Selenium", "Cypress", "PyTest", "API Testing", "Postman"],
    "Sales & Marketing": ["B2B Sales", "Lead Generation", "SEO", "Content Strategy", "CRM", "HubSpot"],
    "Data Analytics": ["SQL", "DuckDB", "PowerBI", "Tableau", "Pandas", "ETL", "Data Modeling"],
}

DESIGNATIONS = {
    "Artificial Intelligence": ["Junior ML Engineer", "ML Engineer", "Senior ML Engineer", "Lead AI Scientist", "Head of AI"],
    "Engineering": ["Associate Software Engineer", "Software Engineer", "Senior Software Engineer", "Tech Lead", "Principal Architect"],
    "Product & Design": ["UI/UX Designer", "Product Designer", "Product Manager", "Lead Product Manager"],
    "Human Resource": ["HR Executive", "HR Generalist", "Senior HR Specialist", "HR Business Partner", "Head of HR"],
    "DevOps & Cloud": ["Cloud Engineer", "Senior DevOps Engineer", "DevOps Lead", "Cloud Architect"],
    "Quality Assurance": ["QA Tester", "QA Automation Engineer", "Senior QA Lead"],
    "Sales & Marketing": ["Sales Executive", "Account Manager", "Marketing Manager", "VP of Growth"],
    "Data Analytics": ["Data Analyst", "Senior Data Analyst", "Analytics Engineer", "Data Analytics Lead"],
}


def generate_synthetic_hr_dataset(count: int = 500, seed: int = 42) -> Dict[str, Any]:
    """Generate a cohesive synthetic HR dataset with deterministic relationships."""
    random.seed(seed)
    fake = Faker("en_IN")
    Faker.seed(seed)

    employees: List[Dict[str, Any]] = []
    allocations: List[Dict[str, Any]] = []

    start_date_range = date(2020, 1, 1)
    end_date_range = date(2026, 10, 1)
    days_span = (end_date_range - start_date_range).days

    for i in range(1, count + 1):
        emp_id = f"EMP{i:04d}"
        first_name = fake.first_name()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}@fiftyfivetech.io"
        phone = fake.phone_number()

        dept = random.choice(DEPARTMENTS)
        dept_name = dept["department_name"]
        dept_id = dept["department_id"]

        designation = random.choice(DESIGNATIONS[dept_name])
        location = random.choice(LOCATIONS)

        # Realistic joining date
        random_days = random.randint(0, days_span)
        joining_date = start_date_range + timedelta(days=random_days)

        # Experience & Salary calculation based on designation level
        level_index = DESIGNATIONS[dept_name].index(designation)
        base_salary = 600000 + (level_index * 450000) + random.randint(20000, 150000)
        years_of_experience = round(1.5 + (level_index * 2.5) + random.uniform(0.1, 2.0), 1)

        # Skills (pick 3-5 from department pool)
        emp_skills = random.sample(SKILL_SETS[dept_name], k=random.randint(3, min(5, len(SKILL_SETS[dept_name]))))

        # Project allocation
        project = random.choice(PROJECTS)
        allocation_pct = random.choice([50, 80, 100])
        status = random.choices(["Active", "On Notice", "Probation"], weights=[88, 7, 5])[0]

        # Performance & leaves
        performance_rating = round(random.triangular(2.8, 5.0, 4.2), 1)
        leave_balance = random.randint(4, 24)

        emp_record = {
            "employee_id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "department_id": dept_id,
            "department_name": dept_name,
            "designation": designation,
            "location": location,
            "joining_date": joining_date.isoformat(),
            "salary": float(base_salary),
            "years_of_experience": years_of_experience,
            "skills": ", ".join(emp_skills),
            "status": status,
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "performance_rating": performance_rating,
            "leave_balance": leave_balance,
        }
        employees.append(emp_record)

        # Allocation record
        allocations.append({
            "allocation_id": f"ALC{i:04d}",
            "employee_id": emp_id,
            "project_id": project["project_id"],
            "allocation_percentage": allocation_pct,
            "role_in_project": designation,
            "start_date": joining_date.isoformat(),
        })

    return {
        "departments": DEPARTMENTS,
        "projects": PROJECTS,
        "employees": employees,
        "allocations": allocations,
        "holidays": get_company_holidays(),
        "meta": {
            "generated_count": count,
            "company_name": "FiftyFive Technologies",
            "seed": seed,
        },
    }
