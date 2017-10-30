from __future__ import print_function

import io
import os
from datetime import datetime
from itertools import permutations
from sys import stderr

from typing import Dict, Union, Iterable, Iterator, List, Tuple, IO, Set

from storytelling_db import StoryTellingDatabase, User, Story, Edit, StoryTellingException, \
    hash_password


def utf8(s):
    # type: (str) -> unicode
    return unicode(s, encoding='utf-8', errors='replace')


class PrivilegedStoryTellingDatabase(StoryTellingDatabase):
    def __init__(self, path='data/storytelling.db'):
        super(PrivilegedStoryTellingDatabase, self).__init__(path)
        self._num_users = -1  # type: int
        self._last_committed_uid = 0  # type: int
        self._usernames = None  # type: Set[unicode]
        self._users = None  # type: Dict[int, User]
        self._stories = None  # type: Dict[int, Story]
        self._edits = None  # type: Dict[int, Dict[int, Edit]]

    @property
    def num_users(self):
        # type: () -> int
        if self._num_users == -1:
            self.db.cursor.execute('SELECT COUNT(*) FROM users')
            self._num_users = self.db.cursor.fetchone()[0]
            self._last_committed_uid = self._num_users
        return self._num_users

    @property
    def uids(self):
        # type: () -> Iterable[int]
        for uid in self.db.cursor.execute('SELECT id FROM users'):
            yield uid[0]

    @property
    def usernames(self):
        # type: () -> Set[str]
        if self._usernames is not None:
            return self._usernames
        self._usernames = {username[0] for username in self.db.cursor.execute(
            'SELECT username FROM users')}
        return self._usernames

    @property
    def users(self):
        # type: () -> Dict[int, User]
        if self._users is not None:
            return self._users
        self._users = {id: User(id, username)
                       for id, username in self.db.cursor.execute(
            'SELECT id, username FROM users')}
        self._usernames = {user.username for user in self._users.viewvalues()}
        return self._users

    @property
    def stories(self):
        # type: () -> Dict[int, Story]
        if self._stories is not None:
            return self._stories
        self._stories = {id: Story(id, storyname)
                         for id, storyname in self.db.cursor.execute(
            'SELECT id, storyname FROM stories')}
        return self._stories

    @property
    def edits(self):
        # type: () -> Dict[int, Dict[int, Edit]]
        if self._edits is not None:
            return self._edits
        self._edits = {
            story.id: {edit.user.id: edit for edit in self.get_edits(story)}
            for story in self.stories.viewvalues()
        }
        return self._edits

    def invalidate(self):
        self._users = None
        self._stories = None
        self._edits = None

    def add_user(self, username, password):
        if username in self.usernames:
            raise StoryTellingException('username already in use')
        uid = self._num_users + 1
        self._num_users = uid
        self._usernames.add(username)
        self._users[uid] = User(uid, username)

    def _yield_new_users(self):
        # type: () -> Iterable[Tuple[int, unicode, unicode, str]]
        start = self._last_committed_uid + 1
        end = self._num_users
        for uid in xrange(start, end + 1):
            if uid % 100 == 0:
                print('adding user #{} out of {}'.format(uid, end))
            username = self._users[uid].username
            yield uid, username, hash_password(username), datetime.now().isoformat()

    def commit_added_users(self):
        if self._last_committed_uid == self._num_users:
            return
        self.db.cursor.executemany('INSERT INTO users VALUES (?, ?, ?, ?)', self._yield_new_users())
        self._last_committed_uid = self._num_users

    def add_story(self, storyname, user, text):
        # type: (unicode, User, unicode) -> Tuple[Story, Edit]
        story, edit = super(PrivilegedStoryTellingDatabase, self).add_story(storyname, user, text)
        self.stories[story.id] = story
        self.edits[story.id] = {user.id: edit}
        return story, edit

    def _yield_edit_values(self, story, uids, texts):
        # type: (Story, Iterator[int], Iterator[unicode]) -> Iterable[Tuple[int, int, unicode, str]]
        story_id = story.id
        edits = self.edits[story_id]
        for text in texts:
            uid = uids.next()
            time = datetime.now()
            edits[uid] = Edit(story, User(uid, None), text, time)
            yield story_id, uids.next(), text, time.isoformat()

    def edit_story_many_times(self, story, uids, texts):
        # type: (Story, Iterator[int], Iterator[unicode]) -> None
        self.db.conn.cursor().executemany('INSERT INTO edits VALUES (?, ?, ?, ?)',
                                          self._yield_edit_values(story, uids, texts))
        self.commit()

    def commit(self):
        self.commit_added_users()
        super(PrivilegedStoryTellingDatabase, self).commit()


class BadGutenbergStoryHeaderException(Exception):
    pass


Number = Union[int, float]


def list_dir_txts(dir_path, max_files=float('inf')):
    # type: (str, Number) -> Iterable[str]
    i = 1
    for filename in os.listdir(dir_path):
        if not filename.endswith('.txt'):
            continue
        filename = dir_path + '/' + filename
        yield filename
        i += 1
        if i > max_files:
            break


