"use client";

import { DEMO_PERSONA, type ApplicantType, type FieldId, type ProjectProfile } from "@sci/shared";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Button, Card, Chip, Label, Notice, PageHeader, PrivacyBanner, Toggle, cx, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { useApplicant, useKeywords, useProfile } from "@/lib/local";

const EMPTY: ProjectProfile = {
  nickname: "", fields: [], subdomains: [], trl: 3, evidence: [], applicant_type: "university", country: "TH",
  institution_type: "university", funding_min_usd: 10000, funding_max_usd: 50000, uses_of_funds: [],
  months_to_milestone: 12, constraints: [],
};

const STEPS = ["Field", "Stage", "Who's applying", "Funding", "Constraints"];

const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

export default function ProfileWizard() {
  const router = useRouter();
  const tax = useQuery({ queryKey: ["taxonomy"], queryFn: api.taxonomy });
  const [saved, setSaved, loaded] = useProfile();
  const [savedKw, setSavedKw] = useKeywords();
  const [, setApplicant] = useApplicant();
  const [p, setP] = useState<ProjectProfile>(EMPTY);
  const [kw, setKw] = useState("");
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (loaded && saved) setP({ ...EMPTY, ...saved });
  }, [loaded]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (savedKw) setKw(savedKw.join(", "));
  }, [savedKw]);

  const trl = useQuery({
    queryKey: ["trl", p.trl, p.evidence],
    queryFn: () => api.trlCheck(p.trl, p.evidence),
  });

  const subdomains = useMemo(
    () => tax.data?.fields.filter((f) => p.fields.includes(f.id)).flatMap((f) => f.subdomains) ?? [],
    [tax.data, p.fields],
  );
  const set = (patch: Partial<ProjectProfile>) => setP((x) => ({ ...x, ...patch }));
  const valid = [p.fields.length > 0, true, !!p.country, p.funding_max_usd > 0, true];

  function loadDemo() {
    setP(DEMO_PERSONA.profile);
    setKw(DEMO_PERSONA.keywords.join(", "));
    setApplicant(DEMO_PERSONA.applicant);
  }

  function finish() {
    const subs = p.subdomains.filter((s) => subdomains.includes(s));
    setSaved({ ...p, subdomains: subs, nickname: p.nickname?.trim() || null });
    setSavedKw(kw.split(",").map((s) => s.trim()).filter(Boolean));
    router.push("/matches");
  }

  if (!tax.data) return <PageHeader eyebrow="Profile" title="Loading…" />;
  const T = tax.data;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader eyebrow="Non-confidential profile" title="Describe your project - without describing your invention">
        Six short questions. Every answer is a category, a stage, or a range. Notice that we never ask what the technology is.
      </PageHeader>
      <PrivacyBanner />

      <div className="my-6 flex items-center gap-2">
        {STEPS.map((s, i) => (
          <button key={s} onClick={() => setStep(i)}
            className={cx("flex-1 rounded-full py-1 text-xs font-semibold", i === step ? "bg-brand-600 text-white" : i < step ? "bg-brand-100 text-brand-700" : "bg-slate-200 text-ink-muted")}>
            {i + 1}. {s}
          </button>
        ))}
      </div>

      <Card className="space-y-6">
        {step === 0 && (
          <>
            <div>
              <Label hint="Pick up to three.">Field(s)</Label>
              <div className="grid gap-2 sm:grid-cols-3">
                {T.fields.map((f) => (
                  <Toggle key={f.id} checked={p.fields.includes(f.id)} disabled={!p.fields.includes(f.id) && p.fields.length >= 3}
                    onChange={() => set({ fields: toggle(p.fields, f.id as FieldId) })}>{f.label}</Toggle>
                ))}
              </div>
            </div>
            {subdomains.length > 0 && (
              <div>
                <Label hint="Second level only - deliberately too broad to reconstruct your invention.">Sub-domain(s)</Label>
                <div className="flex flex-wrap gap-2">
                  {subdomains.map((s) => (
                    <button key={s} onClick={() => set({ subdomains: toggle(p.subdomains, s) })}
                      className={cx("rounded-full border px-3 py-1 text-sm", p.subdomains.includes(s) ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-300 text-ink-soft hover:bg-slate-50")}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {step === 1 && (
          <>
            <div>
              <Label hint="Technology readiness level - pick the one that describes where you are today.">TRL</Label>
              <div className="grid gap-2">
                {T.trl.map((t) => (
                  <label key={t.level} className={cx("flex cursor-pointer gap-3 rounded-lg border p-2.5 text-sm", p.trl === t.level ? "border-brand-500 bg-brand-50" : "border-slate-200 hover:border-slate-300")}>
                    <input type="radio" name="trl" className="mt-1 accent-brand-600" checked={p.trl === t.level} onChange={() => set({ trl: t.level })} />
                    <span><strong>TRL {t.level} - {t.name}.</strong> <span className="text-ink-soft">{t.plain}</span></span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <Label>What exists today?</Label>
              <div className="grid gap-2 sm:grid-cols-3">
                {T.evidence.map((e) => (
                  <Toggle key={e.id} checked={p.evidence.includes(e.id)} onChange={() => set({ evidence: toggle(p.evidence, e.id) })}>{e.label}</Toggle>
                ))}
              </div>
              {trl.data && <div className="mt-3"><Notice tone={trl.data.consistent === false ? "amber" : "green"}>{trl.data.note}</Notice></div>}
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div>
              <Label>Applicant type</Label>
              <div className="grid gap-2 sm:grid-cols-2">
                {T.applicant_types.map((a) => (
                  <label key={a.id} className={cx("flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm", p.applicant_type === a.id ? "border-brand-500 bg-brand-50" : "border-slate-200")}>
                    <input type="radio" className="accent-brand-600" checked={p.applicant_type === a.id} onChange={() => set({ applicant_type: a.id as ApplicantType, has_entity: null })} />
                    {a.label}
                  </label>
                ))}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label>Country</Label>
                <select className={inputCls} value={p.country} onChange={(e) => set({ country: e.target.value })}>
                  {T.countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <Label>Institution type</Label>
                <select className={inputCls} value={p.institution_type ?? ""} onChange={(e) => set({ institution_type: e.target.value })}>
                  {T.institution_types.map((i) => <option key={i.id} value={i.id}>{i.label}</option>)}
                </select>
              </div>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <div>
              <Label hint="A range, not an exact figure (USD).">Funding needed</Label>
              <div className="flex items-center gap-2">
                <input type="number" min={0} step={1000} className={inputCls} value={p.funding_min_usd} onChange={(e) => set({ funding_min_usd: Number(e.target.value) })} />
                <span className="text-ink-muted">to</span>
                <input type="number" min={0} step={1000} className={inputCls} value={p.funding_max_usd} onChange={(e) => set({ funding_max_usd: Number(e.target.value) })} />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {[[5000, 50000], [50000, 250000], [250000, 1000000], [1000000, 5000000]].map(([a, b]) => (
                  <button key={a} onClick={() => set({ funding_min_usd: a, funding_max_usd: b })} className="rounded-full border border-slate-300 px-3 py-0.5 text-xs text-ink-soft hover:bg-slate-50">
                    ${a / 1000}k-${b >= 1e6 ? `${b / 1e6}M` : `${b / 1000}k`}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label>Intended use of funds</Label>
              <div className="grid gap-2 sm:grid-cols-3">
                {T.uses_of_funds.map((u) => (
                  <Toggle key={u.id} checked={p.uses_of_funds.includes(u.id)} onChange={() => set({ uses_of_funds: toggle(p.uses_of_funds, u.id) })}>{u.label}</Toggle>
                ))}
              </div>
            </div>
            <div className="max-w-xs">
              <Label>Months to your next milestone</Label>
              <input type="number" min={1} max={120} className={inputCls} value={p.months_to_milestone} onChange={(e) => set({ months_to_milestone: Number(e.target.value) })} />
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <div>
              <Label>Constraints</Label>
              <div className="grid gap-2 sm:grid-cols-3">
                {T.constraints.map((c) => (
                  <Toggle key={c.id} checked={p.constraints.includes(c.id)} onChange={() => set({ constraints: toggle(p.constraints, c.id) })}>{c.label}</Toggle>
                ))}
              </div>
            </div>
            <div>
              <Label hint="Shown on application drafts. Keep it non-confidential.">Project nickname (optional)</Label>
              <input className={inputCls} maxLength={80} value={p.nickname ?? ""} onChange={(e) => set({ nickname: e.target.value })} placeholder="e.g. Agri-waste materials pilot" />
            </div>
            <div className="rounded-lg border border-dashed border-emerald-300 bg-emerald-50/50 p-3">
              <Label hint="Optional. These are shared with no one and used only for local similarity - they're stored in this browser and never sent to our server, the LLM, or any funder.">
                3-5 generic keywords <Chip tone="green">stays on this device</Chip>
              </Label>
              <input className={inputCls} value={kw} onChange={(e) => setKw(e.target.value)} placeholder="comma separated, e.g. rice straw, low-carbon" />
            </div>
          </>
        )}

        <div className="flex items-center justify-between border-t border-slate-100 pt-4">
          <Button variant="ghost" onClick={loadDemo}>Load demo researcher</Button>
          <div className="flex gap-2">
            {step > 0 && <Button variant="secondary" onClick={() => setStep(step - 1)}>Back</Button>}
            {step < STEPS.length - 1
              ? <Button disabled={!valid[step]} onClick={() => setStep(step + 1)}>Next</Button>
              : <Button disabled={!valid.every(Boolean)} onClick={finish}>Find matches →</Button>}
          </div>
        </div>
      </Card>
    </div>
  );
}
