from control_plane.app.core.db import SessionLocal, init_db
from control_plane.app.services.bootstrap_service import BootstrapService


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = BootstrapService(db).ensure_demo_tenant()
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
