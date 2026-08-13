"use client";

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, FileCode, Terminal, Cpu, Zap, Loader2, AlertCircle, User, ExternalLink, GitPullRequest } from 'lucide-react';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { useSession } from '@/lib/auth-client';
import { getSocket } from '@/lib/socket';

interface JobLogMetadata {
  file_path?: string;
  new_content?: string;
  repo?: string;
  url?: string;
  pr_url?: string;
  pr_number?: number;
  pr_title?: string;
  branch?: string;
}

interface JobLogEntry {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  type: 'message' | 'command' | 'file_change' | 'error' | 'info' | 'screenshot' | 'pr_created';
  content: string;
  metadata?: JobLogMetadata;
  createdAt: string;
}

interface FileChange {
  path: string;
  content: string;
  reason: string;
  timestamp: string;
}

function formatMarkdown(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-zinc-200">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-zinc-800 text-orange-400 px-1.5 py-0.5 rounded text-xs">$1</code>')
    .replace(/\n/g, '<br />');
}

function isFileChangeEntry(log: JobLogEntry): boolean {
  return (log.type === 'file_change' || !!log.metadata?.file_path) && !!log.metadata?.new_content;
}

function toFileChange(log: JobLogEntry): FileChange {
  return {
    path: log.metadata!.file_path as string,
    content: log.metadata!.new_content as string,
    reason: log.content,
    timestamp: log.createdAt,
  };
}

