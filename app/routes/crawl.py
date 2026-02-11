from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.models import CrawlRequest
from app.insert_docs import smart_chunk_markdown, is_sitemap, is_txt, crawl_recursive_internal_links, crawl_markdown_file, parse_sitemap, crawl_batch, extract_section_info
from app.utils import get_chroma_client, get_or_create_collection, add_documents_to_collection

router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.post("/")
async def crawl_website(url: CrawlRequest, current_user: str = Depends(get_current_user)):
    '''
    Endpoint to initiate a web crawl. Requires user authentication.
    Accepts a URL as input and starts the crawling process for that URL.
    Returns a success message or an error message if the crawl fails.
    '''
    try:
        # Detect URL type and crawl accordingly
        if is_txt(url.url):
            crawl_results = await crawl_markdown_file(url.url)
        elif is_sitemap(url.url):
            sitemap_urls = parse_sitemap(url.url)
            if not sitemap_urls:
                raise HTTPException(status_code=400, detail="No URLs found in sitemap")
            crawl_results = await crawl_batch(sitemap_urls)
        else:
            crawl_results = await crawl_recursive_internal_links([url.url])

        # Process and insert results into ChromaDB
        ids, documents, metadatas = [], [], []
        chunk_idx = 0
        for doc in crawl_results:
            url = doc['url']
            md = doc['markdown']
            chunks = smart_chunk_markdown(md)
            for chunk in chunks:
                ids.append(f"chunk-{chunk_idx}")
                documents.append(chunk)
                meta = extract_section_info(chunk)
                meta["chunk_index"] = chunk_idx
                meta["source"] = url
                metadatas.append(meta)
                chunk_idx += 1

        if not documents:
            raise HTTPException(status_code=400, detail="No documents found to insert")

        client = get_chroma_client("./chroma_db")
        collection = get_or_create_collection(client, "docs")
        add_documents_to_collection(collection, ids, documents, metadatas)

        return {"message": f"Crawled and inserted {len(documents)} chunks successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))