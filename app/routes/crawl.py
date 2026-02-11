from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.models import CrawlRequest
from app.config import settings
from app.insert_docs import smart_chunk_markdown, is_sitemap, is_txt, crawl_recursive_internal_links, crawl_markdown_file, parse_sitemap, crawl_batch, extract_section_info
from app.utils import get_chroma_client, get_or_create_collection, add_documents_to_collection

router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.post("/")
async def crawl_website(request: CrawlRequest, current_user: str = Depends(get_current_user)):
    """
    Crawl one or more URLs and store the chunked content in a ChromaDB collection.
    
    This endpoint handles three types of URLs:
    - .txt files: Single markdown/text file fetch
    - Sitemaps: Parse XML to get all URLs, then batch crawl them
    - Regular pages: Recursively crawl following internal links
    """
    
    # Collect all crawl results first, then process them together.
    all_crawl_results = []
    
    for url in request.urls:
        try:
            if is_txt(url):
                results = await crawl_markdown_file(url)
            
            elif is_sitemap(url):
                # Parse the XML to extract all page URLs then crawl all of them in parallel
                sitemap_urls = parse_sitemap(url)
                if not sitemap_urls: # Don't fail it if sitemap is empty, just skip to next URL
                    continue

                # crawl_batch handles parallel crawling with concurrency limits
                results = await crawl_batch(sitemap_urls, max_concurrent=request.max_concurrent)
            
            else:
                results = await crawl_recursive_internal_links([url], max_depth=request.max_depth, max_concurrent=request.max_concurrent)
            
            # Using append would create a nested list, we want to flatten it into a single list of crawl results
            all_crawl_results.extend(results)
            
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            continue
    
    # Check if we got anything to process
    if not all_crawl_results:
        raise HTTPException(status_code=400, detail="No content was successfully crawled from any of the provided URLs")
    
    # ChromaDB needs three parallel lists
    ids = []
    documents = []
    metadatas = []
    chunk_idx = 0  # Global counter across all documents for unique IDs
    
    for doc in all_crawl_results:
        source_url = doc['url']
        markdown_content = doc['markdown']
        
        chunks = smart_chunk_markdown(markdown_content, max_len=request.chunk_size)
        
        for chunk in chunks:
            # Create a unique ID for this chunk
            ids.append(f"chunk-{chunk_idx}")
            
            # The actual text content that will be embedded and searched
            documents.append(chunk)
            
            # Metadata for this chunk
            meta = extract_section_info(chunk)
            meta["chunk_index"] = chunk_idx
            meta["source"] = source_url  # Track which URL this came from
            metadatas.append(meta)
            
            chunk_idx += 1
    
    if not documents:
        raise HTTPException(status_code=400, detail="Crawling succeeded but no text content was extracted")
    
    try:
        # Get a ChromaDB client pointing to our persistence directory
        client = get_chroma_client(settings.CHROMA_DB_DIR)
        
        # Get existing collection or create new one
        collection = get_or_create_collection(client, request.collection_name, embedding_model_name=settings.EMBEDDING_MODEL)
        
        # Insert all chunks in batches 
        add_documents_to_collection(collection, ids, documents, metadatas, batch_size=100)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert documents into ChromaDB: {str(e)}")
    
    return {
        "message": f"Successfully crawled and inserted {len(documents)} chunks",
        "collection": request.collection_name,
        "chunks_inserted": len(documents),
        "urls_processed": len(request.urls),
        "pages_crawled": len(all_crawl_results)
    }
        