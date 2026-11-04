"""Shared pytest setup for the project test suite."""

from dotenv import load_dotenv


# Load DATABASE_URL and/or PG* variables before importing database-backed tests.
load_dotenv()
