from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from app.auth import get_current_user
from app.models import ChatRequest, ChatResponse
from app.config import settings
from app.utils import get_chroma_client, get_or_create_collection, query_collection, format_results_as_context
import json
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

@router.post("/stream")
async def chat_stream(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        chroma_client = get_chroma_client(settings.CHROMA_DB_DIR)
        collection = get_or_create_collection(chroma_client, request.collection_name, embedding_model_name=settings.EMBEDDING_MODEL)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Collection error: {str(e)}")

    # Retrieve relevant chunks
    results = query_collection(collection, request.query, n_results=request.top_k)
    context = format_results_as_context(results)

    # Build the prompt
    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided context. "
        "If the context doesn't contain enough information to answer, say so. "
        "Always cite which source URLs your answer came from."
    )

    user_prompt = f"{context}\n\nQUESTION: {request.query}"

    # Build sources before streaming starts
    sources = []
    if results["metadatas"] and results["metadatas"][0]:
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            sources.append({
                "source": meta.get("source", "unknown"),
                "relevance": round(1 - dist, 3),
                "headers": meta.get("headers", ""),
            })

    async def event_generator():
        try:
            # Send sources first so the client has them immediately
            yield {"event": "sources", "data": json.dumps(sources)}

            # Stream the LLM response
            stream = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            )

            for chunk in stream:
                # Each chunk has a choices array; delta contains the new token
                if chunk.choices[0].delta.content is not None:
                    yield {
                        "event": "token",
                        "data": chunk.choices[0].delta.content
                    }

            # Signal completion
            yield {"event": "done", "data": ""}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    '''
    Docstring for chat
    
    :param request: Description
    :type request: ChatRequest
    :param current_user: Description
    :type current_user: dict
    '''
    try:
        chroma_client = get_chroma_client(settings.CHROMA_DB_DIR)
        collection = get_or_create_collection(chroma_client, request.collection_name, embedding_model_name=settings.EMBEDDING_MODEL)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Collection error: {str(e)}")

    # Retrieve relevant chunks
    results = query_collection(collection, request.query, n_results=request.top_k)
    context = format_results_as_context(results)

    # Build the prompt
    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided context. "
        "If the context doesn't contain enough information to answer, say so. "
        "Always cite which source URLs your answer came from."
    )

    user_prompt = f"{context}\n\nQUESTION: {request.query}"

    # Call OpenAI
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    # Build sources list from metadata
    sources = []
    if results["metadatas"] and results["metadatas"][0]:
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            sources.append({
                "source": meta.get("source", "unknown"),
                "relevance": round(1 - dist, 3),
                "headers": meta.get("headers", ""),
            })

    return ChatResponse(answer=answer, sources=sources)