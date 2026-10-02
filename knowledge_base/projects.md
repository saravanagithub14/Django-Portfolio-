# Saravana Perumal R's projects and publications

## Saravana Perumal R's project: Simple GenAI App Using Ollama

---
type: project
organization: none (personal project)
period: not specified
tags: [generative ai, ollama, langchain, local llm, offline inference, chatbot, python, prompt engineering]
---

Simple GenAI App Using Ollama is a personal project by Saravana Perumal R. The goal was a lightweight chatbot that runs a large language model locally, so it can generate text and hold conversations offline without calling any external API.

Saravana built the app with Ollama to serve the local model and LangChain to handle the prompt and conversation logic, written in Python. Running locally removes API costs and keeps data on the machine, which suits private or offline use.

The project gave Saravana practice in generative AI, LangChain, Ollama, prompt engineering, and conversational AI. Saravana later extended the same local-model approach in a separate project, Q&A Chatbot Using Ollama (Open Source).

Tools used:

- Ollama
- LangChain
- Python

## Saravana Perumal R's project: End-to-End Q&A Chatbot with OpenAI

---
type: project
organization: none (personal project)
period: not specified
tags: [openai api, langchain, streamlit, chatbot, conversational memory, rag, prompt design]
---

End-to-End Q&A Chatbot with OpenAI is a personal project by Saravana Perumal R. Saravana designed and built a context-aware question-and-answer chatbot that gives real-time conversational answers through a web interface.

The chatbot uses the OpenAI API for the language model, LangChain to manage prompts and conversational memory, and Streamlit for the web front end. Conversational memory lets the bot keep track of earlier turns so follow-up questions make sense in context.

Through the project Saravana worked with the OpenAI API, LangChain, Streamlit, prompt design, conversational memory, and core RAG concepts. Saravana later rebuilt the same chatbot on open-source models in the project Q&A Chatbot Using Ollama (Open Source).

Tools used:

- OpenAI API
- LangChain
- Streamlit

## Saravana Perumal R's project: Q&A Chatbot Using Ollama (Open Source)

---
type: project
organization: none (personal project)
period: not specified
tags: [ollama, open source llm, local deployment, langchain, chatbot, low latency, offline inference]
---

Q&A Chatbot Using Ollama (Open Source) is a personal project by Saravana Perumal R. Saravana recreated an earlier OpenAI-based Q&A chatbot using Ollama and open-source models instead of a paid API.

The aim of the rebuild was efficient offline inference and low-latency responses with models running on local hardware. The project let Saravana compare a hosted API approach against a local open-source setup for the same chatbot, a practical tradeoff between cost and privacy on one side and model quality and hardware needs on the other.

Saravana built it with Ollama and LangChain, and it gave hands-on practice in open-source LLMs, local deployment, and chatbot development.

Tools used:

- Ollama
- Open-source LLMs
- LangChain

## Saravana Perumal R's project: RAG Document Q&A with Groq API and Llama3

---
type: project
organization: none (personal project)
period: not specified
tags: [rag, retrieval augmented generation, groq, llama3, chromadb, vector database, document q&a, lpu inference]
---

RAG Document Q&A with Groq API and Llama3 is a personal project by Saravana Perumal R. Saravana built a retrieval-augmented generation (RAG) chatbot that answers questions about documents.

The system stores document content as embeddings in ChromaDB, retrieves the most relevant chunks for each question, and passes them as context to the Llama3 model running on Groq Cloud. Saravana picked Groq for its high-speed LPU inference, which keeps responses fast.

The project gave Saravana working experience with RAG architecture, Groq Cloud, Llama3, ChromaDB, vector databases, and contextual retrieval.

Tools used:

- Groq API (Groq Cloud)
- Llama3
- ChromaDB
- LangChain

## Saravana Perumal R's project: Conversational Q&A Chatbot with PDF Support

---
type: project
organization: none (personal project)
period: not specified
tags: [pdf chatbot, document processing, chromadb, vector embeddings, langchain memory, streamlit, rag]
---

Conversational Q&A Chatbot with PDF Support is a personal project by Saravana Perumal R. Saravana developed an interactive chatbot that lets users upload PDF documents and hold a conversation about their contents.

The chatbot processes PDFs, converts their text into vector embeddings stored in ChromaDB, and uses LangChain retrievers to pull relevant passages for each question. LangChain memory keeps the conversation history so users can ask follow-up questions. A Streamlit interface handles uploads and chat.

The project built Saravana's skills in document processing, ChromaDB, vector embeddings, LangChain memory, and Streamlit interfaces.

Tools used:

