import type { Farmer } from "@/data/types";
import type { SessionUser } from "@/auth/session";

// "data_team" is the one role with cross-country scope for the internal
// pilot (see _docs/business_requirements.md §7); every other role/persona is
// scoped to their own country.
export function hasAllCountryScope(user: SessionUser): boolean {
  return user.role === "data_team";
}

export function canAccessFarmer(user: SessionUser, farmer: Pick<Farmer, "country">): boolean {
  return hasAllCountryScope(user) || farmer.country === user.country;
}

export function scopeFarmers(user: SessionUser, farmers: Farmer[]): Farmer[] {
  return hasAllCountryScope(user) ? farmers : farmers.filter((farmer) => farmer.country === user.country);
}
