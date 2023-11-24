def get_task(task):
    if task == "basic":
        from marmtouch.experiments.basic import Basic as Task
    elif task == "memory":
        from marmtouch.experiments.memory import Memory as Task
    elif task == "dms":
        from marmtouch.experiments.dms import DMS as Task
    else:
        raise ValueError("Unknown task: {}".format(task))
    return Task