- LangChain retrievers and memory
- ChromaDB
- Streamlit

## Saravana Perumal R's project: Search Engine GenAI App Using Tools and Agents

---
type: project
organization: none (personal project)
period: not specified
tags: [langchain agents, tools, semantic search, search engine, llm integration, agentic ai]
---

Search Engine GenAI App Using Tools and Agents is a personal project by Saravana Perumal R. Saravana built a semantic search engine where an LLM agent decides which tools to call to answer a query.

Saravana used LangChain Tools and Agents so the app could query data dynamically and retrieve contextual information, instead of following a fixed retrieval path. This is an early example of agentic AI in Saravana's work: the model chooses actions based on the question.

The project gave Saravana experience with LangChain agents, tool creation, contextual search, LLM integration, and semantic retrieval. It connects directly to the agentic AI focus of Saravana's current role as Gen AI Engineer at Blackbox Learning.

Tools used:

- LangChain Agents
- LangChain Tools

## Saravana Perumal R's project: Chat with SQL Database Using LangChain SQL Toolkit

---
type: project
organization: none (personal project)
period: not specified
tags: [natural language to sql, text to sql, langchain sql toolkit, langchain agents, database querying, streamlit]
---

Chat with SQL Database Using LangChain SQL Toolkit is a personal project by Saravana Perumal R. Saravana created a natural language interface that lets users ask questions about a SQL database in plain English instead of writing queries.

Saravana used LangChain's SQL Toolkit with an agent that translates the user's question into SQL, runs it against the database, and returns the answer. A Streamlit UI provides the chat interface.

The project gave Saravana practice with the LangChain SQL Toolkit, LangChain agents, database querying, natural language to SQL, and Streamlit UIs. It also draws on Saravana's SQL skills, one of Saravana's two programming languages alongside Python.

Tools used:

- LangChain SQL Toolkit and Agents
- SQL
- Streamlit

## Saravana Perumal R's project: Text Summarization Using LangChain

---
type: project
organization: none (personal project)
period: not specified
tags: [text summarization, langchain chains, stuff chain, mapreduce, refine chain, abstractive summarization, prompt engineering]
---

Text Summarization Using LangChain is a personal project by Saravana Perumal R. Saravana developed a system that produces concise, coherent summaries of text.

Saravana implemented three LangChain summarization strategies: Stuff, MapReduce, and Refine. Stuff puts the whole text into one prompt and suits short documents. MapReduce summarizes chunks separately and then combines them, which handles long documents. Refine builds the summary step by step, chunk by chunk. Working with all three let Saravana compare them across document lengths.

The project built Saravana's skills in LangChain chains, text summarization, prompt engineering, abstractive summarization, and evaluation metrics for summaries.

Tools used:

- LangChain (Stuff, MapReduce, Refine chains)

## Saravana Perumal R's project: YouTube and Website Content Summarization

---
type: project
organization: none (personal project)
period: not specified
tags: [summarization, youtube transcript api, web scraping, langchain document loaders, text splitters]
---

YouTube and Website Content Summarization is a personal project by Saravana Perumal R. Saravana built an application that takes a YouTube video or a website URL and returns a summary of its content.

The app pulls transcripts with the YouTube Transcript API and scrapes web pages, loads the content with LangChain document loaders, breaks it into pieces with text splitters, and summarizes it with an LLM.

The project gave Saravana experience with web scraping, the YouTube Transcript API, LangChain document loaders, text splitters, and RAG-style summarization. It builds on Saravana's separate Text Summarization Using LangChain project by adding real-world content sources.

Tools used:

- YouTube Transcript API
- LangChain document loaders and text splitters

## Saravana Perumal R's project: PDF Query RAG with AstraDB

---
type: project
organization: none (personal project)
period: not specified
tags: [astradb, vector search, rag, pdf query, cloud rag, document embeddings, langchain retriever]
---

PDF Query RAG with AstraDB is a personal project by Saravana Perumal R. Saravana built a scalable document query system that answers questions about PDF documents using retrieval-augmented generation.

Saravana used AstraDB, a cloud-hosted database, as the vector store for document embeddings, with a LangChain retriever handling vector search. Using a cloud vector store instead of a local one like ChromaDB is what makes this version scalable.

The project gave Saravana experience with AstraDB, vector search, LangChain retrievers, document embeddings, and cloud-based RAG. Together with Saravana's ChromaDB and Pinecone projects, it shows Saravana working across several vector database options.

Tools used:

- AstraDB
- LangChain retriever

## Saravana Perumal R's project: Multi-Language Code Assistant Using CodeLlama

