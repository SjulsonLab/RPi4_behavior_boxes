from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
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
	# Three possible states: standby, reward_available, and cue
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
	# functions called when state transitions occur 
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
		self.box.reward('left', self.reward_size)
		print("start cue")

	def exit_cue(self):
		print("stop cue")

	########################################################################
	# initialize state machine and behavior box
	########################################################################
	def __init__(self, name):
		self.name = name
		self.machine = TimedStateMachine(model=self, states=KellyTask.states, transitions=KellyTask.transitions, 
			initial='standby')
		self.trial_running = False

		# initialize behavior box
		self.box = behavbox.BehavBox()

	########################################################################
	# call the run() method repeatedly in a while loop in the main session
	# script it will process all detected events from the behavior box (e.g. 
	# nosepokes and licks) and trigger the appropriate state transitions
	########################################################################
	def run(self):

		# read in name of an event the box has detected
		if self.box.event_list:
			event_name = self.box.event_list.popleft()
		else:
			event_name = ''

		if self.state=='standby':
			pass

		elif self.state=='reward_available':
			if event_name=='left_poke_entry':
				self.nosepoke()  # nosepoke here means the transition 

		elif self.state=='cue':
			pass

		# look for keystrokes
		self.box.check_keybd()



	########################################################################
	# methods to start and end the behavioral session
	########################################################################
	def start_session(self):
		ic('TODO: open logfile')
		ic('TODO: start video')

	def end_session(self):
		ic("TODO: close logfile")
		ic('TODO: stop video')


