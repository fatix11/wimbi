import type { Farmer, JourneyEvent } from "./types";
import { MockDataSource } from "./mock-source";
import { SnowflakeDataSource } from "./snowflake-source";

export interface DataSource {
  searchFarmers(query: string): Promise<Farmer[]>;
  getFarmer(glClientId: string): Promise<Farmer | null>;
  getJourney(glClientId: string): Promise<JourneyEvent[]>;
}

let cached: DataSource | null = null;

export function getDataSource(): DataSource {
  if (!cached) {
    // WIMBI_DATA_SOURCE selects the backend; defaults to mock fixtures until
    // real ANALYTICS.REPORTING credentials exist (see .env.local.example).
    cached =
      process.env.WIMBI_DATA_SOURCE === "snowflake"
        ? new SnowflakeDataSource()
        : new MockDataSource();
  }
  return cached;
}
