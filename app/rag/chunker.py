from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

from app.core.config import settings



def chunk_text(text: str, source: str = "upload") -> list[Document]:
  
    text_splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    
    doc = Document(text=text, metadata={"source": source})

    nodes = text_splitter.get_nodes_from_documents([doc])

    return [
        Document(text=node.get_content(), metadata=node.metadata) for node in nodes
    ]

