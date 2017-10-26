from __future__ import print_function

__authors__ = ['Khyber Sen', 'Caleb Smith-Salzburg', 'Michael Ruvinshteyn', 'Terry Guan']
__date__ = '2017-10-20'

import pip
try:
    import passlib
    import python-dateutil
except:
    try:
        pip.main(["install", "passlib"])
        pip.main(["install", "python-dateutil"])
    except SystemExit as e:
        print "not all dependencies were necessarily installed... proceeding on"

import os

from flask import Flask
from flask import render_template
from flask import request
from flask import flash
from flask import session
from flask import Response

from werkzeug.datastructures import ImmutableMultiDict

from util.flask_utils import preconditions
from util.flask_utils import post_only
from util.flask_utils import reroute_to
from util.flask_utils import form_contains
from util.flask_utils import session_contains
from util.flask_utils import bind_args

import util.template_context

from storytelling_db import StoryTellingDatabase
from storytelling_db import User
from storytelling_db import Story
from storytelling_db import Edit
from storytelling_db import StoryTellingException

app = Flask(__name__)

db = StoryTellingDatabase()

"""Keys in session."""
USER_KEY = 'user'
STORY_KEY = 'story'
EDIT_KEY = 'edit'
IS_NEW_STORY_KEY = 'is_new_story'


def get_user():
    # type: () -> User
    """Get User in session."""
    return session[USER_KEY]


def get_story():
    # type: () -> Story
    """Get Story in session."""
    return session[STORY_KEY]


def pop_is_new_story():
    # type: () -> bool
    """Pop is new story from session."""
    return session.pop(IS_NEW_STORY_KEY)


def pop_story():
    # type: () -> Story
    """Pop Story from session."""
    return session.pop(STORY_KEY)


def pop_edit():
    # type: () -> Edit
    """Pop Edit from session."""
    return session.pop(EDIT_KEY)


is_logged_in = session_contains(USER_KEY)


@app.reroute_from('/')
@app.route('/welcome')
def welcome():
    # type: () -> Response
    return render_template('welcome.jinja2')


def get_user_info():
    # type: () -> (str, str)
    """Get username and password from request.form."""
    form = request.form  # type: ImmutableMultiDict
    return form['username'], form['password']


@app.route('/login')
def login():
    # type: () -> Response
    return render_template('login.jinja2')


"""Precondition decorator rerouting to login if is_logged_in isn't True."""
logged_in = preconditions(login, is_logged_in)


@app.route('/auth', methods=['get', 'post'])
@preconditions(login, post_only, form_contains('username', 'password'))
def auth():
    # type: () -> Response
    """
    Authorize and login a User with username and password from POST form.
    If username and password is wrong, flash message raised by db.
    """
    username, password = get_user_info()

    try:
        user = db.get_user(username, password)
    except StoryTellingException as e:
        flash(e.message)
        return reroute_to(login)

    session[USER_KEY] = user
    return reroute_to(home)


@app.route('/home')
@logged_in
def home():
    # type: () -> Response
    """Display a User's home page with all of his edited and unedited Stories."""
    user = get_user()
    return render_template('home.jinja2',
                           edited_stories=sorted(db.get_edited_stories(user)),
                           unedited_stories=sorted(db.get_unedited_stories(user)))



@app.route('/story', methods=['get', 'post'])
@logged_in
@preconditions(home, post_only, form_contains('story'))
def read_or_edit_story():
    # type: () -> Response
    """
    Open Story specified through form for either reading or editing,
    depending on if the User has edited the Story yet.

    If the story_id, storyname pair cannot be verified,
    reroute to home.
    """
    storyname = request.form(['story'])
    try:
        story = db.get_story(storyname)
    except StoryTellingException as e:
        flash(e.message)
        return reroute_to(home)

    session[STORY_KEY] = story
    edits = db.get_edits(story)
    editing = db.can_edit(story, get_user())
    if editing:
        return render_template('edit_story.jinja2', last_edit=max(edits, key=Edit.order))
    else:
        return render_template('read_story.jinja2', edits=sorted(edits, key=Edit.order))


@app.route('/edit', methods=['get', 'post'])
@logged_in
@preconditions(read_or_edit_story, post_only,
               session_contains(STORY_KEY), form_contains('text'))
def edit_story():
    # type: () -> Response
    """
    Edit the Story the User already selected with the text passed through the POST form.
    Reroute to edited_story to display post-edit page, passing Edit and not is_new_story.

    Check again if User can edit the Story.  If not, reroute to home.
    """

    story = get_story()
    user = get_user()

    if not db.can_edit(story, user):
        return reroute_to(home)

    text = request.form['text']
    edit = db.edit_story(story, user, text)
    return reroute_to(edited_story, pop_story(), edit, False)


@app.route('/create_new_story')
@logged_in
def create_new_story():
    # type: () -> Response
    return render_template('create_new_story.jinja2')


@app.route('/add_new_story', methods=['get', 'post'])
@logged_in
@preconditions(create_new_story, post_only, form_contains('storyname', 'text'))
def add_new_story():
    # type: () -> Response
    """
    Add the new Story created by the User
    with the storyname and initial text passed through the POST form.
    Reroute to edited_story display post-creation page
    with Story, Edit, and is_new_story passed through session.

    If storyname already exists, reroute to create_new_story with flash.
    """

    storyname = request.form['storyname']

    if db.story_exists(storyname):
        flash('The story "{}" already exists'.format(storyname))
        return reroute_to(create_new_story)

    text = request.form['text']
    story, edit = db.add_story(storyname, get_user(), text)

    return reroute_to(edited_story, story, edit, True)


@app.route('/edited_story', methods=['get', 'post'])
@logged_in
@preconditions(home, post_only)
@bind_args(home)
def edited_story(story, edit, is_new_story):
    # type: (Story, Edit, bool) -> Response
    """Display post-edit or post-creation page for given Story, Edit, and is_new_story."""
    return render_template('edited_story.jinja2',
                           story=story,
                           edit=edit,
                           is_new_story=is_new_story)

@app.route('/logout')
def logout():
    session.pop(USER_KEY)

if __name__ == '__main__':
    app.debug = True
    app.secret_key = os.urandom(32)
    util.template_context.add_to(app)
    app.run()
