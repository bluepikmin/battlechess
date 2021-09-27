from typing import List

from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from server.routers import game_router, misc_router, user_router
from server.database import models, btchApiDB, crud
from server.schemas import schemas
from server.utils import utils


models.Base.metadata.create_all(bind=btchApiDB.engine)

app = FastAPI()

# allow for CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_game(gameUUID,
             current_user: schemas.User = Depends(utils.get_current_active_user),
             db: Session = Depends(utils.get_db)):
    # TODO check if public and owner/player
    game = crud.get_game_by_uuid(db, gameUUID)
    return game


def set_player(game: models.Game,
               current_user: schemas.User = Depends(utils.get_current_active_user),
               db: Session = Depends(utils.get_db)):
    game.set_player(current_user)

    # if all players are there, start
    if game.is_full():
        crud.create_default_snap(db, current_user, game)
        game.start_game()

    # if this is not here start_game doesn't change the state of the game
    db.commit()

    return game


# We load endpoints
app.include_router(misc_router.router)
app.include_router(user_router.router)
app.include_router(game_router.router)
