import { beforeEach, describe, expect, it } from "vitest";
import { MockDataSource } from "@/data/mock-source";

describe("MockDataSource", () => {
  let source: MockDataSource;

  beforeEach(() => {
    source = new MockDataSource();
  });

  it("searches farmers by name, phone, or gl_client_id", async () => {
    expect(await source.searchFarmers("Grace")).toHaveLength(1);
    expect(await source.searchFarmers("+265991234002")).toHaveLength(1);
    expect(await source.searchFarmers("GL-MW-00003")).toHaveLength(1);
    expect(await source.searchFarmers("no-such-farmer")).toHaveLength(0);
  });

  it("returns null for an unknown farmer id", async () => {
    expect(await source.getFarmer("GL-XX-99999")).toBeNull();
  });

  it("returns journey events sorted chronologically", async () => {
    const events = await source.getJourney("GL-MW-00001");
    expect(events.length).toBeGreaterThan(0);
    const dates = events.map((event) => event.date);
    expect(dates).toEqual([...dates].sort());
  });

  it("returns no journey events for a farmer with none recorded", async () => {
    expect(await source.getJourney("GL-MW-00003")).toEqual([]);
  });
});
