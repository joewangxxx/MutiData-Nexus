# Observability Guide

Status: `release_hardening_ready`
Owner: `general`
Last Updated: `2026-03-20`

This document describes the minimal observability posture for the current release hardening package. It is intentionally small and release-oriented: it focuses on the signals that let us tell whether the release stack is alive, ready, and safe to roll back.

## What We Observe

- Controller process health through `GET /api/v1/ops/healthz`
- Controller readiness through `GET /api/v1/ops/readyz`
- Web process health through `GET /healthz`
- Web readiness through `GET /readyz`
- Release compose health checks for controller, web, and PostgreSQL

## Signal Sources

- FastAPI returns structured JSON envelopes for controller release endpoints.
- Next.js returns lightweight JSON payloads for web release endpoints.
- Docker Compose health checks are the primary release smoke signal in the local release package.
- Audit tables in PostgreSQL remain the source of truth for business actions and workflow outcomes.

## Release Smoke Flow

1. Start the release stack with `docker compose -f compose.release.yaml up -d --build`.
2. Check controller health and readiness.
3. Check web health and readiness.
4. Confirm the stack is serving the release routes before declaring the environment usable.

## What Is Not Included

- No metrics backend has been provisioned.
- No alert routing or paging policy has been defined.
- No log aggregation service has been wired into the release package.
- No dashboarding stack has been standardized for production operations.

## Operational Notes

- Controller readiness fails closed when runtime configuration is invalid or the database is unreachable.
- Web readiness fails closed when the controller health endpoint is unavailable.
- The release package is meant to help operators verify the stack quickly; it is not a substitute for a full production observability platform.
