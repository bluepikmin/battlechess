from typing import Optional, List
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from sqlalchemy.orm import Session

from server.schemas import schemas
from server.database import crud
from server.utils import utils

router = APIRouter()


@router.get("/users/", response_model=List[schemas.User], tags=['Users'])
def read_users(skip: int = 0,
               limit: int = 100,
               current_user: schemas.User = Depends(utils.get_current_active_user),
               db: Session = Depends(utils.get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.post("/users/", tags=['Users'])
def create_user(new_user: schemas.UserCreate, db: Session = Depends(utils.get_db)):
    if not (3 <= len(new_user.username) <= 15 and
            len(new_user.plain_password) >= utils.PASSWORD_MIN_LENGTH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"username should be of lenght (3-15) and password at least {utils.PASSWORD_MIN_LENGTH} chars.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if new_user.email is None:
        new_user.email = ""

    if crud.get_user_by_username(db, new_user.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username taken",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif crud.get_user_by_email(db, new_user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        db_user = crud.create_user(db, new_user)
        return crud.get_user_by_username(db, new_user.username)

@router.get("/users/usernames", response_model=List[str], tags=['Users'])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(utils.get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return [user.username for user in users]


@router.get("/users/u/{userID}", response_model=schemas.User, tags=['Users'])
def read_single_user(userID: int,
                      current_user: schemas.User = Depends(utils.get_current_active_user),
                      db: Session = Depends(utils.get_db)):
    user = crud.get_user_by_id(db, userID)
    return user


@router.get("/users/me/", response_model=schemas.User, tags=['Users'])
def read_users_me(current_user: schemas.User = Depends(utils.get_current_active_user)):
    return current_user


@router.get("/users/me/games/", response_model=List[schemas.Game], tags=['Users'])
def read_own_games(current_user: schemas.User = Depends(utils.get_current_active_user),
                   db: Session = Depends(utils.get_db)):
    print("read own games")
    games = crud.get_games_by_player(db, current_user)
    print(f'{games}')
    return games

@router.get("/users/me/elo", tags=['Users'])
def get_elo_delta(player: int=0, score: Optional[float
] = None, db: Session = Depends(utils.get_db), current_user: schemas.User = Depends(utils.get_current_active_user)):
    if player == 0:
        return {}
    player = crud.get_user_by_id(db, player)
    if score != None:
        return utils.elo(current_user.elo_rating, player.elo_rating, score)
    else:
        return [utils.elo(current_user.elo_rating, player.elo_rating, 1),
        utils.elo(current_user.elo_rating, player.elo_rating, .5),
        utils.elo(current_user.elo_rating, player.elo_rating, 0)]



