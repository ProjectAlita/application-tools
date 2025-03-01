from json import dumps
from typing import Generator
from logging import getLogger
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import TokenTextSplitter

from typing import Optional, List
from langchain_core.pydantic_v1 import BaseModel
from ..utils import tiktoken_length

logger = getLogger(__name__)

PROPOSAL_INDEXER = """
Decompose the "Content" into clear and simple propositions, ensuring they are interpretable out of
context.
1. Split compound sentence into simple sentences. Maintain the original phrasing from the input
whenever possible.
2. For any named entity that is accompanied by additional descriptive information, separate this
information into its own distinct proposition.
3. Decontextualize the proposition by adding necessary modifier to nouns or entire sentences
and replacing pronouns (e.g., "it", "he", "she", "they", "this", "that") with the full name of the
entities they refer to.
4. Present the results as a list of strings, formatted in JSON.

Example:

Input: Title: ¯Eostre. Section: Theories and interpretations, Connection to Easter Hares. Content:
The earliest evidence for the Easter Hare (Osterhase) was recorded in south-west Germany in
1678 by the professor of medicine Georg Franck von Franckenau, but it remained unknown in
other parts of Germany until the 18th century. Scholar Richard Sermon writes that "hares were
frequently seen in gardens in spring, and thus may have served as a convenient explanation for the
origin of the colored eggs hidden there for children. Alternatively, there is a European tradition
that hares laid eggs, since a hare is scratch or form and a lapwing is nest look very similar, and
both occur on grassland and are first seen in the spring. In the nineteenth century the influence
of Easter cards, toys, and books was to make the Easter Hare/Rabbit popular throughout Europe.
German immigrants then exported the custom to Britain and America where it evolved into the
Easter Bunny."
Output: [ "The earliest evidence for the Easter Hare was recorded in south-west Germany in
1678 by Georg Franck von Franckenau.", "Georg Franck von Franckenau was a professor of
medicine.", "The evidence for the Easter Hare remained unknown in other parts of Germany until
the 18th century.", "Richard Sermon was a scholar.", "Richard Sermon writes a hypothes about
the possible explanation for the connection between hares and the tradition during Easter", "Hares
were frequently seen in gardens in spring.", "Hares may have served as a convenient explanation
for the origin of the colored eggs hidden in gardens for children.", "There is a European tradition
that hares laid eggs.", "A hare is scratch or form and a lapwing nest look very similar.", "Both
hares and lapwing nests occur on grassland and are first seen in the spring.", "In the nineteenth
century the influence of Easter cards, toys, and books was to make the Easter Hare/Rabbit popular
throughout Europe.", "German immigrants exported the custom of the Easter Hare/Rabbit to
Britain and America.", "The custom of the Easter Hare/Rabbit evolved into the Easter Bunny in
Britain and America."]


<Content>
{input}
<Content>
"""

CHUNK_SUMMARY_PROMPT = """
You are the steward of a group of chunks, where each chunk represents a set of sentences discussing a similar topic.
Your task is to generate a structured List of JSON output containing both a brief chunk title and a set of one-sentence summary that inform viewers about the chunk content, it also have a list of propositions from user message associated with chunk

Guidelines:
- chunk_title: A short, generalized phrase that broadly describes the topic.
- Example: If the chunk is about apples, generalize it to “Food.”
- If the chunk is about a specific month, generalize it to “Dates & Times.”
- chunk_summary: A concise, one-sentence explanation that clarifies the chunk content and may include guidance on what additional information should be added.
- Example: If given “Greg likes to eat pizza,” the summary should be “This chunk contains information about the types of food Greg likes to eat.
- propositions: A list of propositions from user message associated with chunk
"""

