import type { Metadata } from "next";

import { NewProjectFlow } from "@/components/upload/new-project-flow";

export const metadata: Metadata = { title: "New project" };

export default function NewProjectPage() {
  return (
    <div className="pt-6">
      <h1 className="text-center text-5xl font-extrabold tracking-tight">
        New <span className="gradient-text">project</span>
      </h1>
      <p className="mt-2 mb-10 text-center text-muted">
        Upload a video. Everything else is automatic.
      </p>
      <NewProjectFlow />
    </div>
  );
}
