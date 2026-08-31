import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      country: string;
      department: string;
      role: string;
    } & DefaultSession["user"];
  }

  interface User {
    country: string;
    department: string;
    role: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    country?: string;
    department?: string;
    role?: string;
  }
}
