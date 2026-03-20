import {
  describePriority,
  describeSeverity,
  sortDescendingByRank,
} from "@/lib/presenters";

describe("numeric contract presenters", () => {
  it("maps numeric priority values to stable UI labels", () => {
    expect(describePriority(90)).toBe("high");
    expect(describePriority(60)).toBe("medium");
    expect(describePriority(20)).toBe("low");
  });

  it("maps numeric severity values to stable UI labels", () => {
    expect(describeSeverity(95)).toBe("critical");
    expect(describeSeverity(65)).toBe("warning");
    expect(describeSeverity(20)).toBe("low");
  });

  it("sorts numeric ranks descending instead of lexicographically", () => {
    expect(sortDescendingByRank(20, 90)).toBeGreaterThan(0);
    expect(sortDescendingByRank(95, 65)).toBeLessThan(0);
    expect(sortDescendingByRank(50, 50)).toBe(0);
  });
});
