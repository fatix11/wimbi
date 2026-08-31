export interface Farmer {
  glClientId: string;
  name: string;
  phone: string;
  country: string;
  district: string;
  programs: string[];
  joinDate: string;
}

export type JourneyEventType =
  | "enrollment"
  | "sale"
  | "loan"
  | "repayment"
  | "tree"
  | "buyback";

export interface JourneyEvent {
  id: string;
  glClientId: string;
  type: JourneyEventType;
  date: string;
  program: string;
  description: string;
  amount?: number;
  currency?: string;
}
