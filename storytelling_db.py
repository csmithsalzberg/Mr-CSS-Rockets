from __future__ import print_function

from collections import namedtuple
from datetime import datetime

import dateutil.parser
from passlib.hash import pbkdf2_sha256
from typing import Generator, Tuple

from util.db import Database

DB_SCHEMA = dict(
    users='CREATE TABLE IF NOT EXISTS '
          'users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, start_time TEXT)',

    stories='CREATE TABLE IF NOT EXISTS '
            'stories(id INTEGER PRIMARY KEY, storyname TEXT, start_time TEXT)',

    edits='CREATE TABLE IF NOT EXISTS '
          'edits(story_id INTEGER, user_id INTEGER, text TEXT, time TEXT,'
          'FOREIGN KEY(story_id) REFERENCES stories(id),'
          'FOREIGN KEY(user_id) REFERENCES users(id))',
)


def hash_password(plain_password):
    # type: (str | unicode) -> str | unicode
    """Securely hash password."""
    return pbkdf2_sha256.hash(plain_password)


def verify_password(plain_password, hashed_password):
    # type: (str | unicode) -> bool
    """Verify if plain password matches the hashed password."""
    return pbkdf2_sha256.verify(plain_password, hashed_password)


User = namedtuple('User', ['id', 'username'])  # type: (int, unicode)
User.__repr__ = lambda self: 'User(%s, %s)' % self

Story = namedtuple('Story', ['id', 'storyname'])  # type: (int, unicode)
Story.__repr__ = lambda self: 'Story(%s, %s)' % self

Edit = namedtuple('Edit',
                  ['story', 'user', 'text', 'time'])  # type: (Story, User, unicode, datetime)
Edit.__repr__ = lambda self: 'Edit(%r, %r, %s, %s)' % self


class StoryTellingException(Exception):
    """An Exception thrown by StoryTellingDatabase."""
    pass


