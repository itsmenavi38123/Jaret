# FastAPI Backend

Simple backend API built with FastAPI.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Open in browser:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

## Environment Variables

Create a `.env` file in `backend/` based on the following template:

```
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=jaret

# JWT
JWT_SECRET_KEY=replace-with-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

These are loaded automatically by the settings in `app/core/config.py`.

## Project Structure

```
app/
├── main.py              # Main application entry point
├── core/
│   └── config.py        # App configuration
├── routes/              # API routes
│   ├── base.py          # Base class for class-based routes
│   ├── health.py        # Function-based routes
│   ├── example.py       # Function-based routes
│   └── users.py         # Class-based routes
├── models/              # Database models (optional)
└── schemas/             # Pydantic schemas (optional)
```

## Creating Routes

### Function-Based (Simple)

Create `routes/my_route.py`:
```python
from fastapi import APIRouter
router = APIRouter()
@router.get("/my-endpoint")
async def my_function():
    return {"message": "Hello"}
```

Then in `main.py`:
```python
from app.routes import my_route
app.include_router(my_route.router)
```

### Class-Based (For organized endpoints)

Create `routes/products.py`:
```python
from app.routes.base import BaseRouter, route
class ProductsRouter(BaseRouter):
    def __init__(self):
        super().__init__(prefix="/products", tags=["Products"])
    @route("/", "GET")
    async def get_all(self):
        return {"products": []}
    @route("/{id}", "GET")
    async def get_one(self, id: int):
        return {"id": id}

router = ProductsRouter().router
```

Then in `main.py`:
```python
from app.routes import products
app.include_router(products.router)
```

## Test with curl

```bash
curl http://localhost:8000/
