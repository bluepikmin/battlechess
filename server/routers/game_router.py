from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from sqlalchemy.orm import Session

from server.schemas import schemas
from server.database import crud
from server.utils import utils
from server import btchApi

router = APIRouter()


# lists available games
@router.get("/games", response_model=List[schemas.Game], tags=['Games'])
def list_available_games(status_filter: str = schemas.GameStatus.WAITING,
                         current_user: schemas.User = Depends(utils.get_current_active_user),
                         db: Session = Depends(utils.get_db)):
    games = crud.get_public_game_by_status(db, current_user, status_filter)
    return games

@router.post("/games/", tags=['Games'])
def post_new_game(new_game: schemas.GameCreate,
                  current_user: schemas.User = Depends(utils.get_current_active_user),
                  db: Session = Depends(utils.get_db)):
    return crud.create_game(db, current_user, new_game)

# either creates a new game or joins an existing unstarted random game. Random games can not be joined via "join_game".
@router.patch("/games", tags=['Games'])
def join_random_game(current_user: schemas.User = Depends(utils.get_current_active_user),
                     db: Session = Depends(utils.get_db)):
    game = crud.get_random_public_game_waiting(db, current_user)
    if not game:
        return {}

    game = btchApi.set_player(game, current_user, db)

    db.refresh(game)

    return game

@router.get("/games/{gameUUID}", tags=['Games'])
def get_game_by_uuid(gameUUID: str,
                     current_user: schemas.User = Depends(utils.get_current_active_user),
                     db: Session = Depends(utils.get_db)):
    return crud.get_game_by_uuid(db, gameUUID)



#TODO should be patch
# joines an existing game. error when game already started
@router.get("/games/{gameUUID}/join", tags=['Games'])
def join_game(gameUUID: str,
              current_user: schemas.User = Depends(utils.get_current_active_user),
              db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    game = btchApi.set_player(game, current_user, db)

    return game


# TODO set player ready (maybe not necessary since we're not timing)
# @router.get("/games/{gameUUID}/join")
# def join_game(
#     gameUUID: str,
#     current_user: schemas.User = Depends(utils.get_current_active_user),
#     db: Session = Depends(utils.get_db)
# ):
#     game = btchApi.get_game(gameUUID, current_user, db)
#     if not game:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="game not found",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     game.btchApi.set_player(current_user)
#     return game


# serialized board state
@router.get("/games/{gameUUID}/board", tags=['Games'])
def query_board(gameUUID: str,
                current_user: schemas.User = Depends(utils.get_current_active_user),
                db: Session = Depends(utils.get_db)):
    pass


# who's turn is it (None means that the game is over)
@router.get("/games/{gameUUID}/turn", tags=['Games'])
def query_turn(gameUUID: str,
               current_user: schemas.User = Depends(utils.get_current_active_user),
               db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    return game.turn


@router.post("/games/{gameUUID}/move", tags=['Games'])
def post_move(
    gameUUID: str,
    #move: dict = Body(...), # or pydantic or query parameter? Probably pydantic to make clear what a move is
    gameMove: schemas.GameMove,
    current_user: schemas.User = Depends(utils.get_current_active_user),
    db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"Authorization": "Bearer"},
        )

    if game.status != schemas.GameStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="game is not started",
            headers={"Authorization": "Bearer"},
        )

    # It looks like modifying the pydantic model does not change the db model
    snap = crud.create_snap_by_move(db, current_user, game, gameMove)
    snap4player = schemas.GameSnap.from_orm(snap)
    snap4player.prepare_for_player(game.get_player_color(current_user.id))
    return snap4player


# TODO List[str] might throw ValidationError: <unprintable ValidationError object>
# due to
@router.get("/games/{gameUUID}/moves/{square}", response_model=List[str], tags=['Games'])
def get_moves(gameUUID: str,
              square: str,
              current_user: schemas.User = Depends(utils.get_current_active_user),
              db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"Authorization": "Bearer"},
        )

    if game.status != "started":
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="game is not started",
            headers={"Authorization": "Bearer"},
        )

    # TODO pydantic square validation possible?
    if len(square) != 2 or square < 'a1' or 'h8' < square:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="square is not of format ['a1', 'h8'] ",
            headers={"Authorization": "Bearer"},
        )

    snap = game.snaps[-1]
    color = game.get_player_color(current_user.id)
    moves = snap.getPossibleMoves(square, color)

    # TODO remove this if we're happy with a weird validation error message
    if moves:
        assert type(moves[0]) == str
    return moves


@router.get("/games/{gameUUID}/snap", tags=['Games'])
def get_snap(gameUUID: str,
             current_user: schemas.User = Depends(utils.get_current_active_user),
             db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    # user not allowed to query that game snap for now
    if (game.status != schemas.GameStatus.OVER) and (current_user.id not in [game.white_id, game.black_id]):
        game = None
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"Authorization": "Bearer"},
        )
    snap = game.snaps[-1]

    if not snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="snap not found",
            headers={"Authorization": "Bearer"},
        )

    if game.status != schemas.GameStatus.STARTED or not game.black_id or not game.white_id:
        return snap

    player_color = "black" if current_user.id == game.black_id else "white"
    snap4player = schemas.GameSnap.from_orm(snap)
    print(f'preparing board for {current_user.username} {player_color}')
    snap4player.prepare_for_player(player_color)

    return snap4player



@router.get("/games/{gameUUID}/snaps", tags=['Games'])
def get_snaps(gameUUID: str,
              current_user: schemas.User = Depends(utils.get_current_active_user),
              db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    # user not allowed to query that game snap for now
    if (game.status != schemas.GameStatus.OVER) and (current_user.id not in [game.white_id, game.black_id]):
        game = None
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"Authorization": "Bearer"},
        )

    player_color = "black" if current_user.id == game.black_id else "white"
    result = []
    for snap in game.snaps:

        snap4player = schemas.GameSnap.from_orm(snap)
        snap4player.prepare_for_player(player_color)
        result.append(snap4player)
    return result

@router.get("/games/{gameUUID}/snap/{moveNum}", tags=['Games'])
def get_snap(gameUUID: str,
             moveNum: int,
             current_user: schemas.User = Depends(utils.get_current_active_user),
             db: Session = Depends(utils.get_db)):
    game = btchApi.get_game(gameUUID, current_user, db)
    # user not allowed to query that game snap for now
    if (game.status != schemas.GameStatus.OVER) and (current_user.id not in [game.white_id, game.black_id]):
        game = None
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="game not found",
            headers={"Authorization": "Bearer"},
        )
    snap = crud.get_snap(db, current_user, gameUUID, moveNum)
    if not snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="snap not found",
            headers={"Authorization": "Bearer"},
        )

    player_color = "black" if current_user.id == game.black_id else "white"
    snap4player = schemas.GameSnap.from_orm(snap)
    snap4player.prepare_for_player(player_color)
    return snap4player