"use client";

import type { Applicant, ApplicationOut, FieldValue, FilledField, FormTemplate } from "@sci/shared";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { GrantMeta } from "@/components/GrantBits";
import { Button, Card, Chip, Empty, Label, Notice, PageHeader, Spinner, cx, inputCls } from "@/components/ui";
import { API_URL, ApiError, api } from "@/lib/api";
import { useApplicant, useProfile } from "@/lib/local";

const PLACEHOLDER_RE = /(\[YOU MUST ADD:[^\]]*\])/g;
const hasPlaceholder = (s: string) => s.includes("[YOU MUST ADD:");
const STATUS_TONE = { green: "green", amber: "amber", red: "red" } as const;
const STATUS_TEXT = { green: "from your profile", amber: "verify", red: "needs you" };
const SOURCE_TEXT: Record<string, string> = { profile: "profile", llm: "inferred by Claude", template: "draft scaffold", user: "edited by you", none: "-" };

function Placeholders({ text }: { text: string }) {
  const gaps = text.match(PLACEHOLDER_RE) ?? [];
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      <span className="font-semibold text-amber-900">Replace before export:</span>
      {gaps.map((g, i) => <mark key={i} className="placeholder-mark">{g.slice(15, -1).trim()}</mark>)}
    </div>
  );
}

