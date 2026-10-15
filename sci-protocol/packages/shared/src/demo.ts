import persona from "../../../data/demo/persona.json";
import type { Applicant, ProjectProfile } from "./types";

/** The demo researcher from data/demo/persona.json (also used by the API tests). */
export const DEMO_PERSONA = persona as unknown as { profile: ProjectProfile; keywords: string[]; applicant: Applicant };
