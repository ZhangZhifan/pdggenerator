# -*- coding: utf-8 -*-  
import sys
sys.path.extend(['.', '..'])
from pycparser import c_generator

class PreprocessCGenerator(c_generator.CGenerator):
    """
    修改CGenerator
    使其具有预处理功能
    """
    
    # for循环的next语句，用于处理continue
    loopNext = None

    def visit_For(self, n):
        """
        For 改 While
        在while前写init
        while(cond)
        循环体最后写next
        """
        s = ''
        if n.init:
            s += self.visit(n.init) + ';\n'
        s += 'While ('
        if n.cond:
            s += self.visit(n.cond)
        else:
            s += '1'
        s += ') {\n'

        lastLoopNext = self.loopNext
        if n.next:
            nextStr = self.visit(n.next) + ';\n'
            self.loopNext = nextStr

        s += self._generate_stmt(n.stmt, add_indent=True)
        if n.next:
            s += nextStr
        s += '}\n'
        self.loopNext = lastLoopNext
        return s

    def visit_Continue(self, n):
        s = ''
        if self.loopNext:
            s += self.loopNext
        s += 'continue;'
        return s

def test():
    pass

if __name__ == "__main__":
    test()