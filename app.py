from __future__ import print_function

from sys import stderr

__authors__ = ['Khyber Sen', 'Caleb Smith-Salzburg', 'Michael Ruvinshteyn', 'Terry Guan']
__date__ = '2017-10-30'

from typing import Callable
import os

from flask import \
    Flask, \
    render_template, \
    request, \
    flash, \
    session, \
    Response

from werkzeug.datastructures import ImmutableMultiDict

from util.flask_utils_types import \
    Router, \
    Precondition

from util.flask_utils import \
    preconditions, \
    post_only, \
    reroute_to, \
    form_contains, \
    session_contains, \
    bind_args

from util.template_context import add_template_context
from util.flask_json import use_named_tuple_json

from storytelling_db import \
    StoryTellingDatabase, \
    User, \
    Story, \
    Edit, \
    StoryTellingException

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


is_logged_in = session_contains(USER_KEY)  # type: Precondition
is_logged_in.func_name = 'is_logged_in'


@app.reroute_from('/')
@app.route('/welcome')
def welcome():
    # type: () -> Response
    return render_template('welcome.jinja2', is_loggin_in=is_logged_in())


def get_user_info():
    # type: () -> (str, str)
    """Get username and password from request.form."""
    form = request.form  # type: ImmutableMultiDict
    return form['username'], form['password']


@app.route('/login')
def login():
    # type: () -> Response
    if is_logged_in():
        return reroute_to(home)
    return render_template('login.jinja2')


@preconditions(login, post_only, form_contains('username', 'password'))
def auth_or_signup(db_user_supplier):
    # type: (Callable[[unicode, unicode], User]) -> Response
    if is_logged_in():
        reroute_to(home)
    username, password = get_user_info()
    with db:
        try:
            user = db_user_supplier(username, password)
        except StoryTellingException as e:
            flash(e.message)
            print(e, file=stderr)
            return reroute_to(login)

    session[USER_KEY] = user
    return reroute_to(home)


@app.route('/signup', methods=['get', 'post'])
def signup():
    # type: () -> Response
    return auth_or_signup(db.add_user)


"""Precondition decorator rerouting to login if is_logged_in isn't True."""
logged_in = preconditions(login, is_logged_in)  # type: Router


@app.route('/auth', methods=['get', 'post'])
def auth():
    # type: () -> Response
    """
    Authorize and login a User with username and password from POST form.
    If username and password is wrong, flash message raised by db.
    """
    return auth_or_signup(db.get_user)


@app.route('/home')
@logged_in
def home():
    # type: () -> Response
    """Display a User's home page with all of his edited and unedited Stories."""
    user = get_user()
    with db:
        return render_template('home.jinja2',
                               user=user,
                               edited_stories=sorted(db.get_edited_stories(user)),
                               unedited_stories=sorted(db.get_unedited_stories(user)),
                               )


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
    storyname = request.form['story']

    with db:
        try:
            story = db.get_story(storyname)
        except StoryTellingException as e:
            flash(e.message)
            print(e, file=stderr)
            return reroute_to(home)

        session[STORY_KEY] = story
        editing = db.can_edit(story, get_user())
        if editing:
            return render_template('edit_story.jinja2',
                                   last_edit=db.get_last_edit(story))
        else:
            return render_template('read_story.jinja2',
                                   edits=sorted(db.get_edits(story), key=Edit.order))


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

    with db:
        if not db.can_edit(story, user):
            return reroute_to(home)

    text = request.form['text']
    with db:
        edit = db.edit_story(story, user, text)
    return reroute_to(edited_story, pop_story(), edit, False)


@app.route('/create_new_story')
@logged_in
def create_new_story():
    # type: () -> Response
    return render_template('create_new_story.jinja2')


@app.route('/new_story', methods=['get', 'post'])
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

    with db:
        if db.story_exists(storyname):
            flash('The story "{}" already exists'.format(storyname))
            return reroute_to(create_new_story)

    text = request.form['text']
    with db:
        story, edit = db.add_story(storyname, get_user(), text)

    return reroute_to(edited_story, story, edit, True)


@app.route('/edited_story', methods=['get', 'post'])
@logged_in
@preconditions(home, lambda: False)
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
    # type: () -> Response
    del session[USER_KEY]
    return reroute_to(welcome)


if __name__ == '__main__':
    app.debug = True
    app.secret_key = os.urandom(32)
    add_template_context(app)
    use_named_tuple_json(app)
    app.run()
