from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Show(db.Model):
    __tablename__ = 'show'

    datetime = db.Column('datetime', db.DateTime, primary_key=True)
    venue_id = db.Column('venue_id', db.Integer, db.ForeignKey('venue.id', ondelete="cascade"), primary_key=True)
    artist_id = db.Column('artist_id', db.Integer, db.ForeignKey('artist.id', ondelete="cascade"), primary_key=True)


class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    genres = db.Column(db.ARRAY(db.String(120)))
    address = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_desc = db.Column(db.String(500))
    image_link = db.Column(db.String(500))
    show = db.relationship('Show', cascade="all, delete", passive_deletes=True, backref=db.backref('venue', lazy=True))

    # transfor SQLalchemy model instance into JSON format
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    genres = db.Column(db.ARRAY(db.String(120)))
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_desc = db.Column(db.String(500))
    image_link = db.Column(db.String(500))
    show = db.relationship('Show', cascade="all, delete", passive_deletes=True, backref=db.backref('artist', lazy=True))

    # transfor SQLalchemy model instance into JSON format
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
