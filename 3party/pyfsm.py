"""
pyfsm - Python Finite State Machine
===================================

A simple Python finite state machine implementation.

pyfsm is based on various states contained within a task.
The task can be retrieved using L{pyfsm.task_registry.get_task}.
Use the L{pyfsm.Registry} object as the central L{pyfsm.task_registry}.

Everything in pyfsm is used as a decorator. For example, to declare
a new state, use the following:

>>> @state('task_name')
... def state_name(tsk): # tsk is the task object
...     ...

To specify transitions, use the L{pyfsm.transition} decorator.

>>> @transition(key, 'next_state'):
... def state_name(tsk):
...     ...

Multiple transitions can be chained onto a single state. The function
will be called when the state is entered. In addition, you can specify
callbacks and exit handlers for a specific task. For example, to
perform an event when the value '1' is sent, you could do...

>>> def state_name(tsk):
...     @tsk.callback(1)
...     def print_one(event):
...         print event

To add an exit handler, use L{task.atexit}.

>>> def state_name(tsk):
...     @tsk.atexit
...     def goodbye(self): # self is a task object
...         print 'goodbye'

To start a task, grab the task from the registry and call L{pyfsm.task.start}.

>>> task1 = pyfsm.Registry.get_task('task1')
>>> task1.start('start_state') # start the state machine
>>> task1.send(1) # send 1 as the event to the state machine
>>> task1.send(2) # send 2
>>> ...

Sending immutable values, while it can be useful, doesn't always work.
pyfsm allows you to specify a handler for retrieving the key
used when processing events. These keys can be set on two levels.

 - Specific task
 - Task registry

These are processed, in order. If neither of these works, then the
default handler is used (which just uses the object identity).
For example, to set a custom key retrieval on the task level:

>>> def key_retrieve(event):
...     return event.type # type is the variable we want to use as the key
>>> pyfsm.Registry.set_retrieval_func(key_retrieve, 'task1')

To set a key retrieval for the system as a whole, use the same function
but leave out the string specifying the task name.
"""

# Copyright (c) 2011, Jonathan Sternberg All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:

#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials
#       provided with the distribution.
#     * Neither the name of pyfsm nor the names of its
#       contributors may be used to endorse or promote products
#       derived from this software without specific prior written
#       permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__author__ = 'Jonathan Sternberg'
__copyright__ = 'Copyright 2011'
__credits__ = ['Jonathan Sternberg']
__license__ = 'New BSD'
__version__ = '1.0'
__maintainer__ = 'Jonathan Sternberg'
__email__ = 'jonathansternberg@gmail.com'
__status__ = 'Development'

class task_registry(object):
    """
    Keeps track of the tasks that have been declared.

    This object should not be created by the user, but should
    instead reference the L{pyfsm.Registry} value instead.

    Tasks are added to the L{pyfsm.Registry} automatically
    and can be retrieved with with L{get_task}.
    """
    def __init__(self):
        self.tasks = {}
        self.getattr = None

    def set_retrieval_func(self, getter, task_name = None):
        """
        Sets a function to be used to retrieve the key from an
        event on the task level.

        If a task_name is given, then this will assign the key
        retrieval function to only that specific task.

        @param getter: Retrieval function.
        @type getter: C{function}
        @param task_name: Task to attach this retrieval function to.
        @type task_name: C{str}
        """
        if task_name:
            tsk = self.get_task(task_name)
            tsk.getattr = getter
        else:
            self.getattr = getter
    def get_retrieval_func(self, task_name = None):
        """
        Gets the key retrieval function.

        If a task name is given, then this return a tuple
        with the task's retrieval function as the first element
        and the registry's retrieval function as the second element.

        @param task_name: Task name to get key retrieval function from.
        @type task_name: C{str}
        @returns: Key retrieval function for a task/task registry.
        @rtype: C{(function, function)} or C{function}
        """
        if task_name:
            tsk = self.get_task(task_name)
            return tsk.getter, self.getter
        else:
            return self.getter

    def get_task(self, name):
        """
        Recovers a named task.

        @param name: Task name.
        @type name: C{str}
        @note: If the task does not exist yet, this will create it.
        Tasks are made automatically when using the L{pyfsm.state}
        decorator.
        """
        return self.tasks.setdefault(name, task(name))

"""
Registry where all tasks are stored.

Tasks are made through teh L{pyfsm.state} decorator automatically.
They are stored inside of the L{pyfsm.Registry} object for later
retrieval.
"""
Registry = task_registry()

