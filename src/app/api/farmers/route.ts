import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "@/auth/session";
import { getDataSource } from "@/data/source";
import { scopeFarmers } from "@/rbac/scope";

export async function GET(request: NextRequest) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const query = request.nextUrl.searchParams.get("query") ?? "";
  const results = await getDataSource().searchFarmers(query);
  return NextResponse.json(scopeFarmers(user, results));
}
