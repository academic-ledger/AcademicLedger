import type { QalPoint } from "./qal";

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
  obs: number | null; // observed within-(subfield,year) percentile
  calibrated: boolean;
  qal: QalPoint | null; // illustrative; null when calibration-pending
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
