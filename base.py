"""
SQLAlchemy declarative base for all models.

This module provides the shared Base class that all SQLAlchemy models inherit from.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

