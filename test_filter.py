"""
Pytest tests for filter.py role matching, exclusion, and gating logic.
"""

import pytest
from filter import find_matching_group, passes_filters, _contains_any, _contains_word_boundary, parse_stipend_value


# Word-boundary matching tests
def test_word_boundary_matching():
    """Test that word-boundary matching avoids substring matches."""
    # Should match
    assert _contains_word_boundary("Python Developer", ["python"])
    assert _contains_word_boundary("SQL Expert", ["sql"])
    assert _contains_word_boundary("Machine Learning Engineer", ["machine learning"])
    
    # Should NOT match (substring only)
    assert not _contains_word_boundary("Biology", ["bi"])
    assert not _contains_word_boundary("Bilingual", ["bi"])
    assert not _contains_word_boundary("Bicycle", ["bi"])


# Role group matching tests
def test_core_role_matching():
    """Test core data analyst/BI roles match correctly."""
    role_groups = [
        {
            "name": "core",
            "bypass_location_and_stipend": True,
            "word_boundary_keywords": ["python", "sql", "machine learning"],
            "keywords": [
                "data analyst", "data analytics", "data analysis",
                "data scientist", "data science", "business analyst",
                "business analytics", "business intelligence", " bi ",
                "bi analyst", "bi developer", "power bi", "kpi",
                "dashboard", "reporting analyst", "mis analyst",
                "mis executive", "insights analyst", "junior data analyst",
                "associate data analyst", "operations analyst",
                "business operations analyst"
            ]
        }
    ]
    
    # Should match core
    assert find_matching_group("Data Analyst Intern", role_groups)
    assert find_matching_group("Business Analyst Intern", role_groups)
    assert find_matching_group("Business Intelligence Intern", role_groups)
    assert find_matching_group("MIS Executive", role_groups)
    assert find_matching_group("Operations Analyst Intern", role_groups)
    assert find_matching_group("Power BI Developer", role_groups)
    
    # Python should NOT match without data context
    assert not find_matching_group("Python Developer", role_groups)
    # SQL should NOT match without data context
    assert not find_matching_group("SQL Expert", role_groups)
    # Machine Learning should NOT match without data context
    assert not find_matching_group("Machine Learning Engineer", role_groups)
    
    # Python with data context SHOULD match
    assert find_matching_group("Data Analyst - Python", role_groups)
    assert find_matching_group("Python Data Analyst", role_groups)


def test_tier2_ops_analytics_matching():
    """Test Tier 2 ops_analytics roles match correctly."""
    role_groups = [
        {
            "name": "ops_analytics",
            "bypass_location_and_stipend": False,
            "keywords": [
                "business operations", "process analyst", "process associate",
                "program coordinator", "project coordinator", "erp analyst",
                "erp intern", "strategy analyst", "growth analyst",
                "supply chain analyst", "procurement analyst"
            ]
        }
    ]
    
    assert find_matching_group("Business Operations Intern", role_groups)
    assert find_matching_group("Project Coordinator Intern", role_groups)
    assert find_matching_group("ERP Analyst Intern", role_groups)
    assert find_matching_group("Process Associate", role_groups)


def test_tier3_gated_ops_matching():
    """Test Tier 3 gated_ops roles require gate keywords."""
    role_groups = [
        {
            "name": "gated_ops",
            "bypass_location_and_stipend": False,
            "require_any_keywords": [
                "excel", "sql", "power bi", "tableau", "dashboard",
                "kpi", "reporting", "analysis", "analytics", "mis", "data"
            ],
            "keywords": [
                "operations intern", "project management intern",
                "client success", "implementation", "hr intern",
                "hr operations", "hr executive", "recruitment",
                "talent acquisition", "logistics"
            ]
        }
    ]
    
    # Should match with gate keyword
    assert find_matching_group("Operations Intern - Excel", role_groups)
    assert find_matching_group("Client Success Intern - Analytics", role_groups)
    
    # Should match (role keyword present, gate checked in passes_filters)
    assert find_matching_group("Operations Intern", role_groups)
    assert find_matching_group("Client Success Intern", role_groups)


