import { JobsTable } from "@/components/dashboard/jobs/JobsTable";

export default function JobsPage() {
  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 px-6 py-12">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-widest">Session history</p>
            <h1 className="text-2xl font-bold text-white">All jobs</h1>
          </div>
        </div>
        <JobsTable />
      </div>
    </div>
  );
}
