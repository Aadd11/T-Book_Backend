"""Initial migration

Revision ID: d4b47cf318dc
Revises: 
Create Date: 2025-04-26 22:16:56.109826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4b47cf318dc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('authors',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_authors_name'), 'authors', ['name'], unique=True)
    op.create_table('books',
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('year_published', sa.Integer(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('age_rating', sa.String(), nullable=True),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('book_size_pages', sa.Integer(), nullable=True),
    sa.Column('book_size_description', sa.String(), nullable=True),
    sa.Column('average_rating', sa.Float(), nullable=True),
    sa.Column('rating_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source_url', sa.String(), nullable=True),
    sa.Column('isbn_10', sa.String(length=10), nullable=True),
    sa.Column('isbn_13', sa.String(length=13), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_books_average_rating'), 'books', ['average_rating'], unique=False)
    op.create_index(op.f('ix_books_isbn_10'), 'books', ['isbn_10'], unique=False)
    op.create_index(op.f('ix_books_isbn_13'), 'books', ['isbn_13'], unique=True)
    op.create_index(op.f('ix_books_language'), 'books', ['language'], unique=False)
    op.create_index(op.f('ix_books_title'), 'books', ['title'], unique=False)
    op.create_index(op.f('ix_books_year_published'), 'books', ['year_published'], unique=False)
    op.create_table('genres',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_genres_name'), 'genres', ['name'], unique=True)
    op.create_table('book_authors',
    sa.Column('book_id', sa.UUID(), nullable=False),
    sa.Column('author_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
    sa.PrimaryKeyConstraint('book_id', 'author_id')
    )
    op.create_table('book_genres',
    sa.Column('book_id', sa.UUID(), nullable=False),
    sa.Column('genre_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
    sa.ForeignKeyConstraint(['genre_id'], ['genres.id'], ),
    sa.PrimaryKeyConstraint('book_id', 'genre_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('book_genres')
    op.drop_table('book_authors')
    op.drop_index(op.f('ix_genres_name'), table_name='genres')
    op.drop_table('genres')
    op.drop_index(op.f('ix_books_year_published'), table_name='books')
    op.drop_index(op.f('ix_books_title'), table_name='books')
    op.drop_index(op.f('ix_books_language'), table_name='books')
    op.drop_index(op.f('ix_books_isbn_13'), table_name='books')
    op.drop_index(op.f('ix_books_isbn_10'), table_name='books')
    op.drop_index(op.f('ix_books_average_rating'), table_name='books')
    op.drop_table('books')
    op.drop_index(op.f('ix_authors_name'), table_name='authors')
    op.drop_table('authors')
