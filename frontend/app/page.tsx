import { Hero } from "@/components/landing/Hero";
import { MiniDemo } from "@/components/landing/MiniDemo";
import { StatsStrip } from "@/components/landing/StatsStrip";
import { Chatbot, FinalCta, NewToIpos, Pipeline, WhatYouGet, WontDo } from "@/components/landing/Sections";

export default function Home() {
  return (
    <>
      <Hero />
      <StatsStrip />
      <div className="mx-auto w-full max-w-[1120px] px-4 md:px-6">
      <NewToIpos />
      <Chatbot />
      <Pipeline />
      <WhatYouGet />
      <MiniDemo />
      <WontDo />
      <FinalCta />
      </div>
    </>
  );
}
