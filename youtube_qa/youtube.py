import re

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq

# 1. Load GROQ_API_KEY from .env
load_dotenv()

# 2. Put your YouTube link here
VIDEO_URL = "https://youtu.be/D74el9mvNak?si=PxKyGb55T0wUIzwE"


def extract_video_id(url: str) -> str:
    """Get the video ID from a youtube.com or youtu.be link."""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if not match:
        raise ValueError("Could not find a valid video ID in the URL.")
    return match.group(1)


def get_transcript(video_id: str) -> str:
    """Fetch the transcript text using youtube-transcript-api (v1.x)."""
    ytt = YouTubeTranscriptApi()
    fetched = ytt.fetch(video_id, languages=["en", "hi"])
    return " ".join(snippet.text for snippet in fetched)


def format_docs(docs) -> str:
    return "\n\n".join(d.page_content for d in docs)


def main():
    # 3. Get the transcript
    try:
        video_id = extract_video_id(VIDEO_URL)
        transcript = get_transcript(video_id)
    except Exception as e:
        print(f"Could not load transcript: {e}")
        print("Check that the video has captions and the URL is correct.")
        return

    # 4. Split into chunks
    docs = [Document(page_content=transcript, metadata={"video_id": video_id})]
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    print(f"Transcript loaded. Total chunks: {len(chunks)}")
    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {index} ---\n{chunk.page_content}")

    # 5. Embeddings (free, runs locally)
    # For Hindi videos use: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 6. Store in Chroma (in-memory)
    vectorstore = Chroma.from_documents(chunks, embeddings)

    # 7. Retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    # 8. LLM
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)

    # 9. Prompt
    prompt = ChatPromptTemplate.from_template(
        """Answer only from the transcript context below.
If the answer isn't there, say "Not mentioned in the video".

Context:
{context}

Question: {question}"""
    )

    # 10. Chain
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # 11. Ask questions
    print("\nAsk questions about the video. Type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in {"quit", "exit"}:
            break
        if not question:
            continue
        print("Bot:", chain.invoke(question), "\n")


if __name__ == "__main__":
    main()