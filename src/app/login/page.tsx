import { signIn } from "@/auth/config";
import { devUsers } from "@/auth/dev-users";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="mb-2 text-2xl font-semibold">Wimbi — Dev Login</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        Stand-in for Keycloak SSO until a realm/client exists. Pick a persona
        to sign in as.
      </p>

      <div className="flex flex-col gap-3">
        {devUsers.map((user) => (
          <Card key={user.id}>
            <CardHeader>
              <CardTitle>{user.name}</CardTitle>
              <CardDescription>
                {user.department} ·{" "}
                {user.country === "ALL" ? "All countries" : user.country}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                action={async () => {
                  "use server";
                  await signIn("credentials", {
                    email: user.email,
                    redirectTo: "/search",
                  });
                }}
              >
                <Button type="submit" className="w-full">
                  Sign in as {user.name}
                </Button>
              </form>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
