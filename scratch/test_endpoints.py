import asyncio
import json
import time
import os
import sys
from datetime import datetime

# Set root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from app.main import app

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwZWZhNTVjMi0wYzgxLTQ0MmMtOGUxNC03MDZiZWRjMjhhNDYiLCJlbWFpbCI6InNoYXJtYS5uYXZlZW4zNDE5ODlAZ21haWwuY29tIiwicm9sZSI6IlZpZXdlciIsImlhdCI6MTc4Nzg4ODUxMywiZXhwIjoxNzg3ODkyMTEzLCJ0eXBlIjoiYWNjZXNzIn0.R2mKzMXQSq_8uUfhEgbs4xL3bI6hxtENRS2gX-CDdIY"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

RESULTS_FILE_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "endpoint_test_results.json"))
RESULTS_FILE_MD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "endpoint_test_results.md"))

ENDPOINTS_TO_TEST = [
    {
        "name": "1. Scenario Lab Planning (Canonical Scenario Lab v1.4)",
        "method": "POST",
        "url": "/api/ai/scenarios/full",
        "body": {
            "query": "Hire 2 line cooks at $45k each and expand weekend service hours"
        }
    },
    {
        "name": "2. Dashboard AI Insights (Financial Analyst V6 — INSIGHTS MODE)",
        "method": "GET",
        "url": "/api/ai/insights/latest",
        "body": None
    },
    {
        "name": "3. Financial Overview Drawer Forensics (Financial Analyst V6 — DRAWER MODE)",
        "method": "POST",
        "url": "/api/financial-overview/drawer",
        "body": {
            "kpi_name": "net_margin_pct",
            "current_value": 0.18,
            "prior_value": 0.14,
            "format_type": "percentage"
        }
    },
    {
        "name": "4. Dashboard Ask AI Advisor (Orchestrator v3.7 — ASK MODE)",
        "method": "POST",
        "url": "/api/dashboard/ask",
        "body": {
            "question": "How is my cash runway looking for the upcoming season and what should I prioritize?",
            "surface": "dashboard_ask"
        }
    },
    {
        "name": "5. Business Health Scorecard (Orchestrator v3.7 — HEALTH NARRATIVE MODE)",
        "method": "GET",
        "url": "/api/ai/health/full",
        "body": None
    },
    {
        "name": "6. Research Scout Live Opportunities (Canonical Research Scout V3.1)",
        "method": "POST",
        "url": "/api/ai/opportunities/search",
        "body": {
            "query": "food festivals and catering vendor opportunities in Austin TX",
            "opportunity_types": ["event", "festival", "catering", "vendor_market"],
            "limit": 5
        }
    },
    {
        "name": "7. Business Profile Classification (Canonical Classifier V4.1)",
        "method": "POST",
        "url": "/business-profile/onboarding",
        "body": {
            "onboarding_data": {
                "business_name": "Lone Star Smokehouse",
                "industry_description": "Barbecue Restaurant & Food Truck",
                "naics_code": "722330",
                "city": "Austin",
                "state": "TX",
                "full_time_employees": 6,
                "main_products": "smoked brisket, pulled pork, craft bbq catering",
                "service_model": "counter_service_and_mobile"
            }
        }
    },
    {
        "name": "8. Demand Forecast Generation (Canonical Demand Forecast Analyst v2)",
        "method": "GET",
        "url": "/api/demand-forecast?window=this+weekend",
        "body": None
    }
]


async def run_tests():
    print(f"[{datetime.utcnow().isoformat()}] Starting comprehensive endpoint execution with real token...")
    results = []
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        for idx, item in enumerate(ENDPOINTS_TO_TEST, 1):
            print(f"\n[{idx}/{len(ENDPOINTS_TO_TEST)}] Running {item['name']} -> {item['method']} {item['url']}...")
            start_time = time.time()
            try:
                if item["method"] == "POST":
                    resp = await client.post(item["url"], json=item["body"], headers=HEADERS)
                elif item["method"] == "GET":
                    resp = await client.get(item["url"], headers=HEADERS)
                elif item["method"] == "PATCH":
                    resp = await client.patch(item["url"], json=item["body"], headers=HEADERS)
                else:
                    raise ValueError(f"Unsupported method {item['method']}")
                
                duration = round(time.time() - start_time, 2)
                status_code = resp.status_code
                try:
                    response_json = resp.json()
                except Exception:
                    response_json = {"raw_text": resp.text}
                
                print(f" -> Status: {status_code} ({duration}s)")
                
                result_entry = {
                    "index": idx,
                    "name": item["name"],
                    "method": item["method"],
                    "url": item["url"],
                    "request_body": item["body"],
                    "status_code": status_code,
                    "duration_seconds": duration,
                    "success": 200 <= status_code < 300,
                    "response": response_json,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                results.append(result_entry)
                
            except Exception as ex:
                duration = round(time.time() - start_time, 2)
                print(f" -> Error: {ex} ({duration}s)")
                results.append({
                    "index": idx,
                    "name": item["name"],
                    "method": item["method"],
                    "url": item["url"],
                    "request_body": item["body"],
                    "status_code": 500,
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(ex),
                    "timestamp": datetime.utcnow().isoformat(),
                })
    
    # Write JSON results
    with open(RESULTS_FILE_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[OK] Wrote JSON results to: {RESULTS_FILE_JSON}")
    
    # Write Markdown results
    with open(RESULTS_FILE_MD, "w", encoding="utf-8") as f:
        f.write("# Live Endpoint Execution Results\n\n")
        f.write(f"**Execution Timestamp:** {datetime.utcnow().isoformat()} UTC  \n")
        f.write(f"**Total Tested Endpoints:** {len(results)}  \n\n")
        f.write("---\n\n")
        
        for r in results:
            badge = "PASSED" if r["success"] else "FAILED"
            f.write(f"## {r['index']}. {r['name']}\n\n")
            f.write(f"- **Status:** `{r['status_code']} {badge}`\n")
            f.write(f"- **Method & URL:** `{r['method']} {r['url']}`\n")
            f.write(f"- **Response Time:** `{r['duration_seconds']}s`\n\n")
            
            if r.get("request_body"):
                f.write("**Request Body:**\n```json\n")
                f.write(json.dumps(r["request_body"], indent=2, default=str))
                f.write("\n```\n\n")
            
            f.write("**Response Summary:**\n```json\n")
            resp_str = json.dumps(r.get("response", r.get("error")), indent=2, default=str)
            if len(resp_str) > 2000:
                f.write(resp_str[:2000] + "\n... [truncated for length]")
            else:
                f.write(resp_str)
            f.write("\n```\n\n---\n\n")
            
    print(f"[OK] Wrote Markdown report to: {RESULTS_FILE_MD}")


if __name__ == "__main__":
    asyncio.run(run_tests())
