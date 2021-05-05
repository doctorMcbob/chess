"""
lets do this

Okay I have to write my thoughts out on this, 
I started trying to work in FEN notation, but gave up because it seems stupid
  I looked up some examples of FEN notaion in python and they all parsed into a multid array
  so I figured I would just rock a multid array because why bother

I'm wokring on the gather_moves step, 
  im imagening a dict of key:piece -> function ( ex: pawn_moves() )

Fuck chess notation, im storing moves as ( position, new_position )

Moves are coming along :) lateral and diagonal moves done
  that means bishop, rook and queen are all done.
Knights are done too. 

Pawn and king are a little harder, because they have special moves. En passant and castleing...

I'm imagening pawn promotions happen after the move, we can just check if a pawn is on the back rank.

En passant and castling require some knowledge of the general board state.
maybe like
CAN_CASTLE = {
  white : [True, True], <-- king side, queen side
  black : [True, True],
}
then if you king moves you set CAN_CASTLE[color] = [False, False]
if your rook moves you set that side CAN_CASTLE[color][side] = False

then checking for passing checks will have to be done after introducing the concept of checks...

En passant can be done similarly
CAN_EN_PASSANT = {
  white : [False, False, False, False, False, False, False, False],
  black : [False, False, False, False, False, False, False, False],
}
then in the event of a double pawn move you set
CAN_EN_PASSANT[color][x] = True

and at the beginning of your turn you simply turn them off
CAN_EN_PASSANT[color] = [False, ]*8

EN PASSANT DONE :)))

And even better, to test it I wrote human player move choice
I also wrote a simple random move choice bot

"""
from random import choice
import sys

import pygame
from pygame import Surface, Rect
from pygame.locals import *

from tokens import tokens as tk

#########################
#                       #
#        GLOBALS        #
#                       #
#########################

SW = 96
SCREEN = pygame.display.set_mode((SW*10, SW*10))

WHITE = "human" if "-w" not in sys.argv else sys.argv[sys.argv.index("-w") + 1]
BLACK = "random" if "-b" not in sys.argv else sys.argv[sys.argv.index("-b") + 1]

COLORS = {
    "black square" : (82,52,29),
    "white square" : (201,151,101),
    "black piece"  : ((0, 0, 0), (100, 100, 100)),
    "white piece"  : ((0, 0, 0), (200, 200, 200))
}

PIECE_MAP = {
    "Rr": "rook",
    "Nn": "knight",
    "Bb": "bishop",
    "Kk": "king",
    "Qq": "queen",
    "Pp": "pawn",
}

NEW_BOARD = [
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
    ['P']*8,
    [None]*8,
    [None]*8,
    [None]*8,
    [None]*8,
    ['p']*8,
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
]
BOARD = NEW_BOARD.copy()
TURN = 'white'

CAN_EN_PASSANT = {
    'white': [False] * 8,
    'black': [False] * 8,
}

CAN_CASTLE = {
    'white': [True, True],
    'black': [True, True],
}

#########################
#                       #
#        HELPERS        #
#                       #
#########################

def get_color(piece):
    return "white" if piece.isupper() else "black"


def can_move(pos, color):
    x, y = pos
    if x < 0 or y < 0: return False
    try:
        return BOARD[y][x] is None or get_color(BOARD[y][x]) != color
    except IndexError:
        return False


def check_lateral(pos, color):
    moves = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        x, y = pos
        while 0 <= x < 8 and 0 <= y < 8:
            x += dx
            y += dy
            if can_move((x, y), color):
                moves.append((pos, (x, y)))
                if BOARD[y][x] is not None:
                    break
            else:
                break
    return moves


def check_diagonal(pos, color):
    moves = []
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        x, y = pos
        while 0 <= x < 8 and 0 <= y < 8:
            x += dy
            y += dx
            if can_move((x, y), color):
                moves.append((pos, (x, y)))
                if BOARD[y][x] is not None:
                    break
            else:
                break
    return moves

#########################
#                       #
# MOVE GATHER FUNCTIONS #
#                       #
#########################

