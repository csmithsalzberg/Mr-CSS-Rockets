from __future__ import print_function

from collections import namedtuple
from datetime import datetime

import dateutil.parser
from passlib.hash import pbkdf2_sha256
from typing import Generator, Tuple

from util.db import Database


def hash_password(plain_password):
    # type: (str | unicode) -> str | unicode
    return pbkdf2_sha256.hash(plain_password)


def verify_password(plain_password, hashed_password):
    # type: (str | unicode) -> bool
    return pbkdf2_sha256.verify(plain_password, hashed_password)


User = namedtuple('User', ['id', 'username'])  # type: (int, unicode)

Story = namedtuple('Story', ['id', 'storyname'])  # type: (int, unicode)

Edit = namedtuple('Edit',
                  ['story', 'user', 'text', 'time'])  # type: (Story, User, unicode, datetime)


class StoryTellingException(Exception):
    pass


class StoryTellingDatabase(object):
    def __init__(self, name='data/storytelling.db'):
        # type: (str | unicode) -> None
        self.name = name
        self.db = Database(name)
        self._create_tables()

    def commit(self):
        # type: () -> None
        self.db.commit()

    def hard_close(self):
        # type: () -> None
        self.db.hard_close()

    def close(self):
        # type: () -> None
        self.db.close()

    def __enter__(self):
        # type: () -> StoryTellingDatabase
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: () -> None
        self.close()

    def _create_users_table(self):
        self.db.cursor.execute(
            'CREATE TABLE IF NOT EXISTS '
            'users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, start_time TEXT)')

    def _create_stories_table(self):
        self.db.cursor.execute(
            'CREATE TABLE IF NOT EXISTS '
            'stories(id INTEGER PRIMARY KEY, storyname TEXT, start_time TEXT)')

    def _create_edits_table(self):
        self.db.cursor.execute(
            'CREATE TABLE IF NOT EXISTS '
            'edits(story_id INTEGER, user_id INTEGER, text TEXT, time TEXT,'
            'FOREIGN KEY (story_id) REFERENCES stories(id),'
            'FOREIGN KEY (user_id) REFERENCES users(id))')

    def _create_tables(self):
        self._create_users_table()
        self._create_stories_table()
        self._create_edits_table()
        self.commit()

    def clear(self):
        self.db.cursor.executescript(
            'DROP TABLE users; '
            'DROP TABLE stories; '
            'DROP TABLE edits;'
        )
        self._create_tables()
        self.commit()

    def get_user(self, username, password):
        # type: (unicode, unicode) -> User | None
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
        return self.get_user(username, password) is not None

    def user_exists(self, username):
        # type: (unicode) -> bool
        self.db.cursor.execute('SELECT id FROM users WHERE username = ?', [username])
        return self.db.result_exists()

    def story_exists(self, storyname):
        # type: (unicode) -> bool
        self.db.cursor.execute('SELECT id FROM stories WHERE storyname = ?', [storyname])
        return self.db.result_exists()

    def verify_story(self, story):
        # type: (Story) -> bool
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
        return self._get_stories(user, True)

    def get_unedited_stories(self, user):
        return self._get_stories(user, False)

    def get_edits(self, story):
        # type: (Story) -> Generator[Edit, None, None]
        for user_id, username, text, time in self.db.cursor.execute(
                'SELECT users.id, username, text, time '
                'FROM edits, users, stories '
                'WHERE stories.id = ?',
                [story.id]):
            time = dateutil.parser.parse(time)
            yield Edit(Story(story.id, story.storyname), User(user_id, username), text, time)

    def get_editors(self, story):
        # type: (Story) -> Generator[User, None, None]
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
        return self._get_start_time('users', user)

    def get_story_start_time(self, story):
        # type: (Story) -> datetime
        return self._get_start_time('stories', story)

    def can_edit(self, story, user):
        # type: (Story, User) -> bool
        for other_user in self.get_editors(story):
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
        # type: (unicode, unicode) -> User | None
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
        # type: (unicode, User, unicode) -> Tuple[Story, Edit] | None
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
        # type: (Story, User, unicode) -> Edit | None
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

        try:
            db.edit_story(story, user, 'Second line.')
        except StoryTellingException as e:
            print(e.message)


if __name__ == '__main__':
    main()
