# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

 Domain: International Student Survival Guide in the USDomain: International Student Survival Guide in the US
As an international student, I know how overwhelming it can be to navigate visa status, housing, banking, and cultural adjustment in the US. The information exists  but it is scattered across universities websites, Reddit, and Facebook groups, making misinformation easy and critical details hard to find. A consolidated guide built from real student experiences would serve as a single source of truth for international students.


---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 |InternationalStudent.com |First-year survival guide covering immigration, academics, living expenses, and mental health |https://www.internationalstudent.com/study_usa/way-of-life/first-year-survival-guide-2026/ |
| 2 |Boundless.com |F-1/M-1 visa FAQs sourced from Reddit covering proof of funds and processing times | https://www.boundless.com/blog/top-student-visa-faqs-reddit|
| 3 |VisitorGuard.com | Covers health insurance, budgeting, banking, and cultural adjustment for international students| https://www.visitorguard.com/the-international-students-survival-guide-essential-tips-for-studying-abroad/|
| 4 | r/internationalstudents|Reddit community sharing real experiences on visa, housing, culture, and academics | https://www.reddit.com/r/internationalstudents|
| 5 |r/f1visa |Reddit community focused specifically on F-1 visa questions, OPT, CPT, and staying in status | https://www.reddit.com/r/f1visa|
| 6 |Study in the States — DHS | Official DHS resource covering CPT, OPT, SEVIS, and maintaining F-1 status|https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt |
| 7 | Scholaro.com| Guide on adjusting to the US education system covering grading, mental health, OPT, and SEVIS|https://www.scholaro.com/db/News/how-to-adjust-to-the-us-education-system-268 |
| 8 | UMass/Interstride|Tips from former international students on visa prep, housing, health insurance, and US college life |https://sbspathways.umass.edu/blog/2025/02/05/5-tips-for-first-year-international-students-in-the-us/ |
| 9 |VCU Grad Pod Podcast | Podcast episode on navigating culture, visa regulations, and academic adjustment as an international student|https://gradpodvcu.substack.com/p/the-international-student-experience |
| 10 |USCIS — F-1 Students Official Page | Official US government page covering F-1 visa rules, OPT, CPT, and maintaining status|https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors |
| 11 |InternationalStudent.com — Culture Shock | Stages and signs of culture shock and how to cope while studying in the US | https://www.internationalstudent.com/study_usa/way-of-life/culture-shock/ |
| 12 |InternationalStudent.com — Social Life | Adjusting to US social life, making friends, and campus social norms | https://www.internationalstudent.com/study_usa/way-of-life/social-life/ |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**
Variable — no fixed size; chunks are determined by semantic boundaries (topic shifts) rather than token count, with a **256-token max safeguard**. (Originally specced at 500, but lowered to 256 during implementation — see note below — because the embedding model only reads the first 256 tokens.)

**Overlap:**
0–50 tokens, applied only when a topic segment is force-split for exceeding the size cap (acts purely as a safety buffer against splitting one idea across a size-forced boundary). Semantic boundaries themselves get no overlap.

**Final chunk count:** 172 chunks across 10 ingested documents (12 sources listed; the two Reddit sources were dropped — see Documents note).

**Reasoning:**
International student documents cover distinct subtopics — visa rules, housing, banking, cultural adjustment — that shift naturally between sections. Semantic chunking keeps each topic intact as one coherent chunk rather than cutting mid-idea, which improves retrieval accuracy when a student asks a specific question like "how do I open a bank account" or "what is OPT". Sentences are embedded with `all-MiniLM-L6-v2`, and a new chunk starts wherever the cosine distance between consecutive sentences spikes above the 90th percentile (a topic shift).

**Note — divergence from original spec:** The 500-token cap was lowered to **256** because `all-MiniLM-L6-v2` truncates inputs to 256 tokens; a 500-token chunk would have left ~half its text unsearchable at embedding time. Lowering the cap produces more, smaller chunks (at 8 documents it raised the count from 120 → 154).

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
all-MiniLM-L6-v2 via sentence-transformers

**Top-k:**
5 — within the 3–5 range. At k=5 the retriever supplies enough context for the generation model to ground its answer on the strong/partial questions, at modest token cost. (Eval showed the extra 2 chunks don't rescue off-target queries like the address-change question, but they don't hurt either.)

**Production tradeoff reflection:**
Groq is actually an **LLM provider** (it runs models like LLaMA, Mixtral) — it handles the **generation** part, not the **embedding** part. They are two separate things:

