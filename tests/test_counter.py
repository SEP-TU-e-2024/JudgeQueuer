import threading

from protocol.counter import Counter


#Example unit tests
class TestCounter:
    """Tests for the Counter class"""

    def test_counting(self):
        #Set up a counter starting at 0
        self.counter = Counter(0)
        #Check whether the counter succesfully works
        assert self.counter.generate() == 0
        assert self.counter.generate() == 1
        assert self.counter.generate() == 2
        assert self.counter.generate() == 3
    
    #Define a function to be used by the thread testing
    def thread_function(self):
        return self.counter.generate()
    
    def test_multithread(self):
        #Set up a new counter starting at 0
        self.counter = Counter(0)
        #Store the threads in a list so we can find them back later
        threads = []
        #Start five threads that increment the counter
        for i in range(5):
            #Create a new thread
            x = threading.Thread(target=self.thread_function)
            #Start the thread
            x.start()
            #Add the thread to the threadlist
            threads += [x]
        #Make sure that each individual generate() method got called succesfully
        assert self.counter.generate() == 5
        #Close all of the threads
        for i in threads:
            i.join()