"use client";

import { Sidebar, OctopusIcon } from "@/components/dashboard/Sidebar";
import { useSession } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  if (isPending) {
    return (
      <div className="min-h-screen bg-[#020202] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="min-h-screen bg-[#020202] flex relative">
      <Sidebar 
        isMobileOpen={isMobileOpen} 
        setIsMobileOpen={setIsMobileOpen} 
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
      />
      <div className={`flex-1 flex flex-col transition-all duration-300 ${isCollapsed ? 'md:pl-16' : 'md:pl-[280px]'}`}>
         {/* Desktop Logo - visible when sidebar is collapsed */}
         {isCollapsed && (
            <div className="fixed top-6 left-[80px] hidden md:flex items-center gap-3 z-40 animate-in fade-in slide-in-from-left-4 duration-300">
                <OctopusIcon className="w-6 h-6 text-orange-500" />
                <span className="font-bold text-lg text-white tracking-tight">fixora</span>
            </div>
         )}

         {/* Mobile Header */}
         <header className="md:hidden h-14 border-b border-white/5 flex items-center px-4 bg-[#0C0C0E]">
            <button onClick={() => setIsMobileOpen(true)} className="p-2 text-zinc-400">
               <span className="sr-only">Open sidebar</span>
               <div className="w-5 h-0.5 bg-current mb-1" />
               <div className="w-5 h-0.5 bg-current mb-1" />
               <div className="w-5 h-0.5 bg-current" />
            </button>
            <div className="flex items-center gap-2 ml-4">
              <OctopusIcon className="w-5 h-5 text-orange-500" />
              <span className="font-bold text-white">fixora</span>
            </div>
         </header>
         {children}
      </div>
    </div>
  );
}
