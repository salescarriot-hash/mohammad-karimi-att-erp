# ATT ERP — Customer / Case Management Frontend

Adds a customer-centric operational UI on top of the existing ATT ERP workflow.

## Features
- Customer search/list
- Customer creation
- Customer overview
- Contact list and creation
- Site list and creation
- Case list/search
- Case creation
- Customer statistics
- Persian labels for customer/case types and statuses
- Uses existing FastAPI Customer and Case endpoints

## API endpoints used
- GET /api/v1/customers
- POST /api/v1/customers
- GET /api/v1/customers/{id}
- GET /api/v1/customers/{id}/contacts
- POST /api/v1/customers/{id}/contacts
- GET /api/v1/customers/{id}/sites
- POST /api/v1/customers/{id}/sites
- GET /api/v1/customers/{id}/cases
- POST /api/v1/customers/{id}/cases

Backend Python compilation: OK.
Frontend npm build was not claimed because npm dependencies are not installed in the execution environment.
