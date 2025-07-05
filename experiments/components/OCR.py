import re

class OCRData:
    def __init__(self, data):
        self.data = data
        self.datanum = len(self.data)
        self.samplecount = 0
        
        if self.datanum > 0:
            self.samplecount = len(self.data[0])
            
        self.clean()
            
    
    def clean(self):
        cdata = [[] for d in self.data]
        
        for i,text in enumerate(self.data):
            for t in text:
                tclean = re.sub(r"[^\d.]", "", t)
                
                cdata[i].append(tclean)
                
        self.data = cdata
    
    