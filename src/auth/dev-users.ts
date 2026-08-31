// Dev-only stand-ins for the SuccessFactors-derived identity Keycloak will
// eventually provide (email -> country/department/role). Swapped for the
// real Keycloak OIDC provider once a realm/client exists.
export interface DevUser {
  id: string;
  email: string;
  name: string;
  country: string;
  department: string;
  role: string;
}

export const devUsers: DevUser[] = [
  {
    id: "dev-cc-malawi",
    email: "cc.malawi@oneacrefund.org",
    name: "Chikondi Mvula",
    country: "Malawi",
    department: "Call Center",
    role: "call_center",
  },
  {
    id: "dev-bizops-malawi",
    email: "bizops.malawi@oneacrefund.org",
    name: "Thoko Chirwa",
    country: "Malawi",
    department: "Business Operations",
    role: "business_ops",
  },
  {
    id: "dev-fieldsupervisor-malawi",
    email: "fieldsupervisor.malawi@oneacrefund.org",
    name: "Blessings Gondwe",
    country: "Malawi",
    department: "Field Operations",
    role: "field_supervisor",
  },
  {
    id: "dev-data-team",
    email: "data.team@oneacrefund.org",
    name: "Augustin Faraja",
    country: "ALL",
    department: "Data & Analytics",
    role: "data_team",
  },
];
