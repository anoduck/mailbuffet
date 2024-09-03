#!/usr/bin/env python
# coding: utf-8

# # Mail Buffet
#
# > Extracting Mbox messages to markdown files

# ### Perform imports

# In[2]:


#!/usr/bin/env python3
#! vim:set filetype=python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
# MIT License = 'Copyright (c) 2024 Anoduck'
# This software is released under the MIT License.
# https://anoduck.mit-license.org

# ----------------------------------------------
# This script was inspired by and parts of the code was borrowed from
# an effort to understand how to use the python program formbox written
# by Nguyá»n Gia Phong. Unfortunately, it's mysteries are still
# locked in the mind of it's developer.
# ---------------------------------------------

from simple_parsing import parse
from dataclasses import dataclass
from mailbox import mbox
# from collections import defaultdict
from email.header import decode_header
from email.utils import parsedate_to_datetime
from urllib import parse
from urllib.parse import quote, unquote, urlencode
from markdown import markdown
import os


# ### Process Args
#
# It appears the ipykernel does not like simple_parsing, which is weird.
#
# Hardcoding args to circumvent.

# In[3]:


mbox_file = './exported.mbox'
outdir = './results/'


class cfg:
    """
    A more than simple script to parse the mbox file generated by Google Takeout
    into individual html files.
    """
    mbox_file: str = './exported.mbox'  # Mbox file for extraction
    outdir: str = './results'  # Directory to write files to


# ### Return Mbox object with initializer

# In[4]:


def get_mbox(mbox_file):
    return mbox(mbox_file, create=False)


# ### Get Message parts

# #### Reply to params (???)

# In[40]:


def reply_to(message):
    """Return mailto parameters for replying to the given email."""
    yield 'In-Reply-To', message['Message-ID']
    yield 'Cc', message.get('Reply-To', message['From'])
    subject = message['Subject']
    if subject is None: return
    if subject.lower().startswith('re:'):
        yield 'Subject', subject
    else:
        yield 'Subject', f'Re: {subject}'


# #### Get Header

# In[41]:


def get_header(msg):
    """Return the decoded email header."""
    header = msg.get('header')
    ret_str = str('### Header: ')
    for string, charset in decode_header(header):
        encoding = 'utf-8' if charset is None else charset
        decoded = string.decode(encoding)
        ret_str += decoded + '\n'
    return ret_str


# #### Get Date

# In[6]:


def get_date(message):
    return parsedate_to_datetime(message['Date']).date()


# #### Get Body

# In[43]:


def get_body(message):
    if message.is_multipart():
        for payload in map(get_body, message.get_payload()):
            if payload is not None: return payload
    elif message.get_content_type() in ('text/markdown', 'text/plain'):
        payload = message.get_payload(decode=True).decode()
        return markdown(payload)
    else:
        return None


def get_author(message):
    msgfrom = message['From']
    string = [s for s, _ in decode_header(msgfrom)]
    return ''.join(string).rsplit(maxsplit=1)[0]



# #### format message to markdown string

# In[44]:


def parse_message(msg, msgtype=None, child_ids=None):
    body = get_body(msg)
    if body is None:
       return
    if msgtype == "parent":
        child_str = str(f'''
        ----
        ### Child Parameters
            mailto_params: {urlencode(dict(reply_to(msg)))}
          \n
          Children: {child_ids}
        ''')
    content = str(f'''---
              title: {msg.get('Subject')}
              author: {get_author(msg)}
              subject: {msg.get('subject')}
              message-id: {msg['Message-ID']}
              date: {get_date(msg).isoformat}
              rfc822: {msg.get('rfc822')}
              ---
              \n
              {body}
              ''')
    if msgtype == 'parent':
        content = content + child_str
    return content


# #### Associate function: get Name

# In[9]:


def get_name(message):
    mid = message.get('Message-Id')
    subj = str.join(message['Subject'][:5], '_')
    name = mid + '-' + subj + '.html'
    return name


# ### Secondary Process: Write Thread

# In[46]:


from operator import itemgetter


def write_thread(thread):
    if thread.get('has_children'):
        parent_message = thread.get('parent')
        unsorted_children = thread.get('children')
        children = sorted(unsorted_children, key=itemgetter('date'), reverse=True)
        child_ids = [i for i['Message-Id'] in children]
        fname = get_name(parent_message)
        fpath = os.path.join(outdir, fname)
        with open(fpath, 'w', encoding='utf-8', errors='xmlcharrefreplace') as of:
            pcontent = parse_message(parent_message, msgtype='parent', child_ids=child_ids)
            phtml = markdown(pcontent)
            of.write(phtml)
            of.write('\n')
            of.write('====')
            for child in children:
                child_content = parse_message(child, msgtype=child, child_ids=None)
                child_html = markdown(child_content)
                of.write(child_html)
                of.write('\n')
                of.write('----')
            of.close()
    else:
        pmessage = thread.get('parent')
        fname = get_name(pmessage)
        fpath = os.path.join(outdir, fname)
        with open(fpath, 'w', encoding='utf-8', errors='xmlcharrefreplace') as of:
            pcontent = parse_message(pmessage, msgtype=None, child_ids=None)
            phtml = markdown(pcontent)
            of.write(phtml)
            of.write('\n')
            of.write('====')
            of.close()


# ### Primary Process: Main

# In[47]:


def main():
    messages = get_mbox(mbox_file)
    messages = list(messages)
    parents = []
    for message in messages:
        if not message.get('In-Reply-To'):
            parents.append(message)
    msg_list = []
    for parent in parents:
        maildict = dict()
        pID = parent.get("Message-Id")
        reply_list = []
        for message in messages:
            if message.get('In-Reply-To'):
                if pID in message.get('In-Reply-To'):
                    reply_list.append(message)
        if len(reply_list) >= 1:
            maildict['has_child'] = True
            maildict["parent"] = parent
            maildict["children"] = reply_list
        else:
            maildict['has_child'] = False
            maildict["parent"] = parent
            maildict["children"] = None
        msg_list.append(maildict)
    for thread in msg_list:
        write_thread(thread)


# In[12]:


if __name__ == '__main__':
    #!jupyter nbconvert --to script mailbuffet.ipynb
    main()


# messages = get_mbox(mbox_file)
# msg = messages[0]
# payload = msg.get_body()
# print(payload)
