import sys
sys.path.append("..")
import formats.config as conf
import os
import subprocess as sp

defaultExecutable='runnable'

class JudgeInstance:
    def __init__(self,dir_path):
        os.chdir(dir_path)

        self.echo=sp.Popen(dir_path,stdin=sp.PIPE,stdout=sp.PIPE,universal_newlines=True)
        self.type='traditional'
        self.data=['']
        pass

    def runOneSubstance(self):
        if self.type=='traditional':
            for d in self.data:
                self.echo.stdin.write(d)
                self.echo.stdin.flush()
                result=self.echo.stdout.read()

    def generateResponse(self)->conf.TestPointStatus:


