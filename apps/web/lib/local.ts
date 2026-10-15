"use client";

import type { Applicant, ProjectProfile } from "@sci/shared";
import { useCallback, useEffect, useState } from "react";

/**
 * Everything the researcher enters stays in this browser. The profile (controlled vocabulary only)
 * is sent to the API for matching; private keywords never are; applicant contact details are sent
 * only when generating an application draft.
 */
const KEYS = { profile: "sci.profile.v1", keywords: "sci.keywords.v1", applicant: "sci.applicant.v1" } as const;

function read<T>(key: string): T | null {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
    window.dispatchEvent(new Event("sci-local"));
  } catch {
    /* private mode / storage disabled: the session still works, it just won't persist */
  }
}

function useLocal<T>(key: string): [T | null, (v: T | null) => void, boolean] {
  const [value, setValue] = useState<T | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const sync = () => setValue(read<T>(key));
    sync();
    setLoaded(true);
    window.addEventListener("sci-local", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("sci-local", sync);
      window.removeEventListener("storage", sync);
    };
  }, [key]);
  const set = useCallback((v: T | null) => write(key, v), [key]);
  return [value, set, loaded];
}

export const useProfile = () => useLocal<ProjectProfile>(KEYS.profile);
export const useKeywords = () => useLocal<string[]>(KEYS.keywords);
export const useApplicant = () => useLocal<Applicant>(KEYS.applicant);
