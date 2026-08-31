import { notFound, redirect } from "next/navigation";
import { getSessionUser } from "@/auth/session";
import { getDataSource } from "@/data/source";
import { canAccessFarmer } from "@/rbac/scope";
import { FarmerProfileCard } from "@/components/FarmerProfileCard";
import { JourneyTimeline } from "@/components/JourneyTimeline";

export default async function FarmerProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const user = await getSessionUser();
  if (!user) redirect("/login");

  const { id } = await params;
  const farmer = await getDataSource().getFarmer(id);

  if (!farmer || !canAccessFarmer(user, farmer)) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <FarmerProfileCard farmer={farmer} />
      <h2 className="mt-10 mb-4 text-lg font-semibold">Journey Timeline</h2>
      <JourneyTimeline glClientId={farmer.glClientId} />
    </div>
  );
}
