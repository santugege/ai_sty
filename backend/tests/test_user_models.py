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


def test_user_model_declares_single_admin_index():
    indexes = {index.name: index for index in UserRow.__table__.indexes}

    assert "ix_users_single_admin" in indexes
    assert indexes["ix_users_single_admin"].unique is True
    assert str(indexes["ix_users_single_admin"].dialect_options["sqlite"]["where"]) == (
        "is_admin = true"
    )


def test_user_column_nullability_and_defaults_match_account_design():
    columns = UserRow.__table__.columns

    assert columns["user_id"].nullable is False
    assert columns["email"].nullable is False
    assert columns["username"].nullable is False
    assert columns["password_hash"].nullable is False
    assert columns["is_admin"].default.arg is False
    assert columns["is_active"].default.arg is True


def test_users_migration_exists_and_does_not_allow_admin_promotion_fields():
    migration = Path(
        "backend/alembic/versions/20260510_0004_users.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260510_0004"' in migration
    assert 'down_revision = "20260510_0003"' in migration
    assert 'op.create_table("users"' in migration
    assert '"user_id"' in migration
    assert '"is_admin"' in migration
    assert (
        'op.create_index("ix_users_user_id", "users", ["user_id"], unique=True)'
        in migration
    )
    assert 'op.create_index("ix_users_email", "users", ["email"], unique=True)' in migration
    assert (
        'op.create_index("ix_users_username", "users", ["username"], unique=True)'
        in migration
    )
    assert 'op.drop_index("ix_users_username", table_name="users")' in migration
    assert 'op.drop_index("ix_users_email", table_name="users")' in migration
    assert 'op.drop_index("ix_users_user_id", table_name="users")' in migration
    assert 'op.drop_table("users")' in migration
    assert "roles" not in migration
    assert "permissions" not in migration


def test_single_admin_migration_exists():
    migration = Path(
        "backend/alembic/versions/20260510_0005_single_admin.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260510_0005"' in migration
    assert 'down_revision = "20260510_0004"' in migration
    assert 'op.create_index("ix_users_single_admin"' in migration
    assert "postgresql_where=sa.text(\"is_admin = true\")" in migration
    assert "sqlite_where=sa.text(\"is_admin = true\")" in migration
    assert 'op.drop_index("ix_users_single_admin", table_name="users")' in migration
    assert "roles" not in migration
    assert "permissions" not in migration