---
type: project
organization: none (personal project)
period: not specified
tags: [codellama, code generation, coding assistant, langchain, developer tools, multilingual llm]
---

Multi-Language Code Assistant Using CodeLlama is a personal project by Saravana Perumal R. Saravana developed a coding assistant that generates syntactically correct code in multiple programming languages.

The assistant runs on CodeLlama, Meta's code-specialized language model, with LangChain managing prompts and interaction.

The project gave Saravana experience with CodeLlama, LangChain, code generation, multilingual LLMs, and developer tool automation. It extends Saravana's broader work with open-source models, which also includes Llama3 on Groq and local models through Ollama.

Tools used:

- CodeLlama
- LangChain

## Saravana Perumal R's project: Hybrid Search RAG with Pinecone

---
type: project
organization: none (personal project)
period: not specified
tags: [hybrid search, pinecone, rag, reciprocal rank fusion, rrf, semantic search, keyword search, vector database]
---

Hybrid Search RAG with Pinecone is a personal project by Saravana Perumal R. Saravana implemented a hybrid retrieval system that combines semantic search with keyword-based search.

Semantic search finds passages with similar meaning, while keyword search catches exact terms like names and codes that embeddings can miss. Saravana stored data in Pinecone, used LangChain retrievers for both search types, and merged the two result lists with Reciprocal Rank Fusion (RRF).

The project gave Saravana experience with hybrid retrieval, Pinecone, vector databases, RRF fusion, search optimization, and RAG architecture. It is the most advanced retrieval design in Saravana's project list.

Tools used:

- Pinecone
- LangChain retrievers
- Reciprocal Rank Fusion

## Saravana Perumal R's project: Hugging Face Integration Project

---
type: project
organization: none (personal project)
period: not specified
tags: [hugging face, transformers, langchain pipelines, text generation, summarization, open source models]
---

The Hugging Face Integration Project is a personal project by Saravana Perumal R. Saravana integrated open-source transformer models from Hugging Face into LangChain to build custom text generation and summarization pipelines.

Running Hugging Face models through LangChain lets an application swap between open-source models while keeping the same chain logic.

The project gave Saravana experience with Hugging Face Transformers, LangChain pipelines, model deployment, text generation, and API integration. Saravana also uses Hugging Face Spaces as a deployment option for generative AI apps.

Tools used:

- Hugging Face Transformers
- LangChain

## Saravana Perumal R's project: Generative AI with AWS Bedrock and Lambda

---
type: project
organization: none (personal project)
period: not specified
tags: [aws bedrock, aws lambda, sagemaker, cloud deployment, document q&a, blog generation, generative ai]
---

Generative AI with AWS Bedrock and Lambda is a personal project by Saravana Perumal R. Saravana designed and deployed generative AI applications on Amazon Web Services.

The project included two applications. The first is a document Q&A app built on AWS Bedrock, Amazon's managed service for foundation models. The second is a blog generation app that runs on AWS Lambda, Amazon's serverless compute service. Saravana also worked with SageMaker as part of the project.

The project gave Saravana hands-on experience with AWS Bedrock, Lambda functions, SageMaker, LLM deployment, cloud architecture, and API integration. It is Saravana's main cloud deployment project.

Tools used:

- AWS Bedrock
- AWS Lambda
- AWS SageMaker

## Saravana Perumal R's project: Fine-Tuning LLMs Using Lamini and Google Gemma

---
type: project
organization: none (personal project)
period: not specified
tags: [fine-tuning, lora, qlora, google gemma, lamini, transfer learning, custom dataset, model optimization]
---

Fine-Tuning LLM Models Using Lamini and Google Gemma is a personal project by Saravana Perumal R. Saravana carried out end-to-end fine-tuning of large language models, from preparing a custom dataset to training and optimizing the model.

Saravana used Lamini AI Cloud and Google's Gemma model, with LoRA and QLoRA for parameter-efficient training. LoRA trains small adapter layers instead of the full model, and QLoRA adds quantization to cut memory use further, so fine-tuning becomes possible on modest hardware.

The project gave Saravana experience with fine-tuning, LoRA and QLoRA, Lamini Cloud, custom dataset preparation, model optimization, and transfer learning.

Tools used:

- Lamini AI Cloud
- Google Gemma
- LoRA and QLoRA

## Saravana Perumal R's project: Constructing Insight, Real-Time Object Detection in Construction Sites

---
type: project
organization: none (personal project)
period: not specified
tags: [object detection, yolo, computer vision, deep learning, construction safety, pictor-v2, tensorflow, real-time]
---

Constructing Insight: Real-Time Object Detection in Construction Sites is a personal project by Saravana Perumal R. The goal was to improve safety and efficiency on construction sites by detecting and classifying objects such as buildings, equipment, and workers in real time.

