Lines 32-34 in models.py - "I constrained direction at the schema level with an enum instead of validating in application code, so bad values can't exist in the database." 

"I used create_all for the prototype and documented Alembic as the migration path in the README."

That id 1 is "missing" because of my earlier shell experiment — the Test business got sequence value 1 when I flushed it, Postgres sequences don't roll back. So gaps in an auto-increment id are normal and expected — not a bug
