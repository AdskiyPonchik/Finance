"""Safe amounts, owner indexes and durable recurring-payment receipts."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("transaction", "amount", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("recurringtransaction", "amount", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.create_check_constraint("ck_transaction_amount_nonzero", "transaction", "amount <> 0")
    op.create_check_constraint("ck_recurring_amount_nonzero", "recurringtransaction", "amount <> 0")
    op.create_check_constraint("ck_recurring_day", "recurringtransaction", "day_of_month BETWEEN 1 AND 31")
    op.create_check_constraint("ck_recurring_type", "recurringtransaction", "type IN ('income', 'expense')")
    op.create_index("ix_transaction_owner_date_id", "transaction", ["owner_id", "date", "id"])
    op.create_index("ix_recurring_owner_active", "recurringtransaction", ["owner_id", "is_active"])
    # Legacy schedules have no creation date. Start them at migration day; do not invent old charges.
    op.add_column("recurringtransaction", sa.Column(
        "created_on", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"),
    ))
    op.alter_column("recurringtransaction", "created_on", server_default=None)
    op.create_table(
        "recurringoccurrence",
        sa.Column("recurring_id", sa.Integer(),
                  sa.ForeignKey("recurringtransaction.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("scheduled_date", sa.Date(), primary_key=True),
    )


def downgrade():
    op.drop_table("recurringoccurrence")
    op.drop_column("recurringtransaction", "created_on")
    op.drop_index("ix_recurring_owner_active", table_name="recurringtransaction")
    op.drop_index("ix_transaction_owner_date_id", table_name="transaction")
    for table, name in [
        ("transaction", "ck_transaction_amount_nonzero"),
        ("recurringtransaction", "ck_recurring_amount_nonzero"),
        ("recurringtransaction", "ck_recurring_day"),
        ("recurringtransaction", "ck_recurring_type"),
    ]:
        op.drop_constraint(name, table, type_="check")
    # Downgrade fails rather than truncating values outside the old INTEGER range.
    op.alter_column("transaction", "amount", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("recurringtransaction", "amount", existing_type=sa.BigInteger(), type_=sa.Integer())