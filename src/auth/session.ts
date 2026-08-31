import { auth } from "./config";

export interface SessionUser {
  email: string;
  name: string;
  country: string;
  department: string;
  role: string;
}

export async function getSessionUser(): Promise<SessionUser | null> {
  const session = await auth();
  if (!session?.user?.email) return null;

  return {
    email: session.user.email,
    name: session.user.name ?? session.user.email,
    country: session.user.country,
    department: session.user.department,
    role: session.user.role,
  };
}
