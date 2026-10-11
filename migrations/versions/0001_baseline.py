"""Original schema from Finance commit 0b6dd44; stamp existing installations here."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)
    op.create_table(
        "category", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.Enum("INCOME", "EXPENSE", "VAULT", name="categorytype"), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.UniqueConstraint("name", "owner_id", name="unique_category_for_user"),
    )
    op.create_index("ix_category_name", "category", ["name"])
    op.create_table(
        "transaction", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False),
    )
    op.create_index("ix_transaction_date", "transaction", ["date"])
    op.create_table(
        "recurringtransaction", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("last_run_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
    )


def downgrade():
    op.drop_table("recurringtransaction")
    op.drop_index("ix_transaction_date", table_name="transaction")
    op.drop_table("transaction")
    op.drop_index("ix_category_name", table_name="category")
    op.drop_table("category")
    sa.Enum(name="categorytype").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")