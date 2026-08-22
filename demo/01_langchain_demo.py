"""
DEMO 1 - LangChain (Gemini)
===========================
Fokus: RANTAI linear. prompt | llm | parser

    python demo/01_langchain_demo.py
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel

from config import llm_dengan_fallback


def build(lapor=None):
    llm, _model = llm_dengan_fallback(lapor=lapor)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Kamu penulis teknis Bahasa Indonesia yang ringkas."),
        ("human", "Jelaskan {topik} dalam 3 poin bullet."),
    ])
    chain = prompt | llm | StrOutputParser()

    kritik = ChatPromptTemplate.from_template(
        "Perbaiki teks ini agar mudah dipahami pemula:\n\n{teks}"
    )
    bersusun = {"teks": chain} | kritik | llm | StrOutputParser()

    paralel = RunnableParallel(
        ringkas=chain,
        analogi=ChatPromptTemplate.from_template(
            "Beri 1 analogi sehari-hari untuk {topik}. Maksimal 2 kalimat."
        )
        | llm
        | StrOutputParser(),
    )
    return chain, bersusun, paralel


def jalankan(topik: str):
    """Generator event untuk UI: (tipe, teks)."""
    catatan = []
    chain, bersusun, paralel = build(lapor=catatan.append)
    for c in catatan:
        yield "step", c

    yield "step", "1/3 Chain dasar"
    for chunk in chain.stream({"topik": topik}):
        yield "token", chunk

    yield "step", "2/3 Chain bersusun (output chain 1 jadi input chain 2)"
    for chunk in bersusun.stream({"topik": topik}):
        yield "token", chunk

    yield "step", "3/3 Paralel (dua cabang bersamaan)"
    hasil = paralel.invoke({"topik": topik})
    yield "token", "**Ringkas**\n" + hasil["ringkas"] + "\n\n**Analogi**\n" + hasil["analogi"]

    yield "done", ""


def main():
    for tipe, teks in jalankan("vector database"):
        if tipe == "step":
            print(f"\n\n=== {teks} ===")
        elif tipe == "token":
            print(teks, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
