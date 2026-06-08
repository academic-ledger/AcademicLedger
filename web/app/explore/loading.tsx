import Brand from "@/components/Brand";
import { SkeletonTable } from "@/components/Skeleton";

export default function Loading() {
  return (
    <>
      <div className="routebar" />
      <Brand active="explore" />
      <div className="wrap-explore">
        <h1>Explore the Ledger</h1>
        <p className="lede">Loading the Ledger…</p>
        <SkeletonTable rows={12} />
      </div>
    </>
  );
}
