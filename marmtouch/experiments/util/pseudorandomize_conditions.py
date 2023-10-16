import random
from itertools import groupby


def no_reps_over_max(condition_list, max_reps):
    return max(len(list(seq)) for _, seq in groupby(condition_list)) <= max_reps

def pseudorandomize_conditions(conditions, weights, length, max_reps):
    condition_list = random.choices(conditions, weights=weights, k=length)
    if not max_reps is None:
        while not no_reps_over_max(condition_list, max_reps):
            condition_list = random.choices(conditions, weights=weights, k=length)
    return condition_list

def pseudorandomize_conditions_fixed_number(conditions, weights, length):
    """Pseudorandomize the conditions such that each condition is 
    guaranteed to show up a fixed number of times as specified by weights

    Parameters
    ----------
    conditions: list of Any
        list of condition names as specified in config
    weights: list of int
        list of weights specifying how many repetitions of a condition
        should be presented
    length: int
        number of trials in a block
    """
    weighted_conditions = []
    for condition, weight in zip(conditions, weights):
    weighted_conditions.extend([condition]*weight)
    n_chunks = ceil(length / len(weighted_conditions))
    condition_list = n_chunks * weighted_conditions
    random.shuffle(condition_list)
    return condition_list[:length]