"""
Pytest tests for priority.py ranking logic.
"""

import pytest
from priority import assign_role_rank, assign_location_rank, assign_analytical_boost, assign_date_boost, assign_rank, sort_by_priority


def test_role_ranking():
    """Test that role groups are ranked in correct order."""
    role_groups = [
        {"name": "core", "bypass_location_and_stipend": True, "keywords": ["data analyst"]},
        {"name": "ops_analytics", "bypass_location_and_stipend": False, "keywords": ["operations analyst"]},
        {"name": "hr_analytics", "bypass_location_and_stipend": False, "keywords": ["hr analyst"]},
        {"name": "analyst_adjacent", "bypass_location_and_stipend": False, "keywords": ["marketing analyst"]},
        {"name": "gated_ops", "bypass_location_and_stipend": False, "keywords": ["operations intern"]},
        {"name": "generic_analyst_catchall", "bypass_location_and_stipend": False, "keywords": ["junior analyst"]}
    ]
    
    # Core should have rank 0
    assert assign_role_rank({"title": "Data Analyst Intern"}, role_groups, 10000) == 0
    
    # Ops_analytics should have rank 1
    assert assign_role_rank({"title": "Operations Analyst"}, role_groups, 10000) == 1
    
    # HR_analytics should have rank 2
    assert assign_role_rank({"title": "HR Analyst"}, role_groups, 10000) == 2
    
    # Analyst_adjacent should have rank 3
    assert assign_role_rank({"title": "Marketing Analyst"}, role_groups, 10000) == 3
    
    # Gated_ops should have rank 4
    assert assign_role_rank({"title": "Operations Intern"}, role_groups, 10000) == 4
    
    # Generic catchall should have rank 5
    assert assign_role_rank({"title": "Junior Analyst"}, role_groups, 10000) == 5
    
    # Unmatched should have rank 6 (len of role_groups)
    assert assign_role_rank({"title": "Software Developer"}, role_groups, 10000) == 6


def test_location_ranking():
    """Test that locations are ranked in correct tiers."""
    location_priority_cfg = {
        "default_rank": 3,
        "tiers": [
            {
                "name": "kerala_tier1",
                "rank": 0,
                "locations": ["kerala", "kochi", "ernakulam", "kakkanad", "cochin", "trivandrum", "thiruvananthapuram", "kozhikode", "calicut", "thrissur", "kannur", "kollam"]
            },
            {
                "name": "tier2_cities",
                "rank": 1,
                "locations": ["bangalore", "bengaluru", "hyderabad"]
            },
            {
                "name": "tier3_cities",
                "rank": 2,
                "locations": ["goa", "pondicherry", "puducherry"]
            }
        ]
    }
    
    # Kerala should have rank 0
    assert assign_location_rank("Kerala", None, location_priority_cfg) == 0
    assert assign_location_rank("Kochi", None, location_priority_cfg) == 0
    assert assign_location_rank("Ernakulam", None, location_priority_cfg) == 0
    
    # Bangalore should have rank 1
    assert assign_location_rank("Bangalore", None, location_priority_cfg) == 1
    assert assign_location_rank("Bengaluru", None, location_priority_cfg) == 1
    assert assign_location_rank("Hyderabad", None, location_priority_cfg) == 1
    
    # Goa should have rank 2
    assert assign_location_rank("Goa", None, location_priority_cfg) == 2
    assert assign_location_rank("Pondicherry", None, location_priority_cfg) == 2
    assert assign_location_rank("Puducherry", None, location_priority_cfg) == 2
    
    # Unmatched location should use default_rank 3
    assert assign_location_rank("Mumbai", None, location_priority_cfg) == 3


def test_analytical_boost():
    """Test that analytical keywords give a small priority boost."""
    job_with_analytics = {"title": "Data Analyst - SQL & Excel"}
    assert assign_analytical_boost(job_with_analytics) == -0.1
    
    job_without_analytics = {"title": "Software Developer"}
    assert assign_analytical_boost(job_without_analytics) == 0


