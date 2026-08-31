import { NextResponse } from "next/server";
import { getSessionUser } from "@/auth/session";
import { getDataSource } from "@/data/source";
import { canAccessFarmer } from "@/rbac/scope";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const dataSource = getDataSource();
  const farmer = await dataSource.getFarmer(id);

  if (!farmer) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  if (!canAccessFarmer(user, farmer)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const journey = await dataSource.getJourney(id);
  return NextResponse.json(journey);
}
