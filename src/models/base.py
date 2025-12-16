from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    @declared_attr.directive
    def __table_args__(cls):
        """Set schema to 'gold' for all models."""
        return {'schema': 'gold'}

class SilverBase(DeclarativeBase):
    """Base class for all SQLAlchemy models in silver schema."""
    
    @declared_attr.directive
    def __table_args__(cls):
        """Set schema to 'silver' for all models."""
        return {'schema': 'silver'}