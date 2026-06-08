"""
sources.py — The single source of truth for the corpus.

These are the 10 documents from planning.md (the "Documents" table).
Every downstream stage (ingestion, chunking, embedding) reads this list so the
pipeline stays in sync with the spec.

Each source carries metadata that the rest of the pipeline relies on:
    id          stable short id, used in output filenames
    name        human-readable source name
    url         where to fetch from
    type        "web" (HTML article) or "reddit" (JSON listing)
    official    True for government sources (USCIS, DHS) — used to prioritize
                authoritative immigration info over blogs/Reddit, per the
                "outdated or conflicting information" mitigation in planning.md
    description what subtopics the source covers
"""

SOURCES = [
    {
        "id": "01-internationalstudent",
        "name": "InternationalStudent.com",
        "url": "https://www.internationalstudent.com/study_usa/way-of-life/first-year-survival-guide-2026/",
        "type": "web",
        "official": False,
        "description": "First-year survival guide: immigration, academics, living expenses, mental health",
    },
    {
        "id": "02-boundless",
        "name": "Boundless.com",
        "url": "https://www.boundless.com/blog/top-student-visa-faqs-reddit",
        "type": "web",
        "official": False,
        "description": "F-1/M-1 visa FAQs from Reddit: proof of funds, processing times",
    },
    {
        "id": "03-visitorguard",
        "name": "VisitorGuard.com",
        "url": "https://www.visitorguard.com/the-international-students-survival-guide-essential-tips-for-studying-abroad/",
        "type": "web",
        "official": False,
        "description": "Health insurance, budgeting, banking, cultural adjustment",
    },
    {
        "id": "04-reddit-internationalstudents",
        "name": "r/internationalstudents",
        "url": "https://www.reddit.com/r/internationalstudents",
        "type": "reddit",
        "official": False,
        "description": "Reddit community: real experiences on visa, housing, culture, academics",
    },
    {
        "id": "05-reddit-f1visa",
        "name": "r/f1visa",
        "url": "https://www.reddit.com/r/f1visa",
        "type": "reddit",
        "official": False,
        "description": "Reddit community focused on F-1 visa, OPT, CPT, staying in status",
    },
    {
        "id": "06-studyinthestates-dhs",
        "name": "Study in the States — DHS",
        "url": "https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt",
        "type": "web",
        "official": True,
        "description": "Official DHS resource: CPT, OPT, SEVIS, maintaining F-1 status",
    },
    {
        "id": "07-scholaro",
        "name": "Scholaro.com",
        "url": "https://www.scholaro.com/db/News/how-to-adjust-to-the-us-education-system-268",
        "type": "web",
        "official": False,
        "description": "Adjusting to the US education system: grading, mental health, OPT, SEVIS",
    },
    {
        "id": "08-umass-interstride",
        "name": "UMass / Interstride",
        "url": "https://sbspathways.umass.edu/blog/2025/02/05/5-tips-for-first-year-international-students-in-the-us/",
        "type": "web",
        "official": False,
        "description": "Tips from former international students: visa prep, housing, insurance, college life",
    },
    {
        "id": "09-vcu-gradpod",
        "name": "VCU Grad Pod Podcast",
        "url": "https://gradpodvcu.substack.com/p/the-international-student-experience",
        "type": "web",
        "official": False,
        "description": "Podcast notes: culture, visa regulations, academic adjustment",
    },
    {
        "id": "10-uscis-f1",
        "name": "USCIS — F-1 Students Official Page",
        "url": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors",
        "type": "web",
        "official": True,
        "description": "Official USCIS page: F-1 visa rules, OPT, CPT, maintaining status",
    },
    {
        "id": "11-internationalstudent-cultureshock",
        "name": "InternationalStudent.com — Culture Shock",
        "url": "https://www.internationalstudent.com/study_usa/way-of-life/culture-shock/",
        "type": "web",
        "official": False,
        "description": "Stages and signs of culture shock and how to cope while studying in the US",
    },
    {
        "id": "12-internationalstudent-sociallife",
        "name": "InternationalStudent.com — Social Life",
        "url": "https://www.internationalstudent.com/study_usa/way-of-life/social-life/",
        "type": "web",
        "official": False,
        "description": "Adjusting to US social life, making friends, and campus social norms",
    },
]
