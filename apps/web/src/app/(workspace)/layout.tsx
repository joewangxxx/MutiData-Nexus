import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { getShellSnapshot } from "@/lib/mock-adapters";

export default async function WorkspaceLayout({
  children,
}: {
  children: ReactNode;
}) {
  const snapshot = await getShellSnapshot();

  return <AppShell snapshot={snapshot}>{children}</AppShell>;
}
