import snowflake from "snowflake-sdk";
import type { DataSource } from "./source";
import type { Farmer, JourneyEvent } from "./types";

// Real ANALYTICS.REPORTING implementation. Not wired to live credentials yet
// (see .env.local.example) — V_CLIENT_JOURNEY is the view name confirmed in
// _docs/business_requirements.md; V_FARMER_PROFILE's exact name is assumed pending
// confirmation from the ANALYTICS team.

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var ${name} for Snowflake connection`);
  }
  return value;
}

function createConnection(): snowflake.Connection {
  return snowflake.createConnection({
    account: requireEnv("SNOWFLAKE_ACCOUNT"),
    username: requireEnv("SNOWFLAKE_USER"),
    password: process.env.SNOWFLAKE_PASSWORD,
    warehouse: requireEnv("SNOWFLAKE_WAREHOUSE"),
    database: process.env.SNOWFLAKE_DATABASE ?? "ANALYTICS",
    schema: process.env.SNOWFLAKE_SCHEMA ?? "REPORTING",
    role: process.env.SNOWFLAKE_ROLE,
  });
}

function connect(connection: snowflake.Connection): Promise<snowflake.Connection> {
  return new Promise((resolve, reject) => {
    connection.connect((err, conn) => (err ? reject(err) : resolve(conn)));
  });
}

function execute<T>(
  connection: snowflake.Connection,
  sqlText: string,
  binds: snowflake.Binds = [],
): Promise<T[]> {
  return new Promise((resolve, reject) => {
    connection.execute({
      sqlText,
      binds,
      complete: (err, _stmt, rows) => (err ? reject(err) : resolve((rows ?? []) as T[])),
    });
  });
}

interface FarmerRow {
  GL_CLIENT_ID: string;
  NAME: string;
  PHONE: string;
  COUNTRY: string;
  DISTRICT: string;
  PROGRAMS: string;
  JOIN_DATE: string;
}

interface JourneyRow {
  EVENT_ID: string;
  GL_CLIENT_ID: string;
  EVENT_TYPE: JourneyEvent["type"];
  EVENT_DATE: string;
  PROGRAM: string;
  DESCRIPTION: string;
  AMOUNT: number | null;
  CURRENCY: string | null;
}

function toFarmer(row: FarmerRow): Farmer {
  return {
    glClientId: row.GL_CLIENT_ID,
    name: row.NAME,
    phone: row.PHONE,
    country: row.COUNTRY,
    district: row.DISTRICT,
    programs: row.PROGRAMS ? row.PROGRAMS.split(",") : [],
    joinDate: row.JOIN_DATE,
  };
}

function toJourneyEvent(row: JourneyRow): JourneyEvent {
  return {
    id: row.EVENT_ID,
    glClientId: row.GL_CLIENT_ID,
    type: row.EVENT_TYPE,
    date: row.EVENT_DATE,
    program: row.PROGRAM,
    description: row.DESCRIPTION,
    amount: row.AMOUNT ?? undefined,
    currency: row.CURRENCY ?? undefined,
  };
}

export class SnowflakeDataSource implements DataSource {
  private connectionPromise: Promise<snowflake.Connection> | null = null;

  private getConnection(): Promise<snowflake.Connection> {
    if (!this.connectionPromise) {
      this.connectionPromise = connect(createConnection());
    }
    return this.connectionPromise;
  }

  async searchFarmers(query: string): Promise<Farmer[]> {
    const connection = await this.getConnection();
    const rows = await execute<FarmerRow>(
      connection,
      `SELECT GL_CLIENT_ID, NAME, PHONE, COUNTRY, DISTRICT, PROGRAMS, JOIN_DATE
       FROM V_FARMER_PROFILE
       WHERE NAME ILIKE :1 OR PHONE ILIKE :1 OR GL_CLIENT_ID ILIKE :1
       LIMIT 50`,
      [`%${query}%`],
    );
    return rows.map(toFarmer);
  }

  async getFarmer(glClientId: string): Promise<Farmer | null> {
    const connection = await this.getConnection();
    const rows = await execute<FarmerRow>(
      connection,
      `SELECT GL_CLIENT_ID, NAME, PHONE, COUNTRY, DISTRICT, PROGRAMS, JOIN_DATE
       FROM V_FARMER_PROFILE
       WHERE GL_CLIENT_ID = :1`,
      [glClientId],
    );
    return rows[0] ? toFarmer(rows[0]) : null;
  }

  async getJourney(glClientId: string): Promise<JourneyEvent[]> {
    const connection = await this.getConnection();
    const rows = await execute<JourneyRow>(
      connection,
      `SELECT EVENT_ID, GL_CLIENT_ID, EVENT_TYPE, EVENT_DATE, PROGRAM, DESCRIPTION, AMOUNT, CURRENCY
       FROM V_CLIENT_JOURNEY
       WHERE GL_CLIENT_ID = :1
       ORDER BY EVENT_DATE ASC`,
      [glClientId],
    );
    return rows.map(toJourneyEvent);
  }
}
