import type { DataSource } from "./source";
import type { Farmer, JourneyEvent } from "./types";
import farmersFixture from "./fixtures/farmers.json";
import journeyFixture from "./fixtures/client_journey.json";

const farmers = farmersFixture as Farmer[];
const journeyEvents = journeyFixture as JourneyEvent[];

export class MockDataSource implements DataSource {
  async searchFarmers(query: string): Promise<Farmer[]> {
    const needle = query.trim().toLowerCase();
    if (!needle) return [];

    return farmers.filter(
      (farmer) =>
        farmer.name.toLowerCase().includes(needle) ||
        farmer.phone.includes(needle) ||
        farmer.glClientId.toLowerCase().includes(needle),
    );
  }

  async getFarmer(glClientId: string): Promise<Farmer | null> {
    return farmers.find((farmer) => farmer.glClientId === glClientId) ?? null;
  }

  async getJourney(glClientId: string): Promise<JourneyEvent[]> {
    return journeyEvents
      .filter((event) => event.glClientId === glClientId)
      .sort((a, b) => a.date.localeCompare(b.date));
  }
}
