from pathlib import Path

from app.db import Base
from app.user_models import UserRow


def test_base_metadata_includes_users_table():
    assert "users" in set(Base.metadata.tables)


def test_user_columns_match_account_design():
    assert {
        "id",
        "user_id",
        "email",
        "username",
        "password_hash",
        "is_admin",
        "is_active",
        "created_at",
        "updated_at",
    } <= set(UserRow.__table__.columns.keys())


def test_user_unique_constraints_are_declared():
    columns = UserRow.__table__.columns

    assert columns["user_id"].unique is True
    assert columns["email"].unique is True
    assert columns["username"].unique is True


def test_users_migration_exists_and_does_not_allow_admin_promotion_fields():
    migration = Path(
        "backend/alembic/versions/20260510_0004_users.py"
    ).read_text(encoding="utf-8")

    assert 'op.create_table("users"' in migration
    assert '"user_id"' in migration
    assert '"is_admin"' in migration
    assert "roles" not in migration
    assert "permissions" not in migration
