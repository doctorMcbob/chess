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
CACHE = {
    "black": {}, "white": {}
}

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


NEW_BOARD = {
    "R": {(0, 0), (7, 0)},
    "r": {(0, 7), (7, 7)},
    "N": {(1, 0), (6, 0)},
    "n": {(1, 7), (6, 7)},
    "B": {(2, 0), (5, 0)},
    "b": {(2, 7), (5, 7)},
    "K": {(3, 0)},
    "k": {(3, 7)},
    "Q": {(4, 0)},
    "q": {(4, 7)},
    "P": {(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)},
    "p": {(0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)},
}

CHECKMATE_TEST = {
    "R": {(0, 0), (7, 0)},
    "r": set(),
    "N": set(),
    "n": set(),
    "B": set(),
    "b": set(),
    "K": {(3, 0)},
    "k": {(3, 7)},
    "Q": set(),
    "q": set(),
    "P": set(),
    "p": set(),
}

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
    "moves": {"white": [], "black":[]},
    "legal moves":  {"white": [], "black":[]},
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
    for y in range(8):
        print("  -" + "---" * 8)
        for piece in board:
            if (0, y) in board[piece]:
                pretty_row = "{} |".format(piece)
                break
        else:
            pretty_row = "  |"

        for x in range(1, 8):
            for piece in board:
                if (x, y) in board[piece]:
                    pretty_row += "| {}".format(piece)
                    break
            else:
                pretty_row += "|  "

        print(pretty_row)
    print("  -" + "---" * 8)


def get_color(piece):
    return "white" if piece.isupper() else "black"

def piece_at(board, pos):
    for piece in board:
        if pos in board[piece]:
            return piece

def can_move(board, pos, color):
    x, y = pos
    if x < 0 or y < 0 or x > 7 or y > 7 : return False
    piece = piece_at(board, pos)
    if piece is None:
        return True
    return get_color(piece) != color

def check_lateral(board, pos, color):
    moves = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        x, y = pos
        while 0 <= x < 8 and 0 <= y < 8:
            x += dx
            y += dy
            if can_move(board, (x, y), color):
                moves.append((pos, (x, y)))
                if piece_at(board, (x, y)):
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
                if piece_at(board, (x, y)):
                    break
            else:
                break
    return moves

def get_moves(state, color, debug=DEBUG):
    moves = []
    board = state["board"]
    keys = list(GET_MOVES_MAP.keys())
    for piece in board:
        if get_color(piece) != color: continue
        for x, y in board[piece]:
            for key in keys:
                if piece in key:
                    moves += GET_MOVES_MAP[key](state, (x, y), color)
    return moves

def get_legal_moves(state, color, split=False, debug=DEBUG):
    moves = state["moves"][color]
    legal_moves = []
    captures = []
    for move in moves:
        if not in_check(apply_move(state, move), color):
            # check for castle has to live here instead of in king_moves
            if piece_at(state["board"], move[0]) in "Kk":
                # if we are moving the king
                # and the distance we are moving is two
                x1, y1 = move[0]
                x2, y2 = move[1]
                if abs(x1 - x2) == 2:
                    x = x1 - (x1 - x2) // 2 # not hacky :fingers_crossed:
                    if in_check(apply_move(state, ((x1, y1), (x, y2))), color):
                        continue
            if piece_at(state["board"], move[1])  is not None:
                captures.append(move)
                continue
            else:
                legal_moves.append(move)
    state["legal moves"][color] = (captures, legal_moves)

def in_check(state, color):
    col = "white" if color == "black" else "black"
    for move in state["moves"][col]:
        if piece_at(state["board"], move[1]) == ('K' if color == 'white' else 'k'):
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
    if 0 <= y+d < 8 and not piece_at(state["board"], (x, y+d)):
        moves.append((pos, (x, y+d)))

    # check first move
    if (d == 1 and y == 1) or (d == -1 and y == 6):
        if not piece_at(state["board"], (x, y+d)) and not piece_at(state["board"], (x, y+(d*2))):
            moves.append((pos, (x, y+(d*2))))
    # capture
    if x+1 < 8 and 0 < y+d < 8:
        piece = piece_at(state["board"], (x+1, y+d))
        if piece and get_color(piece) != color:
            moves.append((pos, (x+1, y+d)))
    if 0 <= x-1 and 0 < y+d < 8:
        piece = piece_at(state["board"], (x-1, y+d))
        if piece and get_color(piece) != color:
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
    if not in_check(state, color):
        castle_y = 0 if color == 'white' else 7
        if state["can castle"][color][0] and not any([piece_at(state["board"], (x, castle_y)) for x in range(1, 4)]):
            moves.append((pos, (2, castle_y)))
        if state["can castle"][color][1] and not any([piece_at(state["board"], (x, castle_y)) for x in range(5, 7)]):
            moves.append((pos, (6, castle_y)))
    return moves

