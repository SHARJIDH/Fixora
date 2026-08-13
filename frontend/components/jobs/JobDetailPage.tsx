"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  FileCode,
  Terminal,
  Cpu,
  Zap,
  Loader2,
  AlertCircle,
  ExternalLink,
  Circle,
  User,
} from "lucide-react";
import ReactDiffViewer from "react-diff-viewer-continued";
import { cn } from "@/lib/utils";
import { useSession } from "@/lib/auth-client";
import { getSocket } from "@/lib/socket";

interface JobLogEntry {
  id: string;
  role?: "user" | "assistant" | "system" | "tool";
  type?: "message" | "command" | "file_change" | "error" | "info" | "screenshot";
  content?: string | null;
  metadata?: Record<string, any> | null;
  createdAt?: string | null;
}

interface FileChange {
  path: string;
  content: string | null;
  reason: string;
  timestamp?: string | null;
  patch?: {
    matchPattern?: string;
    replacePattern?: string;
  } | null;
}

const getLogMetadata = (log: JobLogEntry) => {
  if (log.metadata && typeof log.metadata === "object") {
    return log.metadata;
  }
  return {} as Record<string, any>;
};

const getFilePathFromLog = (log: JobLogEntry) => {
  const meta = getLogMetadata(log);
  return meta.file_path || meta.filePath || meta.path || meta.file || null;
};

const getNewContentFromLog = (log: JobLogEntry) => {
  const meta = getLogMetadata(log);
  const candidates = [meta.new_content, meta.newContent, meta.content];
  for (const candidate of candidates) {
    if (typeof candidate === "string") {
      return candidate;
    }
  }
  return null;
};

const getPatchDetailsFromLog = (log: JobLogEntry) => {
  const meta = getLogMetadata(log);
  const matchPattern = meta.match_pattern || meta.matchPattern || null;
  const replacePattern = meta.replace_pattern || meta.replacePattern || null;
  if (!matchPattern && !replacePattern) {
    return null;
  }
  return {
    matchPattern: matchPattern || undefined,
    replacePattern: replacePattern || undefined,
  };
};

const buildFileChanges = (entries: JobLogEntry[]) => {
  const changes: FileChange[] = [];
  const seenPaths = new Set<string>();

  [...entries].reverse().forEach((log) => {
    const path = getFilePathFromLog(log);
    if (!path || seenPaths.has(path)) {
      return;
    }

    const newContent = getNewContentFromLog(log);
    const patch = getPatchDetailsFromLog(log);
    const hasFileChangeSignal = log.type === "file_change" || newContent !== null || patch !== null;

    if (!hasFileChangeSignal) {
      return;
    }

    changes.push({
      path,
      content: newContent,
      reason: log.content || `Updated ${path}`,
      timestamp: log.createdAt || undefined,
      patch,
    });
    seenPaths.add(path);
  });

  return changes;
};

const formatTime = (timestamp?: string | null) => {
  if (!timestamp) return "--";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString();
};

const buildLegacyEntries = (jobId: string, legacy: any): JobLogEntry[] => {
  const entries: JobLogEntry[] = [];
  const rawLogs = Array.isArray(legacy?.logs) ? legacy.logs : [];
  const validationLogs = Array.isArray(legacy?.validationLogs) ? legacy.validationLogs : [];

  rawLogs.forEach((content: string, index: number) => {
    entries.push({
      id: `legacy-${jobId}-${index}`,
      role: "system",
      type: "info",
      content,
    });
  });

  validationLogs.forEach((content: string, index: number) => {
    entries.push({
      id: `legacy-${jobId}-validation-${index}`,
      role: "system",
      type: "info",
      content: `Validation: ${content}`,
    });
  });

  return entries;
};

