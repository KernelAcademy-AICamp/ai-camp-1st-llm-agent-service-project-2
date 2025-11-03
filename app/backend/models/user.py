"""
User model for authentication and profile management
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.backend.database import Base


class User(Base):
    """
    User model for lawyer authentication and profile.

    Attributes:
        id: Unique user identifier (UUID)
        email: User email (used for login)
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        lawyer_registration_number: Optional lawyer registration number
        specializations: List of legal specializations (형사, 교통사고, etc.)
        is_active: Whether the user account is active
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
    """

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Authentication
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Profile
    full_name = Column(String, nullable=False)
    lawyer_registration_number = Column(String, nullable=True)

    # Specializations (법률 전문 분야)
    # Example: ["형사 일반", "교통사고", "성범죄"]
    specializations = Column(JSON, default=list, nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.full_name}')>"

    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "lawyer_registration_number": self.lawyer_registration_number,
            "specializations": self.specializations,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
