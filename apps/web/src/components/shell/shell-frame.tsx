import type { ReactNode } from "react";

type ShellFrameProps = {
  activePath: string;
  currentProjectId?: string | null;
  currentUser: {
    id: string;
    displayName: string;
    organizationName: string;
    organizationRole: string;
  };
  children: ReactNode;
};

type NavItem = {
  href: string;
  label: string;
};

const sharedNav: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/workflow-runs", label: "Workflow Runs" },
  { href: "/inbox", label: "Inbox" },
];

function getProjectNav(projectId: string): NavItem[] {
  return [
    { href: `/projects/${projectId}`, label: "Project Overview" },
    {
      href: `/projects/${projectId}/annotation/queue`,
      label: "Annotation Queue",
    },
    { href: `/projects/${projectId}/risk`, label: "Risk Monitor" },
  ];
}

function getLinkClass(isActive: boolean): string {
  return isActive ? "shell-link shell-link-active" : "shell-link";
}

export function ShellFrame({
  activePath,
  currentProjectId,
  currentUser,
  children,
}: ShellFrameProps) {
  const projectNav = currentProjectId ? getProjectNav(currentProjectId) : [];

  return (
    <div className="shell-root">
      <header className="shell-topbar">
        <div>
          <p className="shell-kicker">MutiData-Nexus</p>
          <h1 className="shell-title">Unified AI data operations</h1>
        </div>
        <div className="shell-user">
          <span>{currentUser.organizationName}</span>
          <strong>{currentUser.displayName}</strong>
        </div>
      </header>
      <div className="shell-body">
        <aside className="shell-sidebar" aria-label="Primary navigation">
          <nav className="shell-nav">
            {sharedNav.map((item) => (
              <a
                key={item.href}
                className={getLinkClass(activePath.startsWith(item.href))}
                href={item.href}
              >
                {item.label}
              </a>
            ))}
          </nav>
          {projectNav.length > 0 ? (
            <nav className="shell-nav" aria-label="Project navigation">
              {projectNav.map((item) => (
                <a
                  key={item.href}
                  className={getLinkClass(activePath.startsWith(item.href))}
                  href={item.href}
                >
                  {item.label}
                </a>
              ))}
            </nav>
          ) : null}
          <div className="shell-user-meta">
            <span>{currentUser.organizationRole.replaceAll("_", " ")}</span>
            <code>{currentUser.id}</code>
          </div>
        </aside>
        <main className="shell-main">{children}</main>
      </div>
    </div>
  );
}
