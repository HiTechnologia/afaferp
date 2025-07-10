__all__ = [
    'on_submit', 'on_enter_approval', 'on_approve', 'on_approval', 'on_reject', 'on_return', 'on_cancel', 'on_draft', 'on_forward', 'on_transfer', 'on_state_updated', 'on_create', 'on_committee_approval'
]

def attrsetter(trigger: str, old_states: str | tuple | None = None, new_states: str | tuple | None = None):
    if isinstance(old_states, str):
        old_states = tuple(old_states.split(","))
    if isinstance(new_states, str):
        new_states = tuple(new_states.split(","))
                
    return lambda method: setattr(method, trigger, (old_states, new_states)) or method

def on_submit(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_submit', old_states, new_states)

def on_enter_approval(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_enter_approval', old_states, new_states)

def on_approve(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_approve', old_states, new_states)

def on_approval(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_approval', old_states, new_states)

def on_reject(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_reject', old_states, new_states)

def on_return(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_return', old_states, new_states)

def on_cancel(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_cancel', old_states, new_states)

def on_draft(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_draft', old_states, new_states)

def on_forward(states: str | None = None):
    return attrsetter('_approval_on_forward', states, None)

def on_transfer(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_transfer', old_states, new_states)

def on_state_updated(old_states: str | None = None, new_states: str | None = None):
    return attrsetter('_approval_on_state_updated', old_states, new_states)

def on_create(states: str | None = None):
    return attrsetter('_approval_on_create', None, states)

def on_committee_approval(states: str | None = None):
    return attrsetter('_approval_on_committee_approval', states, states)