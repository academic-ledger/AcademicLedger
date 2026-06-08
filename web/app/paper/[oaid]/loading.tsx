import Brand from "@/components/Brand";
import { SkeletonPaper } from "@/components/Skeleton";

export default function Loading() {
  return (
    <>
      <div className="routebar" />
      <Brand />
      <SkeletonPaper />
    </>
  );
}
