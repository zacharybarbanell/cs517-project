from z3 import Solver, Bool, And, Or, Not, sat
import json
import re
from tqdm import tqdm
from random import shuffle

#faster expression building - adapted in part from
#https://github.com/obijywk/grilops/blob/master/grilops/fastz3.py
from z3 import BoolRef, main_ctx
from z3.z3core import Z3_mk_and, Z3_mk_or, Z3_mk_not
from z3.z3types import Ast

CTX = main_ctx()
CTX_REF = CTX.ref()

def fastAnd(*args):
    sz = len(args)
    z3args = (Ast * sz)()
    for i, x in enumerate(args):
        z3args[i] = x.as_ast()
    return BoolRef(Z3_mk_and(CTX_REF, sz, z3args),CTX)

def fastOr(*args):
    sz = len(args)
    z3args = (Ast * sz)()
    for i, x in enumerate(args):
        z3args[i] = x.as_ast()
    return BoolRef(Z3_mk_or(CTX_REF, sz, z3args),CTX)

def fastNot(arg):
    return BoolRef(Z3_mk_not(CTX_REF, arg.as_ast()),CTX)

#these speed up expression generation by a factor of nearly ten
And = fastAnd
Or = fastOr
Not = fastNot

class Puzzle():
    def __init__(self, data):
        #store JSON data for output and debugging purposes
        self.metadata = data
        #parse puzzle data - based on parser used by puzz.link/pzv.jp frontend
        #https://github.com/sabo2/pzprjs/blob/master/src/variety-common/Encode.js#L17
        if not re.match(r'^shakashaka/\d+/\d+/[a-eg-z\.\d]+/?$',data['pzv']):
            #throw out weird puzzle data (seems to mostly be typos)
            raise ValueError(f"Bad data: {repr(data['pzv'])}")
        _, w, h, content, *_ = data['pzv'].split('/')
        w = int(w)
        h = int(h)
        self.w = w
        self.h = h
        self.data = [[None] * w for _ in range(h)]
        head = 0
        def write(v):
            if head >= w*h:
                #more weird puzzle data
                raise ValueError(f"Data too long: {repr(data['pzv'])}")
            self.data[head//w][head%w] = v
        for c in content:
            if '0' <= c <= '4':
                write(ord(c)-ord('0'))
            elif '5' <= c <= '9':
                write(ord(c)-ord('5'))
                head += 1
            elif 'a' <= c <= 'e':
                write(ord(c)-ord('a'))
                head += 2
            elif 'g' <= c <= 'z':
                head += ord(c)-ord('g')
            elif c == '.':
                write(-1)
            else:
                #unreachable by earlier regex
                assert(False)
            head += 1

    def __str__(self):
        #pretty-prints puzzle in a grid (only really works with some monospace fonts)
        lookup = {None: '.', -1: '■', 0: '0', 1: '1', 2: '2', 3: '3', 4: '4'}
        return '\n'.join(
            ''.join(
                lookup[self.data[y][x]] for x in range(self.w)
                ) for y in range(self.h)
            )

    def gen_sat_instance(self):
        symbols = {}
        clauses = []
        dirs = 'NESW'
        w,h = self.w,self.h
        #iteration goes from -1 to w/h, including cells one space outside of the grid
        #to enable systematic handling of boundary verticies
        for x in range(-1,w+1):
            for y in range(-1,h+1):
                pfx = f'{x}_{y}_'
                for d in dirs:
                    #create one symbol per space per direction
                    symbols[x,y,d] = Bool(pfx + d)
                if x == -1 or y == -1 or x == w or y == h or self.data[y][x] is not None:
                    #if cell is outside the grid or cell has a clue
                    for d in dirs:
                        #require all four quadrants to be shaded
                        clauses.append(symbols[x,y,d])
                else:
                    s1, s2, s3, s4 = (symbols[x,y,d] for d in dirs)
                    #for unclued cells, either two adjacent quadrants should be shaded, or nothing should be
                    clauses.append(
                        Or(
                            And(s1,s2,Not(s3),Not(s4)),
                            And(s2,s3,Not(s4),Not(s1)),
                            And(s3,s4,Not(s1),Not(s2)),
                            And(s4,s1,Not(s2),Not(s3)),
                            And(Not(s1),Not(s2),Not(s3),Not(s4))
                        )
                    )
        #for each vertex
        for x in range(w+1):
            for y in range(h+1):
                #adjacent 8 quadrants, in a cyclic order
                s = [symbols[  x,  y,'N'], symbols[  x,  y,'W'],
                     symbols[x-1,  y,'E'], symbols[x-1,  y,'N'],
                     symbols[x-1,y-1,'S'], symbols[x-1,y-1,'E'],
                     symbols[  x,y-1,'W'], symbols[  x,y-1,'S']]
                for i in range(8):
                    #disallow 45 degree angles
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                s[i-2]
                            )
                        )
                    )
                    #disallow 135 degree angles
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                Not(s[i-2]),
                                Not(s[i-3]),
                                s[i-4]
                            )
                        )
                    )
                    #disallow 225-315 degree angles
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                Not(s[i-2]),
                                Not(s[i-3]),
                                Not(s[i-4]),
                                Not(s[i-5])
                            )
                        )
                    )
        for x in range(w):
            for y in range(h):
                #if cell contains a number clue
                if self.data[y][x] in (0,1,2,3,4):
                    #adjust clue number to account for adjacent fully shaded cells
                    clue = self.data[y][x] + \
                           (x == 0 or self.data[y][x-1] is not None) + \
                           (x == w-1 or self.data[y][x+1] is not None) + \
                           (y == 0 or self.data[y-1][x] is not None) + \
                           (y == h-1 or self.data[y+1][x] is not None)
                    #quadrants of adjacent cells that touch this cell
                    s1,s2,s3,s4 = symbols[x-1,y,'E'],symbols[x,y-1,'S'],symbols[x+1,y,'W'],symbols[x,y+1,'N']
                    #require exactly (adjusted clue #) touching quadrants to be shaded
                    match clue:
                        case 0:
                            clauses.append(
                                And(Not(s1),Not(s2),Not(s3),Not(s4))
                            )
                        case 1:
                            clauses.append(
                                Or(
                                    And(s1,Not(s2),Not(s3),Not(s4)),
                                    And(s2,Not(s1),Not(s3),Not(s4)),
                                    And(s3,Not(s1),Not(s2),Not(s4)),
                                    And(s4,Not(s1),Not(s2),Not(s3))
                                )
                            )
                        case 2:
                            clauses.append(
                                Or(
                                    And(s1,s2,Not(s3),Not(s4)),
                                    And(s1,s3,Not(s2),Not(s4)),
                                    And(s1,s4,Not(s2),Not(s3)),
                                    And(s2,s3,Not(s1),Not(s4)),
                                    And(s2,s4,Not(s1),Not(s3)),
                                    And(s3,s4,Not(s1),Not(s2))
                                )
                            )
                        case 3:
                            clauses.append(
                                Or(
                                    And(s1,s2,s3,Not(s4)),
                                    And(s1,s2,s4,Not(s3)),
                                    And(s1,s3,s4,Not(s2)),
                                    And(s2,s3,s4,Not(s1))
                                )
                            )
                        case 4:
                            clauses.append(
                                And(s1,s2,s3,s4)
                            )
                        case _:
                            #trivially unsatisfiable clues like a 4 in a corner
                            raise ValueError("Clue too large")
        self.symbols = symbols
        self.clauses = clauses

    def solve(self):
        s = Solver()
        s.add(self.clauses)
        if not s.check() == sat:
            raise ValueError("Unsolvable Puzzle")
        self.solution = s.model()

    def solved_grid(self):
        #pretty print solution in a grid
        def get_symbol(x,y):
            a,b,c,d = self.solution[self.symbols[x,y,'N']], \
                    self.solution[self.symbols[x,y,'E']], \
                    self.solution[self.symbols[x,y,'S']], \
                    self.solution[self.symbols[x,y,'W']]
            match (a.py_value(),b.py_value(),c.py_value(),d.py_value()):
                case (True,True,False,False):
                    return '◥'
                case (False,True,True,False):
                    return '◢'
                case (False,False,True,True):
                    return '◣'
                case (True,False,False,True):
                    return '◤'
                case (False,False,False,False):
                    return ' '
                case _:
                    #illegally filled cells (e.g. only one quadrant filled or fully shaded open cell)
                    raise ValueError(f"Malformed solution data: {x,y,(a,b,c,d)}")
        lookup = {-1: '■', 0: '0', 1: '1', 2: '2', 3: '3', 4: '4'}
        return '\n'.join(
            ''.join(
                lookup[self.data[y][x]] if self.data[y][x] is not None else get_symbol(x,y) for x in range(self.w)
            ) for y in range(self.h)
        )

