from solver import Puzzle

class WebPuzzle(Puzzle):
    def __init__(self,w,h,data):
        self.w = w
        self.h = h
        self.data = [[None] * w for _ in range(h)]
        v = [int(x) for x in data.split(',')]
        for i,x in enumerate(v):
            if x == -1:
                pass
            elif x == -2:
                self.data[i//w][i%w] = -1
            else:
                self.data[i//w][i%w] = x

    def get_js_solution(self):
        #pretty print solution in a grid
        def get_value(x,y):
            a,b,c,d = self.solution[self.symbols[x,y,'N']], \
                    self.solution[self.symbols[x,y,'E']], \
                    self.solution[self.symbols[x,y,'S']], \
                    self.solution[self.symbols[x,y,'W']]
            match (a.py_value(),b.py_value(),c.py_value(),d.py_value()):
                case (True,True,False,False):
                    return 2
                case (False,True,True,False):
                    return 3
                case (False,False,True,True):
                    return 4
                case (True,False,False,True):
                    return 1
                case (False,False,False,False):
                    return None
                case _:
                    #illegally filled cells (e.g. only one quadrant filled or fully shaded open cell)
                    raise ValueError(f"Malformed solution data: {x,y,(a,b,c,d)}")
        o = []
        for y in range(self.h):
            for x in range(self.w):
                if self.data[y][x] is None:
                    val = get_value(x,y)
                    if val != None:
                        o.append(f'Game.currentState.cellStatus[{y}][{x}]={val};')
        return ''.join(o)




        












