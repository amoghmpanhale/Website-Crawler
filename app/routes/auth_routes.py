from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_user, authenticate_user, create_access_token
from app.models import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(user: UserCreate):
    '''
    Endpoint for user registration. Accepts a UserCreate model containing the username 
    and password, creates a new user in the database, and returns a success message or
    an error if the username already exists.
    '''
    if create_user(user.username, user.password):
        return {"message": "User created successfully"}
    else:
        raise HTTPException(status_code=400, detail="Username already exists")
    
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    '''
    Endpoint for user login. Accepts form data containing the username and password, 
    authenticates the user, and returns a JWT token if authentication is successful.
    '''
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}



