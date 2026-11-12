// Landing page copy, docs/12_FRONTEND_SPEC.md section 5 (verbatim), with the Phase 2 changes from


// spec is listed in docs/AKSHAT_TODO.md. `[[id|text]]` marks a glossary term (see components/ui/Rich.tsx).
type Entry = string;

export const LANDING = {
  // 5.2 hero
  "land.h1": "500 pages of fine print, read in minutes.",
  "land.sub": "FinSight reads an IPO offer document, flags the risks in plain English, and shows the page behind every number.",
  "land.cta": "X-ray an IPO",
  "land.sample": "See a sample report",
  "land.how": "How it works",
  "land.free": "Free. Sign in with Google to upload. Runs on open-source models.",
  "land.kicker": "IPO X-ray for Indian retail investors",
  "land.reel.alt": "Animation: FinSight reads the cover page of a made-up Red Herring Prospectus, zooms in on the total issue size, lifts out {value}, and shows it as a fact that matches page 1.",
  "land.reel.label": "Total issue size",
  "land.reel.steps": "What FinSight does with each page",
  "land.reel.step.read": "Read",
  "land.reel.step.find": "Find",
  "land.reel.step.extract": "Extract",
  "land.reel.step.check": "Check",
  "land.reel.pause": "Pause the animation",
  "land.reel.play": "Play the animation",
  "land.reel.note": "A made-up prospectus, read the way FinSight reads a real one.",

  // 5.3 new to IPOs
  "land.new.h": "New to IPOs? Start here.",
  "land.new.1.h": "What is an IPO?",
  "land.new.1.b": "When a company sells its shares to the public for the first time, that's an [[ipo|IPO]] (initial public offering). Anyone with a [[demat|demat account]] can apply for shares.",
  "land.new.2.h": "What is the RHP?",
  "land.new.2.b": "Before the IPO opens, the company publishes a Red Herring Prospectus ([[rhp|RHP]]). It's the official document with the details: how much money is being raised, who is selling shares, and what the money will be used for.",
  "land.new.3.h": "Why does nobody read it?",
  "land.new.3.b": "It's usually 500 to 1,000 pages of legal language. The important numbers are spread across the cover, the offer section and a few tables.",

  // 5.4 chatbot
  "land.bot.h": "Why not just ask a chatbot?",
  "land.bot.b": "General chatbots can be helpful, but with Indian offer documents they often run into two problems. They can mix up lakh, crore and million, and they rarely show which page a number came from. When it's your money, \"probably right\" isn't good enough.",
  "land.bot.row1": "A typical chatbot answer",
  "land.bot.row1v": "\"The fresh issue is ₹800 lakh.\"",
  "land.bot.row2": "What the document says (page 3)",
  "land.bot.row2v": "\"₹800 crore\"",
  "land.bot.verdictHead": "Doesn't match.",
  "land.bot.verdict": "₹800 lakh is ₹8 crore. The document says ₹800 crore. That's 100 times more.",
  "land.bot.caption": "Illustrative example. FinSight's own comparison with general chatbots is in the Model Lab.",

  // 5.5 how it works
  "land.steps.h": "How FinSight works",
  "land.steps.1.h": "It reads the whole document.",
  "land.steps.1.b": "Every page, including the tables, from the RHP and the final prospectus.",
  "land.steps.2.h": "It pulls out the key facts.",
  "land.steps.2.b": "Issue size, price, who is selling, what the money is for. Each fact links to its page.",
  "land.steps.3.h": "It checks every number in its answers.",
  "land.steps.3.b": "Ask a question, and each number in the reply gets a mark.",
  "land.marks.verified": "the same number is in the document.",
  "land.marks.unverifiable": "the number isn't in the pages used.",
  "land.marks.contradicted": "the document says something different.",

  // 5.6 mini demo
  // B05 §2: "What you get", after "How FinSight works"
  "land.get.h": "What you get",
  "land.get.1.h": "The key facts.",
  "land.get.1.b": "Issue size, price, who is selling, what the money is for. Each linked to its page.",
  "land.get.2.h": "Red flags.",
  "land.get.2.b": "13 checks, like losses, cash burn, debt, and how cheaply insiders bought their shares. Each marked OK, Watch or Concern.",
  "land.get.3.h": "Every risk, in plain English.",
  "land.get.3.b": "Companies list dozens of risks in legal language. FinSight rewrites each one in simple words and shows the unusual ones first.",
  "land.get.4.h": "A risk level.",
  "land.get.4.b": "Low, Medium or High, compared with past Indian IPOs, with the reasons listed.",

  "land.demo.h": "Try it here",
  "land.demo.b": "Click a fact. FinSight jumps to the page and highlights where it came from.",
  "land.demo.open": "Open the full workspace",

  // 5.7 languages

  // 5.8 limits
  "land.no.h": "What FinSight won't do",
  "land.no.1": "It won't tell you whether to apply or buy.",
  "land.no.2": "It won't predict listing prices or profits.",
  "land.no.3": "Its risk level describes what the document discloses. It is not a recommendation.",
  "land.no.p": "In India, investment advice can only come from advisers registered with [[sebi|SEBI]]. FinSight sticks to what the documents say.",

  // 5.9 stats
  "land.open.h": "Built in the open",
  "land.open.b": "Every number below comes from tests you can rerun from the source code.",
  "land.stat.ipos": "IPOs analysed",
  "land.stat.ipos.viz": "Issue size of each analysed IPO, oldest to newest",
  "land.stat.ipos.note": "Bars: issue size of each",
  "land.stat.pages.viz": "Pages processed, running total",
  "land.stat.facts": "of key facts match the hand-checked answers",
  "land.stat.facts.note": "195 numbers, 10 IPOs",
  "land.stat.flags": "of red-flag statuses match the hand-checked answers",
  "land.stat.flags.note": "13 checks on each of 10 IPOs",
  "land.stat.source": "Measured on IPOs the models never saw during training. Single run.",
  "land.pipe.h": "From PDF to risk level",
  "land.pipe.upload": "Upload",
  "land.pipe.upload.b": "A text PDF up to 50 MB",
  "land.pipe.parse": "Parse",
  "land.pipe.parse.b": "Every page, word and table",
  "land.pipe.extract": "Extract",
  "land.pipe.extract.b": "Key facts, risks and 13 red-flag checks",
  "land.pipe.verify": "Verify",
  "land.pipe.verify.b": "Every number is checked against its page",
  "land.pipe.risk": "Risk level",
  "land.pipe.risk.b": "Low, Medium or High, with the reasons",
  "land.pipe.pages": "pages processed so far",
  "land.pipe.checks": "red-flag checks per IPO",
  "land.pipe.caught": "of planted number errors caught",
  "land.stat.pages": "pages processed",
  "land.stat.detect": "of planted number errors caught",
  "land.stat.risks": "risks explained",
  "land.stat.corpus": "past IPOs used for comparison",
  "land.stat.robust": "accuracy of our model when the cover page is hidden",
  "land.open.lab": "See the full results",
  "land.open.code": "Read the code on GitHub",

  // 5.10 final
  "land.final.h": "Pick an IPO and see what's inside.",
  "land.final.cta": "Browse IPOs",
} satisfies Record<string, Entry>;
