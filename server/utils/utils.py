from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordBearer
from jose import JWTError, jwt

from server.utils.config import ALGORITHM, SECRET_KEY
from server.database.btchApiDB import SessionLocal
from server.database import crud
from server.schemas import schemas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
PASSWORD_MIN_LENGTH = 3


def elo(A, B, score):
    """
    A : Player One rating
    B : Player Two rating
    score : Game's outcome, between 1 and 0. Usualy 1 means player One no biwon, 0.5 means draw, and 0 means player one lose.
    
    return A Elo delta rating after a game versus B with outcome score 
    """
    scale = 400
    k_factor = 15

    exp = 1/(1 + 10**((B - A)/scale))
    return k_factor*(score - exp)

def new_elo(A, B, score):
    """
    A : Player One rating
    B : Player Two rating
    score : Game's outcome, between 1 and 0. Usualy 1 means player One no biwon, 0.5 means draw, and 0 means player one lose.
    
    return A new elo rating after a game versus B with outcome score 
    """
    return A + elo(A,B,score)
    

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user
