import { Hero } from "@/components/landing/Hero";
import { MiniDemo } from "@/components/landing/MiniDemo";
import { OpenStats } from "@/components/landing/OpenStats";
import { AskLang, Chatbot, FinalCta, NewToIpos, Steps, WhatYouGet, WontDo } from "@/components/landing/Sections";

export default function Home() {
  return (
    <>
      <Hero />
      <NewToIpos />
      <Chatbot />
      <Steps />
      <WhatYouGet />
      <MiniDemo />
      <AskLang />
      <WontDo />
      <OpenStats />
      <FinalCta />
    </>
  );
}
