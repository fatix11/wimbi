import { redirect } from "next/navigation";
import { getSessionUser } from "@/auth/session";
import { FarmerSearchBar } from "@/components/FarmerSearchBar";

export default async function SearchPage() {
  const user = await getSessionUser();
  if (!user) redirect("/login");

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="mb-1 text-2xl font-semibold">Find a farmer</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Search by name, phone number, or account ID.
      </p>
      <FarmerSearchBar />
    </div>
  );
}
