"""
DEMO 1 - LangChain
==================
Fokus: RANTAI (chain) linear. Input -> prompt -> LLM -> parser -> output.
Cocok untuk: RAG sederhana, summarizer, klasifikasi, tool calling 1 agent.

Jalankan:
    pip install langchain langchain-openai
    export OPENAI_API_KEY=sk-...
    python 01_langchain_demo.py
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- 1. Chain dasar: prompt | llm | parser (LCEL pipe operator) ---
prompt = ChatPromptTemplate.from_messages([
    ("system", "Kamu penulis teknis Bahasa Indonesia yang ringkas."),
    ("human", "Jelaskan {topik} dalam 3 poin bullet."),
])
chain = prompt | llm | StrOutputParser()

# --- 2. Chain bersusun: hasil chain 1 jadi input chain 2 ---
kritik_prompt = ChatPromptTemplate.from_template(
    "Perbaiki teks ini agar lebih mudah dipahami pemula:\n\n{teks}"
)
chain_lanjutan = {"teks": chain} | kritik_prompt | llm | StrOutputParser()

# --- 3. Paralel: dua cabang jalan bersamaan ---
paralel = RunnableParallel(
    ringkas=chain,
    analogi=ChatPromptTemplate.from_template("Beri 1 analogi sehari-hari untuk {topik}.")
    | llm
    | StrOutputParser(),
)


def main():
    topik = "vector database"

    print("=== 1. CHAIN DASAR ===")
    print(chain.invoke({"topik": topik}))

    print("\n=== 2. CHAIN BERSUSUN ===")
    print(chain_lanjutan.invoke({"topik": topik}))

    print("\n=== 3. PARALEL ===")
    hasil = paralel.invoke({"topik": topik})
    print("Ringkas:", hasil["ringkas"])
    print("Analogi:", hasil["analogi"])

    print("\n=== 4. STREAMING ===")
    for chunk in chain.stream({"topik": topik}):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
