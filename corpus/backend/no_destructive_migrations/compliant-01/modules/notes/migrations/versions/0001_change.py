def upgrade():
    op.add_column('notes', column)
    op.alter_column('notes', 'title', nullable=False)
