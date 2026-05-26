"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import { TabBar } from "@/components/tab-bar";
import { ActiveJobs } from "@/components/active-jobs";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setOk(true);
  }, [router]);

  if (!ok) return <div className="min-h-dvh bg-bg" />;

  return (
    <div className="mx-auto min-h-dvh max-w-md pb-28">
      {children}
      <ActiveJobs />
      <TabBar />
    </div>
  );
}
