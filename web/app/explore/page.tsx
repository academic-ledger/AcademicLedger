import { Suspense } from "react";
import Brand from "@/components/Brand";
import ExploreClient from "@/components/ExploreClient";

export const dynamic = "force-dynamic";

export default function ExplorePage() {
  return (
    <>
      <Brand active="explore" />
      <Suspense>
        <ExploreClient />
      </Suspense>
    </>
  );
}
