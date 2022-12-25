# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, abort, jsonify
from flask_moment import Moment
import logging
import datetime as dt
import re
import sys
from logging import Formatter, FileHandler
from flask_migrate import Migrate
from forms import *
from models import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
app.app_context().push()
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_ECHO'] = False
db.app = app
db.init_app(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Reusable Functions.
# ----------------------------------------------------------------------------#


def re_search(entity):
    items_list = db.session.execute(db.select(entity.id, entity.name)).all()
    items_list = [item._asdict() for item in items_list]
    values = [item['name'] for item in items_list]
    search_input = request.form.get('search_term', '')
    pattern = r'.*{}.*'.format(search_input)
    search_results = list(filter(lambda x: re.findall(pattern, x, flags=re.IGNORECASE), values))
    data = [item for item in items_list if item['name'] in search_results]
    response = {
        "count": len(data),
        "data": data
    }
    return response, search_input


def get_entity(entity, entity_op, entity_op_str, entity_id):
    # select all entity attributes with lazy loading
    data = db.session.execute(db.select(entity.__table__.columns).where(entity.id == entity_id)).first()._asdict()
    # make separate queries for past and upcoming shows and add the results to the overall data
    query_up_shows = db.session.execute(db.select(entity_op.id.label('{}_id'.format(entity_op_str)),
                                                  entity_op.name.label('{}_name'.format(entity_op_str)),
                                                  entity_op.image_link.label('{}_image_link'.format(entity_op_str)),
                                                  db.func.cast(Show.datetime.label('start_time'), db.String)).join(
                                                  Show).where((Show.venue_id == entity_id) & (Show.datetime >=
                                                                                              dt.datetime.now()))).all()
    up_shows = [item._asdict() for item in query_up_shows]
    query_past_shows = db.session.execute(db.select(entity_op.id.label('{}_id'.format(entity_op_str)),
                                                    entity_op.name.label('{}_name'.format(entity_op_str)),
                                                    entity_op.image_link.label('{}_image_link'.format(entity_op_str)),
                                                    db.func.cast(Show.datetime.label('start_time'), db.String)).join(
                                                    Show).where((Show.venue_id == entity_id) & (Show.datetime <
                                                                                                dt.datetime.now()))).all()
    past_shows = [item._asdict() for item in query_past_shows]
    data["upcoming_shows"] = up_shows
    data["past_shows"] = past_shows
    data["upcoming_shows_count"] = len(up_shows)
    data["past_shows_count"] = len(past_shows)
    return data

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
    error = False
    data = []
    try:
        # select upcoming shows count for each venue in separate subquery
        sub = db.select(Show.venue_id, db.func.count().label('count')).where(
            Show.datetime > dt.datetime.now()).group_by(Show.venue_id).subquery()
        # make join with predefined subquery to select required info
        result = db.session.execute(db.select(Venue.city, Venue.state, db.func.json_agg(
            db.func.json_build_object('id', Venue.id, 'name', Venue.name, 'num_upcoming_shows', db.case(
              (sub.c.count.is_(None), 0), else_=sub.c.count))).label('venues')).join(
                    sub, Venue.id == sub.c.venue_id, isouter=True).group_by(Venue.city, Venue.state)).all()
        for item in result:
            data.append(item._asdict())
    except:
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    try:
        response, search_input = re_search(Venue)
        return render_template('pages/search_venues.html', results=response,
                               search_term=search_input)
    except:
        print(sys.exc_info())
        abort(400)
    finally:
        db.session.close()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    error = False
    data = None
    try:
        data = get_entity(Venue, Artist, 'artist', venue_id)
    except:
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    data = {}
    try:
        count = Venue.query.count()
        venue = Venue(id=count+1,
                      name=request.form.get('name'),
                      genres=request.form.getlist('genres'),
                      address=request.form.get('address'),
                      city=request.form.get('city'),
                      state=request.form.get('state'),
                      phone=request.form.get('phone'),
                      website=request.form.get('website_link'),
                      facebook_link=request.form.get('facebook_link'),
                      seeking_talent=True if request.form.get('seeking_talent') == 'y' else False,
                      seeking_desc=request.form.get('seeking_desc'),
                      image_link=request.form.get('image_link'))
        data = venue.as_dict()
        db.session.add(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + data.get('name', '') + ' could not be listed.')
        return render_template('pages/home.html')
    else:
        # on successful db insert, flash success
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({'success': True})


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    error = False
    data = []
    try:
        # select artist id and artist name for all artists with lazy loading
        result = db.session.execute(db.select(Artist.id, Artist.name)).all()
        for item in result:
            data.append(item._asdict())
    except:
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    try:
        response, search_input = re_search(Artist)
        return render_template('pages/search_artists.html', results=response,
                               search_term=search_input)
    except:
        print(sys.exc_info())
        abort(400)
    finally:
        db.session.close()


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    error = False
    data = None
    try:
        data = get_entity(Artist, Venue, 'venue', artist_id)
    except:
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    # called upon editing existing artist
    try:
        artist = Artist.query.get(artist_id)
        form = ArtistForm(obj=artist)
        form.populate_obj(artist)
        artist = artist.as_dict()
        return render_template('forms/edit_artist.html', form=form, artist=artist)
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # artist record with ID <artist_id> using the new attributes
    error = False
    data = {}
    try:
        data = request.form.to_dict(flat=False)
        data = {key: value if key == 'genres' else value[0] for key, value in data.items()}
        data['website'] = data.pop('website_link')
        if data.get('seeking_venue', None):
            data['seeking_venue'] = True if data['seeking_venue'] == 'y' else False
        Artist.query.filter_by(id=artist_id).update(data)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + data.get('name', '') + ' info could not be edited.')
        return redirect(url_for('show_artist', artist_id=artist_id))
    else:
        # on successful db insert, flash success
        flash('Artist ' + data.get('name', '') + ' info was successfully edited!')
        return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        form = VenueForm(obj=venue)
        form.populate_obj(venue)
        venue = venue.as_dict()
        return render_template('forms/edit_venue.html', form=form, venue=venue)
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # venue record with ID <venue_id> using the new attributes
    error = False
    data = {}
    try:
        data = request.form.to_dict(flat=False)
        data = {key: value if key == 'genres' else value[0] for key, value in data.items()}
        print(data)
        data['website'] = data.pop('website_link')
        if data.get('seeking_talent', None):
            data['seeking_talent'] = True if data['seeking_talent'] == 'y' else False
        Venue.query.filter_by(id=venue_id).update(data)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + data.get('name', '') + ' info could not be edited.')
        return redirect(url_for('show_venue', venue_id=venue_id))
    else:
        # on successful db insert, flash success
        flash('Venue ' + data.get('name', '') + ' info was successfully edited!')
        return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    error = False
    data = None
    try:
        count = Artist.query.count()
        artist = Artist(id=count + 1,
                        name=request.form.get('name'),
                        genres=request.form.getlist('genres'),
                        city=request.form.get('city'),
                        state=request.form.get('state'),
                        phone=request.form.get('phone'),
                        website=request.form.get('website_link'),
                        facebook_link=request.form.get('facebook_link'),
                        seeking_venue=True if request.form.get('seeking_venue') == 'y' else False,
                        seeking_desc=request.form.get('seeking_desc'),
                        image_link=request.form.get('image_link'))
        data = artist.as_dict()
        db.session.add(artist)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + data['name'] + ' could not be listed.')
        return render_template('pages/home.html')
    else:
        # on successful db insert, flash success
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    error = False
    data = []
    try:
        # compose join statement to retrieve required information
        result = db.session.execute(db.select(db.func.cast(
            Show.datetime.label('start_time'), db.String), Show.venue_id, Venue.name.label('venue_name'),
            Show.artist_id, Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link')).join(
            Artist).join(Venue)).all()

        for item in result:
            data.append(item._asdict())
    except:
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    error = False
    try:
        show = Show(datetime=request.form.get('start_time'),
                    venue_id=request.form.get('venue_id'),
                    artist_id=request.form.get('artist_id')
                    )
        db.session.add(show)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
        return render_template('pages/home.html')
    else:
        # on successful db insert, flash success
        flash('Show was successfully listed!')
        return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
