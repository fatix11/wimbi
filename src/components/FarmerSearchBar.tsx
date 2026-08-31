"use client";

import { useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import type { Farmer } from "@/data/types";

export function FarmerSearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Farmer[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleChange(value: string) {
    setQuery(value);
    if (!value.trim()) {
      setResults([]);
      setSearched(false);
      return;
    }

    setLoading(true);
    const response = await fetch(`/api/farmers?query=${encodeURIComponent(value)}`);
    const data = response.ok ? ((await response.json()) as Farmer[]) : [];
    setResults(data);
    setLoading(false);
    setSearched(true);
  }

  return (
    <div>
      <Input
        placeholder="e.g. Grace Banda, +265991234001, GL-MW-00001"
        value={query}
        onChange={(event) => handleChange(event.target.value)}
      />

      {loading && <p className="mt-4 text-sm text-muted-foreground">Searching…</p>}

      {!loading && searched && results.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground">No farmers found.</p>
      )}

      <ul className="mt-4 flex flex-col gap-2">
        {results.map((farmer) => (
          <li key={farmer.glClientId}>
            <Link
              href={`/farmers/${farmer.glClientId}`}
              className="block rounded-lg border p-4 hover:bg-accent"
            >
              <div className="font-medium">{farmer.name}</div>
              <div className="text-sm text-muted-foreground">
                {farmer.phone} · {farmer.district}, {farmer.country} · {farmer.glClientId}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
