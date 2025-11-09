"""Test scanner directly."""
from app.database import SessionLocal
from app.services.scanner_service import ScannerService

if __name__ == "__main__":
    db = SessionLocal()
    try:
        scanner = ScannerService(db)
        result = scanner.scan_nas(
            paths=["/tmp/test_media"],
            scan_type="full"
        )
        print(f"Scan completed: {result.status}")
        print(f"Files found: {result.files_found}")
        print(f"Files new: {result.files_new}")
        print(f"Errors: {result.errors_count}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
