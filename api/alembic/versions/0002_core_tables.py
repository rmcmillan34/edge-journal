from alembic import op
import sqlalchemy as sa

revision = "0002_core_tables"
down_revision = "0001_users"
branch_labels = None
depends_on = None

def upgrade():
    """
    Create core tables: uploads, accounts, instruments, trades.
    """

    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("preset", sa.String(length=64), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="committed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("broker_label", sa.String(length=120), nullable=True),
        sa.Column("base_ccy", sa.String(length=12), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )

    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(length=64), nullable=False, unique=True),
        sa.Column("asset_class", sa.String(length=16), nullable=True),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=True),
        sa.Column("external_trade_id", sa.String(length=128), nullable=True),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("qty_units", sa.Float, nullable=True),
        sa.Column("entry_price", sa.Float, nullable=True),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("open_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gross_pnl", sa.Float, nullable=True),
        sa.Column("fees", sa.Float, nullable=True),
        sa.Column("net_pnl", sa.Float, nullable=True),
        sa.Column("notes_md", sa.String, nullable=True),
        sa.Column("source_upload_id", sa.Integer, sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("trade_key", sa.String(length=256), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("trade_key", name="uq_trades_tradekey"),
    )
    op.create_index("ix_trades_open_time", "trades", ["open_time_utc"])
    op.create_index("ix_trades_close_time", "trades", ["close_time_utc"])

def downgrade():
    op.drop_index("ix_trades_close_time", table_name="trades")
    op.drop_index("ix_trades_open_time", table_name="trades")
    op.drop_constraint("uq_trades_tradekey", "trades", type_="unique")
    op.drop_table("trades")
    op.drop_table("instruments")
    op.drop_table("accounts")
    op.drop_table("uploads")
