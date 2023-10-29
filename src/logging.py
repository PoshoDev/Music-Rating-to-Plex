import os

FILE_LOG = "log.txt"

def log_write(text):
    with open(FILE_LOG, "a", encoding="utf-8") as file:
        file.write(text+'\n')

def log_remove():
    os.remove(FILE_LOG)

def log_print():
    with open(FILE_LOG, "r", encoding="utf-8") as file:
        print(file.read())