class task(object):
    """
    Denotes a task of operation.

    Tasks contain a set of states and transitions. To add a state
    to a task, use the L{pyfsm.state} decorator and give the
    task name as the parameter.
    """
    warn_msg = 'warning: multiple instances of state %s in task %s'
    def __init__(self, name):
        self.name = name
        self.current_state = None
        self.states = {}
        self.getattr = None

        self._locals = {}
        self._globals = {}
        self.callbacks = {}
        self.exit = []
        class callback(object):
            def __init__(callback, key):
                self.key = key
            def __call__(callback, func):
                if not self.callbacks.has_key(self.key):
                    self.callbacks[self.key] = []
                self.callbacks[self.key].append(func)
                return func
        self.callback = callback

    def atexit(self, func):
        """
        Register a function to be called upon exiting the current state.

        @param func: exit handler.
        @type func: C{function}
        @note: The list of exit function clears itself after they are called.
        """
        assert self.current_state, 'state machine is not running'
        self.exit.append(func)
        return func

    def start(self, name):
        """
        Starts the task with the given state name.

        @param name: state name.
        @type name: C{str}
        """
        for x in self.exit:
            x(self)

        self.current_state = self.states[name]
        self.callbacks = {}
        self.exit = []
        self._locals = {}
        self.current_state.enter(self)

    def send(self, event):
        """
        Sends an event to this task.

        It determines what key to use to identify the event by
        calling the appropriate getattr function.

        If any callbacks are registered for this event, then they are
        invoked first.

        If any transitions are registered for this event, a state transition
        is invoked after completing the callbacks.

        @param event: event to send to the state machine
        """
        assert self.current_state, 'state machine is not running'

        # recover the key for this event
        for getattr in (self.getattr, Registry.getattr, lambda x: x):
            try: key = getattr(event)
            except: pass
            else: break

        # check callbacks first
        callback = self.callbacks.get(key, [])
        for x in callback:
            x(event)

        # if a transition exists, change the state
        trans = self.current_state.transitions.get(key, None)
        if trans:
            self.start(trans)

    def start2(self, name, obj):
        """
        Starts the task with the given state name.

        @param name: state name.
        @param obj: data obj. for func.
        @type name: C{str}
        """
        for x in self.exit:
            x(self, obj)

        self.current_state = self.states[name]
        self.callbacks = {}
        self.exit = []
        self._locals = {}
        return self.current_state.enter2(self, obj)
        #return None
        #   just set FSM action, not need realy do !
        
    def send2(self, event, obj):
        """
        Sends an event to this task.

        It determines what key to use to identify the event by
        calling the appropriate getattr function.

        If any callbacks are registered for this event, then they are
        invoked first.

        If any transitions are registered for this event, a state transition
        is invoked after completing the callbacks.

        @param event: event to send to the state machine
        @param obj: data obj. for func.
        """
        assert self.current_state, 'state machine is not running'

        # recover the key for this event
        for getattr in (self.getattr, Registry.getattr, lambda x: x):
            try: key = getattr(event)
            except: pass
            else: break

        # check callbacks first
        callback = self.callbacks.get(key, [])
        for x in callback:
            x(event, obj)

        # if a transition exists, change the state
        trans = self.current_state.transitions.get(key, None)
        if trans:
            return self.start2(trans ,obj)
        else:
            # when state transited, call old  current_state func again!
            return self.current_state.enter2(self, obj)

    def add_state(self, name, state):
        """
        Adds a state to this task.

        @param name: name of the state.
        @type name: C{str}
        @param state: the state object created by the L{pyfsm.state} decorator.
        @type state: L{pyfsm.state}
        @note: This will not prevent multiple states from being
        named the same thing, but it will attempt to warn you.
        """
        if self.states.has_key(name):
            print task.warn_msg % (name, self.name)
        self.states[name] = state

    def get_name(self):
        """
        Retrieves the task name.

        @returns: task name.
        @rtype: C{str}
        """
        return self.name

    @property
    def locals(self):
        """
        Returns a dictionary of local variables.

        @returns: local state variables.
        @rtype: C{dict}
        @note: Local variables are cleared every time a state transition
        happens.
        """
        return self._locals
    @property
    def globals(self):
        """
        Returns a dictionary of global variables.

        @returns: global state variables.
        @rtype: C{dict}
        @note: Global variables are kept for inter-state communication.
        This does not alter the real globals table and is only "global"
        to the specific task.
        """
        return self._globals

class transition(object):
    """
    Decorator to add a transition to a state.

    Used on a function with the following:

    >>> @transition(1, 'goodbye')
    ... def hello_state(tsk):
    ...    ...

    This will create a transition to the 'goodbye' state if the key '1' is
    ever received.

    @param key: event that triggers this transition.
    @param value: the state to transition to when this transition is triggered.
    @type value: C{str}
    """
    def __init__(self, key, value):
        self.key = key
        self.value = value
    def __call__(self, func):
        trans = getattr(func, 'transitions', {})
        trans[self.key] = self.value
        setattr(func, 'transitions', trans)
        return func

class state(object):
    """
    Decorator to create a state.

    A state is made with the following:

    >>> @state('task_name')
    ... def print_hello(tsk):
    ...     print 'hello, world'

    This will register a state named 'print_hello' into the 'task_name'
    task. This assigns 'print_hello' as a L{pyfsm.state} object
    (it is not a function anymore).

    This can (and should) be combined with the L{pyfsm.transition} decorator.

    @param name: the task name this state should be added into.
    @type name: C{str}
    @note: State names are inferred by the function name.
    """
    def __init__(self, name):
        self.task = Registry.get_task(name)
        self.transitions = {}

    def __call__(self, func):
        self.func = func
        self.transitions.update(getattr(func, 'transitions', {}))
        self.task.add_state(func.__name__, self)
        return self

    def enter(self, task):
        """
        Entrance function to this state.

        @param task: task this state is contained within
        @type task: L{pyfsm.task}
        """
        return self.func(task)

    def enter2(self, task, obj):
        """
        Entrance function to this state.

        @param task: task this state is contained within
        @param obj: data obj. for func.
        @type task: L{pyfsm.task}
        """
        return self.func(task, obj)


