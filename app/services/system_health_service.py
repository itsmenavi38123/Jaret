from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import aiohttp
from app.db import get_client, get_database
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services.xero_token_service import xero_token_service
from app.services.system_health_logs_service import system_health_logs_service
from app.config import _now_utc

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

    async def get_health_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive health metrics for admin dashboard
        """
        try:
            # Get error counts from logs
            error_counts = await system_health_logs_service.get_error_counts(hours)

            # Get third-party service status
            external_status = await self.check_external_services()

            # Calculate rates (errors per hour)
            total_errors = sum(error_counts.values())
            error_rate_per_hour = total_errors / hours if hours > 0 else 0

            # Get recent errors for details
            recent_errors = await system_health_logs_service.get_recent_errors(10)

            # Check for rate limit warnings (look for rate limit errors in recent logs)
            rate_limit_warnings = await self._get_rate_limit_warnings(hours)

            # Background job failures (if we had jobs, this would check them)
            # For now, we'll use a placeholder
            background_job_failures = error_counts.get('job_failure', 0)

            # Webhook failures
            webhook_failures = error_counts.get('webhook_failure', 0)

            return {
                "api_error_rate": {
                    "total_errors": total_errors,
                    "rate_per_hour": round(error_rate_per_hour, 2),
                    "period_hours": hours,
                    "breakdown": error_counts
                },
                "webhook_failures": {
                    "count": webhook_failures,
                    "recent": [err for err in recent_errors if err.log_type == 'webhook_failure'][:5]
                },
                "background_job_failures": {
                    "count": background_job_failures,
                    "recent": [err for err in recent_errors if err.log_type == 'job_failure'][:5]
                },
                "third_party_status": external_status,
                "rate_limit_warnings": rate_limit_warnings,
                "timestamp": _now_utc().isoformat()
            }

        except Exception as e:
            return {
                "error": f"Failed to get health metrics: {str(e)}",
                "timestamp": _now_utc().isoformat()
            }

    async def _get_rate_limit_warnings(self, hours: int = 24) -> Dict[str, Any]:
        """Get rate limit warnings from logs"""
        try:
            rate_limit_errors = await system_health_logs_service.get_service_errors("rate_limit", hours)

            return {
                "count": len(rate_limit_errors),
                "recent": [err.model_dump() for err in rate_limit_errors[:5]],
                "services_affected": list(set(err.service for err in rate_limit_errors if err.service))
            }

        except Exception as e:
            return {"error": str(e), "count": 0, "recent": []}

# Global instance
system_health_service = SystemHealthService()