Saravana trained YOLO object detection models on the Pictor-v2 dataset, aiming for accurate detection across varied visual conditions. The work covered image annotation, data preprocessing, model training in TensorFlow, and model evaluation.

The project gave Saravana skills in deep learning, object detection, the YOLO framework, image annotation, real-time processing, data preprocessing, TensorFlow, model evaluation, computer vision, and dataset management.

Tools used:

- YOLO
- TensorFlow
- Pictor-v2 dataset

## Saravana Perumal R's project: Automated Brain Tumor Detection and Classification Using Deep Learning (2024)

---
type: project
organization: none (personal project)
period: 2024
tags: [brain tumor detection, mri, medical imaging, cnn, transfer learning, deep learning, tensorflow, healthcare ai]
---

Automated Brain Tumor Detection and Classification Using Deep Learning is a personal project Saravana Perumal R completed in 2024. The goal was an automated system that detects and classifies brain tumors from MRI scans, to support diagnosis in regions with limited access to skilled neurosurgeons.

Saravana built the system with convolutional neural networks (CNNs) and transfer learning in TensorFlow. Transfer learning starts from a model pretrained on large image datasets, which helps when medical imaging data is limited. The system aimed to speed up MRI analysis and give precise tumor classification and segmentation.

The project combines Saravana's biomedical research background with deep learning. It built skills in deep learning, machine learning, image processing, medical imaging, data handling, and TensorFlow.

Tools used:

- TensorFlow
- CNNs and transfer learning

## Saravana Perumal R's project: Tweet Sentiment Sleuth, Decoding Public Opinion with Machine Learning

---
type: project
organization: none (personal project)
period: not specified
tags: [sentiment analysis, nlp, svm, tf-idf, twitter, text classification, machine learning, python]
---

Tweet Sentiment Sleuth: Decoding Public Opinion with Machine Learning is a personal project by Saravana Perumal R. Saravana analyzed sentiment in a dataset of 13,870 tweets, classifying each as positive, negative, or neutral to understand public perception on various topics.

Saravana built a pipeline that converts tweets to numeric features with TF-IDF and classifies them with a Support Vector Machine (SVM). Text preprocessing in the pipeline filters out the noise common in tweets.

The project gave Saravana skills in text preprocessing, data analysis, SVM classification, TF-IDF, noise handling, sentiment classification, data extraction, Python programming, and natural language processing (NLP).

Tools used:

- Python
- TF-IDF
- SVM classifier

## Saravana Perumal R's research project: 3D Bioprinting of Skin Using Cationized Gelatin and Oxidized Alginate (2020 to 2023)

---
type: project
organization: Sree Chitra Tirunal Institute for Medical Sciences and Technology
period: 2020 to 2023
tags: [3d bioprinting, skin tissue engineering, cationized gelatin, oxidized alginate, scaffolds, wound healing, regenerative medicine, sctimst]
---

From 2020 to 2023, as a Senior Research Fellow at Sree Chitra Tirunal Institute for Medical Sciences and Technology (SCTIMST), Saravana Perumal R worked on 3D bioprinting of skin.

The goal was to engineer scaffolds that mimic the extracellular matrix (ECM) of skin, for use in wound healing and skin grafting. Saravana used two biopolymers with complementary properties, cationized gelatin and oxidized alginate, to formulate bio-inks and print the scaffolds.

The work drew on Saravana's skills in polymeric scaffold development, bio-ink preparation and structural optimization, cell culture, and molecular analysis. It was Saravana's main long-term research project at SCTIMST and contributes to regenerative medicine.

## Saravana Perumal R's research project: Biosynthesized Nanosilver from Alginate Dialdehyde (2021)

---
type: project
organization: Sree Chitra Tirunal Institute for Medical Sciences and Technology
period: 2021
tags: [nanosilver, silver nanoparticles, alginate dialdehyde, green chemistry, nanotechnology, publication, sctimst]
---

In 2021, as a Senior Research Fellow at Sree Chitra Tirunal Institute for Medical Sciences and Technology, Saravana Perumal R worked on biosynthesizing nanosilver from alginate dialdehyde.

The goal was eco-friendly silver nanoparticles for biomedical and environmental use. Saravana's approach used the natural reducing and stabilizing properties of alginate derivatives, avoiding harsher chemical synthesis.

The work involved nanotechnology, green chemistry, and material characterization. It was published in 2021 as a research article titled "Biosynthesized Nanosilver from Alginate Dialdehyde: An In Vitro Evaluation" in the SSRN Electronic Journal.

