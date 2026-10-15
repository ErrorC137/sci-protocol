"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Deadline, GrantMeta } from "@/components/GrantBits";
import { Card, Empty, PageHeader, Spinner, inputCls } from "@/components/ui";
import { api, type GrantFilters } from "@/lib/api";

export default function Discover() {
  const tax = useQuery({ queryKey: ["taxonomy"], queryFn: api.taxonomy });
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [f, setF] = useState<GrantFilters>({ limit: 60 });
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);
  const filters = { ...f, q: debounced || undefined };
  const res = useQuery({ queryKey: ["grants", filters], queryFn: () => api.grants(filters) });

  return (
    <div>
      <PageHeader eyebrow="Discover" title="Funding opportunities">
        Grants, accelerators, foundations, crowdfunding and Web3 programs - weighted toward Thailand, Southeast Asia and
        deep tech. Search is semantic; filters are exact. For ranked, eligibility-checked results, <Link href="/profile" className="font-semibold text-brand-700 underline">build a profile</Link>.
      </PageHeader>

      <Card className="mb-6 grid gap-3 md:grid-cols-6">
        <input className={`${inputCls} md:col-span-2`} placeholder="Search e.g. bio-based construction materials" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className={inputCls} value={f.field?.[0] ?? ""} onChange={(e) => setF({ ...f, field: e.target.value ? [e.target.value] : undefined })}>
          <option value="">Any field</option>
          {tax.data?.fields.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
        </select>
        <select className={inputCls} value={f.country ?? ""} onChange={(e) => setF({ ...f, country: e.target.value || undefined })}>
          <option value="">Any country</option>
          {tax.data?.countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
        <select className={inputCls} value={f.applicant_type ?? ""} onChange={(e) => setF({ ...f, applicant_type: e.target.value || undefined })}>
          <option value="">Any applicant</option>
          {tax.data?.applicant_types.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
        <select className={inputCls} value={f.funder_type ?? ""} onChange={(e) => setF({ ...f, funder_type: e.target.value || undefined })}>
          <option value="">Any funder type</option>
          {tax.data?.funder_types.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-ink-soft md:col-span-2">
          <input type="checkbox" className="accent-brand-600" checked={!!f.no_equity} onChange={(e) => setF({ ...f, no_equity: e.target.checked })} />
          Non-dilutive only (no equity)
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-soft md:col-span-2">
          TRL
          <select className={inputCls} value={f.trl ?? ""} onChange={(e) => setF({ ...f, trl: e.target.value ? Number(e.target.value) : undefined })}>
            <option value="">any</option>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <p className="self-center text-right text-sm text-ink-muted md:col-span-2">
          {res.isFetching ? <Spinner /> : res.data && `${res.data.total} result${res.data.total === 1 ? "" : "s"}`}
        </p>
      </Card>

      {res.error && <Empty title="Couldn't reach the API">Is the backend running at {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}?</Empty>}
      <div className="grid gap-4 md:grid-cols-2">
        {res.data?.items.map(({ grant: g }) => (
          <Card key={g.id} className="flex flex-col gap-2">
            <div>
              <p className="text-xs font-medium text-ink-muted">{g.funder_name}</p>
              <h2 className="font-semibold text-ink">{g.title}</h2>
            </div>
            <GrantMeta g={g} />
            {g.summary && <p className="line-clamp-3 text-sm text-ink-soft">{g.summary}</p>}
            <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
              <Deadline g={g} />
              <div className="flex gap-3 text-sm">
                {g.form_url && <Link href={`/apply/${g.id}`} className="font-semibold text-brand-700 hover:underline">Pre-fill application</Link>}
                {g.url && <a href={g.url} target="_blank" rel="noreferrer" className="text-ink-muted hover:underline">Source ↗</a>}
              </div>
            </div>
          </Card>
        ))}
      </div>
      {res.data && res.data.items.length === 0 && <Empty title="No opportunities match these filters" />}
    </div>
  );
}
