import uuid
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
Your task is to generate a structured JSON output containing both a brief chunk title and a one-sentence summary that inform viewers about the chunk content.

Guidelines:
- Chunk Title: A short, generalized phrase that broadly describes the topic.
- Example: If the chunk is about apples, generalize it to “Food.”
- If the chunk is about a specific month, generalize it to “Dates & Times.”
- Chunk Summary: A concise, one-sentence explanation that clarifies the chunk content and may include guidance on what additional information should be added.
- Example: If given “Greg likes to eat pizza,” the summary should be “This chunk contains information about the types of food Greg likes to eat.”
"""

CHUNK_REFINEMENT_PROMPT = """
You are the steward of a group of chunks, where each chunk represents a set of sentences discussing a similar topic. 
Your task is to generate a structured JSON output containing both an updated chunk title and an updated chunk summary when a new proposition is added to the chunk.

Guidelines:
- Chunk Title: A short, generalized phrase that broadly describes the topic.
- Example: If the chunk is about apples, generalize it to “Food.”
- If the chunk is about a specific month, generalize it to “Dates & Times.”
- Chunk Summary: A concise, one-sentence explanation that clarifies the chunk content and may include guidance on what additional information should be added.
- Example: If given “Greg likes to eat pizza,” the summary should be “This chunk contains information about the types of food Greg likes to eat.”
- You will be provided with:
- A group of propositions currently in the chunk
- The chunk existing summary
- The chunk existing title (if available)
"""

CHUNK_ALLOCATION_PROMPT = """
Determine whether or not the "Proposition" should belong to any of the existing chunks.

A proposition should belong to a chunk of their meaning, direction, or intention are similar.
The goal is to group similar propositions and chunks.

If you think a proposition should be joined with a chunk, return the chunk id.
If you do not think an item should be joined with an existing chunk, just return "No chunks" as Chunk ID.

Example:
Input:
    - Proposition: "Greg really likes hamburgers"
    - Current Chunks:
        - Chunk ID: 2n4l3d
        - Chunk Name: Places in San Francisco
        - Chunk Summary: Overview of the things to do with San Francisco Places

        - Chunk ID: 93833k
        - Chunk Name: Food Greg likes
        - Chunk Summary: Lists of the food and dishes that Greg likes
Output: 93833k
"""

class Sentences(BaseModel):
    """Extracting propositions from a document"""
    sentences: List[str]
    
class ChunkID(BaseModel):
    """Extracting the chunk id"""
    chunk_id: Optional[str]

class ChunkAnalysis(BaseModel):
    """ Extracting the chunk summary abd title from proposition"""
    chunk_summary: str
    chunk_title: str

class AgenticChunker:
    def __init__(self, llm=None):
        self.chunks = {}
        # Whether or not to update/refine summaries and titles as you get new information
        self.generate_new_metadata_ind = True
        self.llm = llm
        self.chunk_summary_llm = llm.with_structured_output(schema=ChunkAnalysis)
        self.chunk_id_llm = llm.with_structured_output(schema=ChunkID)

    def add_propositions(self, propositions):
        for proposition in propositions:
            self.add_proposition(proposition)

    
    def add_proposition(self, proposition):
        # If it's your first chunk, just make a new chunk and don't check for others
        if len(self.chunks) == 0:
            self._create_new_chunk(proposition)
            return
        
        chunk_id = self._find_relevant_chunk(proposition)

        # If a chunk was found then add the proposition to it
        if chunk_id:
            logger.debug(f"Chunk Found ({self.chunks[chunk_id]['chunk_id']}), adding to: {self.chunks[chunk_id]['title']}")
            self.add_proposition_to_chunk(chunk_id, proposition)
        else:
            self._create_new_chunk(proposition)
        

    def add_proposition_to_chunk(self, chunk_id, proposition):
        # Add then
        self.chunks[chunk_id]['propositions'].append(proposition)

        prompt_template = ChatPromptTemplate.from_messages(
            ("system", CHUNK_REFINEMENT_PROMPT),
            ("user", "Chunk's propositions:\n{proposition}\n\nCurrent chunk summary:\n{current_summary}")
        )
        prompt = prompt_template.invoke({"proposition": "\n".join(self.chunks[chunk_id]['propositions']), "current_summary": self.chunks[chunk_id]['summary']})
        result = self.chunk_summary_llm.invoke(prompt)
        
        # Then grab a new summary
        if self.generate_new_metadata_ind:
            self.chunks[chunk_id]['summary'] = result.chunk_summary
            self.chunks[chunk_id]['title'] = result.chunk_title


    def _create_new_chunk(self, proposition):
        new_chunk_id = str(uuid.uuid4())
        chunk_analysis_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHUNK_SUMMARY_PROMPT),
                ("user", "Proposition: {proposition}"),
            ]
        )
        prompt = chunk_analysis_prompt.invoke({"proposition": proposition})
        chunk_analysis = self.chunk_summary_llm.invoke(prompt)

        self.chunks[new_chunk_id] = {
            'chunk_id' : new_chunk_id,
            'propositions': [proposition],
            'title' : chunk_analysis.chunk_title,
            'summary': chunk_analysis.chunk_summary,
            'chunk_index' : len(self.chunks)
        }
        logger.debug(f"New Chunk Created ({new_chunk_id}): {chunk_analysis.chunk_title}")
    
    def get_chunk_outline(self):
        """
        Get a string which represents the chunks you currently have.
        This will be empty when you first start off
        """
        chunk_outline = ""

        for _, chunk in self.chunks.items():
            single_chunk_string = f"""Chunk ({chunk['chunk_id']}): {chunk['title']}\nSummary: {chunk['summary']}\n\n"""
            chunk_outline += single_chunk_string
        
        return chunk_outline

    def _find_relevant_chunk(self, proposition):
        current_chunk_outline = self.get_chunk_outline()

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ( "system", CHUNK_ALLOCATION_PROMPT),
                ("user", "Current Chunks:\n--Start of current chunks--\n{current_chunk_outline}\n--End of current chunks--\n\nDetermine if the following statement should belong to one of the chunks outlined:\n{proposition}"),
            ]
        )
        prompt = prompt_template.invoke({"current_chunk_outline": current_chunk_outline, "proposition": proposition})
        result = self.chunk_id_llm.invoke(prompt)
        return None if 'No chunks' in result.chunk_id else result.chunk_id


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
        chunker.add_propositions(propositions)
        for chunk in chunker.chunks.values():
            chunk_id += 1
            docmeta = doc_metadata.copy()
            docmeta.update({"chunk_id": chunk_id})
            docmeta.update({"chunk_title": chunk['title']})
            docmeta.update({"chunk_summary": chunk['summary']})
            page_content = "\n".join(chunk['propositions'])
            yield Document(
                page_content=f"{chunk['title']}\n\n{chunk['summary']}\n\n{page_content}",
                metadata=docmeta
            )
        
        
            
            
        
    