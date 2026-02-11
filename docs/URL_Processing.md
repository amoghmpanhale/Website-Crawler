# URL Processing Pipeline

This document describes how URLs submitted to the `/crawl` endpoint are processed and stored in ChromaDB.

## Overview

The crawl pipeline transforms web content into searchable vector embeddings through four stages: URL detection, crawling, chunking, and storage.
```
URLs → Detect Type → Crawl Content → Chunk Markdown → Store in ChromaDB
```

## Stage 1: URL Type Detection

Each URL is classified into one of three types, which determines the crawling strategy:

| URL Type | Detection Logic | Example |
|----------|-----------------|---------|
| Text file | Ends with `.txt` | `https://example.com/docs.txt` |
| Sitemap | Contains `sitemap` in path or ends with `sitemap.xml` | `https://example.com/sitemap.xml` |
| Regular page | Everything else | `https://example.com/about` |

## Stage 2: Crawling

Each URL type uses a different crawling strategy:

### Text Files
Single HTTP fetch using a headless browser. Returns the raw content as markdown. No link following.

### Sitemaps
The sitemap XML is parsed to extract all `<loc>` URLs. These URLs are then crawled in parallel using a batch crawler with configurable concurrency (`max_concurrent` parameter). This is efficient for documentation sites that provide a sitemap.

### Regular Pages
Recursive crawling that starts from the given URL, renders the page in a headless browser, extracts the content as markdown, then follows internal links up to a configurable depth (`max_depth` parameter). Each level of depth is processed before moving to the next, preventing infinite loops through URL normalization and visit tracking.

**Crawl output format:**
```json
[
  {"url": "https://example.com/page1", "markdown": "# Page Title\n\nContent..."},
  {"url": "https://example.com/page2", "markdown": "# Another Page\n\nMore content..."}
]
```

## Stage 3: Chunking

Raw markdown is split into smaller pieces for two reasons: embedding models have token limits, and smaller chunks provide more precise search results.

### Chunking Strategy

The `smart_chunk_markdown` function uses hierarchical splitting:

1. First, split by `# ` (h1 headers)
2. If any section exceeds `chunk_size`, split by `## ` (h2 headers)
3. If still too large, split by `### ` (h3 headers)
4. If still too large, split by character count as a fallback

This approach keeps semantically related content together. A section about "Installation" stays in one chunk rather than being split mid-paragraph.

### Chunk Size

The `chunk_size` parameter (default: 1000 characters) controls the maximum chunk length. Smaller chunks mean more precise retrieval but less context per result. Larger chunks provide more context but may include irrelevant content.

## Stage 4: ChromaDB Storage

Each chunk is stored in ChromaDB with three components:

### Document ID
A unique identifier in the format `chunk-{index}` where index is a global counter across all chunks in the request. Example: `chunk-0`, `chunk-1`, `chunk-42`.

### Document Content
The raw text of the chunk. This is what gets embedded by the SentenceTransformer model (`all-MiniLM-L6-v2`) and what gets returned in search results.

### Metadata
Each chunk stores metadata for filtering and display:

| Field | Description | Example |
|-------|-------------|---------|
| `source` | Original URL the content came from | `https://example.com/docs` |
| `chunk_index` | Position in the chunking sequence | `7` |
| `headers` | Headers found in this chunk | `# Installation; ## Requirements` |
| `char_count` | Character count of the chunk | `847` |
| `word_count` | Word count of the chunk | `142` |

## Embedding and Indexing

When documents are added to ChromaDB, the following happens automatically:

1. The SentenceTransformer model converts each chunk's text into a 384-dimensional vector
2. ChromaDB indexes these vectors using HNSW (Hierarchical Navigable Small World) algorithm
3. The index uses cosine distance for similarity measurement
4. Documents are inserted in batches of 100 to manage memory usage

## Example Flow

Given this request:
```json
{
  "urls": ["https://docs.example.com/guide"],
  "collection_name": "my-docs",
  "chunk_size": 1000,
  "max_depth": 2
}
```

The pipeline might produce:

1. **Detection:** Regular page (not .txt, not sitemap)
2. **Crawling:** Visits `/guide`, follows links to `/guide/install` and `/guide/usage` (depth 1), then their subpages (depth 2)
3. **Result:** 15 pages crawled, each with markdown content
4. **Chunking:** 15 pages split into 47 chunks (varies by content length)
5. **Storage:** 47 documents added to collection `my-docs` with embeddings and metadata

## Error Handling

The pipeline is designed for partial success:

- If one URL fails to crawl, others continue processing
- If a sitemap contains invalid URLs, valid ones are still crawled
- If chunking produces no content from a page, other pages still process
- Only if zero content is extracted does the endpoint return an error

This approach prioritizes getting useful results over strict error handling.