GET_MOVES_MAP = {
    "Qq": queen_moves,
    "Rr": rook_moves,
    "Nn": knight_moves,
    "Bb": bishop_moves,
    "Pp": pawn_moves,
    "Kk": king_moves,
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
    slot1 = piece_at(state["board"], pos1)
    slot2 = piece_at(state["board"], pos2)
    col = get_color(slot1)
    
    # en passant check
    if slot1 in 'Pp' and x1 != x2 and slot2 is None:
        pos = (x, y2-1 if col == "white" else y2+1)
        piece = piece_at(state["board"], pos)
        state["board"][piece].remove(pos)
    
    # castle checks
    if slot1 in 'Kk':
        if abs(x2 - x1) > 1:
            if x2 - x1 > 0:
                state["board"]["R" if col == "white" else "r"].remove((y1, 0))
                state["board"]["R" if col == "white" else "r"].add((y1, 3))
            else:
                state["board"]["R" if col == "white" else "r"].remove((y1, 7))
                state["board"]["R" if col == "white" else "r"].add((y1, 5))
        state["can castle"][col] = [False, False]

    state["board"][slot1].remove(pos1)
    state["board"][slot1].add(pos2)

    if state["can castle"]['white'][0] and slot1 == "R" and pos1 == (0, 0):
        state["can castle"]['white'][0] = False
    if state["can castle"]['white'][1] and slot1 == "R" and pos1 == (7, 0):
        state["can castle"]['white'][1] = False
    if state["can castle"]['black'][0] and slot1 == "r" and pos1 == (0, 7):
        state["can castle"]['black'][0] = False
    if state["can castle"]['black'][1] and slot1 == "r" and pos1 == (7, 7):
        state["can castle"]['black'][1] = False

    check_promotions(state, autoqueen)

    state["turn"] = 'white' if state["turn"] == 'black' else 'black'
    state["stack"].append(move)

    state["moves"]["white"] = get_moves(state, "white", debug=DEBUG)
    state["moves"]["black"] = get_moves(state, "black", debug=DEBUG)
    
    return state

def check_promotions(state, piece_choice_func):
    for x, y in list(state["board"]["P"]):
        if y == 7:
            state["board"]["P"].remove((x, y))
            state["board"][piece_choice_func((x, y), 'white')].add((x, y))
    for x, y in list(state["board"]["p"]):
        if y == 0:
            state["board"]["p"].remove((x, y))
            state["board"][piece_choice_func((x, y), 'white')].add((x, y))

def check_perpetual(state):
    if len(state["stack"]) < 8:
        return False
    move1 = state["stack"][-1]
    move2 = state["stack"][-2]
    move3 = state["stack"][-3]
    move4 = state["stack"][-4]
    if (state["stack"][-5] != move1
        or state["stack"][-6] != move2
        or state["stack"][-7] != move3
        or state["stack"][-8] != move4):
        return False
    return True

#########################
#                       #
#    MOVE SELECTORS     #
#                       #
#########################

# progromatic move choice
def random_move(state, color, ply=False):
    return choice(state["legal moves"][color])
def minimax_by_point_value(state, color, ply=3, debug=DEBUG):
    score, move = minimax(ply, point_value, state, color, debug=debug)
    if debug: print("chose", score, move)
    return move
def minimax_by_full_evaluate(state, color, ply=3, debug=DEBUG):
    score, move = minimax(ply, full_evaluate, state, color, debug=debug)
    if debug: print("chose", score, move)
    return move
def minimax_full_evaluate_with_cache(state, color, ply=3, debug=DEBUG):
    cache = {}
    score, move = minimax(ply, full_evaluate, state, color, cache=cache, debug=debug)
    if debug: print("chose", score, move)
    return move
def minimax_full_evaluate_deepen_simple(state, color, ply=3, debug=DEBUG):
    """if there are only a few opponent peices left deepen search"""
    pieces = sum([len(state["board"][key]) for key in state["board"]])
    limit = 5
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
    captures, other = state["legal moves"][color]
    moves = captures + other
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

inverse = {0:7, 1:6, 2:5, 3:4, 4:3, 5:2, 6:1, 7:0}
def drawn_board(state):
    surf = Surface((SW*8, SW*8))
    for y in range(8):
        for x in range(8):
            col = "black square" if (x + y) % 2 == 1 else "white square"
            pygame.draw.rect(surf, COLORS[col], Rect((SW*x, SW*y), (SW, SW)))


    for piece in state["board"]:
        colorset = COLORS["{} piece".format(get_color(piece))]
        for key in PIECE_MAP:
            if piece in key:
                for x, y in state["board"][piece]:
                    tk.draw_token(surf, PIECE_MAP[key], (SW*x, SW*inverse[y]),
                                  col1=colorset[0], col2=colorset[1], PW=SW//16),
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
    state["moves"]["white"] = get_moves(state, "white", debug=DEBUG)
    state["moves"]["black"] = get_moves(state, "black", debug=DEBUG)
    get_legal_moves(state, "white", debug=DEBUG)
    get_legal_moves(state, "black", debug=DEBUG)

    if PIC:
        FRAME = 0
        save_img(drawn_board(state), FRAME)

    draw(state)
    while not check_perpetual(state):
        turn = state["turn"]
        captures, other = state["legal moves"][turn]
        if moves := captures + other:
            state["can en passant"][state["turn"]] = [False] * 8
            move_choose = white_move_choice if state["turn"] == "white" else black_move_choice
            move = move_choose(state, state["turn"], ply=WPLY if state["turn"] == "white" else BPLY)

            pos1, pos2 = move
            if pos1[1] == 1 and pos2[1] == 3 and piece_at(state["board"], pos1) == "P":
                state["can en passant"]['black'][pos1[0]] = True
            if pos1[1] == 6 and pos2[1] == 4 and piece_at(state["board"], pos1) == "p":
                 state["can en passant"]['white'][pos1[0]] = True
                 
            state = apply_move(state, move)

            if PIC:
                FRAME += 1
                save_img(drawn_board(state), FRAME)

                draw(state)
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
    return repr(board)

def check_cache(state, ply, cache=CACHE, Debug=True):
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

def cache_score(state, ply, score, cache=CACHE):
    if not CACHE_PLY or ply < CACHE_PLY: return
    trunc = truncate_board(state["board"])
    cache[state["turn"]][trunc] = (ply, score)

def minimax(ply, evaluate_func, state, color, alpha=-1000, beta=1000, cache=False, debug=False):
    get_legal_moves(state, "white", debug=DEBUG)
    get_legal_moves(state, "black", debug=DEBUG)

    captures, moves = state["legal moves"][state["turn"]]

    if check_perpetual(state): return 0, None

    if len(captures + moves) == 0:
        if in_check(state, state["turn"]):
            if state["turn"] == color:
                return -100 + ply, None
            else:
                return 100 + ply, None
        return 0, None


    if (ply <= 0):# and not captures) or (captures and ply <= -5):
        return evaluate_func(state, color), None


    moves = captures + moves if ply > 0 else captures
    if state["turn"] == color:
        value_max = -1000
        max_move = None
        for move in moves:
            # check cache
            is_cached = check_cache(state, ply)
            if is_cached is None:
                value, _ = minimax(ply-1, evaluate_func, apply_move(state, move), color, alpha, beta, debug=debug)
                cache_score(state, ply, value)
            else:
                value = cache
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
            # check cache
            is_cached = check_cache(state, ply)
            if cache is not None:
                value, _ = minimax(ply-1, evaluate_func, apply_move(state, move), color, alpha, beta, debug=debug)
                cache_score(state, ply, value)
            else:
                value = is_cache
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

    moves = state["moves"]

    points = {
        "black": 0,
        "white": 0,
    }

    for key in moves:
        for move in moves[key]:
            if piece_at(state["board"], move[0]) in "Qq": continue
            for n in move[1]:
                if n in (3, 4): points[key] += .25
                if n in (2, 5): points[key] += .2
                if n in (1, 6): points[key] += .2
                if n in (0, 7): points[key] += .15

    return points["white"] - points["black"] if color == "white" else points["black"] - points["white"]

def king_in_sight_points(state, color, debug=False):
    if debug:
        print("analyzing king safety")
        pretty_print_board(state["board"])
 
    points = {
        "black": sum(state["can castle"]["black"]) * 1.2,
        "white": sum(state["can castle"]["white"]) * 1.2,
    }

    for x, y in state["board"]["K"]:
        points["white"] -= len(check_lateral(state["board"], (x, y), "white"))
        points["white"] -= len(check_diagonal(state["board"], (x, y), "white"))
    for x, y in state["board"]["k"]:
        points["black"] -= len(check_lateral(state["board"], (x, y), "black"))
        points["black"] -= len(check_diagonal(state["board"], (x, y), "black"))

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

