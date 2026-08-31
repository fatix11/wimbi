import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Farmer } from "@/data/types";

export function FarmerProfileCard({ farmer }: { farmer: Farmer }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">{farmer.name}</CardTitle>
        <CardDescription>
          {farmer.district}, {farmer.country} · Joined {farmer.joinDate}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="text-sm text-muted-foreground">
          {farmer.phone} · {farmer.glClientId}
        </div>
        <div className="flex flex-wrap gap-2">
          {farmer.programs.map((program) => (
            <Badge key={program} variant="secondary">
              {program}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
