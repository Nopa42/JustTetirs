import os
import copy
import time
import random
import keyboard

from dataclasses import dataclass
from functools import lru_cache
from enum import Enum


# [0,0] [1,0] ... [0,N]
# [0,1] [1,1] ... [1,N]
#  ...   ...  ...  ...
# [0,N] [0,N+1]...[N,N]
#
# X → Right (Cols)
# Y → Down  (Rows)
# grid[X,Y]

# TODO Add support for Linux keys

class PrintConst:
    GAME_OVER_MSG_LINES = 3
    GAME_OVER_MSG = """┏┓┏┓┳┳┓┏┓ ┏┓┓┏┏┓┳┓╻
┃┓┣┫┃┃┃┣  ┃┃┃┃┣ ┣┫┃
┗┛┛┗┛ ┗┗┛ ┗┛┗┛┗┛┛┗•
"""
    TETRIS_MSG_LINES = 4 
    TETRIS_MSG = """░▀▀█░█░█░█▀▀░▀█▀░░░▀█▀░█▀▀░▀█▀░█▀▄░▀█▀░█▀▀░
░░░█░█░█░▀▀█░░█░░░░░█░░█▀▀░░█░░█▀▄░░█░░▀▀█░
░▀▀░░▀▀▀░▀▀▀░░▀░░░░░▀░░▀▀▀░░▀ ░░▀░▀░▀▀▀░▀▀▀░
"""     
    PRINT_CELL_WIDTH  = 2
    PRINT_CELL_HEIGHT = 2 
    BOARD_PADD        = 11
    UP_BOARDER        = 1


class ANSI:
    COLORS = {
        "RED"    : "\033[0;31m",
        "GREEN"  : "\033[0;32m",
        "YELLOW" : "\033[0;33m",
        "BLUE"   : "\033[0;34m",
        "PURPLE" : "\033[0;35m"
    }

    RESET_COLOR = "\033[0;0m"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h" 
    SAVE_CURSOR_POS     = "\x1b7"
    RESTORE_CURSOR_POS  = "\x1b8"

class Direction(tuple, Enum):
    UP    = (0, -1)
    DOWN  = (0, 1)
    LEFT  = (-1, 0)
    RIGHT = (1, 0)

class ShapesForm:
    COUNT = 7

    SHAPES = {
        "O" : [(0,-1), (1,-1), (0,0), (1,0)],
        "I" : [(0,-2), (0,-1), (0,0), (0,1)],
        "T" : [(-1,-1), (0,-1), (1,-1), (0,0)],
        "L" : [(-1,-1), (-1,0), (-1,1), (0,1)],
        "J" : [(1,-1), (1,0), (1,1), (0,1)],
        "Z" : [(-1,0), (0,0), (0,1), (1,1)],
        "S" : [(-1,1), (0,0), (0,1), (1,0)]
    }           

