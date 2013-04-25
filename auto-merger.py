#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
(GitLab) Auto-Merger

Author: Xin Yin <killkeeper@gmail.com>
"""

import os
import sys
import logging
import MySQLdb

from subprocess import Popen, PIPE
from config import *
from mail import send_mail
from db import User, Project, MergeRequest, DatabaseError

mime_template = """
------------------------------
----   GitLab Auto Merger ----
------------------------------

This is to notify you that, following merge request,
either filed by you or one of your project team member, 
has been processed.

======= Merge Request =======

 * Merge Request: {title}
 * Created at {created_at} by {author}

======== Repository =========

 * Repository: {proj_name} ({proj_path}.git)
 * Merge: [{src_branch}] -> [{dest_branch}]

========== Status ===========

 * {status}

===== Git Operation Log =====

[git merge]

{merge_output}

[git push]

{push_output}

[diff]

{diff_stats}
"""

class GitMergeConflicts(Exception):
    pass

class GitPushError(Exception):
    pass

def system_invoke(args, cwd=None):
    if not cwd:
        cwd = os.getcwd()

    _pipe = Popen(' '.join(map(str, args)), shell=True, cwd=cwd,
        stdout=PIPE)
    _stdout = _pipe.communicate()[0]

    return _pipe.returncode, _stdout

def construct_origin_path(base, creator, proj_path):
    return ':'.join([base, os.path.join(creator, proj_path + '.git')])

def git_diff_stats(creator, proj_path, src_branch, dest_branch):
    repo_path = os.path.join(MERGER_WORKING_DIR, creator, proj_path)

    retcode, diff_stats = system_invoke(["git", "diff", "--stat",
        dest_branch, "origin/"+src_branch], cwd=repo_path)

    return diff_stats

def git_merge_branches(origin_path, creator, proj_path, src_branch, 
        dest_branch):
    repo_path = os.path.join(MERGER_WORKING_DIR, creator, proj_path)
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)
        os.chdir(repo_path)
        print system_invoke(["git", "clone", origin_path, '.'])
    else:
        os.chdir(repo_path)
        # repo exists, fast forward to latest commit of target branch
        system_invoke(["git", "checkout", dest_branch])
        system_invoke(["git", "pull", "origin", dest_branch])

    system_invoke(["git", "fetch", "origin"])

    diff_stats = git_diff_stats(creator, proj_path, src_branch,
            dest_branch)

    retcode, stdout = system_invoke(["git", "merge",
        "origin/"+src_branch, dest_branch])

    merge_output = stdout

    if not retcode == 0:
        raise GitMergeConflicts(stdout)

    retcode, stdout = system_invoke(["git", "push", "origin", dest_branch])
    if not retcode == 0:
        raise GitPushError(stdout)

    return merge_output, stdout, diff_stats

def merge_branchs(db, request):
    assoc_project = Project(db, request['project_id'])
    if not len(assoc_project):
        raise DatabaseError

    proj = assoc_project[0]

    proj_name = proj['name']
    proj_path = proj['path']

    assoc_users = User(db, (proj['creator_id'], request['author_id']))

    if len(assoc_users) == 2:
        if assoc_users[0]['id'] == proj['creator_id']:
            creator, author = assoc_users[0], assoc_users[1]
        else:
            author, creator = assoc_users[0], assoc_users[1]
    elif len(assoc_users) == 1:
        creator = author = assoc_users[0]

    email_recipients = [user['email'] for user in assoc_users]

    origin_path = construct_origin_path(GITLAB_SSH, creator['username'],
            proj_path)

    msg_blob = {
                'title': request['title'],
                'created_at': request['created_at'],
                'creator': creator['username'],
                'author': author['name'],
                'proj_name': proj_name,
                'proj_path': '/'.join([creator['username'], proj_path]),
                'src_branch': request['source_branch'],
                'dest_branch': request['target_branch'],
                }
    try:
        merge_output, push_output, diff_stats = git_merge_branches(
                origin_path,
                creator['username'], proj_path,
                request['source_branch'], request['target_branch'])

        msg_blob['merge_output'] = merge_output
        msg_blob['push_output'] = push_output
        msg_blob['diff_stats'] = diff_stats

        send_merge_confirmation(email_recipients, msg_blob)

    except GitMergeConflicts as e:
        msg_blob['merge_output'] = e.value
        msg_blob['push_output'] = 'NOT REACHED'
        msg_blob['diff_stats'] = git_diff_stats(creator['username'], 
                proj_path, request['source_branch'],
                request['target_branch'])

        send_merge_warnings(email_recipients, msg_blob) 
    except GitPushError as e:
        msg_blob['merge_output'] = ''
        msg_blob['push_output'] = e.value
        msg_blog['diff_stats'] = git_diff_stats(creator['username'], 
                proj_path, request['source_branch'],
                request['target_branch'])

        send_merge_warnings(email_recipients, msg_blob) 

def send_merge_confirmation(recipients, blob):
    blob['status'] = 'SUCCESSFULLY COMPLETED!'
    subject = '[{creator}/{proj_path}.git] '\
            'Merged: {src_branch} -> {dest_branch}'.format(**blob)

    msg = mime_template.format(**blob)

    send_mail(recipients, EMAIL_SENDER, subject, msg)

def send_conflict_warnings():
    blob['status'] = '!!! AUTO-MERGE FAILED TO COMPLETE !!!\n'\
            '!!! PLEASE CHECK POTENTIAL ERROR INFORMATION BELOW !!!'
    subject = '[{creator}/{proj_path}.git] '\
            'FAILED to merge'\
            '{src_branch} -> {dest_branch}'.format(**msg_blob)
    msg = mime_template.format(**msg_blob)

    send_mail(recipients, EMAIL_SENDER, subject, msg)


def main():
    db_conn =  MySQLdb.connect(host=MYSQL['host'],
        user=MYSQL['username'],
        passwd=MYSQL['password'],
        db=MYSQL['database'])

    new_merge_reqs = MergeRequest(db_conn, assignee_id=MERGER_USER_ID)
    if not new_merge_reqs:
        return

    prev_src_branch = ''
    prev_dest_branch = ''
    prev_proj = 0
    for request in new_merge_reqs:
        if not prev_src_branch == request['source_branch'] or \
                not prev_dest_branch == request['target_branch'] or \
                not prev_proj == request['project_id']:

            merge_branchs(db_conn, request)

            prev_src_branch, prev_dest_branch, prev_proj = \
                    request['source_branch'], request['target_branch'], \
                    request['project_id']

if __name__ == "__main__":
    main()
