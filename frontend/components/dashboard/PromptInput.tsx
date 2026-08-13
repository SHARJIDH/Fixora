"use client";

import React, { useState } from "react";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
  repoSelected: boolean;
}

export default function PromptInput({ onSubmit, isLoading, repoSelected }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (prompt.trim() && !isLoading && repoSelected) {
      onSubmit(prompt);
      setPrompt("");
    }
  };

  return (
    <div className="w-full relative group">
      <div className="absolute -inset-1 bg-gradient-to-r from-orange-600/20 to-amber-600/20 blur-2xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
      
      <form 
        onSubmit={handleSubmit}
        className="relative flex items-center bg-zinc-900 border border-zinc-800 rounded-2xl p-2 transition-all group-focus-within:border-orange-500/50 group-focus-within:ring-4 group-focus-within:ring-orange-500/10"
      >
        <div className="flex-1 flex items-center px-4">
          <Sparkles className={`w-5 h-5 transition-colors ${repoSelected ? "text-orange-500" : "text-zinc-600"}`} />
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isLoading || !repoSelected}
            placeholder={repoSelected ? "Write a README for this project..." : "Select a repository to get started..."}
            className="flex-1 bg-transparent border-none focus:ring-0 text-zinc-100 placeholder:text-zinc-600 h-14 py-4 px-4 resize-none leading-normal modern-scrollbar outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="p-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none shadow-lg shadow-orange-500/20 group/btn"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <ArrowRight className="w-5 h-5 group-hover/btn:translate-x-1 transition-transform" />
          )}
        </button>
      </form>
      
      {!repoSelected && (
        <p className="absolute -bottom-6 left-2 text-[10px] text-zinc-500 font-medium tracking-wide flex items-center gap-1">
          <span className="w-1 h-1 bg-zinc-600 rounded-full" /> SELECT A REPO TO OPEN INPUT BUFFER
        </p>
      )}
    </div>
  );
}
