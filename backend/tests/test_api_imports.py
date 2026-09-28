def test_api_modules_import():
    from app.main import app
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/api/v1/customers" in paths
    assert "/api/v1/customers/{customer_id}/cases" in paths
    assert "/api/v1/cases/{case_id}/files" in paths