class StoryBuilder(object):
    DEFAULT_AUTHORS_PATH = 'data/authors.txt'

    @staticmethod
    def find_author_title(f):
        # type: (IO) -> Tuple[unicode, unicode]
        lines = []  # type: List[str]
        while True:
            line = f.readline().strip()  # type: str
            if len(line) == 0:
                if len(lines) == 0:
                    continue
                break
            lines.append(line)
        header = ' '.join(lines).lstrip('The Project Gutenberg Etext of ')  # type: str
        # print(header)

        splitters = (', by ', ' by ', ' Translated by ', ', Edited by ')
        for splitter in splitters:
            if splitter in header:
                header_parts = header.split(splitter, 2)  # type: List[str]
                if len(header_parts) == 2:
                    title, author = header_parts
                    return utf8(title.strip()), utf8(author.strip())

        raise BadGutenbergStoryHeaderException('bad file: {}, header: {}'.format(f.name, header))

    @staticmethod
    def find_authors(dir, max_authors=float('inf')):
        # type: (str, Number) -> Iterable[unicode]
        i = 1
        for filename in list_dir_txts(dir, max_authors):
            with open(filename) as f:
                try:
                    title, author = StoryBuilder.find_author_title(f)
                    print('found author #{} in {}'.format(i, filename))
                    yield author
                    i += 1
                except BadGutenbergStoryHeaderException as e:
                    print(e, file=stderr)

    @staticmethod
    def find_unique_authors(dir, max_authors=float('inf')):
        # type: (str, Number) -> Set[unicode]
        return {author for author in StoryBuilder.find_authors(dir, max_authors)}

    @staticmethod
    def save_authors(dir, out_filename=DEFAULT_AUTHORS_PATH, max_authors=float('inf')):
        if os.path.exists(out_filename):
            with io.open(out_filename, encoding='utf-8') as f:
                authors = {line.strip() for line in f}
        else:
            authors = {}
        with io.open(out_filename, 'w', encoding='utf-8') as f:
            authors.update(StoryBuilder.find_unique_authors(dir, max_authors))
            for author in sorted(authors):
                f.write(author)
                f.write(u'\n')

    def __init__(self, db, authors_filename=DEFAULT_AUTHORS_PATH, tmp_dir='data'):
        # type: (PrivilegedStoryTellingDatabase, str, str) -> None
        self._db = db  # type: PrivilegedStoryTellingDatabase
        self._authors_filename = authors_filename  # type: str
        self.tmp_dir = tmp_dir  # type: str
        self._new_usernames = self._generate_usernames()  # type: Iterator[unicode]
        self._new_uids = self._generate_uids()  # type: Iterator[int]
        _ = self._db.users
        self.num_stories_added = 0  # type: int

    def _generate_usernames(self):
        # type: () -> Iterable[unicode]
        """Generate infinite permutations of usernames."""
        i = 1
        while True:
            simple_usernames = [utf8(line.strip()) for line in open(self._authors_filename)]
            # map(print, simple_usernames)
            for username_parts in permutations(simple_usernames, i):
                # print(username)
                # noinspection PyCompatibility
                yield ', '.join(username_parts)
            i += 1

    def _generate_uids(self):
        # type: () -> Iterable[int]
        for username in self._generate_usernames():
            try:
                user = self._db.add_user(username, username)
                yield user.id
            except StoryTellingException:
                pass

    def add_lines(self, title, author, lines):
        # type: (unicode, unicode, Iterator[unicode]) -> None
        story, edit = self._db.add_story(title, User(author, ''), 'Title: ' + title)
        self._db.edit_story_many_times(story, xrange(1, self._db.num_users + 1).__iter__(), lines)

    def _buffer_story(self, story_filename):
        # type: (str) -> Tuple[str, int, unicode, unicode]
        with open(story_filename) as f:
            title, author = self.find_author_title(f)

            while f.readline()[:3] != '***':
                pass

            tmp = self.tmp_dir + '/' + os.path.basename(story_filename)
            num_lines = 0
            try:
                with io.open(tmp, 'w', encoding='utf-8') as buf:
                    for line in f:
                        line = line.strip()
                        if len(line) == 0:
                            continue
                        buf.write(utf8(line))
                        buf.write(u'\n')
                        num_lines += 1
            except:
                os.remove(tmp)
            return tmp, num_lines, title, author

    def add_gutenberg_story(self, story_filename):
        self.num_stories_added += 1
        tmp, num_lines, title, author = self._buffer_story(story_filename)
        try:
            print(u'adding story #{} {} by {} ({})'.format(self.num_stories_added, title, author,
                                                           utf8(story_filename)))
            num_new_uids = num_lines - self._db.num_users
            add_user = self._db.add_user
            new_usernames = self._new_usernames
            for i in xrange(num_new_uids):
                add_user(new_usernames.next(), '')
            self._db.commit_added_users()

            with io.open(tmp, encoding='utf-8') as buf:
                self.add_lines(title, author, (line.strip() for line in buf))

        finally:
            os.remove(tmp)

    def add_gutenberg_stories(self, dir='data/stories/', max_stories=float('inf')):
        # type: (str, Number) -> Iterable[str]
        i = 1
        for filename in list_dir_txts(dir):
            try:
                self.add_gutenberg_story(filename)
                yield filename
                i += 1
                if i > max_stories:
                    break
            except (BadGutenbergStoryHeaderException, StoryTellingException, Exception) as e:
                print(e, file=stderr)
                self.num_stories_added -= 1


if __name__ == '__main__':
    db = PrivilegedStoryTellingDatabase(path='data/storytelling - GutenbergCopy.db')

    # StoryBuilder.save_authors('D:/gutenberg/flattened', max_authors=10000)
    story_builder = StoryBuilder(db)

    print('ARTIFICIALLY BUILDING STORIES:\n')
    # noinspection PyTypeChecker
    list(story_builder.add_gutenberg_stories(dir='D:/gutenberg/flattened', max_stories=100))
