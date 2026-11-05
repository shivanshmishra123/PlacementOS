"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { CoordinatorShell } from "../../../../components/CoordinatorShell";

export default function ExceptionDetailRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <CoordinatorShell>
      <div className="py-20 text-center font-body text-xs text-slate">
        Redirecting to Operations Dashboard...
      </div>
    </CoordinatorShell>
  );
}
