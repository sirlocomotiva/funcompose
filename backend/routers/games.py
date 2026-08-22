from fastapi import APIRouter

import games

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
def list_games():
    return games.list_public()
