"""Canned answers used when no LLM provider is available (mock provider, or every provider failed)."""
from portfolio.models import Project, Skill, Job

# Educational concept explanations
CONCEPT_ANSWERS = {
    'machine learning': "Machine Learning (ML) is a branch of artificial intelligence where algorithms learn underlying patterns from data to make predictions or decisions without explicit rule-based programming. In my work as an AI Engineer, I design and deploy ML pipelines spanning statistical classification, regression, and model evaluation.",
    'deep learning': "Deep Learning is a specialized subfield of machine learning inspired by biological neural networks. It utilizes multi-layered neural architectures to automatically extract features from complex, high-dimensional data like images, audio, and text.",
    'neural network': "Artificial Neural Networks (ANNs) are computational models inspired by biological brain structures. They consist of interconnected nodes (neurons) arranged in layers that process inputs, apply learned weights, and pass signals forward to produce outputs.",
    'rag': "Retrieval-Augmented Generation (RAG) is an architectural pattern that connects Large Language Models (LLMs) with external knowledge sources (like FAISS vector databases). It retrieves relevant document context before generating answers, ensuring precise, grounded, and hallucination-free responses.",
    'generative ai': "Generative AI refers to artificial intelligence models capable of generating new text, images, audio, or code based on patterns learned from vast training datasets. I specialize in building agentic Gen AI systems and RAG pipelines.",
    'llm': "Large Language Models (LLMs) are massive neural networks trained on vast text corpora to understand, reason, and generate human language. Examples include Llama 3, GPT-4, and Claude.",
    'computer vision': "Computer Vision is a field of AI enabling computers to interpret and analyze visual information from images and video feeds, using convolutional neural networks (CNNs) and vision transformers."
}


# Fallback answering function based on database keyword matching & concept lookup
def get_keyword_fallback_response(query, profile):
    query_lower = query.lower()

    for concept_key, concept_answer in CONCEPT_ANSWERS.items():
        if concept_key in query_lower:
            return concept_answer

    # 1. Check Projects
    matched_projects = []
    for p in Project.objects.all():
        if p.title.lower() in query_lower or any(t.lower() in query_lower for t in p.tag_list) or (p.description and p.description.lower() in query_lower):
            matched_projects.append(p)

    if matched_projects:
        parts = []
        for p in matched_projects[:3]:
            text = f"{p.title} is one I'm proud of. {p.description}"
            if p.github_url and p.github_url != '#':
                text += f" You can find the code at {p.github_url}"
            parts.append(text)
        intro = "Sure, here's what I've worked on along those lines." if len(parts) > 1 else "Yes, I've worked on that."
        return intro + "\n\n" + "\n\n".join(parts)

    # 2. Check Skills
    matched_skills = []
    for s in Skill.objects.all():
        if s.name.lower() in query_lower or (s.context and s.context.lower() in query_lower):
            matched_skills.append(s)

    if matched_skills:
        names = [s.name for s in matched_skills]
        joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
        response_text = f"Yes, I work with {joined} regularly."
        contexts = [s.context for s in matched_skills if s.context]
        if contexts:
            response_text += f" Mostly for things like {contexts[0][0].lower() + contexts[0][1:]}."
        return response_text

    # 3. Check Experience / Jobs
    matched_jobs = []
    for j in Job.objects.all():
        if j.title.lower() in query_lower or j.company.lower() in query_lower or j.description.lower() in query_lower:
            matched_jobs.append(j)

    if matched_jobs:
        return "\n\n".join(
            f"I worked as a {j.title} at {j.company} ({j.period}). {j.description}" for j in matched_jobs[:2]
        )

    # General fallback
    contact_email = profile.email if profile else "saravanaperumalr14@gmail.com"
    return (
        f"Hey! I'm Saravana. Happy to chat about my work in AI engineering and data science, "
        f"the projects I've built, or the tools I use day to day. "
        f"If you'd rather talk directly, you can reach me at {contact_email}."
    )
