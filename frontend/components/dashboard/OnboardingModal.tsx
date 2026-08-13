"use client";

import { useState } from "react";
import { X, ChevronRight, Check, Play, Github, Zap, Shield, Cpu } from "lucide-react";

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OnboardingModal({ isOpen, onClose }: OnboardingModalProps) {
  const [step, setStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      title: "Welcome to Fixora",
      description: "Automate your GitHub workflow with AI. We transform your issues into high-quality pull requests, autonomously.",
      icon: <Zap className="w-8 h-8 text-orange-500" />,
    },
    {
      title: "Trigger via @fixora",
      description: "Simply mention @fixora in any GitHub issue. Our agent will analyze the code, plan changes, and submit a PR for your review.",
      icon: <Cpu className="w-8 h-8 text-orange-500" />,
    },
    {
      title: "Enterprise Grade Security",
      description: "All code execution happens in secure, isolated sandboxes. Your secrets and codebase are always protected.",
      icon: <Shield className="w-8 h-8 text-orange-500" />,
      content: (
        <div className="flex flex-col gap-3 mt-6">
          <a
            href="https://github.com/fixora-test/sample-repo"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:bg-zinc-800 transition-all group"
          >
            <Github className="w-6 h-6 text-zinc-500 group-hover:text-white transition-colors" />
            <div className="text-left">
              <div className="font-semibold text-zinc-100">Try a sample repo</div>
              <div className="text-xs text-zinc-500">See Fixora in action</div>
            </div>
          </a>
          <button className="flex items-center gap-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl opacity-50 cursor-not-allowed">
            <Play className="w-6 h-6 text-zinc-500" />
            <div className="text-left">
              <div className="font-semibold text-zinc-100">Watch walkthrough</div>
              <div className="text-xs text-zinc-500">Coming soon</div>
            </div>
          </button>
        </div>
      ),
    },
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#020202]/80 backdrop-blur-xl">
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-[2rem] shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* Progress bar */}
        <div className="h-1.5 w-full bg-zinc-800">
          <div 
            className="h-full bg-orange-600 transition-all duration-500 ease-out" 
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>

        <div className="p-12">
          <div className="flex justify-between items-start mb-10">
            <div className="w-16 h-16 bg-orange-600/10 rounded-[1.5rem] flex items-center justify-center border border-orange-600/20">
              {steps[step].icon}
            </div>
            <button 
              onClick={onClose}
              className="p-2 text-zinc-500 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <h2 className="text-3xl font-bold text-zinc-100 mb-4 tracking-tight">
            {steps[step].title}
          </h2>
          <p className="text-zinc-400 text-lg leading-relaxed font-medium mb-8">
            {steps[step].description}
          </p>

          {steps[step].content}

          <div className="mt-12 flex justify-end">
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white font-semibold rounded-xl transition-all active:scale-95"
            >
              {step === steps.length - 1 ? (
                <>Get Started <Check className="w-5 h-5" /></>
              ) : (
                <>Next <ChevronRight className="w-5 h-5" /></>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