function FieldInput({ f, value, onChange, onCommit }: { f: FilledField; value: FieldValue; onChange: (v: FieldValue) => void; onCommit: (v: FieldValue) => void }) {
  if (f.type === "signature") {
    return <input disabled className={cx(inputCls, "bg-slate-50")} value="Sign on the official form yourself" />;
  }
  if (f.type === "checkbox" && f.options.length === 0) {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="h-4 w-4 accent-brand-600" checked={value === true} onChange={(e) => { onChange(e.target.checked); onCommit(e.target.checked); }} />
        {value === true ? "Ticked" : "Not ticked"}
      </label>
    );
  }
  if (f.type === "checkbox") {
    const sel = Array.isArray(value) ? value : [];
    return (
      <div className="flex flex-wrap gap-3">
        {f.options.map((o) => (
          <label key={o} className="flex items-center gap-1.5 text-sm">
            <input type="checkbox" className="accent-brand-600" checked={sel.includes(o)}
              onChange={(e) => { const next = e.target.checked ? [...sel, o] : sel.filter((x) => x !== o); onChange(next); onCommit(next); }} />
            {o}
          </label>
        ))}
      </div>
    );
  }
  if (f.type === "select" || f.type === "radio") {
    return (
      <select className={inputCls} value={typeof value === "string" ? value : ""} onChange={(e) => { onChange(e.target.value || null); onCommit(e.target.value || null); }}>
        <option value="">-</option>
        {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }
  const str = typeof value === "string" ? value : "";
  if (f.type === "textarea" || f.narrative) {
    return (
      <div className="space-y-1">
        <textarea rows={Math.min(10, Math.max(3, Math.ceil(str.length / 90)))} className={inputCls} value={str} maxLength={f.maxlen ?? undefined}
          onChange={(e) => onChange(e.target.value)} onBlur={(e) => onCommit(e.target.value)} />
        {hasPlaceholder(str) && <Placeholders text={str} />}
      </div>
    );
  }
  return (
    <input className={inputCls} type={f.type === "email" ? "email" : f.type === "date" ? "date" : "text"} value={str} maxLength={f.maxlen ?? undefined}
      onChange={(e) => onChange(e.target.value)} onBlur={(e) => onCommit(e.target.value)} />
  );
}

function FieldRow({ f, appId, onSaved }: { f: FilledField; appId: string; onSaved: (o: ApplicationOut) => void }) {
  const [value, setValue] = useState<FieldValue>(f.value);
  const [saving, setSaving] = useState(false);
  useEffect(() => setValue(f.value), [f.value]);

  async function patch(edit: { value?: FieldValue; confirmed?: boolean; acknowledged_blank?: boolean }) {
    setSaving(true);
    try {
      onSaved(await api.editApplication(appId, [{ field_id: f.field_id, ...edit }]));
    } finally {
      setSaving(false);
    }
  }
  const commit = (v: FieldValue) => {
    if (JSON.stringify(v) !== JSON.stringify(f.value)) patch({ value: v });
  };
  const empty = value === null || value === "" || (Array.isArray(value) && value.length === 0);
  const str = typeof value === "string" ? value : "";

  return (
    <div id={`f-${f.field_id}`} className={cx("rounded-lg border-l-4 bg-white p-4 shadow-sm",
      f.status === "green" ? "border-emerald-500" : f.status === "amber" ? "border-amber-400" : "border-rose-500")}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-medium text-ink">{f.label}{f.required && <span className="text-rose-600"> *</span>}</span>
        <Chip tone={STATUS_TONE[f.status]}>{STATUS_TEXT[f.status]}</Chip>
        {(f.source === "llm" || f.source === "template" || f.source === "user") && <Chip>{SOURCE_TEXT[f.source]}</Chip>}
        {f.narrative && <Chip tone="violet">narrative draft</Chip>}
        {saving && <Spinner className="text-ink-muted" />}
      </div>
      <FieldInput f={f} value={value} onChange={setValue} onCommit={commit} />
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
        {f.rationale && <span>{f.rationale}</span>}
        {f.maxlen && typeof value === "string" && <span className="tabular-nums">{str.length}/{f.maxlen}</span>}
      </div>
      {f.warnings.map((w) => <p key={w} className="mt-1 text-xs text-amber-800">⚠ {w}</p>)}
      <div className="mt-2 flex flex-wrap gap-3">
        {f.status === "amber" && !hasPlaceholder(str) && (
          <label className="flex items-center gap-1.5 text-xs font-medium text-ink">
            <input type="checkbox" className="accent-emerald-600" checked={f.confirmed} onChange={(e) => patch({ confirmed: e.target.checked })} />
            I’ve checked this value
          </label>
        )}
        {f.status === "red" && empty && (
          <label className="flex items-center gap-1.5 text-xs font-medium text-ink">
            <input type="checkbox" className="accent-slate-600" checked={f.acknowledged_blank} onChange={(e) => patch({ acknowledged_blank: e.target.checked })} />
            Leave blank intentionally{f.type === "signature" ? " (I'll sign the official form)" : ""}
          </label>
        )}
      </div>
    </div>
  );
}

function ApplicantPanel({ applicant, setApplicant }: { applicant: Applicant; setApplicant: (a: Applicant) => void }) {
  const fields: [keyof Applicant, string][] = [["name", "Full name"], ["position", "Position"], ["organization", "Organisation"], ["email", "Email"], ["phone", "Phone"], ["address", "Address"]];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fields.map(([k, label]) => (
        <div key={k}>
          <Label>{label}</Label>
          <input className={inputCls} value={applicant[k] ?? ""} onChange={(e) => setApplicant({ ...applicant, [k]: e.target.value })} />
        </div>
      ))}
    </div>
  );
}