class StoryTellingDatabase(object):
    """DB-API Wrapper for the DB for this Storytelling Game.

    :ivar name: name of database
    :type name: str

    :ivar db: low level database object
    :type db: Database
    """

    def __init__(self, name='data/storytelling.db'):
        # type: (str | unicode) -> None
        """Create DB with given name and open low level connection through `Database`"""
        self.name = name
        self.db = Database(name)
        self._create_tables()

    def commit(self):
        # type: () -> None
        """Commit DB."""
        self.db.commit()

    def hard_close(self):
        # type: () -> None
        """Close DB without committing."""
        self.db.hard_close()

    def close(self):
        # type: () -> None
        """Close and commit DB."""
        self.db.close()

    def __enter__(self):
        # type: () -> StoryTellingDatabase
        """Do nothing when entering with statement."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: () -> None
        """Close DB after with statement."""
        self.close()

    def _create_tables(self):
        # type: () -> None
        """Create all tables according to `DB_SCHEMA`."""
        map(self.db.cursor.execute, DB_SCHEMA.viewvalues())
        self.commit()

    def clear(self):
        # type: () -> None
        """Drop and recreate tables."""
        self.db.cursor.executescript(
            ''.join('DROP TABLE {};'.format(table) for table in DB_SCHEMA))
        self._create_tables()
        self.commit()

    def get_user(self, username, password):
        # type: (unicode, unicode) -> User | None
        """
        Get User with given username and password.

        If username doesn't exist or password doesn't match,
        raise `StoryTellingException` with a message.
        """
        self.db.cursor.execute('SELECT id, password FROM users WHERE username = ?', [username])
        result = self.db.cursor.fetchone()
        if result is None:
            raise StoryTellingException('wrong username')
        user_id, hashed_password = result
        if not verify_password(password, hashed_password):
            raise StoryTellingException('wrong password')
        return User(user_id, username)

    def verify_user(self, username, password):
        # type: (unicode, unicode) -> bool
        """Verify given username and password is a valid User."""
        return self.get_user(username, password) is not None

    def user_exists(self, username):
        # type: (unicode) -> bool
        """Check if User with given username exists."""
        self.db.cursor.execute('SELECT id FROM users WHERE username = ?', [username])
        return self.db.result_exists()

    def story_exists(self, storyname):
        # type: (unicode) -> bool
        """Check if Story with given storyname exists."""
        self.db.cursor.execute('SELECT id FROM stories WHERE storyname = ?', [storyname])
        return self.db.result_exists()

    def verify_story(self, story):
        # type: (Story) -> bool
        """Verify given Story exists with matching id and storyname."""
        self.db.cursor.execute('SELECT id FROM stories WHERE id = ? AND storyname = ?',
                               [story.id, story.storyname])
        return self.db.result_exists()

    def _get_stories(self, user, edited):
        # type: (User, bool) -> Generator[Story, None, None]
        cmp = '=' if edited else '!='
        for story_id, storyname in self.db.cursor.execute(
                'SELECT stories.id, storyname FROM edits, stories, users WHERE users.id {} ?'
                        .format(cmp),
                [user.id]):
            yield Story(story_id, storyname)

    def get_edited_stories(self, user):
        # type: (User) -> Generator[Story, None, None]
        """Yield all Stories edited by given User."""
        return self._get_stories(user, True)

    def get_unedited_stories(self, user):
        # type: (User) -> Generator[Story, None, None]
        """Yield all Stories not edited yet by given User."""
        return self._get_stories(user, False)

    def get_edits(self, story):
        # type: (Story) -> Generator[Edit, None, None]
        """Yield all Edits of a given Story."""
        for user_id, username, text, time in self.db.cursor.execute(
                'SELECT users.id, username, text, time '
                'FROM edits, users, stories '
                'WHERE stories.id = ?'
                'AND users.id = stories.id',
                [story.id]):
            time = dateutil.parser.parse(time)
            yield Edit(Story(story.id, story.storyname), User(user_id, username), text, time)

    def get_editors(self, story):
        # type: (Story) -> Generator[User, None, None]
        """Yield all Users who have edited a given Story."""
        for edit in self.get_edits(story):
            yield edit.user

    def _get_start_time(self, table, user_or_story):
        # type: (User | Story) -> datetime
        # should use some sort of table inheritance if such a thing exists
        self.db.cursor.execute('SELECT start_time FROM {} WHERE id = ?'.format(table),
                               [user_or_story.id])
        time = self.db.cursor.fetchone()[0]
        return dateutil.parser.parse(time)

    def get_user_start_time(self, user):
        # type: (User) -> datetime
        """Get start time of given User."""
        return self._get_start_time('users', user)

    def get_story_start_time(self, story):
        # type: (Story) -> datetime
        """Get start time of given Story."""
        return self._get_start_time('stories', story)

    def can_edit(self, story, user):
        # type: (Story, User) -> bool
        """Check if given User can edit given Story,
        i.e. the User hasn't edited the given Story yet."""
        for other_user in self.get_editors(story):
            print('other_user:', other_user)
            if user.id == other_user.id:
                return False
        return True

    def _add_user_hard(self, username, password):
        # type: (unicode, unicode) -> User
        hashed_password = hash_password(password)
        self.db.cursor.execute('INSERT INTO users VALUES (NULL, ?, ?, ?)',
                               [username, hashed_password, datetime.now().isoformat()])
        user_id = self.db.cursor.lastrowid
        self.commit()
        return User(user_id, username)

    def add_user(self, username, password):
        # type: (unicode, unicode) -> User
        """
        Add and return User with given username and password.

        If User with given username already exists,
        raise a StoryTellingException.
        """
        if self.user_exists(username):
            raise StoryTellingException('username already exists')
        return self._add_user_hard(username, password)

    def _create_story_hard(self, storyname):
        # type: (unicode) -> Story
        self.db.cursor.execute('INSERT INTO stories VALUES (NULL, ?, ?)',
                               [storyname, datetime.now().isoformat()])
        story_id = self.db.cursor.lastrowid
        self.commit()
        return Story(story_id, storyname)

    def _add_story_hard(self, storyname, user, text):
        # type: (unicode, User, unicode) -> Tuple[Story, Edit]
        story = self._create_story_hard(storyname)
        edit = self._edit_story_hard(story, user, text)
        return story, edit

    def add_story(self, storyname, user, text):
        # type: (unicode, User, unicode) -> Tuple[Story, Edit]
        """
        Add a new story with given storyname and created by given User with given text.
        Return a tuple of the Story created and the first Edit.

        If a Story with the given storyname already exists,
        raise a StoryTellingException.

        :param storyname: storyname of Story to be created
        :param user: User creating the new Story
        :param text: the text starting the Story
        :return: the Story created and the first Edit
        """
        if self.story_exists(storyname):
            raise StoryTellingException('story already exists')
        return self._add_story_hard(storyname, user, text)

    def _edit_story_hard(self, story, user, text):
        # type: (Story, User, unicode) -> Edit
        time = datetime.now()
        self.db.cursor.execute('INSERT INTO edits VALUES (?, ?, ?, ?)',
                               [story.id, user.id, text, time.isoformat()])
        self.commit()
        return Edit(story, user, text, time)

    def edit_story(self, story, user, text):
        # type: (Story, User, unicode) -> Edit
        """
        Edit a given Story by given User and with given text,
        returning the Edit made.

        If the User cannot edit the Story (see #can_edit(Story, User)),
        raise a StoryTellingException.
        """
        if not self.can_edit(story, user):
            raise StoryTellingException('already edited this story')
        return self._edit_story_hard(story, user, text)


def main():
    with StoryTellingDatabase() as db:
        db.clear()

        db.add_user(u'Khyber', u'Sen')
        user = db.get_user(u'Khyber', u'Sen')
        print(user)
        print(db.user_exists(u'Khyber'))

        story, edit = db.add_story(u'Story1', user, u'First line.')
        print(story)

        map(print, db.get_edited_stories(user))

        map(print, db.get_edits(story))

        map(print, db.get_editors(story))

        # try:
        #     db.edit_story(story, user, 'Second line.')
        # except StoryTellingException as e:
        #     print(e.message)

        user2 = db.add_user(u'User', u'Password')
        story2, edit2 = db.add_story(u'Story2', user2, u'First line.')
        print('story2 editors:')
        map(print, db.get_edits(story2))

        print('error:')

        edit3 = db.edit_story(story2, user, u'Second line.')

        print(user2)
        print(story2)
        print(edit2)
        print(edit3)


if __name__ == '__main__':
    main()
