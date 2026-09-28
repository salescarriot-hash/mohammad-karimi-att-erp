# ATT ERP — Operational Dashboard

Added an operational Dashboard to the existing ATT ERP frontend.

## Backend

`GET /api/v1/dashboard/summary`

The endpoint returns counts for:
- Open Cases
- Active RFQs
- Pending Verification Tasks
- Supplier Quotes in progress
- Pending Commercial Decisions
- Pending Pricing
- Pending Customer Quotations
- Approved / Sent Customer Quotations
- RFQ Lines pending verification

It also returns recent Cases, RFQs, Supplier Quotes, and Customer Quotations.

## Frontend

A new **Dashboard** tab is now the default landing page. It includes KPI cards and recent operational tables, with a manual refresh action.

The dashboard is read-only and does not change business data.