function ApplyInner({ grantId }: { grantId: string }) {
  const router = useRouter();
  const search = useSearchParams();
  const appParam = search.get("app");
  const [profile, , loaded] = useProfile();
  const [savedApplicant, setSavedApplicant] = useApplicant();
  const [applicant, setApplicantState] = useState<Applicant>({});
  useEffect(() => { if (savedApplicant) setApplicantState(savedApplicant); }, [savedApplicant]);

  const grant = useQuery({ queryKey: ["grant", grantId], queryFn: () => api.grant(grantId) });
  const form = useQuery({ queryKey: ["form", grantId], queryFn: () => api.grantForm(grantId), enabled: !!grant.data?.form_url, retry: false });
  const [uploaded, setUploaded] = useState<FormTemplate | null>(null);
  const [out, setOut] = useState<ApplicationOut | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [attest, setAttest] = useState(false);
  const [reviewProblems, setReviewProblems] = useState<ApplicationOut["problems"] | null>(null);

  useEffect(() => {
    if (appParam && !out) api.application(appParam).then(setOut).catch(() => router.replace(`/apply/${grantId}`));
  }, [appParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const template = uploaded ?? form.data ?? out?.template ?? null;

  async function generate() {
    if (!profile) return;
    setBusy("Pre-filling from your profile…");
    setErr(null);
    try {
      setSavedApplicant(applicant);
      const o = await api.createApplication({ grant_id: grantId, template_id: uploaded?.id, profile, applicant });
      setOut(o);
      router.replace(`/apply/${grantId}?app=${o.application.id}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function upload(file: File) {
    setBusy("Extracting fields from your form…");
    setErr(null);
    try {
      setUploaded(await api.uploadForm(file));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function review() {
    if (!out) return;
    setReviewProblems(null);
    try {
      setOut(await api.review(out.application.id, attest));
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setReviewProblems(e.body?.problems ?? []);
      else setErr((e as Error).message);
    }
  }

  if (!loaded || grant.isLoading) return <Card className="flex items-center gap-2"><Spinner /> Loading…</Card>;
  if (!grant.data) return <Empty title="Opportunity not found" />;
  const g = grant.data;
  const app = out?.application;
  const s = out?.summary;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Application pre-fill" title={g.title}>
        <span className="text-ink-muted">{g.funder_name}</span>
      </PageHeader>
      <GrantMeta g={g} />
      <Notice tone="blue">
        <strong>Nothing is ever submitted for you.</strong> Every field is marked green (from your profile), amber (inferred or drafted - verify)
        or red (needs you). Narrative answers are scaffolds with explicit <mark className="placeholder-mark">[YOU MUST ADD: …]</mark> gaps - we never invent
        technical claims. Export unlocks only after you’ve reviewed everything.
      </Notice>
      {g.raw.form_note && <Notice>{g.raw.form_note}</Notice>}
      {!profile && <Notice tone="red">Build your <a className="underline" href="/profile">profile</a> first - the draft is filled from it.</Notice>}

      {!app && (
        <Card className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-ink">Form</p>
              {form.isLoading && <p className="flex items-center gap-2 text-sm text-ink-muted"><Spinner /> Fetching and parsing the funder’s form…</p>}
              {template ? (
                <p className="text-sm text-ink-soft">
                  {template.title || "Untitled form"} · {template.fields.length} fields · {template.kind.replace("_", " ")} · extracted via {template.extraction}
                  {template.form_url.startsWith("local:") && (
                    <> · <a className="underline" target="_blank" rel="noreferrer" href={`${API_URL}/demo-forms/${template.form_url.slice(6)}`}>view original</a></>
                  )}
                </p>
              ) : !form.isLoading && <p className="text-sm text-ink-soft">No public form on file for this funder. Upload the PDF or HTML form you downloaded from them.</p>}
            </div>
            <label className="cursor-pointer text-sm font-semibold text-brand-700 hover:underline">
              Upload a form (PDF / HTML)
              <input type="file" accept=".pdf,.html,.htm,application/pdf,text/html" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            </label>
          </div>
          <details className="rounded-lg border border-slate-200 p-3" open={!savedApplicant}>
            <summary className="cursor-pointer text-sm font-semibold text-ink">Your contact details (stored in this browser; sent only to fill this draft)</summary>
            <div className="mt-3"><ApplicantPanel applicant={applicant} setApplicant={setApplicantState} /></div>
          </details>
          <div className="flex items-center gap-3">
            <Button disabled={!template || !profile || !!busy} onClick={generate}>Generate pre-filled draft</Button>
            {busy && <span className="flex items-center gap-2 text-sm text-ink-muted"><Spinner /> {busy}</span>}
          </div>
          {err && <Notice tone="red">{err}</Notice>}
        </Card>
      )}

      {app && s && out && (
        <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
          <div className="space-y-3">
            {app.fields.map((f) => <FieldRow key={f.field_id} f={f} appId={app.id} onSaved={setOut} />)}
          </div>
          <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
            <Card>
              <p className="text-3xl font-bold text-ink">{Math.round(((s.green + s.amber) / s.total) * 100)}%</p>
              <p className="text-sm text-ink-muted">pre-filled ({s.total} fields)</p>
              <div className="mt-3 flex h-2 overflow-hidden rounded-full">
                <div className="bg-emerald-500" style={{ width: `${(s.green / s.total) * 100}%` }} />
                <div className="bg-amber-400" style={{ width: `${(s.amber / s.total) * 100}%` }} />
                <div className="bg-rose-500" style={{ width: `${(s.red / s.total) * 100}%` }} />
              </div>
              <div className="mt-2 flex justify-between text-xs text-ink-muted">
                <span>{s.green} green</span><span>{s.amber} amber</span><span>{s.red} red</span>
              </div>
              {app.llm_used && <p className="mt-2 text-xs text-violet-700">Claude inferred some amber values.</p>}
            </Card>
            <Card>
              <p className="font-semibold text-ink">Review</p>
              {out.problems.length > 0 ? (
                <>
                  <p className="text-sm text-ink-muted">{out.problems.length} item{out.problems.length > 1 ? "s" : ""} need you before export:</p>
                  <ul className="mt-2 max-h-56 space-y-1 overflow-auto text-xs">
                    {out.problems.map((p) => (
                      <li key={p.field_id ?? p.label}><a href={`#f-${p.field_id}`} className="text-brand-700 hover:underline">{p.label}</a> <span className="text-ink-muted">- {p.problem}</span></li>
                    ))}
                  </ul>
                </>
              ) : <p className="text-sm text-emerald-700">Every field is resolved.</p>}
              <label className="mt-3 flex gap-2 text-xs text-ink">
                <input type="checkbox" className="mt-0.5 accent-brand-600" checked={attest} onChange={(e) => setAttest(e.target.checked)} />
                I have reviewed every field and I am responsible for this application. SCI Protocol will not submit it.
              </label>
              <div className="mt-3"><Button disabled={!attest || app.reviewed} onClick={review}>{app.reviewed ? "Reviewed ✓" : "Complete review"}</Button></div>
              {reviewProblems && reviewProblems.length > 0 && <p className="mt-2 text-xs text-rose-700">Still {reviewProblems.length} item(s) to resolve.</p>}
            </Card>
            <Card>
              <p className="font-semibold text-ink">Export</p>
              {!app.reviewed && <p className="text-xs text-ink-muted">Locked until review is complete.</p>}
              <div className="mt-2 flex flex-col gap-2">
                {out.template.kind === "pdf_acroform" && <ExportLink ok={app.reviewed} href={api.exportUrl(app.id, "pdf")}>Filled PDF</ExportLink>}
                <ExportLink ok={app.reviewed} href={api.exportUrl(app.id, "md")}>Copy-paste pack (.md)</ExportLink>
                {out.template.kind === "html_form" && <ExportLink ok={app.reviewed} href={api.exportUrl(app.id, "json")}>Web-form payload (.json)</ExportLink>}
              </div>
            </Card>
          </aside>
        </div>
      )}
    </div>
  );
}

function ExportLink({ ok, href, children }: { ok: boolean; href: string; children: ReactNode }) {
  return ok
    ? <a href={href} className="rounded-lg border border-slate-300 px-3 py-2 text-center text-sm font-semibold text-ink hover:bg-slate-50">{children}</a>
    : <span className="rounded-lg border border-dashed border-slate-200 px-3 py-2 text-center text-sm text-slate-400">{children}</span>;
}

export default function ApplyPage({ params }: { params: { id: string } }) {
  return <Suspense><ApplyInner grantId={params.id} /></Suspense>;
}
