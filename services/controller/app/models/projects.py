from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import json_type, utc_now
from app.models.enums import AssetKind, DatasetStatus, ProjectRole, ProjectStatus


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_project_org_code"),)

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", native_enum=False), nullable=False
    )
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    settings: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    archived_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="projects")
    memberships = relationship("ProjectMembership", back_populates="project")


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role", native_enum=False), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project = relationship("Project", back_populates="memberships")
    user = relationship("User", back_populates="project_memberships")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status", native_enum=False), nullable=False
    )
    metadata_json: Mapped[dict] = mapped_column("metadata", json_type, default=dict, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    archived_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceAsset(Base):
    __tablename__ = "source_assets"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)
    asset_kind: Mapped[AssetKind] = mapped_column(
        Enum(AssetKind, name="asset_kind", native_enum=False), nullable=False
    )
    uri: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_rate: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)
    transcript: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", json_type, default=dict, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
