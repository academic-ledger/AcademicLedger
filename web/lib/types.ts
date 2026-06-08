import type { QalPoint } from "./qal";

// One reference-class view of a paper (field cohort OR co-citation neighborhood).
export interface MetricView {
  obs: number;
  calibrated: boolean;
  qal: QalPoint | null; // null when calibration-pending
  n?: number; // neighborhood size (neighborhood metric only)
}

export interface Metrics {
  field: MetricView | null; // single OpenAlex subfield cohort
  synthetic: MetricView | null; // the synthetic field — official reference class (§5)
  official: "field" | "synthetic";
}

// One row of the shared record list (explore + author tables consume this).
export interface RecordItem {
  oaid: string;
  title: string;
  authors: string | null;
  venue: string | null;
  year: number | null;
  cites: number;
  sid: string | null; // subfield id, e.g. "1803"
  subfield: string | null; // subfield label
  field: string | null; // field label
  oa: boolean;
  doi: string | null;
  retracted: boolean;
  obs: number | null; // official observed percentile (neighborhood when present, else field)
  calibrated: boolean;
  qal: QalPoint | null; // official QaL; null when calibration-pending
  metrics: Metrics | null; // both reference classes (field + co-citation neighborhood)
}

export interface AuthorHeader {
  name: string;
  aff: string | null;
  orcid: string | null;
  oaid: string;
  works_count: number;
  cites: number;
  seed: string[];
}

export interface AuthorPayload {
  author: AuthorHeader;
  works: RecordItem[];
}
