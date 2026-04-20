import pickle

def save_data(filename, data):
    with open(filename, "wb") as f:
        pickle.dump(data, f)

def load_data(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)