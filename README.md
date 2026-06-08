# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

**International Student Survival Guide in the US.** The system answers practical questions international students face — visa status (F-1, OPT, CPT, SEVIS), housing, banking, budgeting, health insurance, and cultural adjustment.

This knowledge is valuable because it is genuinely hard to find in one place. The authoritative pieces are scattered across government sites (USCIS, DHS), university international-student offices, immigration blogs, and student communities like Reddit. Official channels are accurate but fragmented and written in legal language; community sources are relatable but often outdated or contradictory, which makes misinformation easy and costly (an immigration mistake can end a student's status). A guide that consolidates these sources into a single, source-cited answer engine serves as a more trustworthy starting point than any one site alone.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

12 sources were targeted; 10 were successfully ingested. The two Reddit sources could not be ingested (see note below).

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | InternationalStudent.com — First-Year Survival Guide | Website | https://www.internationalstudent.com/study_usa/way-of-life/first-year-survival-guide-2026/ |
| 2 | Boundless.com — Student Visa FAQs | Website (Reddit-sourced) | https://www.boundless.com/blog/top-student-visa-faqs-reddit |
| 3 | VisitorGuard.com — Survival Guide | Website | https://www.visitorguard.com/the-international-students-survival-guide-essential-tips-for-studying-abroad/ |
| 4 | r/internationalstudents | Reddit | https://www.reddit.com/r/internationalstudents *(not ingested — blocked)* |
| 5 | r/f1visa | Reddit | https://www.reddit.com/r/f1visa *(not ingested — blocked)* |
| 6 | Study in the States — DHS (OPT) | Government (official) | https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt |
| 7 | Scholaro.com — Adjusting to the US Education System | Website | https://www.scholaro.com/db/News/how-to-adjust-to-the-us-education-system-268 |
| 8 | UMass / Interstride — 5 Tips for First-Year Students | University blog | https://sbspathways.umass.edu/blog/2025/02/05/5-tips-for-first-year-international-students-in-the-us/ |
| 9 | VCU Grad Pod Podcast — International Student Experience | Podcast transcript | https://gradpodvcu.substack.com/p/the-international-student-experience |
| 10 | USCIS — Students and Exchange Visitors | Government (official) | https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors |
| 11 | InternationalStudent.com — Culture Shock | Website | https://www.internationalstudent.com/study_usa/way-of-life/culture-shock/ |
| 12 | InternationalStudent.com — Social Life | Website | https://www.internationalstudent.com/study_usa/way-of-life/social-life/ |

**Note on the Reddit sources (#4, #5):** Reddit now blocks unauthenticated access to its listing/`.json` endpoints with a 403, regardless of User-Agent. The ingestion script supports two ways to include them — registering a free Reddit API app (OAuth) or dropping saved thread text into `documents/manual/` — but for this submission they were left out. The Reddit *perspective* is partly preserved through source #2 (Boundless), whose visa FAQs are themselves sourced from Reddit. The ingestion pipeline records these two as failed sources in `documents/manifest.json` rather than crashing.

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
Semantic chunking with a **256-token maximum**. There is no fixed size — chunk boundaries are placed where the topic shifts. Each document's sentences are embedded with `all-MiniLM-L6-v2`, and a new chunk starts wherever the cosine distance between two consecutive sentences exceeds the 90th percentile of distances in that document (a topic shift). Any topic segment longer than 256 tokens is then packed into multiple sub-chunks so nothing exceeds the cap. Token counts use the embedding model's own tokenizer.

**Overlap:**
0–50 tokens, applied **only** when a topic segment has to be force-split for exceeding the 256-token cap. Semantic boundaries themselves get no overlap, since the whole point is that the topic changed. The overlap is purely a safety buffer against splitting a single idea across a size-forced boundary.

**Preprocessing:**
During ingestion, HTML is parsed with BeautifulSoup; `script`/`style`/`nav`/`header`/`footer`/`aside`/`form` tags are stripped, and the main content region (`<main>`/`<article>` when present) is kept. Headings, paragraphs, and list items are preserved on their own lines so the chunker has real section structure to split on. A metadata header (source, URL, official flag, fetch time) is written to each `.txt` file and stripped back off before chunking.

**Why these choices fit your documents:**
The corpus is a mix of long guides, an FAQ, a podcast transcript, and government pages, all covering clearly distinct subtopics (visa rules vs. housing vs. banking vs. culture shock). Semantic chunking keeps each subtopic intact as one coherent chunk instead of cutting mid-idea, which matters when a student asks a narrow question like "what is OPT" or "signs of culture shock." This was visibly validated: the culture-shock query retrieved a single clean chunk listing the symptoms rather than fragments.

**Final chunk count:**
**172 chunks** across the 10 ingested documents (min 2 tokens, max 256, avg ~136).

---

## Sample Chunks

Five representative chunks, each labeled with its source document and `chunk_id` (long chunks trimmed with […] for readability; full text is in `chunks.json`).

**1. Source: Study in the States — DHS** — `06-studyinthestates-dhs__0000` (252 tokens)
> […Quick Links: Overview · Recommend OPT · Edit OPT Request …] F-1 students often want to work. However, employment opportunities are limited, and strict rules apply. This document discusses different types of optional practical training (OPT) including: required forms, processes, and updating SEVIS. **What is Optional Practical Training?** Optional practical training is one type of work permission available for eligible F-1 students. It allows students to get real-world work experience related to their field of study. While a Designated School Official (DSO) recommends OPT in SEVIS, it is the student who must apply for the work permit with the U.S. Citizenship and Immigration Service (USCIS). If the OPT is approved, USCIS will issue an Employment Authorization Document (EAD).

**2. Source: InternationalStudent.com — Culture Shock** — `11-internationalstudent-cultureshock__0000` (204 tokens)
> Culture shock is a feeling of disorientation many people feel when experiencing an entirely new way of life. […] These symptoms generally include: - Sadness, loneliness, melancholy - Preoccupation with health - Aches, pains, allergies - Insomnia or excessive sleep - Changes in mood, depression, feeling vulnerable - Anger, irritability, resentment - Loss of identity - Lack of confidence - Obsessions over cleanliness - Longing for family - Feelings of being lost or overlooked

**3. Source: VisitorGuard.com** — `03-visitorguard__0000` (226 tokens)
> The International Student's Survival Guide: Essential Tips for Studying Abroad in 2026 […] **Research your destination country.** Learn about its culture, customs, local laws, and any potential risks. […] **Know about visa and documentation.** International students planning to study in the US must obtain the appropriate student visa. The most common types are F-1 visas for academic studies, J-1 visas for cultural exchange, and M-1 visas for vocational studies.

**4. Source: VCU Grad Pod Podcast** — `09-vcu-gradpod__0000` (234 tokens)
> The International Student Experience and International Student Services […] For many, it's not just about adjusting to a different culture; it's about understanding a new academic framework, balancing visa regulations, and building meaningful relationships in a completely unfamiliar environment. […] In this episode, we are joined by Kelly Richard, a Global Learning Specialist at VCU, to explore the struggles that international students face in their journeys […].

**5. Source: InternationalStudent.com — First-Year Survival Guide** — `01-internationalstudent__0000` (249 tokens)
> First-Year Survival Guide for International Students in the U.S. (2026 Edition). […] This guide uses information from USCIS, College Board, ICE/SEVP, and the CDC […]. International students must maintain visa status by following USCIS requirements, including full-time enrolment and proper employment authorization. Attending sessions offered by the international student office helps clarify SEVIS rules. **Students should update their address within 10 days of moving** and avoid unauthorized work.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
`all-MiniLM-L6-v2` via `sentence-transformers`. It runs locally (no API cost or latency), is fast enough to embed the whole corpus in a few seconds, and produces 384-dimensional embeddings that work well for short-passage semantic similarity. The same model is used for both indexing chunks and embedding queries, so document and query vectors share one space. Vectors are stored in ChromaDB with cosine similarity.

**Production tradeoff reflection:**
The main limitation surfaced during implementation: `all-MiniLM-L6-v2` only encodes the first **256 tokens** of any input, so I capped chunks at 256 to avoid silently dropping text at embed time (the original plan said 500). If I were deploying for real users and cost weren't a constraint, I'd weigh:
- **Context length** — a longer-context embedder (e.g. an OpenAI `text-embedding-3` model or a BGE/E5 variant) would let me use larger, more self-contained chunks, reducing the chance that an answer is split across chunk boundaries (the Q2-style risk).
- **Domain accuracy** — immigration text is dense and jargon-heavy; a larger or instruction-tuned embedding model would likely rank the exact answer chunk higher (Q2 and Q5's answer chunks ranked #2–3, not #1).
- **Multilingual support** — international students often think in their first language; a multilingual model (e.g. `paraphrase-multilingual-MiniLM` or a multilingual E5) would let students query in their native language.
- **Latency vs. hosting** — a local MiniLM is essentially free and private; an API-hosted model adds per-query cost and network latency but typically improves accuracy. For this domain I'd lean toward a stronger model only if evaluation showed retrieval ranking was the bottleneck — which, given the LLM recovered most answers from k=5 anyway, it mostly wasn't.

---

## Retrieval Test Results

Three queries run directly against the retriever (`retrieve(query, k=3)`), showing the top chunks returned with their cosine similarity and source.

**Query 1: "What is OPT and when can I apply for it?"**
| Rank | Sim | Source | chunk_id |
|---|---|---|---|
| 1 | 0.609 | Study in the States — DHS [OFFICIAL] | `06-studyinthestates-dhs__0010` |
| 2 | 0.609 | Study in the States — DHS [OFFICIAL] | `06-studyinthestates-dhs__0029` |
| 3 | 0.583 | Study in the States — DHS [OFFICIAL] | `06-studyinthestates-dhs__0012` |

**Query 2: "How can international students make friends and adjust socially in the US?"**
| Rank | Sim | Source | chunk_id |
|---|---|---|---|
| 1 | 0.755 | InternationalStudent.com — Social Life | `12-internationalstudent-sociallife__0008` |
| 2 | 0.738 | InternationalStudent.com — Social Life | `12-internationalstudent-sociallife__0003` |
| 3 | 0.713 | Scholaro.com | `07-scholaro__0006` |

*Why these chunks are relevant:* All three come from the two sources in the corpus that actually discuss social adjustment. The top two are from the dedicated "Social Life" guide (one on the role of socialization, one quoting a real international student's advice), and the third is the Scholaro chunk on American communication style — directly on point for "adjusting socially." The embedding model ranked the purpose-built social-life source above the general guides, which is exactly the desired behavior.

**Query 3: "What health insurance do international students need in the US?"**
| Rank | Sim | Source | chunk_id |
|---|---|---|---|
| 1 | 0.682 | UMass / Interstride | `08-umass-interstride__0001` |
| 2 | 0.676 | VisitorGuard.com | `03-visitorguard__0002` |
| 3 | 0.591 | VisitorGuard.com | `03-visitorguard__0005` |

*Why these chunks are relevant:* Chunks 2 and 3 (both VisitorGuard) directly address the query — chunk 2 states that "many universities require students to have health coverage" and describes choosing between university-provided and external plans, and chunk 3 advises "purchasing a comprehensive health insurance plan to cover medical costs." Chunk 1 (UMass) is the weakest of the three: it's a general "get your affairs in order before you leave" passage that mentions insurance only in passing, which is why its similarity is closest to the others despite ranking first — a good illustration that top rank doesn't always mean most specific.

*(Honest note on Query 1: the retriever returned only official DHS chunks, but skewed toward the procedural "how to file OPT in SEVIS" steps rather than the definitional chunk `06-…__0000` that best explains what OPT is. The full `ask()` pipeline still answers OPT questions correctly because it reads across all k=5 chunks, but this query shows the retriever favoring procedure over definition.)*

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
The generation model (Groq, `llama-3.3-70b-versatile`, temperature 0.2) is given this system prompt:

> You are The Unofficial Guide, an assistant for international students in the United States. Answer the student's question using ONLY the numbered sources provided in the context.
> Rules:
> 1. If the context does not contain the answer, say: "I don't have enough information in my sources to answer that confidently." Do not use outside knowledge and never invent visa rules, deadlines, or dollar amounts.
> 2. When sources disagree, prefer the ones marked [OFFICIAL] (USCIS / DHS) and note the disagreement.
> 3. Cite the source name(s) you used in your answer, e.g. (Source: Study in the States — DHS).
> 4. Be concise and practical. Immigration mistakes are costly, so do not overstate certainty.

This is enforced structurally, not just by instruction:
- **Numbered, labeled context.** Each retrieved chunk is injected as `[Source N: <name> [OFFICIAL]]` followed by its text. The `[OFFICIAL]` tag (set during ingestion for USCIS/DHS) lets the model prefer authoritative sources when they conflict — the mitigation for outdated/conflicting immigration info.
- **Low temperature (0.2)** to keep answers faithful rather than creative.
- **Verified refusal behavior.** Tested with an out-of-domain question ("What is the capital of France?") and an in-domain but uncovered question (Q1, bank-account documents) — in both cases the model returned the refusal sentence instead of answering from general knowledge.

**How source attribution is surfaced in the response:**
Two ways. (1) The model cites source names inline in its answer per rule 3. (2) `ask()` returns a deduplicated, relevance-ordered list of "Source name — URL" strings alongside the answer; the Gradio UI shows this in a separate **"Retrieved from"** box so the student can see exactly which documents informed the answer and follow the links.

---

## Example Responses

Actual output from the system (`ask()`), unedited.

**Example 1 — in-domain, with source attribution**
> **Q:** How many months of full-time CPT disqualifies me from OPT?
> **Answer:** 12 months of full-time CPT disqualifies you from OPT. (Source: Study in the States — DHS [OFFICIAL], Source 1 and Source 2)
> **Retrieved from:** Study in the States — DHS — https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt

**Example 2 — in-domain, with source attribution**
> **Q:** What are common signs of culture shock?
> **Answer:** Common signs of culture shock include sadness, loneliness, melancholy, preoccupation with health, aches, pains, allergies, insomnia or excessive sleep, changes in mood, depression, feeling vulnerable, anger, irritability, resentment, loss of identity, lack of confidence, obsessions over cleanliness, and longing for family. (Source: InternationalStudent.com — Culture Shock, Source 1)
> **Retrieved from:** InternationalStudent.com — Culture Shock; Scholaro.com; VCU Grad Pod Podcast

**Example 3 — out-of-scope query (refusal)**
> **Q:** What is the best pizza place in New York City?
> **Answer:** I don't have enough information in my sources to answer that confidently.

The system refuses cleanly: the question is unrelated to the corpus, so even though three chunks were retrieved (the nearest neighbors), none supported an answer and the grounding instruction produced a refusal instead of a guess.

---

## Query Interface

The interface is a **Gradio web app** (`app.py`), launched with `python app.py` and opened at `http://127.0.0.1:7860`.

**Input field**
- *Your question* — a single free-text box. Submit by clicking **Ask** or pressing Enter. Five example questions are provided as one-click fillers.

**Output fields**
- *Answer* — the grounded, source-cited answer generated by Groq (or the refusal sentence when the corpus doesn't support an answer).
- *Retrieved from* — a bulleted list of the source documents (name + URL) that the answer was drawn from, so attribution is always visible.

**Sample interaction transcript**
```
[Your question]   How many months of full-time CPT disqualifies me from OPT?
                  (user clicks "Ask")

[Answer]          12 months of full-time CPT disqualifies you from OPT.
                  (Source: Study in the States — DHS [OFFICIAL], Source 1 and Source 2)

[Retrieved from]  • Study in the States — DHS —
                    https://studyinthestates.dhs.gov/sevis-help-hub/student-records/
                    fm-student-employment/f-1-optional-practical-training-opt
```

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What documents do I need to open a bank account in the US as an international student? | Passport, I-20, university enrollment letter; some banks need SSN/ITIN but Chase and BofA allow accounts without one | "I don't have enough information in my sources to answer that confidently." — refused, no document list given | Off-target | Did not answer (grounded refusal — see Failure Case) |
| 2 | How many days do I have to report an address change to maintain my F-1 status? | Within 10 days of moving, update address with the DSO through SEVIS | "You have 10 days to report any changes in your address to the DSO." (Source: Study in the States — DHS) | Partially relevant (answer chunk ranked #2–3, not #1) | Accurate |
| 3 | How many months of full-time CPT disqualifies me from OPT? | 12 months or more of full-time CPT eliminates OPT eligibility; part-time CPT does not | "12 months of full-time CPT disqualifies you from OPT." (Source: Study in the States — DHS) | Relevant (all 5 chunks from official DHS) | Accurate |
| 4 | What are common signs of culture shock international students experience in the US? | Homesickness, anxiety, irritability, fatigue, social withdrawal; hardest weeks 4–8 | Listed sadness, loneliness, insomnia, mood changes, irritability, loss of identity, etc., plus the four phases and the weeks 4–8 frustration window | Relevant | Accurate |
| 5 | What is the grace period after completing my program before I must leave the US on an F-1 visa? | 60 days after the program end date to depart, change status, or apply for OPT | "The grace period … is 60 days." (Source: Boundless.com) | Partially relevant | Accurate |

**Retrieval quality:** Relevant (Q3, Q4) / Partially relevant (Q2, Q5) / Off-target (Q1)
**Response accuracy:** Accurate (Q2–Q5, 4/5) / Did not answer (Q1, correct grounded refusal — no hallucination)

A note worth making: the LLM recovered the exact fact on Q2 and Q5 even though the answer chunk wasn't the top hit (similarity ~0.40–0.49). Retrieving k=5 and letting the model read across chunks mattered more than getting the single best chunk to rank first.

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
Q1 — "What documents do I need to open a bank account in the US as an international student?"

**What the system returned:**
"I don't have enough information in my sources to answer that confidently." The model declined to list any documents.

**Root cause (tied to a specific pipeline stage):**
This is a **document-ingestion / source-coverage** failure, not a retrieval or generation bug. Grepping the chunk store for banking terms shows the corpus only mentions banking in passing — "Open a U.S. bank account and set up a phone plan" and "Opening a local bank account simplifies transactions" — and **no source states the actual documents required** (passport, Form I-20, enrollment letter, SSN/ITIN). Retrieval did return the most banking-adjacent chunks it had, but none contained the answer, so the grounding instruction correctly triggered a refusal. The pipeline behaved exactly as designed: faced with no supporting evidence, it refused rather than fabricating an immigration-adjacent answer (which is the dangerous failure mode this project's grounding is meant to prevent).

**What you would change to fix it:**
Fix it at the source, not the retriever: add a source that actually covers banking documentation (e.g. a "how to open a US bank account as an international student" guide, or the VisitorGuard banking section if it has document specifics) so the fact exists in the corpus. The wrong fix would be loosening the grounding to let the model answer from general knowledge — that would reintroduce hallucination risk for visa rules. Lowering retrieval precision wouldn't help either, since the information simply isn't there to retrieve.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Writing the planning.md Documents table and Architecture diagram first meant each pipeline stage had a clear, concrete target before any code was written. The sources table became `sources.py` almost directly, and the five-stage architecture (Ingestion → Chunking → Embedding/Store → Retrieval → Generation) mapped one-to-one onto `ingest.py`, `chunk.py`, `embed_store.py`, `retrieve.py`, and `query.py`. The Anticipated Challenges section also paid off: because I'd already decided to "add source + date metadata to each chunk" and "prioritize official sources," that metadata was carried from ingestion all the way into the grounding prompt's `[OFFICIAL]` tags, instead of being bolted on later.

**One way your implementation diverged from the spec, and why:**
The spec set a 500-token maximum chunk size, but I lowered it to **256**. While implementing the embedding stage I confirmed that `all-MiniLM-L6-v2` truncates inputs at 256 tokens — so a 500-token chunk would have had roughly half its text silently dropped before embedding, making that text unsearchable. Capping at 256 ensures every token in every chunk is actually represented in its vector. The tradeoff is more, smaller chunks (the count rose from 120 to 154 at 8 documents, and ended at 172 across 10), which is acceptable and arguably better for retrieving narrow facts. I updated the Chunking Strategy section of planning.md to record this change, as the spec instructed.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — Chunking implementation and the 256-token decision**

- *What I gave the AI:* My Chunking Strategy section from planning.md (semantic chunking, 500-token max, 0–50 token overlap) and the ingested documents, and asked it to implement `chunk_text()`/`chunk.py`.
- *What it produced:* A semantic chunker that embeds sentences with `all-MiniLM-L6-v2`, splits at 90th-percentile cosine-distance topic shifts, enforces a size cap, and adds overlap only on size-forced splits. On the first run it flagged that 26% of chunks exceeded 256 tokens and would be truncated by the embedding model.
- *What I changed or overrode:* I decided to lower the cap from my specced 500 to 256 to match the model's real input limit, rather than keep 500 and accept silent truncation. I also had it update planning.md's Chunking Strategy to record the change.

**Instance 2 — Ingestion of blocked Reddit sources**

- *What I gave the AI:* My sources table from planning.md, including two Reddit communities, with the instruction to fetch and store raw text from each URL.
- *What it produced:* `ingest.py` using `requests` + BeautifulSoup. The two Reddit sources returned 403s; it tested fallback strategies (old.reddit host, different User-Agents) and confirmed Reddit now requires OAuth, then added optional OAuth support and a manual-fallback path so the run fails soft instead of crashing.
- *What I changed or overrode:* Rather than set up Reddit API credentials, I chose to drop the two Reddit sources for this submission and proceed with the other 10, noting in the README that Boundless (#2) partly preserves the Reddit perspective. I directed it to keep the failed sources recorded in the manifest rather than removing them.
