import type { Metadata } from "next";

import { ProjectDetail } from "@/components/app/project-detail";

export const metadata: Metadata = { title: "Project" };

export default function ProjectPage() {
  return <ProjectDetail />;
}
