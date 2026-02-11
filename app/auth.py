import sqlite3
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import settings
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_db():
    '''
    Establishes a connection to the SQLite database and returns the connection object. The database file is named 'users.db'.
    '''
    
    conn = sqlite3.connect('users.db')

    if conn is not None:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        ''')
        conn.commit()
    return conn

def create_user(username: str, password: str):
    '''
    Creates a new user in the database with the provided username and password. The password is hashed using bcrypt before being stored in the database.
    '''
    conn = get_db()
    try:
        cursor = conn.cursor()
        hashed_password = context.hash(password)
        cursor.execute('INSERT INTO users (username, hashed_password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        if conn:
            conn.close()
    
def authenticate_user(username: str, password: str):
    '''
    Authenticates a user by verifying the provided password against the stored hashed password in the database.
    Returns True if authentication is successful, otherwise False.
    '''
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, hashed_password FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            stored_hashed_password = row[1]
            if context.verify(password, stored_hashed_password):
                return {"id": row[0], "username": username}
        return False
    except Exception as e:
        print(f"Error during authentication: {e}")
        return False
    finally:
        if conn:
            conn.close()

def create_access_token(data: dict):
    '''
    This function generates a JWT token using the SECRET_KEY and ALGORITHM defined in the settings.
    '''
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode['exp'] = expiry_time
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token

async def get_current_user(token: str = Depends(oauth2_scheme)):
    '''
    Docstring for get_current_user
    
    :param token: Description
    :type token: str
    '''

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "username": row[1]}
        raise HTTPException(status_code=401, detail="User not found")
    finally:        
        if conn:
            conn.close()