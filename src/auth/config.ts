import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { devUsers } from "./dev-users";

// Dev-only Credentials provider today; swap for a Keycloak-compatible OIDC
// provider (next-auth's generic "oidc" provider) once a realm/client exists —
// the session shape and every RBAC check downstream stays the same.
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "Dev Login",
      credentials: {
        email: { label: "Email", type: "text" },
      },
      authorize: async (credentials) => {
        const email = credentials?.email;
        const devUser = devUsers.find((candidate) => candidate.email === email);
        return devUser ?? null;
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.country = user.country;
        token.department = user.department;
        token.role = user.role;
      }
      return token;
    },
    session({ session, token }) {
      session.user.country = (token.country as string | undefined) ?? "";
      session.user.department = (token.department as string | undefined) ?? "";
      session.user.role = (token.role as string | undefined) ?? "";
      return session;
    },
  },
});
