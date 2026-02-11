from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.config import settings
from app.models import CreateCollection, CollectionInfo
import chromadb

chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)

router = APIRouter(prefix="/collections", tags=["collections"])

@router.get("/")
def list_collections(current_user: str = Depends(get_current_user)):
    '''
    Endpoint to list all collections in the ChromaDB database. Requires user authentication.
    Returns a list of collection names.
    '''
    collections = chroma_client.list_collections()
    return [col.name for col in collections]

@router.post("/")
def create_collection(collection: CreateCollection, current_user: str = Depends(get_current_user)):
    '''
    Endpoint to create a new collection in the ChromaDB database. Requires user authentication.
    Accepts a collection name as input and creates the collection if it does not already exist.
    Returns the collection information or an error message if the collection already exists.
    '''
    try:
        collection = chroma_client.get_or_create_collection(name=collection.name)
        return {"name": collection.name, "document_count": collection.count()}
    except chromadb.errors.InvalidArgumentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete("/{name}")
def delete_collection(name: str, current_user: dict = Depends(get_current_user)):
    '''
    Endpoint to delete a collection from the ChromaDB database. Requires user authentication.
    Accepts a collection name as input and deletes the collection if it exists.
    Returns a success message or an error message if the collection does not exist.
    '''
    try:
        chroma_client.delete_collection(name=name)
        return {"message": f"Collection '{name}' deleted successfully"}
    except chromadb.errors.InvalidArgumentError as e:
        raise HTTPException(status_code=404, detail=str(e))
    