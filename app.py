"""
app.py — Gradio web UI for The Unofficial Guide (Milestone 5).

Thin presentation layer over query.ask() — all retrieval + grounded generation
lives in query.py. Run this to demo the system in a browser.

Usage:
    python app.py
    # then open the local URL it prints (http://127.0.0.1:7860)
"""

import gradio as gr

from query import ask

EXAMPLES = [
    "What documents do I need to open a bank account in the US as an international student?",
    "How many days do I have to report an address change to maintain my F-1 status?",
    "How many months of full-time CPT disqualifies me from OPT?",
    "What are common signs of culture shock international students experience in the US?",
    "What is the grace period after completing my program before I must leave the US?",
]


def handle_query(question: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown(
        "# The Unofficial Guide\n"
        "Ask anything about surviving as an international student in the US — "
        "visas, housing, banking, OPT/CPT, culture shock. Answers are grounded "
        "in collected sources and cite where they came from."
    )
    inp = gr.Textbox(label="Your question",
                     placeholder="e.g. What is OPT and when can I apply?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
