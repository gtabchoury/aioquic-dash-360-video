import time

class Buffer():
    def __init__(self, n_segments, segment_time):
        self.n_segments = n_segments
        self.segment_time = segment_time
        self.producer_current = 0
        self.consumer_current = 0
        self.finished = False
        self.lockings = 0
        self.timer = 0

    def write(self):
        #print('Buffer: write')
        self.producer_current += 1

    def read(self):
        #print('Buffer: read')
        self.consumer_current += 1

    def finish(self):
        #print('Buffer: finished')
        self.finished = True

    def start(self):
        while not self.finished:
            if (self.producer_current<=self.consumer_current):
                #print('Buffer: locked')
                self.lockings += 1
                #while (self.producer_current<=self.consumer_current):
                #    self.timer += 1
            else:
                self.read()
                time.sleep(1)
        print('Buffer finished!')
                
