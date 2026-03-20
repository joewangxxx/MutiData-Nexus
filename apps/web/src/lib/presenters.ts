export function humanizeToken(value: string) {
  return value.replaceAll("_", " ");
}

export function describePriority(value: number) {
  if (value >= 80) {
    return "high";
  }

  if (value >= 50) {
    return "medium";
  }

  if (value > 0) {
    return "low";
  }

  return "routine";
}

export function describeSeverity(value: number) {
  if (value >= 90) {
    return "critical";
  }

  if (value >= 60) {
    return "warning";
  }

  if (value > 0) {
    return "low";
  }

  return "informational";
}

export function sortDescendingByRank(left: number, right: number) {
  return right - left;
}

export function formatDateTime(value: string | null) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatCount(value: number | undefined) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}
