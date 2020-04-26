import os

import csv 
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Insert row by row
with open('books.csv', mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    line_count = 0
    for row in csv_reader:
        db.execute("INSERT INTO books (ISBN, title, author, year) VALUES (:ISBN, :title, :author, :year)",
                {"ISBN": row["isbn"], "title": row["title"], "author": row["author"], "year": row["year"]})
        line_count += 1
        db.commit()

    print(f'Processed {line_count} lines.')

