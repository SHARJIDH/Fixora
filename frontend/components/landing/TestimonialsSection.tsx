"use client";

import { Play } from "lucide-react";
import Image from "next/image";

interface Testimonial {
  company: string;
  companyLogo?: string;
  quote: string;
  author: string;
  role: string;
  avatar: string;
}

const testimonials: Testimonial[] = [
  {
    company: "TechFlow",
    quote: "Fixora performs exceptionally well with complex codebases. It handles our microservices architecture and does an excellent job with multi-language projects.",
    author: "Alexandra Chen",
    role: "CTO",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=alexandra",
  },
  {
    company: "DevScale",
    quote: "Fixora has a clear advantage when it comes to understanding context. With their AI, we reduced our bug fix time by 80%, and developers love it.",
    author: "Marcus Johnson",
    role: "VP of Engineering",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=marcus",
  },
  {
    company: "CodeCraft",
    quote: "We are 100% automation-driven. Fixora was selected on merit to handle our issue triaging and code generation. Their Docker validation gives us confidence.",
    author: "Sarah Williams",
    role: "Head of Platform",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=sarah",
  },
];

const featuredVideo = {
  thumbnail: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=800&fit=crop&crop=face",
  name: "James Rodriguez",
  role: "CTO & Founder, StartupAI",
  caseStudy: "StartupAI",
};

export function TestimonialsSection() {
  return (
    <section className="relative py-32 px-4 bg-black">
      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Why developers choose us
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Here&apos;s what engineering teams say about our platform
          </p>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Video Card */}
          <div className="relative rounded-3xl overflow-hidden group cursor-pointer min-h-[500px] lg:min-h-[600px]">
            {/* Video Thumbnail */}
            <div 
              className="absolute inset-0 bg-cover bg-center bg-no-repeat"
              style={{
                backgroundImage: `url(${featuredVideo.thumbnail})`,
              }}
            />
            
            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
            
            {/* Play Button */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex items-center gap-3 px-6 py-3 rounded-full bg-black/60 backdrop-blur-sm border border-white/20 group-hover:bg-black/80 transition-colors">
                <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center">
                  <Play className="w-4 h-4 text-black fill-black ml-0.5" />
                </div>
                <span className="text-white font-medium">
                  Watch {featuredVideo.caseStudy} case study
                </span>
              </div>
            </div>
            
            {/* Author Info */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
              <p className="text-white font-semibold text-lg">
                {featuredVideo.name}
              </p>
              <p className="text-gray-400 text-sm">
                {featuredVideo.role}
              </p>
            </div>
          </div>

          {/* Testimonial Cards Stack */}
          <div className="flex flex-col gap-4">
            {testimonials.map((testimonial, index) => (
              <div
                key={index}
                className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.03] to-transparent p-6 hover:bg-white/[0.05] transition-colors"
              >
                {/* Company Name */}
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xl font-bold text-white">
                    {testimonial.company}
                  </span>
                </div>
                
                {/* Quote */}
                <p className="text-gray-300 leading-relaxed mb-4">
                  &ldquo;{testimonial.quote}&rdquo;
                </p>
                
                {/* Author */}
                <div className="flex items-center gap-3">
                  <Image
                    src={testimonial.avatar}
                    alt={testimonial.author}
                    width={40}
                    height={40}
                    className="w-10 h-10 rounded-full bg-white/10"
                  />
                  <div>
                    <p className="text-white font-medium text-sm">
                      {testimonial.author}
                    </p>
                    <p className="text-gray-500 text-sm">
                      {testimonial.role}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
