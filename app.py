from __future__ import print_function

__authors__ = ['Khyber Sen', 'Caleb Smith-Salzburg', 'Michael Ruvinshteyn', 'Terry Guan']
__date__ = '2017-10-20'

import os

from flask import Flask, render_template, request, flash, session
from flask import Response
from werkzeug.datastructures import ImmutableMultiDict

from util.flask_utils import preconditions, post_only, reroute_to, form_contains, session_contains

from storytelling_db import StoryTellingDatabase, User, Story

USER_KEY = 'user'
STORY_KEY = 'story'
EDIT_KEY = 'edit'

app = Flask(__name__)

db = StoryTellingDatabase()

is_logged_in = session_contains(USER_KEY)


@app.reroute_from('/')
@app.route('/welcome')
def welcome():
    # type: () -> Response
    return render_template('welcome.jinja2')


def get_user_info():
    # type: () -> (str, str)
    form = request.form  # type: ImmutableMultiDict
    return form['username'], form['password']


@app.route('/login')
def login():
    # type: () -> Response
    return render_template('login.jinja2')


logged_in = preconditions(login, is_logged_in)


@app.route('/auth', methods=['get', 'post'])
@preconditions(login, post_only, form_contains('username', 'password'))
def auth():
    # type: () -> Response
    username, password = get_user_info()
    user = db.get_user(username, password)
    if user is None:
        flash('wrong username or password')
        return reroute_to(login)
    session[USER_KEY] = user
    return reroute_to(home)


def get_user():
    # type: () -> User
    return session[USER_KEY]


@app.route('/home')
@logged_in
def home():
    # type: () -> Response
    user = get_user()
    return render_template('home.jinja2',
                           edited_stories=db.get_edited_stories(user),
                           unedited_stories=db.get_unedited_stories(user))


@app.route('/story', methods=['get', 'post'])
@logged_in
@preconditions(home, post_only, form_contains('story_id', 'storyname'))
def read_or_edit_story():
    # type: () -> Response
    story_id = int(request.form['story_id'])
    storyname = request.form['storyname']
    story = Story(story_id, storyname)

    # request could be tampered with, must verify story exists first
    if not db.verify_story(story):
        return reroute_to(home)

    edits = db.get_edits(story)
    return render_template('story.jinja2',
                           edits=edits,
                           editing=db.can_edit(story, get_user()))


@app.route('/create_new_story')
@logged_in
def create_new_story():
    # type: () -> Response
    return render_template('create_new_story.jinja2')


@app.route('/add_new_story', methods=['get', 'post'])
@logged_in
@preconditions(create_new_story, post_only, form_contains('storyname', 'text'))
def add_new_story():
    storyname = request.form['storyname']

    if db.story_exists(storyname):
        flash('The story "{}" already exists'.format(storyname))
        return reroute_to(create_new_story)

    text = request.form['text']
    story, edit = db.add_story(storyname, get_user(), text)

    session[STORY_KEY] = story
    session[EDIT_KEY] = edit
    return reroute_to(created_new_story)


@app.route('/created_new_story', methods=['get', 'post'])
@logged_in
@preconditions(home, post_only, session_contains(STORY_KEY, EDIT_KEY))
def created_new_story():
    return render_template('created_new_story.jinja2',
                           story=session[STORY_KEY],
                           edit=session[EDIT_KEY])


if __name__ == '__main__':
    app.debug = True
    app.secret_key = os.urandom(32)
    app.run()
