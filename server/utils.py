import random
import string
from typing_extensions import Annotated
from passlib.context import CryptContext

from .config import HANDLEBASEURL

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    # TODO catch UnknownHashError for plain-text stored passwords
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# TODO use Random-Word or something for more user-friendly handles
def get_random_string(length=6):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def handle2uuid(uuid):
    return HANDLEBASEURL + uuid

def defaultBoard():
    return (
        'RNBQKBNR'
        'PPPPPPPP'
        '________'
        '________'
        '________'
        '________'
        'pppppppp'
        'rnbqkbnr'
    )


def extij2ad(i, j):
    square = chr(j - 2 + 97) + str(8 - (i - 2))
    return square


def ad2extij(square):
    i = 8 - int(square[1]) + 2
    j = ord(square[0]) - ord('a') + 2
    return (i, j)

def ad2ij(square):
    i = 8 - int(square[1])
    j = ord(square[0]) - ord('a')
    return (i, j)

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
    