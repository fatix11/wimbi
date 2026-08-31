import Link from "next/link";
import { getSessionUser } from "@/auth/session";
import { signOut } from "@/auth/config";
import { Button } from "@/components/ui/button";

export async function AppHeader() {
  const user = await getSessionUser();

  return (
    <header className="flex items-center justify-between border-b px-6 py-3">
      <Link href="/search" className="text-lg font-semibold tracking-tight">
        Wimbi
      </Link>

      {user && (
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">
            {user.name} · {user.department} ·{" "}
            {user.country === "ALL" ? "All countries" : user.country}
          </span>
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/login" });
            }}
          >
            <Button type="submit" variant="ghost" size="sm">
              Log out
            </Button>
          </form>
        </div>
      )}
    </header>
  );
}