puzzles = []
def main():
    errors = 0

    #data obtained from https://puzz.link/db/?type=shakashaka&variant=no
    #using an undocumented but public API to get the full JSON data for all puzzles matching those conditions
    with open("pzvs_anon.json") as f:
        for line in json.loads(f.read()):
            try:
                puzzles.append(Puzzle(line))
            except ValueError:
                errors += 1

    print(f'Data successfully loaded for {len(puzzles)}/{len(puzzles)+errors} puzzles.')

    for p in tqdm(puzzles, 'Generating SAT instances'):
        p.gen_sat_instance()

    for p in tqdm(puzzles, 'Solving puzzles'):
        p.solve()

    bad_puzzles = []

    #Z3 occasionally outputs wrong solutions (despite correctly identifying the expressions as satisfiable)
    #see https://github.com/Z3Prover/z3/issues/7658
    for p in tqdm(puzzles, 'Finding puzzles with broken solutions'):
        if not p.solution.eval(And(*p.clauses)).py_value():
            bad_puzzles.append(p)

    #try a few times
    for _ in range(5):
        if len(bad_puzzles) == 0:
            break
        print(f'{len(bad_puzzles)} puzzles with broken solutions found.')
        bpp = []
        for p in tqdm(bad_puzzles, 'Re-solving puzzles with broken solutions'):
            #for some reason changing clause order has a good chance to fix them
            shuffle(p.clauses)
            p.solve()
            if not p.solution.eval(And(*p.clauses)).py_value():
                bpp.append(p)
        bad_puzzles = bpp

    if len(bad_puzzles) > 0:
        print('Failed to fix all broken puzzles, aborting.')
        for p in bad_puzzles:
            print(p.metadata)
        return

    with open('solutions_out.txt','wb') as f:
        for p in tqdm(puzzles, 'Writing solutions to file'):
            f.write(bytes(str(p.metadata),'utf8'))
            f.write(b'\n')
            f.write(bytes(p.solved_grid(),'utf8'))
            f.write(b'\n\n')

    print('Complete!')

if __name__ == "__main__":
    main()
