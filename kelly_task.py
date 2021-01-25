from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import behavbox

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
	pass


class KellyTask(object):

	# some parameters
	timeout_length = 5  # in seconds
	reward_size    = 10 # in uL

	########################################################################
	# possible states in state machine
	########################################################################
	states = [
		State(name='standby', on_enter=['enter_standby'], on_exit=['exit_standby']),
		State(name='reward_available', on_enter=['enter_reward_available'], 
			on_exit=['exit_reward_available']),
		{'name': 'cue', 'timeout': timeout_length, 'on_timeout': 'timeup', 'on_enter': 'enter_cue', 'on_exit': 'exit_cue'}
	]

	########################################################################
	# list of possible transitions between states
	# format is: [event_name, source_state, destination_state]
	########################################################################
	transitions = [
		['trial_start', 'standby', 'reward_available'],
		['nosepoke', 'reward_available', 'cue'],
		['timeup', 'cue', 'standby']
	]

	########################################################################
	# functions called on state transitions 
	########################################################################
	def enter_standby(self): 
		print("entering standby")
		self.trial_running = False

	def exit_standby(self):
		pass

	def enter_reward_available(self):
		print("entering reward_available")
		print("start white noise")
		self.trial_running = True

	def exit_reward_available(self):
		print("stop white noise")

	def enter_cue(self):
		print("deliver reward")
		self.box.reward('right', self.reward_size)
		print("start cue")

	def exit_cue(self):
		print("stop cue")


	########################################################################
	# initializing object
	########################################################################
	def __init__(self, name):
		self.name = name
		self.machine = TimedStateMachine(model=self, states=KellyTask.states, transitions=KellyTask.transitions, 
			initial='standby')
		self.trial_running = False

		# initialize behavior box
		self.box = behavbox.BehavBox()


	########################################################################
	# call this method repeatedly in a while loop in the session script
	########################################################################
	def run(self):

		# read in name of an event the box has detected
		event_name = self.box.event_list.popleft()

		if self.state=='standby':
			pass

		elif self.state=='reward_available':
			if event_name=='right_poke_entry':
				self.nosepoke()

		elif self.state=='cue':
			pass





