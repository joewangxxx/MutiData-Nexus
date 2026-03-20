import { listInboxItems } from "@/lib/mock-adapters";

describe("listInboxItems", () => {
  it("orders derived inbox items by numeric priority descending", async () => {
    const items = await listInboxItems();

    expect(items.length).toBeGreaterThan(1);

    for (let index = 1; index < items.length; index += 1) {
      expect(items[index - 1].priority).toBeGreaterThanOrEqual(items[index].priority);
    }
  });
});
