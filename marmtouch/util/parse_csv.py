def parse_csv(path):
    lines = open(path, 'r').read().splitlines()
    headers = lines.pop(0).split(',')
    data = [dict(zip(headers, line.split(','))) for line in lines]
    return data