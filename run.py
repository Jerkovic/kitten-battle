from flask.ext.script import Manager
from app import app, db
from app import User, Kitten

manager = Manager(app)


@manager.command
def reset_db():
    """ Resets database and creates some initial fixtures for us """
    db.drop_all()
    db.create_all()
    
    username = "jerkovic"
    email = "erilundin@gmail.com"
    u1 = User(username, email, 'test')
    db.session.add(u1)
    db.session.commit()
    
    for name in ['Fluffy', 'Zeebree', 'Starky', 'Yawney', 'Tyson', 'Pretty', 'Happey', 'Chaperon', 'Fraidy', 'Weee', 'Licky', 'Cuddley', 'Rocky', 'Prey', 'Strangy', 'Garfield']:
        k = Kitten(name, u1.id)
        db.session.add(k)
    
    db.session.commit()



@manager.command
def initdb():
    """Creates all database tables."""
    db.create_all()


@manager.command
def dropdb():
    """Drops all database tables."""
    db.drop_all()


if __name__ == '__main__':
    manager.run()