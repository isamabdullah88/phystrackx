

class OCRData:
    def __init__(self, data):
        self.data = data
        self.datanum = len(self.data)
        self.samplecount = 0
        
        if self.datanum > 0:
            self.samplecount = len(self.data[0])
            
            
    
    