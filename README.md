# FastAPI Backend

FastAPI + MongoDB backend that supports authentication, QuickBooks Online integrations, and a consolidated financial overview API.

## Quick Start

1. **Create a virtual environment (recommended)**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # macOS/Linux: source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Open the interactive docs**
   - Swagger UI: http://localhost:8000/docs

## Environment Variables

Create a `.env` file in `backend/` that defines the secrets below.

```ini
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=jaaret

# JWT
JWT_SECRET_KEY=replace-with-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# QuickBooks
QUICKBOOKS_CLIENT_ID=your-qbo-client-id
QUICKBOOKS_CLIENT_SECRET=your-qbo-client-secret
QUICKBOOKS_REDIRECT_URI=https://your-app.com/quickbooks/callback
QUICKBOOKS_ENVIRONMENT=sandbox  # or production

# Xero
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=https://your-app.com/xero/callback

# Research Scout (Web Search APIs - optional)
TAVILY_API_KEY=your-tavily-api-key
SERPER_API_KEY=your-serper-api-key

# Weather API (optional - for weather badges)
OPENWEATHER_API_KEY=your-openweather-api-key
```

Settings are loaded via `app.config.Settings`, so all values automatically flow into the FastAPI app.

## Project Structure

```
app/
├── main.py                        # FastAPI application setup
├── config.py                      # Pydantic settings + JWT helpers
├── db.py                          # MongoDB connection helpers
├── models/
│   ├── users.py                   # User model
│   └── quickbooks/
│       └── token.py               # QuickBooks token models
├── routes/
│   ├── auth/                      # Authentication + JWT endpoints
│   ├── quickbooks/                # QuickBooks OAuth flow
│   ├── xero/                      # Xero OAuth + account routes
│   └── financial_overview.py      # Financial overview endpoint
└── services/
    ├── quickbooks_service.py           # OAuth + low-level QBO helpers
    ├── quickbooks_financial_service.py # Financial aggregation logic
    └── quickbooks_token_service.py     # Token persistence
```

## Key Endpoints

| Endpoint | Description |
| -------- | ----------- |
| `POST /auth/register` | Register a new user |
| `POST /auth/login` | Login and receive access/refresh tokens |
| `GET /quickbooks/login` | Initiate the QuickBooks OAuth2 flow |
| `GET /quickbooks/callback` | Handle QuickBooks callback and store tokens |
| `GET /xero/auth/login` | Initiate the Xero OAuth2 flow |
| `GET /xero/auth/callback` | Handle Xero callback and store tokens |
| `GET /xero/account-types` | List Xero account type metadata |
| `GET /xero/accounts` | List accounts from Xero (requires Xero token + tenant) |
| `GET /api/financial-overview?realm_id=12345` | Aggregated KPIs sourced from QuickBooks |
| `POST /api/ai/opportunities/search` | Research Scout - Find opportunities with market intelligence |
| `GET /api/ai/opportunities/search` | Research Scout - GET version |

All secured routes require an `Authorization: Bearer <access_token>` header using the token returned from `/auth/login`.

## Financial Overview Workflow

1. Authenticate and obtain an access token.
2. Connect QuickBooks via `/quickbooks/login` and complete the Intuit consent flow.
3. Call `GET /api/financial-overview?realm_id=<QB_REALM_ID>` with the authenticated bearer token.  
   Optional `force_refresh=true` triggers a token refresh before data retrieval.
4. The service orchestrates QuickBooks reports (`ProfitAndLoss`, `BalanceSheet`, `CashFlow`) and returns data shaped like the shared `SAFE_STUB` structure.

The response consolidates:

- Revenue metrics (MTD / QTD / YTD)
- Gross / net margin and operating expense ratios
- Liquidity and efficiency ratios (current, quick, DSO/DPO, CCC)
- Cashflow burn, runway projections, basic forecasting, and heuristics for variance & risks

Missing report data gracefully degrades corresponding fields to `null` and reduces the AI confidence score.

## Xero Workflow

1. Authenticate and obtain an access token via `/auth/login`.
2. Call `/xero/auth/login` to retrieve the consent URL, complete the Intuit consent screen, and allow the callback to store credentials.
3. Use `/xero/auth/tokens` to confirm the stored tenant and retrieve the `tenant_id` for subsequent requests.
4. Interact with `/xero/accounts` endpoints, supplying the stored `access_token` and `tenant_id` (or refresh as needed).

## Testing Tips

- Use the Swagger UI to authorize requests: click **Authorize** and paste your bearer token.
- Supply a valid QuickBooks `realm_id` linked to the authenticated user’s stored token.
- The console logs produced by `uvicorn --reload` are helpful for watching request/response activity during development.

## Research Scout API

The Research Scout API provides opportunity discovery and market intelligence. See [RESEARCH_SCOUT_API.md](./RESEARCH_SCOUT_API.md) for complete documentation.

**Quick Start**:
1. Ensure user has `business_profile` and `opportunities_profile` set
2. Call `POST /api/ai/opportunities/search` with query
3. Receive structured JSON with opportunities, digest, benchmarks, and recommendations

## Maintenance Notes

- `requirements.txt` trimmed to the FastAPI + Mongo + QuickBooks essentials.
- Linter warnings about third-party imports disappear after installing dependencies in your local environment.
