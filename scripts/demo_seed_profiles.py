"""Curated narrative and feedback templates for demo data backfills."""

from __future__ import annotations

from typing import Dict

DEMO_STORY_PROFILES: Dict[str, Dict[str, str]] = {
    "BIOL-101": {
        "celebration": "students are getting more confident turning observations into evidence-backed biological claims",
        "challenge": "early lab write-ups still flatten into description instead of analysis when the prompt gets more open-ended",
        "change": "we are front-loading a short data-interpretation rehearsal before the first full lab report",
        "feedback": "This foundational course is doing the right work for the rest of the program; keep reinforcing the move from observation to argument.",
    },
    "BIOL-201": {
        "celebration": "students are explaining cell structure-function relationships with much more precision than in the baseline run",
        "challenge": "abstract pathway diagrams still overload some students unless they get multiple concrete walkthroughs",
        "change": "we are adding one more guided practice set before the first signalling-heavy assessment",
        "feedback": "The conceptual climb here is visible, but the scaffold around pathway reasoning still matters more than a single polished lecture.",
    },
    "BIOL-250": {
        "celebration": "students respond well when field observations are tied directly back to course vocabulary and classification work",
        "challenge": "lab logistics and safety routines still eat time when too many moving parts land in the same week",
        "change": "we are simplifying the field workflow and making the prep checklist impossible to skip",
        "feedback": "The ecology content is landing, but the operational side of the course still needs tighter guardrails so performance reflects understanding, not logistics.",
    },
    "BIOL-251": {
        "celebration": "students are increasingly willing to justify experimental choices instead of just following the lab script",
        "challenge": "shared equipment creates bottlenecks that ripple into rushed analysis and thinner conclusions",
        "change": "we are staggering the practical work and adding clearer interim checkpoints before the final synthesis",
        "feedback": "Strong course energy here. The next improvement is throughput: when equipment bottlenecks ease, the analytical writing should get cleaner too.",
    },
    "BIOL-252": {
        "celebration": "students light up when the genetics work becomes pattern-finding rather than rote terminology",
        "challenge": "software-heavy moments still split the room between students who race ahead and students who freeze",
        "change": "we are building in supported practice before the graded analysis so the tooling is not the main obstacle",
        "feedback": "The curiosity signal is strong. Keep the bioinformatics layer, but continue smoothing the learning curve so the tool does not overshadow the biology.",
    },
    "BIOL-301": {
        "celebration": "students are designing stronger investigations and defending their choices with more confidence",
        "challenge": "the analysis phase is still where promising projects lose momentum if the statistical choices are underspecified",
        "change": "we are adding another structured checkpoint on method justification before final submission",
        "feedback": "This remains one of the best places to model authentic scientific reasoning. Keep tightening the analysis coaching because that is the real constraint.",
    },
    "HIST-101": {
        "celebration": "students are making better use of source evidence and quoting with more purpose instead of dropping in disconnected facts",
        "challenge": "some written responses still summarize documents without explaining why the evidence matters",
        "change": "we are adding one short source-analysis rehearsal before the larger written assignment",
        "feedback": "The writing is moving in the right direction. Keep emphasizing claim-evidence reasoning so the historical content feels analytical, not just descriptive.",
    },
    "ZOOL-101": {
        "celebration": "students are connecting species-level observations to larger taxonomic patterns much more readily now",
        "challenge": "classification language is still brittle when students have to apply it outside the examples shown in class",
        "change": "we are adding more low-stakes identification practice before the major practicals",
        "feedback": "Good momentum in the introductory zoology sequence. The next win is transfer: can students classify novel cases without waiting for a familiar example?",
    },
    "ZOOL-205": {
        "celebration": "students are getting more fluent at linking anatomy, behaviour, and ecological context in the same explanation",
        "challenge": "the course still asks for a lot of synthesis at once, and weaker students can lose the thread when several concepts stack up together",
        "change": "we are breaking the larger tasks into smaller synthesis checkpoints before the final integration work",
        "feedback": "The integrative ambition of this course is good. Keep the synthesis tasks, but give students more visible stepping stones on the way there.",
    },
    "ZOOL-310": {
        "celebration": "students are starting to write about advanced animal systems with the specificity we want from upper-division work",
        "challenge": "students can still revert to memorized phrasing when they are pushed to explain mechanism under time pressure",
        "change": "we are adding one more oral-reasoning checkpoint so students practice explaining mechanism before the final written task",
        "feedback": "Upper-division zoology is showing strong content mastery. Keep pushing on explanation quality so the mechanistic reasoning is as strong as the recall.",
    },
    "_default": {
        "celebration": "students are showing stronger command of the core ideas than they did at the beginning of the sequence",
        "challenge": "some of the harder analytical moves still require more guided practice than the current pacing allows",
        "change": "we are adding one more scaffolded checkpoint before the next major assessment",
        "feedback": "The course is trending in the right direction. The next step is making the strongest analytical habit explicit so more students can repeat it.",
    },
}

DEMO_TERM_CONTEXT: Dict[str, str] = {
    "FA2023": "In the first seeded run, ",
    "SP2024": "Compared with the prior fall, ",
    "FA2024": "By this fall run, ",
    "SP2025": "This spring cohort showed that ",
    "": "In the current demo term, ",
}
