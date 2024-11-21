"""
Run this script with one variable:
 - PO filename to create an issue for that file
 - or '--all' to create the issues for all untranslated files that doesn't have an open issue already
 - or '--one' to create the next one issue
"""

import os
import sys
from glob import glob
from pathlib import Path

from github import Github
from potodo.potodo import PoFileStats

PYTHON_VERSION = "3.13"
PENDING_ENTRIES_FOR_GOOD_FIRST_ISSUE = 5
GOOD_FIRST_ISSUE_LABEL = "good first issue"
ISSUE_LABELS = [PYTHON_VERSION]
ISSUE_TITLE = 'Translate `{pofilename}`'
ISSUE_BODY = '''This file is {translated_percent}% translated and needs to reach 100%.

The rendered version of this file will be available at https://docs.python.org/es/{python_version}/{urlfile} once translated.
Meanwhile, the English version is shown.

Current stats for `{pofilename}`:

- Total entries: {pofile_entries}

- Entries that need work: {pending_entries} - ({pending_percent}%)
  - Fuzzy: {pofile_fuzzy}
  - Untranslated: {pofile_untranslated}

Please, comment here if you want this file to be assigned to you and a member will assign it to you as soon as possible, so you can start working on it.

Remember to follow the steps in our [Contributing Guide](https://python-docs-es.readthedocs.io/page/CONTRIBUTING.html).'''


class IssueAlreadyExistingError(Exception):
    """Issue already existing in GitHub"""


class PoFileAlreadyTranslated(Exception):
    """Given PO file is already 100% translated"""


class GitHubIssueGenerator:
    def __init__(self):
        g = Github(os.environ.get('GITHUB_TOKEN'))
        self.repo = g.get_repo('python/python-docs-es')
        self._issues = None

    @property
    def issues(self):
        if self._issues is None:
            self._issues = self.repo.get_issues(state='open')

        return self._issues

    def check_issue_not_already_existing(self, pofilename):
        for issue in self.issues:
            if pofilename in issue.title:

                print(f'Skipping {pofilename}. There is a similar issue already created at {issue.html_url}')
                raise IssueAlreadyExistingError


    @staticmethod
    def check_translation_is_pending(pofile):
        no_fuzzy_translations = pofile.fuzzy == 0
        translated_match_all_entries = pofile.translated == pofile.entries
        no_untranslated_entries_left = pofile.untranslated == 0

        if no_fuzzy_translations and (translated_match_all_entries or no_untranslated_entries_left):
            print(f'Skipping {pofile.filename}. The file is 100% translated already.')
            raise PoFileAlreadyTranslated



    def issue_generator(self, pofilename):
        pofile = PoFileStats(Path(pofilename))

        self.check_issue_not_already_existing(pofilename)
        self.check_translation_is_pending(pofile)

        pending_entries = pofile.fuzzy + pofile.untranslated

        if pending_entries <= PENDING_ENTRIES_FOR_GOOD_FIRST_ISSUE:
            labels = ISSUE_LABELS + [GOOD_FIRST_ISSUE_LABEL]
        else:
            labels = ISSUE_LABELS

        urlfile = pofilename.replace('.po', '.html')
        title = ISSUE_TITLE.format(pofilename=pofilename)
        body = ISSUE_BODY.format(
            translated_percent=pofile.percent_translated,
            python_version=PYTHON_VERSION,
            urlfile=urlfile,
            pofilename=pofilename,
            pofile_fuzzy=pofile.fuzzy,
            pending_percent=100 - pofile.percent_translated,
            pofile_entries=pofile.entries,
            pofile_untranslated=pofile.untranslated,
            pending_entries=pending_entries,
        )
        # https://pygithub.readthedocs.io/en/latest/github_objects/Repository.html#github.Repository.Repository.create_issue
        issue = self.repo.create_issue(title=title, body=body, labels=labels)

        return issue

    def create_issues(self, only_one=False):
        po_files = glob("**/*.po")
        existing_issue_counter = 0
        already_translated_counter = 0
        created_issues_counter = 0

        print(f"TOTAL PO FILES: {len(po_files)}")

        for pofilename in po_files:
            try:
                issue = self.issue_generator(pofilename)
                created_issues_counter += 1
                print(f'Issue "{issue.title}" created at {issue.html_url}')
                if only_one:
                    break
            except IssueAlreadyExistingError:
                existing_issue_counter += 1
            except PoFileAlreadyTranslated:
                already_translated_counter += 1

        print("Stats:")
        print(f"- Existing issues: {existing_issue_counter}")
        print(f"- Already translated files: {already_translated_counter}")
        print(f"- Created issues: {created_issues_counter}")


def main():
    error_msg = "Specify PO filename or '--all' to create all the issues, or '--one' to create the next one issue"
    if len(sys.argv) != 2:
        raise Exception(error_msg)

    arg = sys.argv[1]

    gh = GitHubIssueGenerator()

    if arg == "--all":
        gh.create_issues()

    elif arg == "--one":
        gh.create_issues(only_one=True)

    else:
        try:
            gh.issue_generator(arg)
        except FileNotFoundError:
            raise Exception(error_msg)

if __name__ == "__main__":
    main()