# Exclusion tests
def test_exclude_keywords():
    """Test that exclude keywords reject titles correctly."""
    filters = {
        "role_groups": [
            {
                "name": "core",
                "bypass_location_and_stipend": True,
                "keywords": ["data analyst", "power bi", "bi developer"]
            }
        ],
        "exclude_keywords": [
            "qa", "quality assurance", "tester", "testing", "sdet",
            "software developer", "java developer", "web developer",
            "app developer", "mobile developer", "full stack",
            "network engineer", "cyber", "tax", "telecaller",
            "sales executive", "content writer", "graphic design",
            "video editor", "customer support", "customer service", "data entry"
        ]
    }
    
    # Core roles should NOT be excluded
    job_core = {"title": "Power BI Developer", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert passes_filters(job_core, filters)
    
    # Non-core roles with exclude keywords should be rejected
    job_qa = {"title": "QA Intern", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert not passes_filters(job_qa, filters)
    
    job_tester = {"title": "Software Test Engineer", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert not passes_filters(job_tester, filters)
    
    job_support = {"title": "Customer Support Executive", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert not passes_filters(job_support, filters)
    
    job_telecaller = {"title": "Telecaller", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert not passes_filters(job_telecaller, filters)
    
    job_data_entry = {"title": "Data Entry Operator", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert not passes_filters(job_data_entry, filters)


def test_qatar_not_excluded_by_qa():
    """Test that 'Qatar' in title is not rejected by 'qa' exclude."""
    filters = {
        "role_groups": [
            {
                "name": "core",
                "bypass_location_and_stipend": True,
                "keywords": ["data analyst", "business analyst"]
            }
        ],
        "exclude_keywords": ["qa", "quality assurance"]
    }
    
    job_qatar = {"title": "Qatar Data Analyst", "location": "Remote", "stipend": "10000", "date_posted": "Today"}
    assert passes_filters(job_qatar, filters)


# Gate mechanism tests
def test_require_any_keywords_gate():
    """Test that Tier 3 gated roles require gate keywords."""
    role_groups = [
        {
            "name": "gated_ops",
            "bypass_location_and_stipend": False,
            "require_any_keywords": [
                "excel", "sql", "power bi", "tableau", "dashboard",
                "kpi", "reporting", "analysis", "analytics", "mis", "data"
            ],
            "keywords": ["operations intern", "client success"]
        }
    ]
    
    filters = {
        "role_groups": role_groups,
        "exclude_keywords": []
    }
    
    # With gate keyword - should pass
    job_with_gate = {
        "title": "Operations Intern - Excel & KPI reporting",
        "location": "Kochi",
        "stipend": "8000",
        "date_posted": "Today"
    }
    assert passes_filters(job_with_gate, filters)
    
    # Without gate keyword - should fail
    job_without_gate = {
        "title": "Operations Intern",
        "location": "Kochi",
        "stipend": "8000",
        "date_posted": "Today"
    }
    assert not passes_filters(job_without_gate, filters)


# Location variant tests
def test_location_variants():
    """Test that location spelling variants are handled correctly."""
    filters = {
        "role_groups": [
            {
                "name": "core",
                "bypass_location_and_stipend": True,
                "keywords": ["data analyst"]
            },
            {
                "name": "ops_analytics",
                "bypass_location_and_stipend": False,
                "keywords": ["operations analyst"]
            }
        ],
        "location_rules": {
            "always_allow": ["kerala", "kochi", "ernakulam", "kakkanad"],
            "conditional": [
                {"min_stipend": 8000, "locations": ["bangalore", "bengaluru", "hyderabad", "goa", "pondicherry"]}
            ]
        }
    }
    
    # Core roles bypass location rules entirely
    job_kerala = {"title": "Data Analyst", "location": "Kerala", "stipend": "5000", "date_posted": "Today"}
    assert passes_filters(job_kerala, filters)
    
    job_kochi = {"title": "Data Analyst", "location": "Kochi", "stipend": "5000", "date_posted": "Today"}
    assert passes_filters(job_kochi, filters)
    
    # Core roles in Bangalore bypass stipend checks
    job_bangalore = {"title": "Data Analyst", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert passes_filters(job_bangalore, filters)
    
    job_bangalore_low = {"title": "Data Analyst", "location": "Bangalore", "stipend": "5000", "date_posted": "Today"}
    assert passes_filters(job_bangalore_low, filters)  # Core bypasses stipend
    
    # Non-core roles must respect location rules
    job_ops_kerala = {"title": "Operations Analyst", "location": "Kerala", "stipend": "5000", "date_posted": "Today"}
    assert passes_filters(job_ops_kerala, filters)  # Kerala is always_allow
    
    job_ops_bangalore = {"title": "Operations Analyst", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    assert passes_filters(job_ops_bangalore, filters)  # Meets min_stipend
    
    job_ops_bangalore_low = {"title": "Operations Analyst", "location": "Bangalore", "stipend": "5000", "date_posted": "Today"}
    assert not passes_filters(job_ops_bangalore_low, filters)  # Fails min_stipend


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
