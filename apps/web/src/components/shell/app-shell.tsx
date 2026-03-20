"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import type { ShellSnapshot } from "@/lib/mock-adapters";

import { ShellFrame } from "./shell-frame";

function getProjectIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/projects\/([^/]+)/);
  return match?.[1] ?? null;
}

type AppShellProps = {
  snapshot: ShellSnapshot;
  children: ReactNode;
};

export function AppShell({ snapshot, children }: AppShellProps) {
  const pathname = usePathname();
  const currentProjectId = getProjectIdFromPath(pathname);

  return (
    <ShellFrame
      activePath={pathname}
      currentProjectId={currentProjectId}
      currentUser={snapshot.currentUser}
    >
      {children}
    </ShellFrame>
  );
}
