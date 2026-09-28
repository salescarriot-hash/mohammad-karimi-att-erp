# ATT ERP Backend

FastAPI + SQLAlchemy backend for ATT ERP.

## Current modules
- Customers
- Customer Contacts
- Customer Sites
- Cases
- Case Files

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set `DATABASE_URL` in `.env` before using database endpoints.

## Key API paths
- `GET /health`
- `POST/GET /api/v1/customers`
- `POST/GET /api/v1/customers/{customer_id}/cases`
- `GET/PATCH /api/v1/customers/{customer_id}/cases/{case_id}`
- `POST/GET /api/v1/cases/{case_id}/files`

Case files are stored under `storage/cases/{case_id}/` using generated storage names; the original customer filename is preserved in the database.
