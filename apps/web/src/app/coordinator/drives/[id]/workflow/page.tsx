"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";

export default function WorkflowRedirectPage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const router = useRouter();

  useEffect(() => {
    if (driveId) {
      router.replace(`/coordinator/drives/${driveId}/intake`);
    } else {
      router.replace("/coordinator/drives");
    }
  }, [driveId, router]);

  return (
    <CoordinatorShell>
      <div className="py-20 text-center font-body text-xs text-slate">
        Redirecting to Drive Intake Workspace...
      </div>
    </CoordinatorShell>
  );
}
