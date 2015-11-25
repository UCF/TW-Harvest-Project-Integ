import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from jobs.models import dbsetup


def main():
    dbsetup()

if __name__ == '__main__':
    main()