---

**How the pipeline works:**
```
Your documents
     ↓
Embedding model  ← converts text to vectors (for retrieval)
     ↓
Vector database (ChromaDB)
     ↓
User asks a question → retrieve top-k chunks
     ↓
Groq (LLaMA/Mixtral) ← generates the answer using retrieved chunks
```

---

So you still need an embedding model separately. Looking at your `requirements.txt` from earlier, you already have one installed:

```
sentence-transformers==3.4.1  ← this is your embedding model
```

The default model it uses is **`all-MiniLM-L6-v2`**, which is a great fit for your project.

---

**So your answers would be:**

**Embedding model:** `all-MiniLM-L6-v2` via sentence-transformers

**Top-k:** 3-5 is standard  retrieves enough context without overwhelming the LLM

**Tradeoffs for real deployment:**
none
---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What documents do I need to open a bank account in the US as an international student?|Passport, I-20, and university enrollment letter; some banks may require an SSN or ITIN but Chase and Bank of America allow accounts without one |
| 2 | How many days do I have to report an address change to maintain my F-1 status?| Within 10 days of moving, students must update their address with their DSO through SEVIS|
| 3 | How many months of full-time CPT disqualifies me from OPT?| 12 months or more of full-time CPT eliminates OPT eligibility; part-time CPT does not affect OPT|
| 4 | What are common signs of culture shock international students experience in the US?|Homesickness, anxiety, irritability, fatigue, and social withdrawal — typically hitting hardest between weeks 4 and 8 of the first semester |
| 5 | What is the grace period after completing my program before I must leave the US on an F-1 visa?|60 days after the program end date to depart, change status, or apply for OPT |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Outdated or conflicting immigration information — Sources like Reddit posts or blogs may contain outdated visa rules (OPT deadlines, SEVIS requirements change frequently). If a student retrieves an old chunk saying "you have 60 days grace period" but the rule changed, they could make a costly immigration mistake. Mitigation: prioritize official sources (USCIS, DHS) and add source + date metadata to each chunk.

2. Chunks splitting key information across boundaries — A chunk might contain "you must report your address..." but the consequence "...or risk losing your F-1 status" lands in the next chunk. If only the first chunk is retrieved, the answer is incomplete and potentially misleading. Mitigation: semantic chunking reduces this risk, and overlap provides a safety buffer.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->
     Document Ingestion     Chunking              Embedding + Vector Store
─────────────────   ──────────────────    ──────────────────────────
Reddit, USCIS,   →  Semantic chunking  →  all-MiniLM-L6-v2          
DHS, blogs,          via sentence-         (sentence-transformers)   
guides               transformers          stored in ChromaDB        
                                                    ↓
                                    ┌───────────────────────────┐
                                    │                           │
                               Retrieval                   Generation
                          ──────────────────          ─────────────────
                          top-k (3-5) chunks   →      Groq (LLaMA)
                          from ChromaDB               generates answer
                          via similarity search       using retrieved
                                                      chunks as context

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->
     Got it! Here's the corrected last row:

| Pipeline Stage | AI Tool | Input | Expected Output | How to Verify |
|---|---|---|---|---|
| Document Ingestion | Claude | List of 10 sources from planning.md | I'll give Claude my sources table and ask it to implement `ingest.py` that fetches and stores raw text from each URL using `requests` and `BeautifulSoup` | Check each source loads without errors and raw text is not empty |
| Chunking | Claude | Chunking Strategy section from planning.md | I'll give Claude my chunking strategy section and ask it to implement `chunk_text()` using semantic chunking with a 500 token max safeguard | Print sample chunks and verify no chunk cuts mid-sentence or mid-idea |
| Embedding + Vector Store | Claude | Chunking strategy + architecture diagram from planning.md | I'll give Claude my architecture diagram and ask it to implement `embed_and_store()` using `all-MiniLM-L6-v2` via sentence-transformers and store vectors in ChromaDB | Query ChromaDB directly and confirm vectors are stored correctly |
| Retrieval | Claude | Architecture diagram + top-k decision from planning.md | I'll give Claude my architecture diagram and ask it to implement `retrieve()` that returns top-3 most similar chunks for a given query from ChromaDB | Test with 3 sample questions and verify returned chunks are relevant |
| Generation | **Groq** | Retrieved top-3 chunks + student question | Groq's LLaMA model receives the chunks and question and generates a grounded answer | Run all 5 evaluation questions and verify answers match expected answers in evaluation plan |

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
