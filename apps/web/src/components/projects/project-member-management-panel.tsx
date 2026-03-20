"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState, StatusBadge } from "@/components/ui/primitives";
import type { ProjectMembershipDetail } from "@/lib/contracts";

function compactObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== ""),
  ) as T;
}

async function requestJson(
  path: string,
  method: "PATCH" | "DELETE",
  body?: Record<string, unknown>,
) {
  const response = await fetch(path, {
    method,
    headers: body
      ? {
          "content-type": "application/json",
        }
      : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  let payload: { error?: { message?: string } } | null = null;

  if (text) {
    try {
      payload = JSON.parse(text) as { error?: { message?: string } };
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    throw new Error(
      payload?.error?.message ?? `Request to ${path} failed with status ${response.status}.`,
    );
  }

  return payload;
}

type ProjectMemberRowProps = {
  projectId: string;
  member: ProjectMembershipDetail;
};

function ProjectMemberRow({ projectId, member }: ProjectMemberRowProps) {
  const router = useRouter();
  const [projectRole, setProjectRole] = useState(member.project_role);
  const [status, setStatus] = useState(member.status);
  const [saving, setSaving] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const active = member.status === "active";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await requestJson(`/api/projects/${projectId}/members/${member.id}`, "PATCH", {
        ...compactObject({
          project_role: projectRole,
          status,
        }),
      });

      setStatusMessage("Member updated. Refreshing the project.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Member update failed.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    setDeactivating(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await requestJson(`/api/projects/${projectId}/members/${member.id}`, "DELETE");
      setStatusMessage("Member deactivated. Refreshing the project.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Member deactivation failed.");
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <article className="stack-item">
      <div className="inline-meta">
        <StatusBadge value={member.status} />
        <span>{member.user.display_name}</span>
      </div>
      <h3>{member.user.email}</h3>
      <p className="muted-text">Project member role and status stay visible in the overview.</p>

      {active ? (
        <form className="stack-list" onSubmit={handleSubmit}>
          <div className="section-grid">
            <label className="stack-list span-6">
              <span className="muted-text">Role</span>
              <select
                aria-label={`Role for ${member.user.display_name}`}
                className="input-field"
                value={projectRole}
                onChange={(event) => setProjectRole(event.target.value)}
              >
                {["annotator", "reviewer", "project_manager", "observer"].map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>
            <label className="stack-list span-6">
              <span className="muted-text">Status</span>
              <select
                aria-label={`Status for ${member.user.display_name}`}
                className="input-field"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                {["active", "inactive"].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="button-row">
            <button className="button-primary" type="submit" disabled={saving || deactivating}>
              {saving ? "Saving..." : "Save changes"}
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={handleDeactivate}
              disabled={saving || deactivating}
            >
              {deactivating ? "Deactivating..." : "Deactivate member"}
            </button>
          </div>
        </form>
      ) : (
        <p className="muted-text">Inactive member records are retained for auditability.</p>
      )}

      {statusMessage ? (
        <p aria-live="polite" className="muted-text">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p aria-live="polite" className="muted-text">
          {errorMessage}
        </p>
      ) : null}
    </article>
  );
}

type ProjectMemberManagementPanelProps = {
  projectId: string;
  members: ProjectMembershipDetail[];
};

export function ProjectMemberManagementPanel({
  projectId,
  members,
}: ProjectMemberManagementPanelProps) {
  const activeMembers = members.filter((member) => member.status === "active").length;
  const inactiveMembers = members.length - activeMembers;

  if (members.length === 0) {
    return (
      <EmptyState
        title="No project members"
        description="Project members will appear here once the backend returns live membership records."
      />
    );
  }

  return (
    <div className="stack-list">
      <div className="stack-meta">
        <span>{activeMembers} active</span>
        <span>{inactiveMembers} inactive</span>
      </div>
      <div className="stack-list">
        {members.map((member) => (
          <ProjectMemberRow key={member.id} projectId={projectId} member={member} />
        ))}
      </div>
    </div>
  );
}
