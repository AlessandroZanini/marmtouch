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