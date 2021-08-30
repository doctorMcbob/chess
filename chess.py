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

-------

Okay rethinking this, as I start to have to look ahead in turns
im going to have to keep track of en passant and castle states for each board state.

perhaps a generic BOARD_STATE dictionary can be passed around and created.

CURRENT_STATE = { # at the beginning
   en_passant : {
      white : [...],
      black : [...]
   },
   castle : {
      white : [...],
      black : [...]
   },
   board : [[...], [...], ...] 

CURRENT_STATE = apply_turn(CURRENT_STATE) <-- returns a new board state

========
god hath forsaken us and I am coming back to this project after like 6 months

implementing current state changes. information for whose turn it is will also live in the CURRENT_STATE

ALAS I HAVE FIXED CASTLING

now we get to do the real experiments

Before we can start playing games we need to start analyzing positions

point_value done, just tally the point value difference between players

later expirement with a more verbose position analysis that considers 
  number of squares in sight and king vulnerability

minimax done, abstract enough to use alternate analysis functions

it takes FOREVER to complete a game with even a search depth of 3. 
thinking about optomizations now.
"""
from random import choice
from copy import deepcopy
import sys, os

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
BLACK = "femm" if "-b" not in sys.argv else sys.argv[sys.argv.index("-b") + 1]

WPLY = 2 if "-wply" not in sys.argv else int(sys.argv[sys.argv.index("-wply") + 1] )
BPLY = 2 if "-bply" not in sys.argv else int(sys.argv[sys.argv.index("-bply") + 1])
CACHE_PLY = False if "-cache" not in sys.argv else int(sys.argv[sys.argv.index("-cache") + 1])

DEBUG = "-d" in sys.argv
PIC = "-pic" in sys.argv
if PIC:
    import datetime
    IMG_PATH = "pics/" + str(datetime.datetime.now())+ "/"


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

CHECKMATE_TEST = [
    ['R', None, None, None, 'K', None, None, 'R'],
    [None]*8,
    [None]*8,
    [None]*8,
    [None]*8,
    [None]*8,
    [None]*8,
    [None, None, None, None, 'k', None, None, None]
]

PIECE_VALUE = {
    "Kk": 0,
    "Pp": 1,
    "Bb": 3,
    "Nn": 3,
    "Rr": 5,
    "Qq": 9,
}

CURRENT_STATE = {
    "board": NEW_BOARD.copy() if "-cmt" not in sys.argv else CHECKMATE_TEST.copy(),
    "turn": "white",
    
    "can castle": {
        "white": [True, True],
        "black": [True, True],
    },
    "can en passant": {
        "white": [False] * 8,
        "black": [False] * 8,
    },
    "stack": [],
}

CACHED_SCORES = {
    "black": {},
    "white": {},
}

#########################
#                       #
#        HELPERS        #
#                       #
#########################

def pretty_print_board(board):
    print("@   0  1  2  3  4  5  6  7")
    for y, row in enumerate(board):
        print("  -" + "---" * 8)
        pretty_row = "{} |".format(y)
        for piece in row:
            pretty_row += "  |" if piece is None else "{} |".format(piece)
        print(pretty_row)
    print("  -" + "---" * 8)


def get_color(piece):
    return "white" if piece.isupper() else "black"


def can_move(board, pos, color):
    x, y = pos
    if x < 0 or y < 0: return False
    try:
        return board[y][x] is None or get_color(board[y][x]) != color
    except IndexError:
        return False


def check_lateral(board, pos, color):
    moves = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        x, y = pos
        while 0 <= x < 8 and 0 <= y < 8:
            x += dx
            y += dy
            if can_move(board, (x, y), color):
                moves.append((pos, (x, y)))
                if board[y][x] is not None:
                    break
            else:
                break
    return moves


def check_diagonal(board, pos, color):
    moves = []
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        x, y = pos
        while 0 <= x < 8 and 0 <= y < 8:
            x += dy
            y += dx
            if can_move(board, (x, y), color):
                moves.append((pos, (x, y)))
                if board[y][x] is not None:
                    break
            else:
                break
    return moves


def get_moves(state, color, no_check=False):
    moves = []
    for y, row in enumerate(state["board"]):
        for x, piece in enumerate(row):
            if piece is None or (no_check and piece in "Kk"): continue
            if get_color(piece) == color:
                keys = list(GET_MOVES_MAP.keys())
                keys.sort()
                for key in keys:
                    if piece in key:
                        moves += GET_MOVES_MAP[key](state, (x, y), color)
    return moves
                

def get_legal_moves(state, color, debug=True):
    debug = False
    moves = get_moves(state, color)
    legal_moves = []
    captures = []
    for move in moves:
        if debug: pretty_print_board(apply_move(state, move)["board"])
        if not in_check(apply_move(state, move), color):
            # check for castle has to live here instead of in king_moves
            x1, y1 = move[0]
            x2, y2 = move[1]
            if state["board"][y1][x1] in "Kk":
                # if we are moving the king
                # and the distance we are moving is two
                if abs(x1 - x2) == 2:
                    x = x1 - (x1 - x2) // 2 # not hacky :fingers_crossed:
                    if in_check(apply_move(state, ((x1, y1), (x, y2))), color):
                        continue
            if debug: print('legal')
            if state["board"][y2][x2] is not None:
                captures.append(move)
                continue
            legal_moves.append(move)    
        elif debug: print('ilegal')
    return captures + legal_moves

def in_check(state, color, no_check=False):
    col = "white" if color == "black" else "black"
    for move in get_moves(state, col, no_check):
        x, y = move[1]
        if state["board"][y][x] == ('K' if color == 'white' else 'k'):
            return True
    return False


#########################
#                       #
# MOVE GATHER FUNCTIONS #
#                       #
#########################

def pawn_moves(state, pos, color): 
    x, y = pos
    moves = []
    d = 1 if color == 'white' else -1
    # basic movement
    if 0 <= y+d < 8 and state["board"][y+d][x] is None:
        moves.append((pos, (x, y+d)))
    # check first move
    if (d == 1 and y == 1) or (d == -1 and y == 6):
        if state["board"][y+d][x] is None and state["board"][y+(d*2)][x] is None:
            moves.append((pos, (x, y+(d*2))))
    # capture
    if x+1 < 8 and 0 < y+d < 8:
        if state["board"][y+d][x+1] is not None and get_color(state["board"][y+d][x+1]) != color:
            moves.append((pos, (x+1, y+d)))
    if 0 <= x-1 and 0 < y+d < 8:
        if state["board"][y+d][x-1] is not None and get_color(state["board"][y+d][x-1]) != color:
            moves.append((pos, (x-1, y+d)))
    # en passant
    if (d == 1 and y == 4) or (d == -1 and y == 3):
        if x+1 < 8 and state["can en passant"][color][x+1]:
            moves.append((pos, (x+1, y+d)))
        if 0 <= x-1 and state["can en passant"][color][x-1]:
            moves.append((pos, (x-1, y+d)))

    return moves


def rook_moves(state, pos, color):
    return check_lateral(state["board"], pos, color)


def knight_moves(state, pos, color):
    x, y = pos
    moves = []
    for dx, dy in [(2, 1), (2, -1), (-2, 1), (-2, -1),
                   (1, 2), (-1, 2), (1, -2), (-1, -2)]:
        if can_move(state["board"], (x+dx, y+dy), color):
            moves.append((pos, (x+dx, y+dy))) 
    return moves


def bishop_moves(state, pos, color):
    return check_diagonal(state["board"], pos, color)


def queen_moves(state, pos, color):
    return check_lateral(state["board"], pos, color) + check_diagonal(state["board"], pos, color)


def king_moves(state, pos, color):
    x, y = pos
    moves = []
    for dx, dy in [(1, -1), (1, 0), (1, 1),
                   (0, -1),         (0, 1),
                   (-1,-1),(-1, 0),(-1, 1)]:
        if can_move(state["board"], (x+dx, y+dy), color):
            moves.append((pos, (x+dx, y+dy)))

    # castle
    if not in_check(state, color, no_check=True):
        castle_y = 0 if color == 'white' else 7
        if state["can castle"][color][0] and not any(state["board"][castle_y][1:4]):
            moves.append((pos, (2, castle_y)))
        if state["can castle"][color][1] and not any(state["board"][castle_y][5:7]):
            moves.append((pos, (6, castle_y)))
    return moves

GET_MOVES_MAP = {
    "1Rr": rook_moves,
    "2Nn": knight_moves,
    "3Bb": bishop_moves,
    "0Qq": queen_moves,
    "4Kk": king_moves,
    "5Pp": pawn_moves,
}

#########################
#                       #
#  GAME FUNCTIONALITY   #
#                       #
#########################

def apply_move(state, move):
    state = deepcopy(state)
    pos1, pos2 = move
    x1, y1 = pos1
    x2, y2 = pos2
    col = get_color(state["board"][y1][x1])        
    
    # en passant check
    if state["board"][y1][x1] in 'Pp' and x1 != x2 and state["board"][y2][x2] == None:
        if col == 'white':
            state["board"][y2-1][x2] = None
        else:
            state["board"][y2+1][x2] = None

    # castle checks
    if state["board"][y1][x1] in 'Kk':
        if abs(x2 - x1) > 1:
            if x2 - x1 > 0:
                state["board"][y1][5] = state["board"][y1][7]
                state["board"][y1][7] = None
            else:
                state["board"][y1][3] = state["board"][y1][0]
                state["board"][y1][0] = None

        state["can castle"][col] = [False, False]

    state["board"][y2][x2] = state["board"][y1][x1]
    state["board"][y1][x1] = None

    if state["can castle"]['white'][0] and state["board"][0][0] != "R":
        state["can castle"]['white'][0] = False
    if state["can castle"]['white'][1] and state["board"][0][7] != "R":
        state["can castle"]['white'][1] = False
    if state["can castle"]['black'][0] and state["board"][7][0] != "r":
        state["can castle"]['black'][0] = False
    if state["can castle"]['black'][1] and state["board"][7][7] != "r":
        state["can castle"]['black'][1] = False

    check_promotions(state, autoqueen)
    state["turn"] = 'white' if state["turn"] == 'black' else 'black'
    state["stack"].append(move)
    return state


def check_promotions(state, piece_choice_func):
    for x, piece in enumerate(state["board"][7]):
        if piece == "P":
            state["board"][7][x] = piece_choice_func((7, x), 'white')
    for x, piece in enumerate(state["board"][0]):
        if piece == "p":
            state["board"][0][x] = piece_choice_func((0, x), 'black')


def check_perpetual(state):
    state = deepcopy(state)
    if len(state["stack"]) < 8:
        return False
    move1 = state["stack"].pop()
    move2 = state["stack"].pop()
    move3 = state["stack"].pop()
    move4 = state["stack"].pop()
    if (state["stack"].pop() != move1
        or state["stack"].pop() != move2
        or state["stack"].pop() != move3
        or state["stack"].pop() != move4):
        return False
    return True

def check_game_going(state):
    white, black = False, False
    for row in state["board"]:
        if 'K' in row: white = True
        if 'k' in row: black = True
    return white and black

#########################
#                       #
#    MOVE SELECTORS     #
#                       #
#########################

# progromatic move choice
def random_move(state, color, ply=False):
    return choice(get_legal_moves(state, color))
def minimax_by_point_value(state, color, ply=3, debug=DEBUG):
    score, move = minimax(ply, point_value, state, color, debug=debug)
    if debug: print("chose", score, move)
    return move
def minimax_by_full_evaluate(state, color, ply=3, debug=DEBUG):
    score, move = minimax(ply, full_evaluate, state, color, debug=debug)
    if debug: print("chose", score, move)
    return move
def minimax_full_evaluate_deepen_simple(state, color, ply=3, debug=DEBUG):
    """if there are only a few opponent peices left deepen search"""
    pieces = 0
    limit = 8
    for y, row in enumerate(state["board"]):
        for x, piece in enumerate(row):
            if piece:
                pieces += 1
                if pieces > limit: break
    if pieces < limit:
        ply += min([2, limit - pieces])
    return minimax_by_full_evaluate(state, color, ply=ply, debug=debug)
    
# progromatic promotion choice
def random_promote(pos, col):
    return choice('RNBQ') if col == 'white' else choice('rnbq')
def autoqueen(pos, col):
    return 'Q' if col == 'white' else 'q'

# human move choice
def human_move_select(state, color, ply=False):
    moves = get_legal_moves(state, color)
    piece_to_move = None
    moves_for_piece = []
    while True:
        board = drawn_board(state)
        
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
# human promotion choice
# to do...


PLAYERS = {
    "human": [human_move_select, autoqueen],
    "random": [random_move, random_promote],
    "pvmm": [minimax_by_point_value, autoqueen], # point value mini max
    "femm": [minimax_by_full_evaluate, autoqueen], # full evaluate mini max
    "femmds": [minimax_full_evaluate_deepen_simple, autoqueen],
}

#########################
#                       #
# PYGAME SPECIFIC DRAW  #
#                       #
#########################

def drawn_board(state):
    surf = Surface((SW*8, SW*8))
    for y in range(8):
        for x in range(8):
            col = "black square" if (x + y) % 2 == 1 else "white square"
            pygame.draw.rect(surf, COLORS[col], Rect((SW*x, SW*y), (SW, SW)))

    for y, row in enumerate(state["board"][::-1]):
        for x, piece in enumerate(row):
            if piece is None: continue
            colorset = COLORS[get_color(piece) + " piece"]

            for key in PIECE_MAP:
                if piece in key:
                    tk.draw_token(surf, PIECE_MAP[key], (SW*x, SW*y),
                                      col1=colorset[0], col2=colorset[1], PW=SW//16)

    return surf

def draw(state):
    SCREEN.fill((150, 150, 150))
    SCREEN.blit(drawn_board(state), (SW, SW))
    for x in range(1, 9):
        tk.draw_token(SCREEN, "{}".format("_ABCDEFGH"[x]), (x*SW, SW*9), col1=(150, 150, 150), col2=(0, 0, 0), PW=(SW//16))
    for y in range(1, 9):
        tk.draw_token(SCREEN, "{}".format(y), (0, SW*(9-y)), col1=(150, 150, 150), col2=(0, 0, 0), PW=(SW//16))
    pygame.display.update()

        
def run(state, white_move_choice, white_promotion_func, black_move_choice, black_promotion_func):
    if PIC:
        FRAME = 0
        save_img(drawn_board(state), FRAME)

    draw(state)
    while check_game_going(state) and not check_perpetual(state):
        turn = state["turn"]
        if moves := get_legal_moves(state, state["turn"], debug=DEBUG):
            state["can en passant"][state["turn"]] = [False] * 8
            move_choose = white_move_choice if state["turn"] == "white" else black_move_choice
            move = move_choose(state, state["turn"], ply=WPLY if state["turn"] == "white" else BPLY)

            pos1, pos2 = move
            if pos1[1] == 1 and pos2[1] == 3 and state["board"][pos1[1]][pos1[0]] == "P":
                state["can en passant"]['black'][pos1[0]] = True
            if pos1[1] == 6 and pos2[1] == 4 and state["board"][pos1[1]][pos1[0]] == "p":
                state["can en passant"]['white'][pos1[0]] = True
            
            state = apply_move(state, move)

            if PIC:
                FRAME += 1
                save_img(drawn_board(state), FRAME)

            draw(state)
        else:
            if in_check(state, state["turn"]):
                return '{} wins!'.format('white' if state["turn"] == 'black' else 'black')
            else:
                return 'Draw'

        wait = True
        while wait:
            wait = False
            for e in pygame.event.get():
                if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                    quit()
                if e.type == KEYDOWN:
                    wait = False

# ~~~~ MISC / UTILS ~~~~
# todo: reorganize later
def save_img(img, frame):
    if not os.path.isdir(IMG_PATH): os.mkdir(IMG_PATH)
    pygame.image.save(img, IMG_PATH + str(frame) + ".png")

def truncate_board(board):
    return ",".join(["".join([str(peice) for peice in row]) for row in board])    

def check_cache(state, ply, cache, debug=True):
    if CACHE_PLY == False: return
    trunc = truncate_board(state["board"])
    if trunc in cache[state["turn"]]:
        cached_ply, score = cache[state["turn"]][trunc]
        if ply <= cached_ply:
            if debug:
                print("using cache")
                print("ply: ", ply, " cached: ", cached_ply)
                print(sum([len(cache[key]) for key in cache]))
            return score
    return None

def cache_score(state, ply, score, cache):
    if ply < CACHE_PLY: return
    trunc = truncate_board(state["board"])
    cache[state["turn"]][trunc] = (ply, score)

def minimax(ply, evaluate_func, state, color, alpha=-1000, beta=1000, debug=False):
    moves = get_legal_moves(state, state["turn"])

    if check_perpetual(state): return 0, None

    if len(moves) == 0:
        if in_check(state, state["turn"]):
            if state["turn"] == color:
                return -100 + ply, None
            else:
                return 100 + ply, None
        return 0, None

    if ply == 0:
        return evaluate_func(state, color), None
    
    if state["turn"] == color:
        value_max = -1000
        max_move = None
        for move in moves:
            value, _ = minimax(ply - 1, evaluate_func, apply_move(state, move), color, alpha, beta, debug=debug)
            if debug:
                print(ply, state, pretty_print_board(state["board"]))
                print(alpha, beta, value, value_max)
            if value >= value_max:
                value_max = value
                max_move = move
            if value > alpha:
                alpha = value
            if beta <= alpha:
                break
        return value_max, max_move
    else:
        value_min = 1000
        min_move = None
        for move in moves:
            value, _ = minimax(ply - 1, evaluate_func, apply_move(state, move), color, alpha, beta, debug=debug)
            if debug:
                print(ply, state, pretty_print_board(state["board"]))
                print(alpha, beta, value, value_min)
            if value <= value_min:
                value_min = value
                min_move = move
            if value < beta:
                beta = value
            if beta <= alpha:
                break
        return value_min, min_move
            
def full_evaluate(state, color, debug=False):
    return sum([func(state, color, debug=debug) for func in [point_value, line_of_sight_points, king_in_sight_points]])

def line_of_sight_points(state, color, debug=False):
    if debug:
        print("analyzing sights")
        pretty_print_board(state["board"])

    moves = {
        "black": get_moves(state, "black"),
        "white": get_moves(state, "white"),
    }

    points = {
        "black": 0,
        "white": 0,
    }

    for key in moves:
        for move in moves[key]:
            if state["board"][move[0][1]][move[0][0]] in "Qq": continue
            for n in move[1]:
                if n in (3, 4): points[key] += .3
                if n in (2, 5): points[key] += .2
                if n in (1, 6): points[key] += .2
                if n in (0, 7): points[key] += .1

    return points["white"] - points["black"] if color == "white" else points["black"] - points["white"]

def king_in_sight_points(state, color, debug=False):
    if debug:
        print("analyzing king safety")
        pretty_print_board(state["board"])
 
    points = {
        "black": sum(state["can castle"]["black"]) * 1.5,
        "white": sum(state["can castle"]["white"]) * 1.5,
    }

    for y, row in enumerate(state["board"]):
        for king in "Kk":
            if king in row:
                x = row.index(king)
                points["white" if king.isupper() else "black"] -= len(check_lateral(state["board"], (x, y), "black" if king.isupper() else "white"))
                points["white" if king.isupper() else "black"] -= len(check_diagonal(state["board"], (x, y), "black" if king.isupper() else "white"))

    return points[color] * 0.01

def point_value(state, color, debug=False):
    if debug:
        print("analyzing point value")
        pretty_print_board(state["board"])

    board = state["board"]
    score = 0
    
    for y, row in enumerate(board):
        for x, piece in enumerate(row):
            for key in PIECE_VALUE.keys():
                if piece and piece in "Pp":
                    score += 0.01 * y if color == "white" else 0.01 * (7 - y)
                    
                if piece and piece in key:
                    score += PIECE_VALUE[key] * (1 if get_color(piece) == color else -1)
                   
    if debug: print("score: ", score)
    return score * 2

if __name__ == "__main__":
    print(
        run(CURRENT_STATE, PLAYERS[WHITE][0], PLAYERS[WHITE][1], PLAYERS[BLACK][0], PLAYERS[BLACK][1])
    )

