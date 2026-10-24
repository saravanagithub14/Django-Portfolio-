"""
V.E.R.A.'s specialist agents. `chatbot/rag/pipeline.py::run` is the orchestrator: it runs the guard,
routes the message (one LLM call) and hands it to one agent.

    guard.py      prompt-injection checks on the way in, prompt-leak and phone-number checks on the way out
    privacy.py    deflects questions about Saravana's private life (no LLM call)
    tutor.py      teaches any topic (intuition, analogy, how it works), bridging to Saravana's related work
    portfolio.py  answers about Saravana from the knowledge base and website (the RAG answer step)

Each agent returns the reply plus what the orchestrator logs; none of them raise on LLM failure
(a None reply makes the view fall back to keyword matching).
"""