def pawn_moves(pos, color):
    x, y = pos
    moves = []
    d = 1 if color == 'white' else -1
    if 0 <= y+d < 8 and BOARD[y+d][x] is None:
        moves.append((pos, (x, y+d)))
    if (d == 1 and y == 1) or (d == -1 and y == 6):
        if BOARD[y+d][x] is None and BOARD[y+(d*2)][x] is None:
            moves.append((pos, (x, y+(d*2))))
    # capture
    if x+1 < 8 and 0 < y+d < 8:
        if BOARD[y+d][x+1] is not None and get_color(BOARD[y+d][x+1]) != color:
            moves.append((pos, (x+1, y+d)))
    if 0 <= x-1 and 0 < y+d < 8:
        if BOARD[y+d][x-1] is not None and get_color(BOARD[y+d][x-1]) != color:
            moves.append((pos, (x-1, y+d)))
    # en passant
    if (d == 1 and y == 4) or (d == -1 and y == 3):
        if x+1 < 8 and CAN_EN_PASSANT[color][x+1]:
            moves.append((pos, (x+1, y+d)))
        if 0 <= x-1 and CAN_EN_PASSANT[color][x-1]:
            moves.append((pos, (x-1, y+d)))

    return moves


def rook_moves(pos, color):
    return check_lateral(pos, color)


def knight_moves(pos, color):
    x, y = pos
    moves = []
    for dx, dy in [(2, 1), (2, -1), (-2, 1), (-2, -1),
                   (1, 2), (-1, 2), (1, -2), (-1, -2)]:
        if can_move((x+dx, y+dy), color):
            moves.append((pos, (x+dx, y+dy))) 
    return moves


def bishop_moves(pos, color):
    return check_diagonal(pos, color)


def queen_moves(pos, color):
    return check_lateral(pos, color) + check_diagonal(pos, color)


def king_moves(pos, color):
    # TODO: CHECK FOR CHECKS ON CASTLING
    x, y = pos
    moves = []
    for dx, dy in [(1, -1), (1, 0), (1, 1),
                   (0, -1),         (0, 1),
                   (-1,-1),(-1, 0),(-1, 1)]:
        if can_move((x+dx, y+dy), color):
            moves.append((pos, (x+dx, y+dy)))

    # castle
    castle_y = 0 if color == 'white' else 7
    if CAN_CASTLE[color][0] and not any(BOARD[castle_y][1:4]):
        moves.append((pos, (2, castle_y)))
    if CAN_CASTLE[color][1] and not any(BOARD[castle_y][5:7]):
        moves.append((pos, (6, castle_y)))
    return moves

GET_MOVES_MAP = {
    "Rr": rook_moves,
    "Nn": knight_moves,
    "Bb": bishop_moves,
    "Qq": queen_moves,
    "Kk": king_moves,
    "Pp": pawn_moves,
}

def get_moves(color):
    moves = []
    for y, row in enumerate(BOARD):
        for x, piece in enumerate(row):
            if piece is None: continue
            for key in GET_MOVES_MAP:
                if piece in key:
                    if get_color(piece) == color:
                        moves += GET_MOVES_MAP[key]((x, y), color)
    return moves

#########################
#                       #
#  GAME FUNCTIONALITY   #
#                       #
#########################

def apply_move(move):
    pos1, pos2 = move
    x1, y1 = pos1
    x2, y2 = pos2
    col = get_color(BOARD[y1][x1])        
    
    # en passant check
    if BOARD[y1][x1] in 'Pp' and x1 != x2 and BOARD[y2][x2] == None:
        if col == 'white':
            BOARD[y2-1][x2] = None
        else:
            BOARD[y2+1][x2] = None

    # castle checks
    if BOARD[y1][x1] in 'Kk':
        if abs(x2 - x1) > 1:
            if x2 - x1 > 0:
                BOARD[y1][5] = BOARD[y1][7]
                BOARD[y1][7] = None
            else:
                BOARD[y1][3] = BOARD[y1][0]
                BOARD[y1][0] = None

        CAN_CASTLE[col] = [False, False]

    BOARD[y2][x2] = BOARD[y1][x1]
    BOARD[y1][x1] = None

    if CAN_CASTLE['white'][0] and BOARD[0][0] != "R":
        CAN_CASTLE['white'][0] = False
    if CAN_CASTLE['white'][1] and BOARD[0][7] != "R":
        CAN_CASTLE['white'][1] = False
    if CAN_CASTLE['black'][0] and BOARD[7][0] != "r":
        CAN_CASTLE['black'][0] = False
    if CAN_CASTLE['black'][1] and BOARD[7][7] != "r":
        CAN_CASTLE['black'][1] = False



def check_promotions(piece_choice_func):
    for x, piece in enumerate(BOARD[7]):
        if piece == "P":
            BOARD[7][x] = piece_choice_func((7, x), 'white')
    for x, piece in enumerate(BOARD[0]):
        if piece == "p":
            BOARD[0][x] = piece_choice_func((0, x), 'black')


