def get_in_ks(count):
    num_str = str(count)
    if count >= 1000:
        num_str = str(round(float(count) / 1000.0, 1)) + "K"
        num_str = num_str.replace(".0K", "K")
    return num_str