## Saravana Perumal R's research project: Ferulic Acid Incorporated Antimicrobial Self-Crosslinking Hydrogel (2021)

---
type: project
organization: Sree Chitra Tirunal Institute for Medical Sciences and Technology
period: 2021
tags: [hydrogel, ferulic acid, antimicrobial, wound healing, biomaterials, self-crosslinking, publication, sctimst]
---

In 2021, as a Senior Research Fellow at Sree Chitra Tirunal Institute for Medical Sciences and Technology, Saravana Perumal R worked on a self-crosslinking hydrogel incorporating ferulic acid.

The goal was a biomaterial for antimicrobial and wound healing applications. The hydrogel combines the antioxidant and antimicrobial properties of ferulic acid with a self-crosslinking system that forms the gel without added crosslinkers.

The work used Saravana's skills in biomaterial engineering, antimicrobial testing, and hydrogel systems, with applications in regenerative medicine and infection control. It was published in 2021 as a research article titled "Ferulic Acid Incorporated Anti-Microbial Self Crosslinking Hydrogel" in the SSRN Electronic Journal.

## Saravana Perumal R's research project: Role of siRNA in Memory Formation in C. elegans (2019)

---
type: project
organization: not specified
period: 2019
tags: [sirna, rna interference, memory formation, c elegans, neurogenetics, molecular biology]
---

In 2019 Saravana Perumal R studied the role of small interfering RNA (siRNA) in memory formation in the model organism Caenorhabditis elegans.

The research explored siRNA-mediated gene silencing pathways and how they regulate neural plasticity and memory. The goal was to understand the genetic and molecular basis of memory.

The project used Saravana's skills in molecular biology, neurogenetics, RNA interference, and model organism research. It sits alongside Saravana's other research from the same period, which includes vaccine work at ICAR's Central Institute of Brackishwater Aquaculture and biomaterials research at Sree Chitra Tirunal Institute for Medical Sciences and Technology.

## Saravana Perumal R's research project: Periostin-Integrin Signaling in Hematopoiesis (Masters Dissertation, 2017 to 2018)

---
type: project
organization: Indian Institute of Science Education and Research, Thiruvananthapuram
period: November 2017 to November 2018
tags: [periostin, integrin, hematopoiesis, stem cells, bone marrow niche, masters dissertation, publication, iiser]
---

For the master's dissertation at IISER Thiruvananthapuram, from November 2017 to November 2018, Saravana Perumal R researched the role of periostin-integrin signaling in regulating hematopoiesis, the process that produces blood cells.

The study looked at how extracellular matrix components affect the behavior of stem and progenitor cells in the bone marrow niche, and the molecular mechanisms that govern blood cell development and maintenance. Saravana used cell culture, molecular biology, and microscopy to design and run the experiments.

The work led to a 2019 book chapter, "Periostin and Integrin Signaling in Stem Cell Regulation," in Advances in Experimental Medicine and Biology. It reflects Saravana's expertise in stem cell biology and molecular signaling pathways.

## Saravana Perumal R's book chapter: Emerging Strategies in Bone Tissue Engineering (2022)

---
type: project
organization: not specified
period: 2022
tags: [publication, book chapter, bone tissue engineering, regenerative medicine, biomaterials]
---

In 2022 Saravana Perumal R co-authored a book chapter titled "Emerging Strategies in Bone Tissue Engineering," published in the book Tissue Engineering on pages 469 to 492.

The chapter came out while Saravana was a Senior Research Fellow in biomedical technology at Sree Chitra Tirunal Institute for Medical Sciences and Technology (2019 to 2023), where Saravana's research focused on biomaterials and tissue engineering.

It is one of four publications on Saravana's record, alongside a 2019 chapter on periostin and integrin signaling and two 2021 research articles on nanosilver and an antimicrobial hydrogel.

## Saravana Perumal R's undergraduate project: Plant Protoplast Isolation from Brahmi (2016)

---
type: project
organization: University of Kerala
period: 2016
tags: [protoplast isolation, bacopa monnieri, brahmi, plant tissue culture, undergraduate dissertation, medicinal plants]
---

For the undergraduate dissertation in 2016, during the BSc in Botany and Biotechnology at the University of Kerala, Saravana Perumal R worked on isolating plant protoplasts from Brahmi (Bacopa monnieri), a medicinal plant known for nootropic and antioxidant properties.

The goal was to optimize protoplast isolation techniques for cellular studies and biotechnology uses such as genetic engineering and secondary metabolite production.

The project used Saravana's skills in plant tissue culture and enzymatic techniques. It is the earliest research project on Saravana's record.
