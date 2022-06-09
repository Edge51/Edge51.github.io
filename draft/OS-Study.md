# Operating System

lock
critical sections
atomic

coarse-grained
fine-grained

how to build a efficient lock

evaluating locks

criteria
fairness
performance

Solution 1: controlling interrupts

benefits: simplicity
negatives:
	privileged :dangerous
	not working on multiprocessor machine
	interrupts may lost
	inefficient

failed attempt: Loads/Stores

test-and-set I think it's just fetch and set although the name test is given for you can test the old value with return value.
compare-and-swap
load-linked and store-conditional

too much spinning

yielding cpu
	running, ready, blocking
	self deschedule
	still loop running and yielding
	starvation: some thread still may not be able to execute

sleeping instead of yielding
	pack,unpack
	spin lock with queue determine which thread to run next, pack to sleep until some call unpack(threadid)
	wakeup/waiting race: setpark

futex