class Config:
    GRID_HEIGHT         = 20        
    GRID_WIDTH          = 10
    FPS_GOAL            = 60
    START_SHAPE_POS     = (GRID_WIDTH // 2, -2)
    GRID_LINE_PRINT_LEN = (GRID_WIDTH + 1) * 2
    LINES_PER_LEVEL     = 5
    START_LEVEL         = 1
    GRAVITY_CLOCK       = 20
    SHAPE_TEXTURE       = ['#', '▒', '▓', '█']
    DIFFICULTY_CURVE    = 3


clear            = lambda: os.system('cls')
cursor_to_pos    = lambda line, column: print(f"\033[{line};{column}f", end="")
cursor_to_line   = lambda line   : print(f"\033[{line}H", end="")
cursor_to_column = lambda column : print(f"\033[{column}G", end="")


class RandomBag:
    def __init__(self, maximum):
        self.maximum = maximum
        self.shuff_bag = []

    def generate_random_bag(self):        
        list_ = list(range(self.maximum))

        while list_:
            select = random.choice(list_)
            self.shuff_bag.append(select)
            list_.remove(select)

    def get_next(self):
        if not self.shuff_bag:
            self.generate_random_bag()

        # Removes and return the last item from the list
        return self.shuff_bag.pop()

class Cell:
    def __init__(self, content = "", falling = False, color = ""):
        self.content = content
        # self.falling = falling
        self.color   = color

class Grid:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols

        # Init 2D array of size cols rows with cell calss instances
        self.state = [[Cell() for _ in range(cols)] for _ in range(rows)]

    def __getitem__(self, pos):
        x, y = pos
        
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self.state[y][x]
        
        raise IndexError(f"[ERROR] - invalid grid coordinates ({x}, {y}), out of range.")

    def __setitem__(self, pos, value):
        x, y = pos

        # Test if assigned value is a Cell
        if not isinstance(value, Cell):
            raise TypeError(f"[ERROR] - grid cell accepts Cell objects only, got {type(value).__name__} instead.")

        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.state[y][x] = value
        
        else:
            raise IndexError(f"[ERROR] - invalid grid coordinates ({x}, {y}), out of range.")

class Shape:
    def __init__(self, x, y, offsets, texture, color):
        self.x = x                  # Shape origin cords
        self.y = y
        self.shape_parts = offsets  # Relative to x, y
        self.texture = texture
        self.color = color
        # self.falling = True
    
    def __iter__(self):
        # Set shape iturable to cell x, y

        for offset in self.shape_parts:
            x_pos = self.x + offset[0]
            y_pos = self.y + offset[1]

            yield (x_pos, y_pos)

class Render():

    # TODO Simplfy this func
    def print_title_screen(grid):
        longest_title_message_len = max([len(message_line) for message_line in PrintConst.TETRIS_MSG.splitlines()])
        
        # Board is wider than title
        if longest_title_message_len < Config.GRID_LINE_PRINT_LEN:

            # Print TETRIS message center aligned to board
            for message_line in PrintConst.TETRIS_MSG.splitlines():
                print(f"{message_line:^{Config.GRID_LINE_PRINT_LEN}}")

        else:
            print(PrintConst.TETRIS_MSG)
    
    def print_game_over(grid):
        print(ANSI.SAVE_CURSOR_POS)
        
        cursor_to_line(Config.GRID_HEIGHT + PrintConst.GAME_OVER_MSG_LINES)      

        # Print GANE OVER message center aligned and over grid
        for message_line in PrintConst.GAME_OVER_MSG.splitlines():
            print(f"\033[{(Config.GRID_LINE_PRINT_LEN - len(message_line)) // 2 + PrintConst.BOARD_PADD}C{message_line}")

        # Fix and unhide cursor
        cursor_to_line(Config.GRID_HEIGHT * 2 + PrintConst.TETRIS_MSG_LINES)
        print(ANSI.SHOW_CURSOR)   

    def print_grid(grid):

        @lru_cache(maxsize=5)
        def build_grid(grid):
            print_lines = []

            top    = f"┌{"─┬" * (grid.cols - 1)}─┐"
            middle = f"├{"─┼" * (grid.cols - 1)}─┤"
            bottom = f"└{"─┴" * (grid.cols - 1)}─┘"

            print_lines.append(top)

            for row in grid.state:
                formatted_cells = (f"│{cell.color}{cell.content if cell.content else ' '}{ANSI.RESET_COLOR}" for cell in row)

                # Join formated cells to line
                content_row = f"{''.join(formatted_cells)}│"
                print_lines.append(content_row) 

                print_lines.append(middle)

            # Overide last middle with fotter line
            print_lines[-1] = bottom

            cursor_to_line(PrintConst.TETRIS_MSG_LINES)

            # Pads and print list of lines
            return("\n".join(f"{PrintConst.BOARD_PADD * ' '}{line}" for line in print_lines))

        print(build_grid(grid))
    
    def print_shape(shape):
        pos_x, pos_y = shape.x, shape.y
        
        for position in shape.shape_parts:
            dx, dy = position

            if pos_y + dy < 0:
                continue

            cursor_to_pos((dy + pos_y) * PrintConst.PRINT_CELL_HEIGHT + PrintConst.TETRIS_MSG_LINES + PrintConst.UP_BOARDER, (pos_x + dx) * PrintConst.PRINT_CELL_WIDTH + PrintConst.BOARD_PADD + 2)
            print(f"{shape.color}{shape.texture}{ANSI.RESET_COLOR}")

        cursor_to_line(PrintConst.TETRIS_MSG_LINES + PrintConst.UP_BOARDER + Config.GRID_HEIGHT * 2)


class TetrisGame():
    def __init__(self):
        self.grid  = Grid(Config.GRID_HEIGHT, Config.GRID_WIDTH)
        self.level = Config.START_LEVEL
        self.spawner = self.create_shape_generator()
        self.current_shape = self.spawner()
        self.is_game_over = False
        self.cleared_lines = 0
        self.gravity_state = 0
    
    def create_shape_generator(self):    
        shape_colors = list(ANSI.COLORS.values())
        shapeRand = RandomBag(ShapesForm.COUNT)
        
        def generate_shape():
            return Shape(  
                Config.START_SHAPE_POS[0],     
                Config.START_SHAPE_POS[1],
                list(ShapesForm.SHAPES.values())[shapeRand.get_next()], 
                random.choice(Config.SHAPE_TEXTURE),
                random.choice(shape_colors)
            )
        
        return generate_shape

    def input_handler(self):
        keyboard.on_press_key("left arrow"  , lambda _: self.move_shape   (Direction.LEFT ))
        keyboard.on_press_key("right arrow" , lambda _: self.move_shape   (Direction.RIGHT))
        keyboard.on_press_key("down arrow"  , lambda _: self.move_shape   (Direction.DOWN ))
        keyboard.on_press_key("up arrow"    , lambda _: self.rotate_shape ())            # Rotate anti clock 
        keyboard.on_press_key("space"       , lambda _: self.hard_drop    ())
    
    def line_complete(self):

        # Iturate bottom up with index
        for index, row in enumerate(self.grid.state):
            
            if all(cell.content != "" for cell in row):
                self.cleared_lines += 1
                self.grid.state.pop(index)                
                self.grid.state.insert(0, [Cell() for _ in range(self.grid.cols)])
    
    def shape_to_grid(self):
        ShapeCell = Cell(self.current_shape.texture, False, self.current_shape.color)

        for position in self.current_shape:
            x, y = position
            
            if y < 0:
                continue

            self.grid[x, y] = ShapeCell
            
    def valid_grid_position(self, x, y): 
        if 0 > x or x >= self.grid.cols or y >= self.grid.rows: 
            return False

        if y > 0:
            if self.grid[x, y].content:
                return False
        
        # Free and valid
        return True

    def move_shape(self, direction):
        dx, dy = direction

        for x, y in self.current_shape:
            x2 = x + dx
            y2 = y + dy

            if not self.valid_grid_position(x2, y2):
                return False
        
        self.current_shape.x += dx
        self.current_shape.y += dy

        return True

    def rotate_shape(self):
        
        # Calc offsets of rotated shape
        new_offsets = [(y, -x) for x, y in self.current_shape.shape_parts]
        
        # Validation Check, is legal rotation
        for dx, dy in new_offsets:
            x2 = self.current_shape.x + dx
            y2 = self. current_shape.y + dy

            if not self.valid_grid_position(x2, y2):
                return False
        
        self.current_shape.shape_parts = new_offsets
        return True

    def hard_drop(self):
        while self.move_shape(Direction.DOWN):
            pass

    def advance_state(self):
        self.gravity_state += 1
        
        if self.gravity_state >= (Config.GRAVITY_CLOCK - Config.DIFFICULTY_CURVE * self.level):

            self.gravity_state = 0
            
            # If active piece cant fall 
            if not self.move_shape(Direction.DOWN):

                    # Shape to grid
                    self.shape_to_grid()
                    
                    if self.current_shape.y < 1:
                        self.is_game_over = True 

                        Render.print_game_over(self.grid)
                        return

                    self.line_complete()
                    self.current_shape = self.spawner()          
                    self.level = self.cleared_lines // Config.LINES_PER_LEVEL + Config.START_LEVEL
        
        Render.print_grid(self.grid)
        Render.print_shape(self.current_shape)


def main():
    clear()

    # Init Game
    game = TetrisGame()                            
    
    game.input_handler()
    
    Render.print_title_screen(game.grid)

    dropedFrames = 0
    
    print(ANSI.HIDE_CURSOR)

    # Game Loop
    while not game.is_game_over:
        start_time = time.time()

        game.advance_state()
        elapsed = (time.time() - start_time)
        
        print(f"Elapsed: {elapsed :.3f} | Droped Frames: {dropedFrames} | Level: {game.level}")
        
        if elapsed < 1 / (Config.FPS_GOAL):
            time.sleep( 1 / (Config.FPS_GOAL) - elapsed)
        else:
            dropedFrames += 1

if __name__ == "__main__":
    main()   