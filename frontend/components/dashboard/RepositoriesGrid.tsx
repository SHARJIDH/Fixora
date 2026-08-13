"use client";

import { GitBranch, Lock, Globe, ExternalLink, Plus, Loader2 } from "lucide-react";
import Link from "next/link";

interface Repository {
  id: string;
  name: string;
  fullName: string;
  description: string | null;
  isPrivate: boolean;
  htmlUrl: string;
  language: string | null;
  defaultBranch: string | null;
}

interface RepositoriesGridProps {
  repositories: Repository[];
  loading?: boolean;
  onConnect?: () => void;
}

const languageColors: Record<string, string> = {
  TypeScript: "bg-blue-500",
  JavaScript: "bg-yellow-500",
  Python: "bg-green-500",
  Go: "bg-cyan-500",
  Rust: "bg-orange-500",
  Java: "bg-red-500",
  Ruby: "bg-red-400",
  PHP: "bg-purple-500",
  C: "bg-gray-500",
  "C++": "bg-pink-500",
  "C#": "bg-purple-400",
};

export function RepositoriesGrid({ repositories, loading, onConnect }: RepositoriesGridProps) {
  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm font-medium">Fetching repositories...</span>
      </div>
    );
  }

  if (repositories.length === 0) {
    return (
      <div className="bg-zinc-900/10 border-2 border-dashed border-zinc-800/50 p-20 rounded-[2rem] text-center">
        <div className="w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mx-auto mb-6 transform hover:rotate-12 transition-transform">
          <Plus className="w-8 h-8 text-orange-500" />
        </div>
        <h3 className="text-xl font-bold text-zinc-100 mb-2">No repositories connected</h3>
        <p className="text-zinc-500 text-sm font-medium mb-8 max-w-xs mx-auto">
          Connect your GitHub account to start automating your workflow with Fixora.
        </p>
        {onConnect && (
          <button
            onClick={onConnect}
            className="inline-flex items-center gap-2 px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-orange-500/10"
          >
            Connect First Repository
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-zinc-500" />
          </div>
          <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-tight">Connected Repositories ({repositories.length})</h2>
        </div>
        <button 
          onClick={onConnect}
          className="text-xs font-bold text-orange-400 hover:text-orange-300 transition-colors flex items-center gap-1.5"
        >
          Add more <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {repositories.map((repo) => (
          <div
            key={repo.id}
            className="group modern-card p-6 flex flex-col justify-between hover:border-orange-500/30 transition-all cursor-pointer relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/5 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
            
            <div className="relative z-10">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center group-hover:border-orange-500/20 group-hover:bg-orange-500/5 transition-all">
                    {repo.isPrivate ? (
                      <Lock className="w-5 h-5 text-zinc-600 group-hover:text-orange-500/60" />
                    ) : (
                      <Globe className="w-5 h-5 text-orange-500/40 group-hover:text-orange-500/60" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-zinc-100 truncate group-hover:text-orange-400 transition-colors">
                      {repo.name}
                    </h3>
                    <p className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest mt-0.5">
                      {repo.fullName.split('/')[0]}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Description */}
              <p className="text-xs text-zinc-500 font-medium leading-relaxed mb-6 line-clamp-2 h-8">
                {repo.description || "No description provided for this repository."}
              </p>
            </div>
            
            {/* Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-zinc-800/50 relative z-10">
              <div className="flex items-center gap-1.5">
                {repo.language && (
                  <>
                    <span className={`w-1.5 h-1.5 rounded-full ${languageColors[repo.language] || "bg-zinc-700"}`} />
                    <span className="text-[10px] font-bold text-zinc-600 uppercase">{repo.language}</span>
                  </>
                )}
              </div>
              
              <a
                href={repo.htmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-2 bg-zinc-900 rounded-lg border border-zinc-800 text-zinc-600 hover:text-zinc-200 hover:border-zinc-700 transition-all opacity-0 group-hover:opacity-100 transform translate-y-2 group-hover:translate-y-0"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
