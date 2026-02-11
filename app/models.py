from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    '''
    Pydantic model for user creation. This model defines the expected structure of the data when creating a new user, including username and password fields.
    '''
    username: str
    password: str

class Token(BaseModel):
    '''
    Pydantic model for JWT token response. This model defines the structure of the response when a token is generated, including the access token and its type.
    '''
    access_token: str
    token_type: str = "bearer"

class CreateCollection(BaseModel):
    '''
    Pydantic model for creating a new collection. This model defines the expected structure of the data when creating a new collection, including the collection name.
    '''
    name: str
    description: Optional[str] = None

class CollectionInfo(BaseModel):
    '''
    Pydantic model for collection information. This model defines the structure of the data when retrieving collection information, including the collection name and description.
    '''
    name: str
    description: Optional[str] = None
    document_count: int = 0

class ChatRequest(BaseModel):
    '''
    Pydantic model for chat request. This model defines the expected structure of the data when sending a chat request, including the collection name and the user query.
    '''
    query: str
    collection_name: str
    top_k: int = 5

class ChatResponse(BaseModel):
    '''
    Pydantic model for chat response. This model defines the structure of the data when receiving a chat response, including the generated answer and the source documents used to generate the answer.
    '''
    answer: str
    sources: list[dict] = []
