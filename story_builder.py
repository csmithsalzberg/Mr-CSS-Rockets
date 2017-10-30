from itertools import permutations, chain

import os
from typing import Dict, Generator, Union

from storytelling_db import StoryTellingDatabase, User, Story, Edit, StoryTellingException


class PrivilegedStoryTellingDatabase(StoryTellingDatabase):
    def __init__(self, path='data/storytelling.db'):
        super(PrivilegedStoryTellingDatabase, self).__init__(path)
        self._users = None  # type: Dict[int, User]
        self._stories = None  # type: Dict[int, Story]
        self._edits = None  # type: Dict[int, Dict[int, Edit]]

    @property
    def users(self):
        # type: () -> Dict[int, User]
        if self._users is not None:
            return self._users
        self._users = {id: User(id, username)
                       for id, username in self.db.cursor.execute(
            'SELECT id, username FROM users')}
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


class StoryBuilder(object):
    def __init__(self, db, users_filename):
        # type: (PrivilegedStoryTellingDatabase, str) -> None
        self._db = db
        self._users_file = users_filename
        self._new_users = self._generate_users()

    def _generate_usernames(self):
        # type: () -> Generator[unicode, None, None]
        """Generate infinite permutations of usernames."""
        i = 1
        while True:
            simple_usernames = [line.strip() + ' ' for line in self._users_file]
            for username in permutations(simple_usernames, i):
                # noinspection PyCompatibility
                yield unicode(username.strip())
            i += 1

    def _generate_users(self):
        for username in self._generate_usernames():
            try:
                yield self._db.add_user(username, username)
            except StoryTellingException:
                pass

    def add_story(self, story_filename):
        # type: (str) -> None
        existing_users = self._db.users.viewvalues()
        users = chain(existing_users, self._new_users)

        storyname = os.path.basename(story_filename)
        story = self._db.add_story(storyname, users.next(), storyname)

        for line in open(story_filename):
            line = line.strip()
            if len(line) == 0:
                continue
            self._db.edit_story(story, users.next(), line)

        self._db.invalidate()

    def add_stories(self, dir):
        for filename in os.listdir(dir):
            self.add_story(dir + os.sep + filename)

    def walk_stories(self, dir, num_stories=float('inf')):
        # type: (str, Union[int, float]) -> Generator[str, None, None]
        i = 0
        for dirpath, dirname, filenames in os.walk(dir):
            for filename in filenames:
                if i < num_stories:
                    return
                filename = dirpath + os.sep + filename
                self.add_story(filename)
                i += 1
                yield filename


if __name__ == '__main__':
    from pprint import pprint

    db = PrivilegedStoryTellingDatabase(path='../data/storytelling.db')
    pprint(db.edits)
