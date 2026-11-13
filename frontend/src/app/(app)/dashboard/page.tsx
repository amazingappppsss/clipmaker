import type { Metadata } from "next";

import { ProjectList } from "@/components/app/project-list";

export const metadata: Metadata = { title: "Projects" };

export default function DashboardPage() {
  return <ProjectList />;
}
