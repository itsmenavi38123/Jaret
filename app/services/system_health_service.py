from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import aiohttp
from app.db import get_client, get_database
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services.xero_token_service import xero_token_service

class SystemHealthService:
    def __init__(self):
        self.client = None

    async def check_database_health(self) -> Dict[str, Any]:
        """Check MongoDB connectivity and basic operations"""
        try:
            # Try to get database and perform a simple operation
            db = get_database()
            # Ping the database
            await db.command('ping')
            return {"status": "healthy", "message": "Database connection OK"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    async def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        results = {"quickbooks": "unknown", "xero": "unknown"}

        try:
            # Check QuickBooks API (using a simple endpoint that doesn't require auth)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("https://app-api.qbo.intuit.com/v3/company/health") as response:
                    if response.status == 200:
                        results["quickbooks"] = "healthy"
                    else:
                        results["quickbooks"] = "degraded"
        except Exception:
            results["quickbooks"] = "unhealthy"

        try:
            # Check Xero API health
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("https://api.xero.com/connections") as response:
                    # This might require auth, so just check if endpoint is reachable
                    if response.status in [200, 401, 403]:  # 401/403 means API is up but needs auth
                        results["xero"] = "healthy"
                    else:
                        results["xero"] = "degraded"
        except Exception:
            results["xero"] = "unhealthy"

        return results

    async def check_application_health(self) -> Dict[str, Any]:
        """Check internal application health"""
        try:
            # Check if we can access our own endpoints
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("http://localhost:8000/") as response:
                    if response.status == 200:
                        return {"status": "healthy", "message": "Application responding"}
                    else:
                        return {"status": "degraded", "message": f"Application returned status {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Application not responding: {str(e)}"}

    async def get_system_status(self) -> str:
        """
        Get overall system status based on health checks
        Returns: "Healthy", "Degraded", or "Unhealthy"
        """
        try:
            # Run all health checks concurrently
            db_check, external_check, app_check = await asyncio.gather(
                self.check_database_health(),
                self.check_external_services(),
                self.check_application_health()
            )

            # Determine overall status
            critical_failures = 0
            warnings = 0

            # Database is critical
            if db_check["status"] != "healthy":
                critical_failures += 1

            # Application is critical
            if app_check["status"] == "unhealthy":
                critical_failures += 1
            elif app_check["status"] == "degraded":
                warnings += 1

            # External services are not critical but affect status
            external_healthy = sum(1 for status in external_check.values() if status == "healthy")
            external_total = len(external_check)

            if external_healthy < external_total * 0.5:  # Less than 50% of external services healthy
                warnings += 1

            # Determine final status
            if critical_failures > 0:
                return "Unhealthy"
            elif warnings > 0:
                return "Degraded"
            else:
                return "Healthy"

        except Exception as e:
            # If health check itself fails, assume degraded
            return "Degraded"

# Global instance
system_health_service = SystemHealthService()