function renderLogIcon(log: JobLogEntry) {
  if (log.type === 'command') return <Terminal className="w-4 h-4" />;
  if (log.type === 'file_change') return <FileCode className="w-4 h-4" />;
  if (log.type === 'error') return <AlertCircle className="w-4 h-4" />;
  if (log.role === 'user') return <User className="w-4 h-4" />;
  return <Cpu className="w-4 h-4" />;
}

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { data: session } = useSession();
  
  const [logs, setLogs] = useState<JobLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [fileChanges, setFileChanges] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchLogs(): Promise<void> {
      try {
        const res = await fetch(`/api/jobs/${jobId}/feed`);
        if (!res.ok) throw new Error('Failed to fetch logs');
        const data = await res.json();

        if (isMounted) {
          setLogs(data.entries || []);

          const changes: FileChange[] = [];
          const seenPaths = new Set<string>();

          [...(data.entries || [])].reverse().forEach(function deduplicateFileChanges(log: JobLogEntry) {
            if (isFileChangeEntry(log)) {
              const path = log.metadata!.file_path as string;
              if (!seenPaths.has(path)) {
                changes.push(toFileChange(log));
                seenPaths.add(path);
              }
            }
          });

          setFileChanges(changes);
          if (!selectedFile && changes.length > 0) {
            setSelectedFile(changes[0].path);
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchLogs();

    const socket = getSocket();

    socket.emit('join_job', { jobId });

    function handleJobLog(data: { jobId: string; entry: JobLogEntry }) {
      if (data.jobId !== jobId) return;

      setLogs(function appendIfNew(prev) {
        if (prev.some(l => l.id === data.entry.id)) return prev;
        return [...prev, data.entry];
      });

      const log = data.entry;
      if (!isFileChangeEntry(log)) return;

      const path = log.metadata!.file_path as string;
      const newChange = toFileChange(log);

      setFileChanges(function upsertChange(prev) {
        const index = prev.findIndex(f => f.path === path);
        if (index !== -1) {
          const updated = [...prev];
          updated[index] = newChange;
          return updated;
        }
        if (!selectedFile) setSelectedFile(path);
        return [...prev, newChange];
      });
    }

    socket.on('job_log', handleJobLog);
    socket.on('job_status', function noop() {});

    return function cleanup() {
      isMounted = false;
      socket.emit('leave_job', { jobId });
      socket.off('job_log', handleJobLog);
      socket.off('job_status');
    };
  }, [jobId, selectedFile]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const selectedFileContent = fileChanges.find(f => f.path === selectedFile)?.content || '';

  return (
    <div className="flex h-screen bg-[#020202] text-zinc-100 overflow-hidden font-modern selection:bg-orange-500/30">
      <main className="flex-1 flex flex-col h-screen relative">
        {/* Modern Top Nav */}
        <header className="h-16 border-b border-zinc-800/50 flex items-center justify-between px-6 bg-black/20 backdrop-blur-xl sticky top-0 z-50">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="flex items-center gap-2 group">
               <div className="w-6 h-6 bg-orange-600 rounded-md flex items-center justify-center transform group-hover:rotate-12 transition-transform shadow-lg shadow-orange-500/20">
                 <span className="text-white text-[10px] font-bold">N</span>
               </div>
               <span className="font-bold text-lg tracking-tight">fixora</span>
            </Link>
            <div className="h-4 w-[1px] bg-zinc-800 mx-2" />
            <span className="text-zinc-500 text-xs font-medium uppercase tracking-widest">Job #{jobId.split('-')[1] || jobId.substring(0,8)}</span>
          </div>

          <div className="flex items-center gap-4">
             {session?.user && (
               <div className="w-8 h-8 rounded-full border border-zinc-800 overflow-hidden bg-zinc-900 flex items-center justify-center">
                 {session.user.image ? (
                   <Image src={session.user.image} alt="User" width={32} height={32} className="object-cover" />
                 ) : (
                   <User className="w-4 h-4 text-zinc-600" />
                 )}
               </div>
             )}
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <div className="w-1/2 flex flex-col border-r border-zinc-800/50 bg-zinc-900/5">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <Terminal className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">Activity log</span>
              </div>
              <Zap className="w-4 h-4 text-zinc-800" />
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8 modern-scrollbar">
              {logs.length === 0 && loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-4">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                  <span className="text-sm text-zinc-600 font-medium uppercase tracking-widest">Connecting to frequency...</span>
                </div>
              ) : logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                   <Terminal className="w-10 h-10 text-zinc-800" />
                   <div className="space-y-1">
                      <p className="text-zinc-500 font-bold uppercase tracking-widest">No activity data</p>
                      <p className="text-[10px] text-zinc-700 font-medium">Ready for transmission</p>
                   </div>
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="group relative">
                    <div className="flex items-start gap-4">
                      <div className="flex-none pt-1">
                        <div className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center border transition-all",
                          log.role === 'user' ? "bg-zinc-900 border-zinc-800 text-zinc-500" : "bg-orange-600/10 border-orange-500/20 text-orange-500"
                        )}>
                          {renderLogIcon(log)}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2 pb-1 border-b border-zinc-800/20">
                          <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">
                            {log.role === 'assistant' ? 'AI Agent' : log.role.toUpperCase()}
                          </span>
                          <span className="text-[10px] text-zinc-700 font-medium">{new Date(log.createdAt).toLocaleTimeString()}</span>
                        </div>

                        {log.type === 'file_change' ? (
                          <div className="bg-orange-500/5 border border-orange-500/10 rounded-xl p-4 group-hover:border-orange-500/30 transition-all">
                             <div className="flex items-center gap-3 mb-2">
                                <FileCode className="w-4 h-4 text-orange-500" />
                                <span className="text-sm font-bold text-orange-400 truncate">{log.metadata?.file_path}</span>
                             </div>
                             <p className="text-xs text-zinc-400 mb-4 line-clamp-2">{log.content}</p>
                             <button
                                onClick={() => {
                                   if (log.metadata?.file_path) {
                                      setSelectedFile(log.metadata.file_path);
                                   }
                                }}
                                className="flex items-center gap-2 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest transition-colors"
                             >
                                View diff <ArrowLeft className="w-3 h-3 rotate-180" />
                             </button>
                             <div className="text-zinc-500 mt-3 font-mono text-[9px] uppercase flex items-center gap-2">
                                <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-500 rounded border border-orange-500/20">Job #{jobId.slice(0, 8)}</span>
                                <span>•</span>
                                <span>{log.metadata?.repo || 'codebase'}</span>
                             </div>
                          </div>
                        ) : log.type === 'pr_created' ? (
                          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-5 group-hover:border-emerald-500/40 transition-all">
                             <div className="flex items-center gap-3 mb-3">
                                <GitPullRequest className="w-5 h-5 text-emerald-500" />
                                <span className="text-sm font-bold text-emerald-400">Pull Request Created</span>
                             </div>
                             <h3 className="text-base font-semibold text-zinc-200 mb-2">{log.metadata?.pr_title}</h3>
                             {log.metadata?.branch && (
                               <div className="flex items-center gap-2 mb-3">
                                 <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">{log.metadata.branch}</span>
                                 <span className="text-zinc-600 text-xs">→</span>
                                 <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">main</span>
                               </div>
                             )}
                             <div
                               className="text-xs text-zinc-500 mb-4 whitespace-pre-wrap line-clamp-4"
                               dangerouslySetInnerHTML={{ __html: formatMarkdown(log.content || '') }}
                             />
                             {log.metadata?.pr_url && (
                               <a
                                 href={log.metadata.pr_url}
                                 target="_blank"
                                 rel="noopener noreferrer"
                                 className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors"
                               >
                                 <GitPullRequest className="w-3.5 h-3.5" />
                                 View PR #{log.metadata.pr_number}
                                 <ExternalLink className="w-3 h-3" />
                               </a>
                             )}
                          </div>
                        ) : log.type === 'command' ? (
                          <div className="font-mono text-xs text-orange-400 bg-orange-600/5 border border-orange-500/10 rounded-lg px-4 py-3">
                             <span className="text-orange-900 mr-2">$</span> {log.content}
                          </div>
                        ) : log.type === 'screenshot' ? (
                          <div className="mt-2 rounded-xl overflow-hidden border border-zinc-800 bg-black/40">
                             <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
                                <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[200px]">{log.metadata?.url}</span>
                                <a href={log.content} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-wider">
                                   Full Size <ExternalLink className="w-3 h-3" />
                                </a>
                             </div>
                             <div className="relative aspect-video bg-zinc-900/20">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={log.content}
                                  alt="Screenshot"
                                  className="absolute inset-0 w-full h-full object-contain"
                                />
                             </div>
                          </div>
                        ) : (
                          <div
                            className={cn(
                              "text-sm leading-relaxed whitespace-pre-wrap font-medium prose-invert",
                              log.type === 'error' ? "text-red-400" : "text-zinc-400"
                            )}
                            dangerouslySetInnerHTML={{ __html: formatMarkdown(log.content || '') }}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>

          <div className="w-1/2 flex flex-col bg-zinc-900/10">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <FileCode className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">Modified files ({fileChanges.length})</span>
              </div>
            </div>

            <div className="flex-1 flex flex-col overflow-hidden relative">
               {fileChanges.length === 0 ? (
                 <div className="flex-1 flex flex-col items-center justify-center p-12 gap-4">
                    <Loader2 className="w-6 h-6 text-zinc-800 animate-spin" />
                    <span className="text-xs text-zinc-700 font-medium uppercase tracking-widest">Awaiting payload</span>
                 </div>
               ) : (
                 <>
                   <div className="flex overflow-x-auto bg-zinc-900/30 scrollbar-hide border-b border-zinc-800/50">
                     {fileChanges.map(file => (
                       <button
                         key={file.path}
                         onClick={() => setSelectedFile(file.path)}
                         className={cn(
                           "px-6 py-3 text-xs font-semibold whitespace-nowrap transition-all relative",
                           selectedFile === file.path
                             ? "text-white bg-zinc-900/50"
                             : "text-zinc-600 hover:text-zinc-400"
                         )}
                       >
                         {file.path.split('/').pop()}
                         {selectedFile === file.path && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-600 rounded-full" />
                         )}
                       </button>
                     ))}
                   </div>

                   <div className="flex-1 overflow-auto bg-[#0d1117] relative group border-t border-zinc-800/20">
                     <pre className="p-0 m-0">
                       <code className="block text-[13px] leading-[20px]" style={{ fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace' }}>
                         {selectedFileContent.split('\n').map((line, i) => (
                           <div key={i} className="flex hover:bg-[#161b22] transition-colors">
                             <span className="select-none text-[#484f58] text-right min-w-[50px] px-[10px] py-0 inline-block">{i + 1}</span>
                             <span className="text-[#e6edf3] px-3 flex-1">{line || ' '}</span>
                           </div>
                         ))}
                       </code>
                     </pre>
                   </div>
                 </>
               )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
