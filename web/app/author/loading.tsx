import Brand from "@/components/Brand";
import { SkeletonAuthor } from "@/components/Skeleton";

export default function Loading() {
  return (
    <>
      <div className="routebar" />
      <Brand active="author" />
      <SkeletonAuthor />
    </>
  );
}
