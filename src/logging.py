import os

FILE_LOG = "log.txt"
FILE_ERRORS = "errors.txt"

def log_write(text):
    with open(FILE_LOG, "a", encoding="utf-8") as file:
        file.write(text+'\n')

def log_error(text):
    with open(FILE_ERRORS, "a", encoding="utf-8") as file:
            file.write(text+'\n')

def log_remove():
    if os.path.exists(FILE_LOG):
        os.remove(FILE_LOG)
    if os.path.exists(FILE_ERRORS):
        os.remove(FILE_ERRORS)

def log_print():
    with open(FILE_LOG, "r", encoding="utf-8") as file:
        print(file.read())