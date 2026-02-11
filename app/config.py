from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    '''
    Settings class to hold configuration values for the application. Manage using Pydantic's BaseSettings for easy environment variable management.
    '''
    model_config  = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
    SECRET_KEY: str # Secret key for JWT token generation, loaded from environment variable
    ALGORITHM: str = "HS256" # Algorithm used for JWT token encoding
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Token expiration time in minutes
    OLLAMA_MODEL: str = "llama3.1:8b" # Ollama model to use for generating responses
    CHROMA_DB_DIR: str = "./chroma_db" # Directory for ChromaDB storage
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2" # SentenceTransformer model for generating embeddings
    CHUNK_SIZE: int = 1000 # Default chunk size for document processing
    MAX_CRAWL_DEPTH: int = 3 # Default maximum crawl depth for recursive crawling

settings = Settings()