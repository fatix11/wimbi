import { describe, expect, it } from "vitest";
import { canAccessFarmer, hasAllCountryScope, scopeFarmers } from "@/rbac/scope";
import type { SessionUser } from "@/auth/session";
import type { Farmer } from "@/data/types";

const malawiUser: SessionUser = {
  email: "cc.malawi@oneacrefund.org",
  name: "Chikondi Mvula",
  country: "Malawi",
  department: "Call Center",
  role: "call_center",
};

const dataTeamUser: SessionUser = {
  email: "data.team@oneacrefund.org",
  name: "Augustin Faraja",
  country: "ALL",
  department: "Data & Analytics",
  role: "data_team",
};

const malawiFarmer: Farmer = {
  glClientId: "GL-MW-00001",
  name: "Grace Banda",
  phone: "+265991234001",
  country: "Malawi",
  district: "Lilongwe",
  programs: ["Credit"],
  joinDate: "2022-09-12",
};

const kenyaFarmer: Farmer = {
  ...malawiFarmer,
  glClientId: "GL-KE-00001",
  country: "Kenya",
};

describe("rbac/scope", () => {
  it("lets a country-scoped user access a farmer in their own country", () => {
    expect(canAccessFarmer(malawiUser, malawiFarmer)).toBe(true);
  });

  it("blocks a country-scoped user from a farmer in a different country", () => {
    expect(canAccessFarmer(malawiUser, kenyaFarmer)).toBe(false);
  });

  it("lets a data_team user access farmers in any country", () => {
    expect(hasAllCountryScope(dataTeamUser)).toBe(true);
    expect(canAccessFarmer(dataTeamUser, malawiFarmer)).toBe(true);
    expect(canAccessFarmer(dataTeamUser, kenyaFarmer)).toBe(true);
  });

  it("filters a farmer list down to the user's country scope", () => {
    expect(scopeFarmers(malawiUser, [malawiFarmer, kenyaFarmer])).toEqual([malawiFarmer]);
  });

  it("does not filter the list for a data_team user", () => {
    expect(scopeFarmers(dataTeamUser, [malawiFarmer, kenyaFarmer])).toEqual([
      malawiFarmer,
      kenyaFarmer,
    ]);
  });
});