export default function JobDetailPage() {
  const params = useParams();
  const jobIdParam = params?.id as string | string[] | undefined;
  const jobId = Array.isArray(jobIdParam) ? jobIdParam[0] : jobIdParam || "";
  const { data: session } = useSession();

  const [logs, setLogs] = useState<JobLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [fileChanges, setFileChanges] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("processing");

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLogs([]);
    setFileChanges([]);
    setSelectedFile(null);
    setLoading(true);
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;

    let isMounted = true;

    const fetchLogs = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}/feed`);
        if (!res.ok) throw new Error("Failed to fetch logs");
        const data = await res.json();
        let entries: JobLogEntry[] = Array.isArray(data.entries) ? data.entries : [];

        if (entries.length === 0) {
          const legacyRes = await fetch(`/api/jobs/${jobId}/logs`);
          if (legacyRes.ok) {
            const legacyData = await legacyRes.json();
            entries = buildLegacyEntries(jobId, legacyData);
          }
        }

        if (isMounted) {
          setLogs(entries || []);
          const changes = buildFileChanges(entries || []);
          setFileChanges(changes);
          if (!selectedFile && changes.length > 0) {
            setSelectedFile(changes[0].path);
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchLogs();

    const socket = getSocket();

    socket.emit("join_job", { jobId });

    socket.on("job_log", (data: { jobId: string; entry: JobLogEntry }) => {
      if (data.jobId === jobId) {
        setLogs((prev) => {
          if (prev.some((l) => l.id === data.entry.id)) return prev;
          return [...prev, data.entry];
        });

        const log = data.entry;
        const path = getFilePathFromLog(log);
        const newContent = getNewContentFromLog(log);
        const patch = getPatchDetailsFromLog(log);
        const hasFileChangeSignal = log.type === "file_change" || newContent !== null || patch !== null;

        if (path && hasFileChangeSignal) {
          setFileChanges((prev) => {
            const index = prev.findIndex((f) => f.path === path);
            const updated = {
              path,
              content: newContent,
              reason: log.content || `Updated ${path}`,
              timestamp: log.createdAt || undefined,
              patch,
            } as FileChange;

            if (index !== -1) {
              const next = [...prev];
              next[index] = updated;
              return next;
            }

            return [updated, ...prev];
          });

          setSelectedFile((current) => current || path);
        }
      }
    });

    socket.on("job_status", (data: { jobId: string; status: string; stage?: string }) => {
      if (data.jobId === jobId) {
        setJobStatus(data.status);
      }
    });

    return () => {
      isMounted = false;
      socket.emit("leave_job", { jobId });
      socket.off("job_log");
      socket.off("job_status");
    };
  }, [jobId]);

  useEffect(() => {
    if (!fileChanges.length) return;
    if (!selectedFile || !fileChanges.some((file) => file.path === selectedFile)) {
      setSelectedFile(fileChanges[0].path);
    }
  }, [fileChanges, selectedFile]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const selectedFileEntry = useMemo(
    () => fileChanges.find((file) => file.path === selectedFile) || null,
    [fileChanges, selectedFile]
  );

  const selectedFileContent = selectedFileEntry?.content ?? "";
  const selectedFileHasContent = selectedFileEntry?.content !== null && selectedFileEntry?.content !== undefined;

  const visibleLogs = useMemo(() => {
    return logs.filter((log) => {
      const hasContent = typeof log.content === "string" && log.content.trim().length > 0;
      const hasFileMetadata = !!getFilePathFromLog(log);
      const isStructured = log.type === "file_change" || log.type === "command" || log.type === "screenshot";
      return hasContent || hasFileMetadata || isStructured;
    });
  }, [logs]);

  if (!jobId) {
    return (
      <div className="min-h-screen bg-[#020202] text-zinc-100 flex items-center justify-center">
        <p className="text-zinc-500 text-sm">Missing job id.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#020202] text-zinc-100 overflow-hidden font-modern selection:bg-orange-500/30">
      <main className="flex-1 flex flex-col min-h-screen relative">
        {/* Top Bar */}
        <header className="h-14 border-b border-zinc-800/50 flex items-center justify-between px-6 bg-zinc-900/20 sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <Link href="/dashboard/jobs" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1.5">
              <ArrowLeft className="w-3 h-3" /> Jobs
            </Link>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <span className="text-zinc-400 text-xs font-medium uppercase tracking-widest">
              Job #{jobId.split("-")[1] || jobId.substring(0, 8)}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {jobStatus === "processing" || jobStatus === "analyzing" || jobStatus === "generating" ? (
              <div className="flex items-center gap-2 bg-orange-500/10 px-3 py-1.5 border border-orange-500/20 rounded-lg">
                <Loader2 className="w-3 h-3 text-orange-500 animate-spin" />
                <span className="text-[10px] font-bold text-orange-400 uppercase tracking-widest">Processing</span>
              </div>
            ) : jobStatus === "completed" ? (
              <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 border border-emerald-500/20 rounded-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">Completed</span>
              </div>
            ) : jobStatus === "failed" ? (
              <div className="flex items-center gap-2 bg-red-500/10 px-3 py-1.5 border border-red-500/20 rounded-lg">
                <AlertCircle className="w-3 h-3 text-red-500" />
                <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest">Failed</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-zinc-800 px-3 py-1.5 border border-zinc-700 rounded-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{jobStatus}</span>
              </div>
            )}
          </div>
        </header>

        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* Activity Feed Panel */}
          <div className="w-full md:w-1/2 flex flex-col bg-zinc-900/5 min-h-[50vh] md:min-h-0">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <Terminal className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">Activity log</span>
              </div>
              <Zap className="w-4 h-4 text-zinc-800" />
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8 modern-scrollbar">
              {visibleLogs.length === 0 && loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-4">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                  <span className="text-sm text-zinc-600 font-medium uppercase tracking-widest">Connecting to frequency...</span>
                </div>
              ) : visibleLogs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                  <Terminal className="w-10 h-10 text-zinc-800" />
                  <div className="space-y-1">
                    <p className="text-zinc-500 font-bold uppercase tracking-widest">No activity data</p>
                    <p className="text-[10px] text-zinc-700 font-medium">Ready for transmission</p>
                  </div>
                </div>
              ) : (
                visibleLogs.map((log) => {
                  const filePath = getFilePathFromLog(log);
                  const patchDetails = getPatchDetailsFromLog(log);
                  const roleLabel = log.role === "assistant" ? "AI Agent" : log.role ? log.role.toUpperCase() : "SYSTEM";
                  const commandOutput = log.metadata?.output || log.metadata?.result || log.metadata?.stdout;
                  const commandText = log.content || log.metadata?.command || "Command executed";

                  return (
                    <div key={log.id} className="group relative">
                      <div className="flex items-start gap-4">
                        <div className="flex-none pt-1">
                          <div
                            className={cn(
                              "w-8 h-8 rounded-lg flex items-center justify-center border transition-all",
                              log.role === "user"
                                ? "bg-zinc-900 border-zinc-800 text-zinc-500"
                                : "bg-orange-600/10 border-orange-500/20 text-orange-500"
                            )}
                          >
                            {log.type === "command" ? (
                              <Terminal className="w-4 h-4" />
                            ) : log.type === "file_change" ? (
                              <FileCode className="w-4 h-4" />
                            ) : log.type === "error" ? (
                              <AlertCircle className="w-4 h-4" />
                            ) : log.role === "user" ? (
                              <User className="w-4 h-4" />
                            ) : (
                              <Cpu className="w-4 h-4" />
                            )}
                          </div>
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-2 pb-1 border-b border-zinc-800/20">
                            <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">{roleLabel}</span>
                            <span className="text-[10px] text-zinc-700 font-medium">{formatTime(log.createdAt)}</span>
                          </div>

                          {log.type === "file_change" ? (
                            <div className="bg-orange-500/5 border border-orange-500/10 rounded-xl p-4 group-hover:border-orange-500/30 transition-all">
                              <div className="flex items-center gap-3 mb-2">
                                <FileCode className="w-4 h-4 text-orange-500" />
                                <span className="text-sm font-bold text-orange-400 truncate">{filePath || "Unknown file"}</span>
                              </div>
                              <p className="text-xs text-zinc-400 mb-4 line-clamp-2">
                                {log.content || (filePath ? `Updated ${filePath}` : "File change recorded")}
                              </p>
                              {patchDetails && (
                                <div className="space-y-2 text-[10px] text-zinc-500 font-mono mb-4">
                                  {patchDetails.matchPattern && (
                                    <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg p-2">
                                      <div className="uppercase text-[9px] text-zinc-600 mb-1">Match</div>
                                      <div className="whitespace-pre-wrap break-words">{patchDetails.matchPattern}</div>
                                    </div>
                                  )}
                                  {patchDetails.replacePattern && (
                                    <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg p-2">
                                      <div className="uppercase text-[9px] text-zinc-600 mb-1">Replace</div>
                                      <div className="whitespace-pre-wrap break-words">{patchDetails.replacePattern}</div>
                                    </div>
                                  )}
                                </div>
                              )}
                              <button
                                onClick={() => {
                                  if (filePath) {
                                    setSelectedFile(filePath);
                                  }
                                }}
                                className={cn(
                                  "flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest transition-colors",
                                  filePath ? "text-orange-500 hover:text-orange-400" : "text-zinc-600 cursor-not-allowed"
                                )}
                                disabled={!filePath}
                              >
                                View diff <ArrowLeft className="w-3 h-3 rotate-180" />
                              </button>
                              <div className="text-zinc-500 mt-3 font-mono text-[9px] uppercase flex items-center gap-2">
                                <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-500 rounded border border-orange-500/20">
                                  Job #{jobId.slice(0, 8)}
                                </span>
                                <span>•</span>
                                <span>{log.metadata?.repo || "codebase"}</span>
                              </div>
                            </div>
                          ) : log.type === "command" ? (
                            <div className="space-y-3">
                              <div className="font-mono text-xs text-orange-400 bg-orange-600/5 border border-orange-500/10 rounded-lg px-4 py-3">
                                <span className="text-orange-900 mr-2">$</span> {commandText}
                              </div>
                              {commandOutput && (
                                <div className="bg-zinc-900/50 border border-zinc-800/60 rounded-lg px-4 py-3 text-xs font-mono text-zinc-400 whitespace-pre-wrap">
                                  {commandOutput}
                                </div>
                              )}
                            </div>
                          ) : log.type === "screenshot" ? (
                            <div className="mt-2 rounded-xl overflow-hidden border border-zinc-800 bg-black/40">
                              <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
                                <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[200px]">
                                  {log.metadata?.url}
                                </span>
                                <a
                                  href={log.content || ""}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-wider"
                                >
                                  Full Size <ExternalLink className="w-3 h-3" />
                                </a>
                              </div>
                              <div className="relative aspect-video bg-zinc-900/20">
                                {log.content ? (
                                  <img
                                    src={log.content}
                                    alt="Screenshot"
                                    className="absolute inset-0 w-full h-full object-contain"
                                  />
                                ) : (
                                  <div className="absolute inset-0 flex items-center justify-center text-xs text-zinc-600">
                                    Screenshot unavailable
                                  </div>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div
                              className={cn(
                                "text-sm leading-relaxed whitespace-pre-wrap font-medium",
                                log.type === "error" ? "text-red-400" : "text-zinc-400"
                              )}
                            >
                              {log.content || ""}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          </div>

          {/* File Changes Panel */}
          <div className="w-full md:w-1/2 flex flex-col border-t md:border-t-0 md:border-l border-zinc-800/50 bg-zinc-900/10 min-h-[50vh] md:min-h-0">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <FileCode className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">
                  Modified files ({fileChanges.length})
                </span>
              </div>
              {fileChanges.length > 0 && (
                <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                  <Circle className="w-3 h-3 text-orange-500" />
                  <span>Latest update</span>
                </div>
              )}
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
                    {fileChanges.map((file) => (
                      <button
                        key={file.path}
                        onClick={() => setSelectedFile(file.path)}
                        className={cn(
                          "px-6 py-3 text-xs font-semibold whitespace-nowrap transition-all relative",
                          selectedFile === file.path ? "text-white bg-zinc-900/50" : "text-zinc-600 hover:text-zinc-400"
                        )}
                      >
                        {file.path.split("/").pop()}
                        {selectedFile === file.path && (
                          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-600 rounded-full" />
                        )}
                      </button>
                    ))}
                  </div>

                  {selectedFileEntry && !selectedFileHasContent ? (
                    <div className="flex-1 overflow-auto bg-[#0a0a0a] relative border-t border-zinc-800/20">
                      <div className="p-6 space-y-4">
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <AlertCircle className="w-4 h-4 text-orange-500" />
                          Diff content is not available for this change.
                        </div>
                        {selectedFileEntry.patch && (
                          <div className="space-y-3">
                            {selectedFileEntry.patch.matchPattern && (
                              <div className="bg-zinc-900/50 border border-zinc-800/60 rounded-lg p-3 text-xs font-mono text-zinc-400 whitespace-pre-wrap">
                                <div className="uppercase text-[9px] text-zinc-600 mb-2">Match</div>
                                {selectedFileEntry.patch.matchPattern}
                              </div>
                            )}
                            {selectedFileEntry.patch.replacePattern && (
                              <div className="bg-zinc-900/50 border border-zinc-800/60 rounded-lg p-3 text-xs font-mono text-zinc-400 whitespace-pre-wrap">
                                <div className="uppercase text-[9px] text-zinc-600 mb-2">Replace</div>
                                {selectedFileEntry.patch.replacePattern}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-auto bg-[#0a0a0a] relative group border-t border-zinc-800/20">
                      <ReactDiffViewer
                        oldValue=""
                        newValue={selectedFileContent}
                        splitView={true}
                        useDarkTheme={true}
                        styles={{
                          variables: {
                            dark: {
                              diffViewerBackground: "transparent",
                              diffViewerColor: "#a1a1aa",
                              addedBackground: "rgba(16, 185, 129, 0.05)",
                              addedColor: "#10b981",
                              wordAddedBackground: "rgba(16, 185, 129, 0.1)",
                              removedBackground: "rgba(239, 68, 68, 0.05)",
                              removedColor: "#ef4444",
                              wordRemovedBackground: "rgba(239, 68, 68, 0.1)",
                              gutterBackground: "transparent",
                              gutterColor: "#3f3f46",
                            },
                          },
                          line: {
                            fontFamily: "var(--font-modern), Menlo, monospace",
                            fontSize: "13px",
                          },
                        }}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