def check_game_going():
    white, black = False, False
    for row in BOARD:
        if 'K' in row: white = True
        if 'k' in row: black = True
    return white and black

#########################
#                       #
#    MOVE SELECTORS     #
#                       #
#########################

def random_move(moves):
    return choice(moves)
    

def random_promote(pos, col):
    return choice('RNBQ') if col == 'white' else choice('rnbq')


def human_move_select(moves):
    piece_to_move = None
    moves_for_piece = []
    while True:
        board = drawn_board()
        
        if piece_to_move:
            x, y = piece_to_move
            y = 7 - y
            pygame.draw.circle(board, (50, 200, 50), (x*SW + (SW//2), y*SW + (SW//2)), SW//4) 

        for move in moves_for_piece:
            x, y = move[1]
            y = 7 - y
            pygame.draw.circle(board, (50, 200, 50), (x*SW + (SW//2), y*SW + (SW//2)), SW//4)

        SCREEN.blit(board, (SW, SW))
        pygame.display.update()
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                quit()
            if e.type == MOUSEBUTTONDOWN:
                if SW < e.pos[0] < SW*9 and SW < e.pos[1] < SW*9:
                    x = e.pos[0] // SW -1
                    y = 8 - (e.pos[1] // SW)
                    pos = (x, y)
                    if pos == piece_to_move:
                        piece_to_move = None
                        moves_for_piece = []
                    else:
                        for move in moves:
                            if move[0] == pos:
                                piece_to_move = pos
                                for move in moves:
                                    moves_for_piece = list(filter(lambda move: move[0] == pos, moves))
                        for move in moves_for_piece:
                            if move[1] == pos:
                                return move


def autoqueen(pos, col):
    return 'Q' if col == 'white' else 'q'


PLAYERS = {
    "human": [human_move_select, autoqueen],
    "random": [random_move, random_promote],
}

#########################
#                       #
# PYGAME SPECIFIC DRAW  #
#                       #
#########################

def drawn_board():
    surf = Surface((SW*8, SW*8))
    for y in range(8):
        for x in range(8):
            col = "black square" if (x + y) % 2 == 1 else "white square"
            pygame.draw.rect(surf, COLORS[col], Rect((SW*x, SW*y), (SW, SW)))

    for y, row in enumerate(BOARD[::-1]):
        for x, piece in enumerate(row):
            if piece is None: continue
            colorset = COLORS[get_color(piece) + " piece"]

            for key in PIECE_MAP:
                if piece in key:
                    tk.draw_token(surf, PIECE_MAP[key], (SW*x, SW*y),
                                      col1=colorset[0], col2=colorset[1], PW=SW//16)

    return surf


def run(white_move_choice, white_promotion_func, black_move_choice, black_promotion_func):
    global TURN
    while check_game_going():
        SCREEN.fill((150, 150, 150))
        SCREEN.blit(drawn_board(), (SW, SW))
        for x in range(1, 9):
            tk.draw_token(SCREEN, "{}".format("_ABCDEFGH"[x]), (x*SW, SW*9), col1=(150, 150, 150), col2=(0, 0, 0), PW=(SW//16))
        for y in range(1, 9):
            tk.draw_token(SCREEN, "{}".format(y), (0, SW*(9-y)), col1=(150, 150, 150), col2=(0, 0, 0), PW=(SW//16))

        moves = get_moves(TURN)
        if (moves):
            CAN_EN_PASSANT[TURN] = [False] * 8
            move = white_move_choice(moves) if TURN == 'white' else black_move_choice(moves)

            pos1, pos2 = move
            if pos1[1] == 1 and pos2[1] == 3 and BOARD[pos1[1]][pos1[0]] == "P":
                CAN_EN_PASSANT['black'][pos1[0]] = True
            if pos1[1] == 6 and pos2[1] == 4 and BOARD[pos1[1]][pos1[0]] == "p":
                CAN_EN_PASSANT['white'][pos1[0]] = True

            apply_move(move)
            if TURN == 'white':
                check_promotions(white_promotion_func)
            else:
                check_promotions(black_promotion_func)
                
        TURN = 'white' if TURN == 'black' else 'black'
        
        pygame.display.update()
        wait = True
        while wait:
            wait = False
            for e in pygame.event.get():
                if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                    quit()
                if e.type == KEYDOWN:
                    wait = False


if __name__ == "__main__":
    run(PLAYERS[WHITE][0], PLAYERS[WHITE][1], PLAYERS[BLACK][0], PLAYERS[BLACK][1])

                
