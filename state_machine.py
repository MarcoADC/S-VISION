

class StateMachine():
    def __init__(self, transitions, state='Idle'):
        self.state = state
        self.transitions = transitions

    def transition(self, event):
        if event in self.transitions[self.state]:
            self.state = self.transitions[self.state][event]
        else:
            print(f'comando {event} invalido para {self.state}')

        return self.state

    def __str__(self):
        return f'Current state: {self.state}'