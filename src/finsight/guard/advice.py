"""Advice, forecast and rating detector for English, Hindi and Hinglish (FR-07, ADR-046).

FinSight explains what an offer document says. It never tells anyone to apply, rates an IPO,
compares IPOs, or predicts listing gains, prices or profits (PRD section 9). ``check_advice`` is
a keyword and regex rule set, one rule per kind of request, with no model call:

- ``decision``    "should I apply", "निवेश करूँ", "karna chahiye": asks what to do
- ``forecast``    "will it double", "listing gain", "अगले साल मुनाफ़ा": asks about the future
- ``rating``      "is it overpriced", "rate it out of 10", "worth it": asks for an opinion
- ``comparison``  "which is better", "किसमें निवेश करूँ": asks to pick
- ``strategy``    "how many lots for allotment", "use my wife's account": asks how to game it
- ``gmp``         grey-market-premium questions (its meaning may be explained, its use may not)
- ``personal``    "I have ₹50,000, where do I put it": asks for a personal decision

Risk-level questions ("is this IPO risky?", "how risky is it?", "explain the risk level") are
facts since B2.6a: FinSight answers them with the computed risk level and its reasons. "Is it
safe?", "is it a good IPO?" and "should I apply?" are still refused (the level is then shown as
facts next to the refusal, B05 §7).

Questions that merely sound evaluative ("is there pending litigation", "what are the risks",
"minimum shares to apply for", "what does GMP mean") are facts and are not blocked. A
how-to question ("how do I apply") is procedural and passes unless another rule fires.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

Reason = Literal["advice_intent"]
REASON: Reason = "advice_intent"
_NUKTA = "़"
_CHANDRABINDU = "ँ"
_ANUSVARA = "ं"


def normalize_question(text: str) -> str:
    """Lower case, one spelling of Hindi nasal and nukta forms, single spaces."""
    text = unicodedata.normalize("NFC", text).casefold()
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace(_NUKTA, "")
        .replace(_CHANDRABINDU, _ANUSVARA)
    )
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class AdviceCheck:
    """Result of the advice-intent rules on one question."""

    blocked: bool
    reason: Reason | None = None
    category: str | None = None
    matched: str | None = None


_EN = "(?:^|[^a-z])"  # a word boundary that also works next to Devanagari
_END = "(?![a-z])"

# (category, pattern). Patterns run on the normalised question.
RULES: list[tuple[str, str]] = [
    # ---- decision ---------------------------------------------------------------- English
    (
        "decision",
        r"\b(?:should|shall)\s+(?:i|we)\b|\bshould (?:one|anyone|people|(?:a |the )?(?:retail |small |new |first[- ]time )?investors?)\b.{0,25}\b(?:apply|invest|subscribe|bid|buy)\b",
    ),
    (
        "decision",
        r"\b(?:i|we) should (?:apply|invest|subscribe|bid|buy|sell|skip|avoid|take|put|go)\b",
    ),
    ("decision", r"\bdo you (?:think|recommend|suggest|advise)\b"),
    ("decision", r"\b(?:would|will|can) you (?:recommend|suggest|advise)\b"),
    (
        "decision",
        r"\b(?:recommend|advise|suggest)(?:ed|ation)?\b.{0,40}\b(?:apply|invest|buy|subscribe|ipo|bid)",
    ),
    ("decision", r"\bworth (?:it|applying|investing|subscribing|the risk|buying)\b"),
    (
        "decision",
        r"\b(?:good|bad|safe|wise|smart|right) (?:idea|investment|buy|bet|to (?:apply|invest|buy|subscribe))\b",
    ),
    (
        "decision",
        r"\b(?:apply|invest|bid|buy|sell|subscribe)(?: in it| for it)? or (?:not|skip|avoid|wait)\b",
    ),
    (
        "decision",
        r"\b(?:skip|avoid|ignore) (?:it|this ipo|the ipo)\b.{0,30}\?|\bshould i (?:skip|avoid)",
    ),
    # ---- decision ---------------------------------------------------------------- Hinglish
    (
        "decision",
        r"\b(?:karna|lena|bharna|lagana|kharidna|bechna|bachna|rakhna) (?:chahiye|chahie|chahiy)\b",
    ),
    (
        "decision",
        r"\b(?:apply|invest|bid|subscribe|buy|sell|bharu|lagau|laga du|laga dun)(?: kar)? ?(?:karu|karun|kar du|kar dun|kardu|lu|lun|du|dun)\b",
    ),
    ("decision", r"\b(?:lagau|lagaun|laga du|laga dun|lagaoon)\b"),
    (
        "decision",
        r"\b(?:kisme|kisme|kaunse|kaunsa|kaun sa|kaun se) .{0,25}\b(?:lu|lun|lagau|lagaun|karu|invest|apply)\b",
    ),
    (
        "decision",
        r"\b(?:le )?(?:lu|lun)(?: kya| ya| na)?\s*\??$|\b(?:dalna|daalna|dena|rakhna|lagana) (?:chahiye|chahie)\b|\b(?:lu|lun) kya\b|\bkarna (?:sahi|theek|thik) (?:rahega|hoga|hai)\b|\bchalega kya\b",
    ),
    # ---- decision ---------------------------------------------------------------- Hindi
    (
        "decision",
        r"(?:अप्लाई|आवेदन|निवेश|खरीदना|खरीदें|बेचना|बचना|लेना|करना|भरना|लगाना)\s+(?:नहीं\s+)?चाहिए",
    ),
    ("decision", r"(?:करूं|कर दूं|कर लूं|लूं|लगाऊं|खरीदूं|बेचूं|भरूं|डालूं|चुनूं|बचूं|रखूं)(?:[ ?]|$)"),
    ("decision", r"(?:सही|ठीक|बेहतर) रहेगा"),
    # ---- forecast ---------------------------------------------------------------- English
    (
        "forecast",
        r"\bwill\b.{0,50}\b(?:go up|go down|rise|fall|double|triple|jump|crash|multibagger|make (?:me |us |you )?(?:money|profit)|give (?:me |us |you )?(?:good |great |high |decent |any )?(?:returns?|gains?|profit|listing)|list (?:above|below|higher|lower|at|flat)|be profitable|beat the market)",
    ),
    (
        "forecast",
        r"\blisting[- ]day (?:price|gains?|returns?|pop)\b|\bhow much (?:will|can|could|would) (?:i|we|one)\b.{0,20}\b(?:make|earn|gain|get|profit)\b|\bprofit\b.{0,20}\b(?:will|can|could) (?:i|we)\b|\bwill (?:i|we) (?:make|earn|lose|gain)\b",
    ),
    (
        "forecast",
        r"\blisting (?:gains?|price|pop|premium|returns?|profit)\b|\bgain on listing\b|\blist at\b",
    ),
    (
        "forecast",
        r"\bmultibagger\b|\btarget price\b|\bprice target\b|\b(?:predict|forecast|projected)\b",
    ),
    (
        "forecast",
        r"\bexpected? (?:returns?|profit|price|listing|gains?|growth)\b|\b(?:returns?|profit|gains?|price) (?:can|could|should|will) (?:i|we)? ?(?:expect|get|be)\b|\bwhat returns?\b",
    ),
    (
        "forecast",
        r"\bnext (?:year|quarter|fy|few years|month).{0,50}\b(?:profit|revenue|earn|loss|price|growth|sales)|\b(?:profit|revenue|earnings|price|growth|sales)\b.{0,50}\bnext (?:year|quarter|fy|month)\b",
    ),
    (
        "forecast",
        r"\bfuture (?:profit|revenue|earnings|price|growth|returns?)\b|\bin (?:a|one|1|two|2|five|5) years?\b.{0,40}\b(?:price|worth|double|value)\b",
    ),
    # ---- forecast ---------------------------------------------------------------- Hinglish
    (
        "forecast",
        r"\b(?:listing|list) (?:gain|gains|pe|par|me|mein|ke baad|price)\b|\blisting gain\b",
    ),
    (
        "forecast",
        r"\b(?:milega|milenge|banega|jayega|jayenge|honge|hoga|badhega|girega|chadhega|badhenge)\b.{0,25}\b(?:kya|na)\b|\b(?:kitna|kitne) (?:jayega|badhega|milega|girega|chadhega)\b",
    ),
    (
        "forecast",
        r"\b(?:profit|munafa|fayda|return|returns|gain)\w*\b.{0,20}\b(?:hoga|milega|honge|aayega|banega)\b|\b(?:upar|neeche|niche) (?:jayega|jaega|jayenge|jaayega)\b",
    ),
    (
        "forecast",
        r"\b(?:double|dugna|dugni|tripple|triple|multibagger)\b.{0,25}\b(?:honge|hoga|banega|ho jayega|ho jayenge)\b|\bmultibagger\b",
    ),
    # ---- forecast ---------------------------------------------------------------- Hindi
    (
        "forecast",
        r"अगले (?:साल|वर्ष|तिमाही|महीने).{0,50}(?:मुनाफ|लाभ|कमाई|राजस्व|आय|शेयर|भाव|कीमत|नुकसान|घाटा)|(?:मुनाफ|लाभ|कमाई|राजस्व|भाव|कीमत).{0,40}अगले (?:साल|वर्ष|तिमाही)",
    ),
    (
        "forecast",
        r"लिस्टिंग (?:पर|में|के बाद|के दिन|गेन|लाभ|मुनाफ|प्राइस|का भाव)|(?:भाव|कीमत|शेयर)\S*.{0,30}(?:खुलेंगे|चढ़ेंगे|चढ़ेगा|ऊपर जाएगा|नीचे जाएगा)|(?:दोगुना|दुगुना|तिगुना|मल्टीबैगर)|भविष्यवाणी|अनुमान लगा",
    ),
    (
        "forecast",
        r"(?:मुनाफ|लाभ|कमाई|रिटर्न|भाव|कीमत)\S*.{0,30}(?:होगा|होगी|होंगे|बढ़ेगा|बढ़ेगी|गिरेगा|जाएगा|मिलेगा|मिलेगी)",
    ),
    # ---- rating / opinion -------------------------------------------------------- English
    (
        "rating",
        r"\brate\b.{0,30}\b(?:ipo|company|issue|this)\b|\bout of (?:10|5|100)\b|\bratings?\b.{0,20}\b(?:ipo|company|issue)\b",
    ),
    (
        "rating",
        r"\b(?:over|under)[- ]?(?:priced|valued)\b|\b(?:overpriced|underpriced|overvalued|undervalued)\b",
    ),
    (
        "rating",
        r"\bvaluation\b.{0,40}\b(?:high|low|fair|expensive|cheap|reasonable|justified|steep|right)\b|\b(?:high|low|fair|expensive|cheap|reasonable|steep)\b.{0,30}\bvaluation\b",
    ),
    (
        "rating",
        r"\b(?:fair|good|reasonable|right|expensive|cheap|decent|attractive|too (?:high|low|much|costly)) (?:price|value|pricing)\b|\bpriced (?:fairly|well|right|too)\b",
    ),
    ("rating", r"\bred flags?\b|\bgreen flags?\b"),
    (
        "rating",
        r"\bis (?:it|this(?: ipo| company)?|the ipo|the company|the issue) (?:a )?(?:good|bad|safe|great|fine|decent|a (?:buy|sell))\b",
    ),
    ("rating", r"\b(?:good|great|bad|poor) (?:ipo|company|issue|investment)\b.{0,15}\?"),
    ("rating", r"\bis the risk worth\b|\bworth the risk\b"),
    # ---- rating / opinion -------------------------------------------------------- Hinglish
    ("rating", r"\b(?:overpriced|underpriced|mehnga|mehenga|mahanga|sasta|sasti)\b"),
    (
        "rating",
        r"\b(?:accha|achha|acha|achchha|badhiya|safe|sahi|theek|thik) (?:hai|rahega|ipo|company) (?:kya|ya nahi)\b|\bworth hai\b|\brating\b.{0,15}\b(?:do|bata|kya)\b",
    ),
    # ---- rating / opinion -------------------------------------------------------- Hindi
    ("rating", r"(?:10|दस|5|पांच) में से|नंबर दोगे|नंबर दो|रेटिंग|रेट करो|रेट कर"),
    (
        "rating",
        r"(?:भाव|कीमत|मूल्यांकन|वैल्यूएशन)\S* (?:ज़्यादा|ज्यादा|कम|सही|महंगा|ठीक|वाजिब)|महंगा|सस्ता|ओवरप्राइस",
    ),
    ("rating", r"(?:अच्छा|बुरा|सुरक्षित|जोखिम भरा|ठीक) (?:है|रहेगा|होगा) (?:क्या|या नहीं)|उठाने लायक"),
    ("rating", r"(?:पहली बार|नए) निवेश(?:क| करने वाले).{0,30}(?:ठीक|सही|अच्छा|सुरक्षित)"),
    # ---- comparison -------------------------------------------------------------- English
    (
        "comparison",
        r"\b(?:which|what)(?: one| ipo| company| stock| share)?(?: is| would be| are)? (?:better|best|safer|worth)\b",
    ),
    (
        "comparison",
        r"\bbetter (?:than|to apply|to invest|option|investment|choice|ipo)\b|\b(?:better|best) (?:ipo|investment|option|choice)\b",
    ),
    (
        "comparison",
        r"\bwhich (?:ipo|company|stock|share)s? (?:should|to|is|has|will|gives?|offers?|looks?)\b|\bwhich of (?:these|the two|them)\b|\b(?:more|better|higher|bigger) (?:upside|returns?|gains?|potential)\b",
    ),
    # ---- comparison -------------------------------------------------------------- Hinglish / Hindi
    (
        "comparison",
        r"\b(?:kaunsa|kaun sa|kaunse|kaun se|konsa|kon sa) (?:ipo |share |stock |company )?(?:better|accha|achha|best|lu|lun|lena)\b|\bbetter hai\b",
    ),
    (
        "comparison",
        r"(?:में से|मे से) (?:किस|कौन)|किसमें (?:निवेश|पैसा|लगा)|कौन सा (?:ipo|आईपीओ|शेयर|कंपनी|स्टॉक)|बेहतर (?:है|रहेगा|कौन)",
    ),
    # ---- strategy ---------------------------------------------------------------- English
    (
        "strategy",
        r"\bhow many lots?\b.{0,60}\b(?:apply|get|allot|allotment|should|improve|chance|win)",
    ),
    (
        "strategy",
        r"\b(?:improve|increase|boost|better|maximi[sz]e) (?:my |the |our )?(?:allotment )?(?:chances?|odds)\b|\bchances? of (?:getting )?allot",
    ),
    (
        "strategy",
        r"\b(?:two|2|three|3|several|many|separate|another|second|extra)\b.{0,20}\b(?:demat|accounts?|applications?|pan)\b.{0,40}\b(?:allot|chances?|apply|ipo|improve|increase)",
    ),
    (
        "strategy",
        r"\bmultiple (?:accounts?|applications?|demat)\b|\b(?:wife|husband|family|relatives?|friends?|parents?|brother|sister)(?:'s|s')? (?:demat |bank )?(?:account|name|pan)\b",
    ),
    (
        "strategy",
        r"\b(?:take|get|borrow|use) (?:a )?(?:loan|credit|margin)\b.{0,40}\b(?:apply|invest|ipo|bid|category|hni)\b|\bloan to (?:apply|invest|bid)\b",
    ),
    (
        "strategy",
        r"\b(?:bid|apply|subscribe)\b.{0,30}\bcut[- ]?off\b.{0,25}\b(?:or|better|safer|should)\b|\bcut[- ]?off\b.{0,25}\bor\b.{0,25}\b(?:lower|higher|band|price)\b",
    ),
    ("strategy", r"\bhni\b.{0,30}\b(?:category|route)\b.{0,30}\b(?:better|should|worth)\b"),
    # ---- strategy ---------------------------------------------------------------- Hinglish / Hindi
    (
        "strategy",
        r"\b(?:kitne|kitna) lots?\b.{0,40}\b(?:lagau|lagaun|lagana|apply|allotment|mil jaye|milega|chance)|\ballotment (?:mil|milne)|\bchance badh",
    ),
    (
        "strategy",
        r"\bcut[- ]?off (?:pe|par|price pe)\b.{0,25}\b(?:bid|apply|karu|karun)\b|\b(?:bid|apply) karu\b.{0,20}\bya\b",
    ),
    (
        "strategy",
        r"कितने लॉट.{0,30}(?:लगाऊं|लगाएं|अप्लाई|अलॉटमेंट|मिल)|अलॉटमेंट (?:मिल|के चांस)|बीवी|पत्नी के (?:खाते|डीमैट)",
    ),
    # ---- hold / sell / long-term questions --------------------------------------- all
    (
        "decision",
        r"\b(?:buy|hold|sell|exit|book profit)\b.{0,20}\b(?:or|/)\b.{0,20}\b(?:buy|hold|sell|exit|wait)\b|\b(?:hold|sell|exit)\b.{0,25}\b(?:after|on|at) listing\b",
    ),
    (
        "decision",
        r"\bwould you (?:invest|apply|buy|bid|subscribe|put)\b|\b(?:shouldn't|should not|shouldnt) (?:i )?(?:apply|invest|bid|buy|subscribe)\b",
    ),
    (
        "rating",
        r"\b(?:good|great|bad|safe|worth(?:while)?|solid)\b.{0,30}\b(?:investment|invest(?:ing)?)\b|\b(?:long|short)[- ]?term\b.{0,30}\b(?:good|safe|better|hold|investment|worth)\b",
    ),
    (
        "decision",
        r"\b(?:lu|lun|karu|karun|du|dun|lagau|bhar du)\s+ya\s+(?:nahi|nahin|na|hold|wait|ruk)\b|\b(?:bech|kharid|bhar|apply|invest|laga)\w*\s+(?:du|dun|doon|karu|karun|lu|lun)\b|\bhold karu\b",
    ),
    (
        "rating",
        r"\b(?:invest|apply|paisa lagana|lagana|lagane|karna|lena)(?: karna)? (?:safe|sahi|theek|thik|accha|achha|acha|faydemand|fayde ka)\b|\b(?:long|short)[- ]?term (?:ke liye|me|mein)\b.{0,20}\b(?:accha|achha|safe|sahi|better)\b",
    ),
    (
        "rating",
        r"(?:अच्छा|अच्छे|अच्छी|बुरा|खराब|सुरक्षित) (?:है|हैं|होगा|रहेगा|रहेंगे)\b|(?:लगाना|लगाने|निवेश करना|खरीदना|लेना) (?:सुरक्षित|सही|ठीक|फायदेमंद|अच्छा)|लंबे समय (?:के लिए|तक).{0,25}(?:अच्छ|सही|सुरक्षित|रखें|रखना)",
    ),
    # ---- GMP --------------------------------------------------------------------- all
    ("gmp", r"\bgmp\b|grey[- ]?market|gray[- ]?market|ग्रे[- ]?मार्केट|जीएमपी"),
    # ---- personal ---------------------------------------------------------------- all
    (
        "personal",
        r"\bmy (?:savings|money|portfolio|salary|budget|capital|risk (?:appetite|profile))\b|\bi have (?:₹|rs\.?|inr)? ?[\d,]+\b|\bi am a (?:first[- ]time|new|retired|senior|beginner)\b",
    ),
    (
        "personal",
        r"\bfirst[- ]time (?:investor|applicant|buyer)\b|\b(?:like me|for someone like me|suit(?:s|able)? (?:me|my))\b|\bfor (?:a )?(?:beginner|retiree|senior citizen|student)\b.{0,15}\?",
    ),
    (
        "personal",
        r"\bmere paas\b.{0,25}\b(?:rupaye|rupay|hazar|lakh|rs)\b|\bmere (?:paise|rupaye|liye)\b|\bmain (?:naya|pehli baar)\b",
    ),
    (
        "personal",
        r"मेरे पास.{0,25}(?:रुपये|रुपए|रुपय|हज़ार|हजार|लाख|₹)|पहली बार निवेश|मेरे लिए|मेरी (?:बचत|आय|सैलरी)",
    ),
]
_COMPILED = [(category, re.compile(pattern)) for category, pattern in RULES]

# "what does GMP mean" is a fact; "is the GMP a good sign, should I apply" is not
_GMP_DEFINITION = re.compile(
    r"\b(?:what (?:is|does|do) (?:a |an )?(?:gmp|grey[- ]?market(?: premium)?)\b(?! (?:today|now|currently|for|of|is)\b)"
    r"|meaning of|define|full form of|explain|stands for)"
    r"|\b(?:gmp|premium)\b.{0,25}\b(?:mean|means|stands? for|full form|meaning)\b"
    r"|\bmatlab\b|\bkya hota hai\b|\bkya hai\b|\bkise kehte\b"
    r"|क्या (?:होता|होती) है|क्या है|मतलब|का अर्थ|किसे कहते"
)
_PROCEDURAL = re.compile(
    r"\bhow (?:do|can|to|should) (?:i|we) (?:apply|bid|subscribe|check|participate)\b|\bhow to (?:apply|bid|subscribe|check)\b"
    r"|\b(?:kaise|kahan|kahaan|kab)\b|कैसे|कहां|कहाँ|कब"
)
_WEAK_DECISION = re.compile(
    r"(?:करूं|कर दूं|कर लूं|लूं|लगाऊं|खरीदूं|बेचूं|भरूं|डालूं|चुनूं|बचूं|रखूं|karu|karun|kar du|kardu|lu|lun|du|dun)$"
)
_DECIDERS = {"decision", "comparison", "rating", "forecast", "strategy", "personal"}


def check_advice(question: str) -> AdviceCheck:
    """Is this a request for advice, a forecast, a rating or a pick? (never calls a model)."""
    q = normalize_question(question)
    if not q:
        return AdviceCheck(False)
    hits = [(category, m) for category, rx in _COMPILED if (m := rx.search(q))]
    procedural = _PROCEDURAL.search(q) is not None
    kept = []
    for category, m in hits:
        if category == "decision" and procedural and _WEAK_DECISION.search(m.group().strip(" ?")):
            continue  # "मैं आवेदन कैसे करूं?" asks how, not whether
        kept.append((category, m))
    gmp = [h for h in kept if h[0] == "gmp"]
    others = [h for h in kept if h[0] != "gmp"]
    if gmp and not others and _GMP_DEFINITION.search(q):
        return AdviceCheck(False)  # the meaning of the term may be explained
    if kept:
        category, m = others[0] if others else gmp[0]
        return AdviceCheck(True, REASON, category, m.group().strip())
    return AdviceCheck(False)
