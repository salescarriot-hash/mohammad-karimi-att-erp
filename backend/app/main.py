from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.customers import router as customers_router
from app.api.cases import router as cases_router, workspace_router as case_workspace_router
from app.api.files import router as files_router
from app.api.rfqs import router as rfqs_router
from app.api.verifications import router as verifications_router
from app.api.master_matching import router as master_matching_router
from app.api.master_intelligence import router as master_intelligence_router
from app.api.part_context import router as part_context_router
from app.api.suppliers import router as suppliers_router
from app.api.commercial import router as commercial_router
from app.api.commercial_intelligence import router as advanced_commercial_intelligence_router
from app.api.commercial_decision import router as commercial_decision_router
from app.api.pricing import router as pricing_router
from app.api.pricing_intelligence import router as pricing_intelligence_router
from app.api.quotations import router as quotations_router
from app.api.dashboard import router as dashboard_router
from app.api.supplier_quote_intelligence import router as supplier_quote_intelligence_router
from app.api.supplier_performance import router as supplier_performance_router
from app.api.approvals import router as approvals_router
from app.api.templates import router as templates_router
from app.api.supplier_rfq_templates import router as supplier_rfq_templates_router
from app.api.supplier_rfq_workflow import router as supplier_rfq_workflow_router
from app.api.supplier_quote_comparison import router as supplier_quote_comparison_router
from app.api.industrial_knowledge import router as industrial_knowledge_router
from app.api.knowledge_extraction import router as knowledge_extraction_router
from app.api.knowledge_conflicts import router as knowledge_conflicts_router

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(customers_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(case_workspace_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(rfqs_router, prefix="/api/v1")
app.include_router(verifications_router, prefix="/api/v1")
app.include_router(master_matching_router, prefix="/api/v1")
app.include_router(master_intelligence_router, prefix="/api/v1")
app.include_router(part_context_router, prefix="/api/v1")
app.include_router(suppliers_router, prefix="/api/v1")
app.include_router(commercial_router, prefix="/api/v1")
app.include_router(advanced_commercial_intelligence_router, prefix="/api/v1")
app.include_router(commercial_decision_router, prefix="/api/v1")
app.include_router(pricing_router, prefix="/api/v1")
app.include_router(pricing_intelligence_router, prefix="/api/v1")
app.include_router(quotations_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(supplier_quote_intelligence_router, prefix="/api/v1")
app.include_router(supplier_performance_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(supplier_rfq_templates_router, prefix="/api/v1")
app.include_router(supplier_rfq_workflow_router, prefix="/api/v1")
app.include_router(supplier_quote_comparison_router, prefix="/api/v1")
app.include_router(industrial_knowledge_router, prefix="/api/v1")
app.include_router(knowledge_extraction_router, prefix="/api/v1")
app.include_router(knowledge_conflicts_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