def test_date_boost():
    """Test that newer postings get a small priority boost."""
    job_today = {"title": "Data Analyst", "date_posted": "Today"}
    assert assign_date_boost(job_today) == -0.2
    
    job_yesterday = {"title": "Data Analyst", "date_posted": "1 day ago"}
    assert assign_date_boost(job_yesterday) == -0.1
    
    job_old = {"title": "Data Analyst", "date_posted": "7 days ago"}
    assert assign_date_boost(job_old) == 0
    
    job_no_date = {"title": "Data Analyst", "date_posted": ""}
    assert assign_date_boost(job_no_date) == 0


def test_combined_ranking():
    """Test that role rank, location rank, and boosts combine correctly."""
    config = {
        "filters": {
            "role_groups": [
                {"name": "core", "bypass_location_and_stipend": True, "keywords": ["data analyst"]},
                {"name": "ops_analytics", "bypass_location_and_stipend": False, "keywords": ["operations analyst"]}
            ],
            "location_priority": {
                "default_rank": 3,
                "tiers": [
                    {"name": "kerala_tier1", "rank": 0, "locations": ["kerala", "kochi"]},
                    {"name": "tier2_cities", "rank": 1, "locations": ["bangalore", "hyderabad"]}
                ]
            }
        }
    }
    
    # Core + Kerala + analytics + today = best rank
    job1 = {"title": "Data Analyst - SQL", "location": "Kochi", "stipend": "8000", "date_posted": "Today"}
    rank1 = assign_rank(job1, config)
    assert rank1[0] == 0  # role rank
    assert rank1[1] == 0  # location rank
    assert rank1[2] < 0   # boost sum
    
    # Core + Bangalore = worse location rank
    job2 = {"title": "Data Analyst", "location": "Bangalore", "stipend": "10000", "date_posted": "Today"}
    rank2 = assign_rank(job2, config)
    assert rank2[0] == 0  # role rank
    assert rank2[1] == 1  # location rank (higher = worse)
    
    # Ops_analytics + Kerala = worse role rank
    job3 = {"title": "Operations Analyst", "location": "Kochi", "stipend": "8000", "date_posted": "Today"}
    rank3 = assign_rank(job3, config)
    assert rank3[0] == 1  # role rank (higher = worse)
    assert rank3[1] == 0  # location rank
    
    # job1 should rank higher than job2 (same role, better location)
    assert rank1 < rank2
    # job2 should rank higher than job3 (same location, better role)
    assert rank2 < rank3


def test_sort_by_priority():
    """Test that jobs are sorted by (role_rank, location_rank, boosts)."""
    config = {
        "filters": {
            "role_groups": [
                {"name": "core", "bypass_location_and_stipend": True, "keywords": ["data analyst"]},
                {"name": "ops_analytics", "bypass_location_and_stipend": False, "keywords": ["operations analyst"]}
            ],
            "location_priority": {
                "default_rank": 3,
                "tiers": [
                    {"name": "kerala_tier1", "rank": 0, "locations": ["kerala", "kochi"]},
                    {"name": "tier2_cities", "rank": 1, "locations": ["bangalore"]}
                ]
            }
        }
    }
    
    jobs = [
        {"title": "Operations Analyst", "location": "Kochi", "stipend": "8000", "date_posted": "Today", "source": "Internshala"},
        {"title": "Data Analyst", "location": "Bangalore", "stipend": "10000", "date_posted": "Today", "source": "Internshala"},
        {"title": "Data Analyst - SQL", "location": "Kochi", "stipend": "8000", "date_posted": "Today", "source": "Internshala"}
    ]
    
    sorted_jobs = sort_by_priority(jobs, config)
    
    # Best: Data Analyst - SQL (Core + Kerala + analytics boost)
    assert sorted_jobs[0]["title"] == "Data Analyst - SQL"
    # Second: Data Analyst (Core + Bangalore)
    assert sorted_jobs[1]["title"] == "Data Analyst"
    # Third: Operations Analyst (Ops_analytics + Kerala)
    assert sorted_jobs[2]["title"] == "Operations Analyst"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
