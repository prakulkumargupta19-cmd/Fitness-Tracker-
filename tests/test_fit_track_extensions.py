import io

from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

from backend.app import app
from backend.reference_extensions import _participant_rows, _passport_id, _projection


def test_reference_backend_routes_are_registered():
    routes = {(rule.rule, method) for rule in app.url_map.iter_rules() for method in rule.methods}

    assert ("/api/fit-track/students/bulk-sports", "POST") in routes
    assert ("/api/fit-track/reports/projection.csv", "GET") in routes
    assert ("/api/fit-track/tournaments/<int:tournament_id>/participants/import", "POST") in routes
    assert ("/api/fit-track/certificates/<int:certificate_id>/download", "GET") in routes


def test_participant_import_reads_required_xlsx_columns():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Name", "Department", "Category", "Year"])
    sheet.append(["Aarav Student", "BBA", "Boys", 2026])
    payload = io.BytesIO()
    workbook.save(payload)
    payload.seek(0)

    rows = _participant_rows(
        FileStorage(stream=payload, filename="participants.xlsx")
    )

    assert rows == [
        {
            "name": "Aarav Student",
            "department": "BBA",
            "category": "Boys",
            "year": "2026",
        }
    ]


def test_passport_and_projection_windows_are_deterministic():
    assert _passport_id(27).startswith("IKC-SP-")
    period, start, end = _projection("weekly")
    assert period == "weekly"
    assert len(start) == 10
    assert len(end) == 10
