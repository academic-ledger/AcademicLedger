import { handlers } from "@/auth";

// pg (and thus the users/orcid_works writes in the signIn event) needs the Node runtime.
export const runtime = "nodejs";

export const { GET, POST } = handlers;