CHUNK_REFINEMENT_PROMPT = """
You are the steward of a group of chunks, where each chunk represents a set of sentences discussing a similar topic. 
Your task is to generate a structured JSON output containing both an updated chunk title and an updated chunk summary to better represent propositions in chunk

Guidelines:
- chunk_title: Updated chunk title that represents information provided in chunk in one concise manned.
- Example: If the chunk is about apples, generalize it to “Food.”
- If the chunk is about a specific month, generalize it to “Dates & Times.”
- Chunk Summary: An explanation that clarifies the chunk content with summary of the information available in propositions.

You will be provided with:
- A group of propositions currently in the chunk
- Existing chunk existing summary
- Existing chunk existing title
"""


class Sentences(BaseModel):
    """Extracting propositions from a document"""
    sentences: List[str]
    
class ChunkRefinement(BaseModel):
    """Extracting the chunk details"""
    chunk_title: str
    chunk_summary: str

class ChunkDetails(BaseModel):
    """Extracting the chunk details"""
    chunk_title: str
    chunk_summary: str
    propositions: List[str]

class ChunkAnalysis(BaseModel):
    """ Extracting the chunk summary abd title from proposition"""
    chunks: List[ChunkDetails]

class AgenticChunker:
    def __init__(self, llm=None):
        self.chunks = {}
        # Whether or not to update/refine summaries and titles as you get new information
        self.generate_new_metadata_ind = True
        self.llm = llm
        self.chunk_summary_llm = llm.with_structured_output(schema=ChunkAnalysis)
        self.chunk_refinement_llm = llm.with_structured_output(schema=ChunkRefinement)

    def create_chunkes(self, proposition):
        chunk_analysis_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHUNK_SUMMARY_PROMPT),
                ("user", "Proposition: {proposition}"),
            ]
        )
        prompt = chunk_analysis_prompt.invoke({"proposition": proposition})
        return self.chunk_summary_llm.invoke(prompt)
            
    def chunk_refinement(self, chunk):
        chunk_refinement_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHUNK_REFINEMENT_PROMPT),
                ("user", "Chunk: {chunk}"),
            ]
        )
        prompt = chunk_refinement_prompt.invoke({"chunk": dumps(chunk)})
        result = self.chunk_refinement_llm.invoke(prompt)
        return result

    def add_propositions(self, propositions):
        self.create_chunkes(propositions)
        for chunk in self.chunks:
            refined = self.chunk_refinement(chunk)
            yield {
                "title": refined.chunk_title,
                "summary": refined.chunk_summary,
                "propositions": chunk.propositions
            }
            


def proposal_chunker(file_content_generator: Generator[Document, None, None], config: dict, *args, **kwargs):
    llm = config.get("llm")
    max_tokens_doc = config.get("max_doc_tokens", 4096)
    if not llm:
        raise ValueError("Missing LLM model")
    structured_llm = llm.with_structured_output(schema=Sentences)
    for doc in file_content_generator:
        chunk_id = 0
        doc_metadata = doc.metadata
        doc_content = doc.page_content
        if tiktoken_length(doc_content) > max_tokens_doc:
            splits = TokenTextSplitter(encoding_name='cl100k_base', 
                                       chunk_size=max_tokens_doc, chunk_overlap=0
                                       ).split_text(doc_content)
        else:
            splits = [doc_content]
        propositions = []
        for split in splits:
            prompt_template = ChatPromptTemplate.from_messages(("user", PROPOSAL_INDEXER))
            prompt = prompt_template.invoke({"input": split})
            result = structured_llm.invoke(prompt)
            propositions.extend(result.sentences)
        chunker = AgenticChunker(llm=llm)
        for chunk in chunker.add_propositions(propositions):
            chunk_id += 1
            docmeta = doc_metadata.copy()
            docmeta.update({"chunk_title": chunk['title']})
            docmeta.update({"chunk_summary": chunk['summary']})
            page_content = "\n".join(chunk['propositions'])
            yield Document(
                metadata=docmeta,
                page_content=f"{chunk['title']}\n\n{chunk['summary']}\n\n{page_content}",
            )
        
        
            
            
        
    