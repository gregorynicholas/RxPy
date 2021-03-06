# Current Thread Scheduler

import time
import logging
from datetime import timedelta

from rx.internal import PriorityQueue

from .scheduler import Scheduler
from .scheduleditem import ScheduledItem

log = logging.getLogger('Rx')

class Trampoline(object):
    def __init__(self):
        self.queue = PriorityQueue(4)

    def enqueue(self, item):
        return self.queue.enqueue(item)

    def dispose(self):
        self.queue = None

    def run(self):
        #print "Trampoline:run"
        while self.queue.length > 0:
            item = self.queue.dequeue()
            if not item.is_cancelled():
                diff = item.duetime - Scheduler.now()
                while diff > timedelta(0):
                    seconds = diff.seconds + diff.microseconds / 1E6 + diff.days * 86400
                    log.info("Trampoline:run(), Sleeping: %s" % seconds)
                    time.sleep(seconds)
                    diff = item.duetime - Scheduler.now()
                
                if not item.is_cancelled():
                    #print("item.invoke")
                    item.invoke()

class CurrentThreadScheduler(Scheduler):    
    def __init__(self):
        self.queue = 0 # Must be different from None, FIXME: 

    def schedule(self, action, state=None):
        log.debug("CurrentThreadScheduler.schedule(state=%s)", state)
        return self.schedule_relative(timedelta(0), action, state)

    def schedule_relative(self, duetime, action, state=None):
        log.debug("CurrentThreadScheduler.schedule_relative(duetime=%s, state=%s)" % (duetime, state))
        dt = self.now() + Scheduler.normalize(duetime)
        si = ScheduledItem(self, state, action, dt)
        
        if not self.queue:
            self.queue = Trampoline()
            try:
                self.queue.enqueue(si)
                self.queue.run()
            finally:
                self.queue.dispose()
                self.queue = None            
        else:
            self.queue.enqueue(si)
        
        return si.disposable

    def schedule_absolute(self, duetime, action, state=None):
        return self.schedule_relative(duetime - self.now(), action, state=None)

    def schedule_required(self):
        return self.queue is None
    
    def ensure_trampoline(self, action):
        if self.queue is None:
            return self.schedule(action)
        else:
            return action(self, None)

current_thread_scheduler = CurrentThreadScheduler()