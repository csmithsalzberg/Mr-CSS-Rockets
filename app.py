from __future__ import print_function

from werkzeug.datastructures import ImmutableMultiDict

__authors__ = ['Khyber Sen', 'Caleb Smith-Salzburg', 'Michael Ruvinshteyn', 'Terry Guan']
__date__ = '2017-10-20'

import os

from flask import Flask, render_template, request, flash, session
from flask import Response

from util.flask_utils import preconditions, post_only, reroute_to

from storytelling_db import StoryTellingDatabase

USER_KEY = 'username'

app = Flask(__name__)

db = StoryTellingDatabase()


def is_logged_in():
    # type: () -> bool
    return USER_KEY in session


@app.reroute_from('/')
@app.route('/welcome')
def welcome():
    # type: () -> Response
    pass


def valid_account_form():
    # type: () -> bool
    return 'username' in request.form and 'password' in request.form


def get_account():
    # type: () -> (str, str)
    form = request.form  # type: ImmutableMultiDict
    return form['username'], form['password']


@app.route('/login')
def login():
    # type: () -> Response
    pass


logged_in = preconditions(login, is_logged_in)


@app.route('/auth', methods=['get', 'post'])
@preconditions(login, post_only, valid_account_form)
def auth():
    # type: () -> Response
    username, password = get_account()
    user = db.get_user(username, password)
    if user is None:
        flash('wrong username or password')
        return reroute_to(login)
    session[USER_KEY] = user
    return reroute_to(home)


@app.route('/home')
@logged_in
def home():
    # type: () -> Response
    user = session[USER_KEY]
    edited_stories = db.get_edited_stories(user)
    unedited_stories = db.get_unedited_stories(user)
    return render_template('TODO',
                           edited_stories=edited_stories,
                           unedited_stories=unedited_stories)


if __name__ == '__main__':
    app.debug = True
    app.secret_key = os.urandom(32)
    app.run()
