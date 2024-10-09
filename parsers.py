#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from sys import platform
from datetime import datetime

from sharedutils import openjson
from sharedutils import runshellcmd
from sharedutils import todiscord, totweet
from sharedutils import stdlog, dbglog, errlog

if platform == 'darwin':
    fancygrep = 'grep -oE'
else:
    fancygrep = 'grep -oP'

def posttemplate(victim, group_name, timestamp, victim_url=None):
    '''
    assuming we have a new post - form the template we will use for the new entry in posts.json
    '''
    schema = {
        'post_title': victim,
        'group_name': group_name,
        'discovered': timestamp,
        'victim_url': victim_url  # 被害者のURLを追加
    }
    dbglog(schema)
    return schema

def existingpost(post_title, group_name):
    '''
    check if a post already exists in posts.json
    '''
    posts = openjson('posts.json')
    for post in posts:
        if post['post_title'] == post_title and post['group_name'] == group_name:
            return True
    dbglog('post does not exist: ' + post_title)
    return False

def appender(post_title, group_name, victim_url=None):
    '''
    append a new post to posts.json
    '''
    if len(post_title) == 0:
        errlog('post_title is empty')
        return
    if len(post_title) > 90:
        post_title = post_title[:90]
    if existingpost(post_title, group_name) is False:
        posts = openjson('posts.json')
        newpost = posttemplate(post_title, group_name, str(datetime.today()), victim_url)
        stdlog('adding new post - ' + 'group:' + group_name + ' title:' + post_title + ' url:' + (victim_url or 'N/A'))
        posts.append(newpost)
        with open('posts.json', 'w', encoding='utf-8') as outfile:
            dbglog('writing changes to posts.json')
            json.dump(posts, outfile, indent=4, ensure_ascii=False)
        if os.environ.get('DISCORD_WEBHOOK') is not None:
            todiscord(newpost['post_title'], newpost['group_name'], os.environ.get('DISCORD_WEBHOOK'))
        if os.environ.get('X_CONSUMER_KEY') is not None:
            totweet(newpost['post_title'], newpost['group_name'])

'''
all parsers here are shell - mix of grep/sed/awk & perl - runshellcmd is a wrapper for subprocess.run
'''

def synack():
    stdlog('parser: ' + 'synack')
    parser='''
    grep 'card-title' source/synack-*.html --no-filename | cut -d ">" -f2 | cut -d "<" -f1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('synack: ' + 'parsing fail')
    for post in posts:
        appender(post, 'synack')

def everest():
    stdlog('parser: ' + 'everest')
    parser = '''
    grep '<h2 class="entry-title' source/everest-*.html | cut -d '>' -f3 | cut -d '<' -f1 | sort | uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('everest: ' + 'parsing fail')
    for post in posts:
        appender(post, 'everest')


def suncrypt():
    stdlog('parser: ' + 'suncrypt')
    parser = '''
    cat source/suncrypt-*.html | tr '>' '\n' | grep -A1 '<a href="client?id=' | sed -e '/^--/d' -e '/^<a/d' | cut -d '<' -f1 | sed -e 's/[ \t]*$//' "$@" -e '/Read more/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('suncrypt: ' + 'parsing fail')
    for post in posts:
        appender(post, 'suncrypt')

def lorenz():
    stdlog('parser: ' + 'lorenz')
    parser = '''
    grep 'h3' source/lorenz-*.html --no-filename | cut -d ">" -f2 | cut -d "<" -f1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lorenz: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lorenz')

def lockbit2():
    stdlog('parser: ' + 'lockbit2')
    # egrep -h -A1 'class="post-title"' source/lockbit2-* | grep -v 'class="post-title"' | grep -v '\--' | cut -d'<' -f1 | tr -d ' '
    parser = '''
    awk -v lines=2 '/post-title-block/ {for(i=lines;i;--i)getline; print $0 }' source/lockbit2-*.html | cut -d '<' -f1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort | uniq | grep -v "\.\.\.$"
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lockbit2: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lockbit2')

'''
used to fetch the description of a lb2 post - not used
def lockbit2desc():
    stdlog('parser: ' + 'lockbit2desc')
    # sed -n '/post-block-text/{n;p;}' source/lockbit2-*.html | sed '/^</d' | cut -d "<" -f1
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lockbit2: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lockbit2')
'''

def arvinclub():
    stdlog('parser: ' + 'arvinclub')
    # grep 'bookmark' source/arvinclub-*.html --no-filename | cut -d ">" -f3 | cut -d "<" -f1
    # grep 'rel="bookmark">' source/arvinclub-*.html -C 1 | grep '</a>' | sed 's/^[^[:alnum:]]*//' | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep '<h1 class="post-title">' source/arvinclub-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    parser = '''
    grep --no-filename  -C 1 '<p><strong>Name:</strong></p>' source/arvinclub-*.html  | grep 'class="highlight"' | cut -d '>' -f 6
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('arvinclub: ' + 'parsing fail')
    for post in posts:
        appender(post, 'arvinclub')

def hiveleak():
    stdlog('parser: ' + 'hiveleak')
    # grep 'bookmark' source/hive-*.html --no-filename | cut -d ">" -f3 | cut -d "<" -f1
    # egrep -o 'class="">([[:alnum:]]| |\.)+</h2>' source/hiveleak-hiveleak*.html | cut -d '>' -f 2 | cut -d '<' -f 1 && egrep -o 'class="lines">([[:alnum:]]| |\.)+</h2>' source/hiveleak-hiveleak*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sort -u
    # egrep -o 'class="lines">.*?</h2>' source/hiveleak-hiveleak*.html | cut -d '>' -f 2 | cut -d '<' -f 1 && egrep -o 'class="lines">.*?</h2>' source/hiveleak-hiveleak*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sort -u
    # jq -r '.[].title' source/hiveleak-hiveapi*.html || true
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('hiveleak: ' + 'parsing fail')
    for post in posts:
        appender(post, 'hiveleak')

def avaddon():
    stdlog('parser: ' + 'avaddon')
    parser = '''
    grep 'h6' source/avaddon-*.html --no-filename | cut -d ">" -f3 | sed -e s/'<\/a'// -e 's/&amp;/\&/g' | perl -MHTML::Entities -ne 'print decode_entities($_)'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('avaddon: ' + 'parsing fail')
    for post in posts:
        appender(post, 'avaddon')

def xinglocker():
    stdlog('parser: ' + 'xinglocker')
    parser = '''
    grep "h3" -A1 source/xinglocker-*.html --no-filename | grep -v h3 | awk -v n=4 'NR%n==1' | sed -e 's/^[ \t]*//' -e 's/^ *//g' -e 's/[[:space:]]*$//' -e 's/&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('xinglocker: ' + 'parsing fail')
    for post in posts:
        appender(post, 'xinglocker')

def clop():
    stdlog('parser: ' + 'clop')
    # grep 'PUBLISHED' source/clop-*.html --no-filename | sed -e s/"<strong>"// -e s/"<\/strong>"// -e s/"<\/p>"// -e s/"<p>"// -e s/"<br>"// -e s/"<strong>"// -e s/"<\/strong>"// -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep 'g-menu-item-title' source/clop-*.html --no-filename | sed -e s/'<span class="g-menu-item-title">'// -e s/"<\/span>"// -e 's/^ *//g' -e 's/[[:space:]]*$//' -e 's/^ARCHIVE[[:digit:]]$//' -e s/'^HOW TO DOWNLOAD?$'// -e 's/^ARCHIVE$//' -e 's/^HOME$//' -e '/^$/d'
    parser = '''
    grep '<td><a href="' source/clop-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('clop: ' + 'parsing fail')
    for post in posts:
        appender(post, 'clop')

def revil():
    stdlog('parser: ' + 'revil')
    # grep 'href="/posts' source/revil-*.html --no-filename | cut -d '>' -f2 | sed -e s/'<\/a'// -e 's/^[ \t]*//'
    parser = '''
    grep 'justify-content-between' source/revil-*.html --no-filename | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' -e '/ediban/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('revil: ' + 'parsing fail')
    for post in posts:
        appender(post, 'revil')

def conti():
    stdlog('parser: ' + 'conti')
    # grep 'class="title">&' source/conti-*.html --no-filename | cut -d ";" -f2 | sed -e s/"&rdquo"//
    parser = '''
    grep 'newsList' source/conti-continewsnv5ot*.html --no-filename | sed -e 's/        newsList(//g' -e 's/);//g' | jq '.[].title' -r  || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('conti: ' + 'parsing fail')
    for post in posts:
        appender(post, 'conti')
    
def pysa():
    stdlog('parser: ' + 'pysa')
    parser = '''
    grep 'icon-chevron-right' source/pysa-*.html --no-filename | cut -d '>' -f3 | sed 's/^ *//g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('pysa: ' + 'parsing fail')
    for post in posts:
        appender(post, 'pysa')

def nefilim():
    stdlog('parser: ' + 'nefilim')
    parser = '''
    grep 'h2' source/nefilim-*.html --no-filename | cut -d '>' -f3 | sed -e s/'<\/a'// | perl -MHTML::Entities -ne 'print decode_entities($_)'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('nefilim: ' + 'parsing fail')
    for post in posts:
        appender(post, 'nefilim') 

def mountlocker():
    stdlog('parser: ' + 'mountlocker')
    parser = '''
    grep '<h3><a href=' source/mount-locker-*.html --no-filename | cut -d '>' -f5 | sed -e s/'<\/a'// -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('mountlocker: ' + 'parsing fail')
    for post in posts:
        appender(post, 'mountlocker')

def babuk():
    stdlog('parser: ' + 'babuk')
    parser = '''
    grep '<h5>' source/babuk-*.html --no-filename | sed 's/^ *//g' | cut -d '>' -f2 | cut -d '<' -f1 | grep -wv 'Hospitals\|Non-Profit\|Schools\|Small Business' | sed '/^[[:space:]]*$/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('babuk: ' + 'parsing fail')
    for post in posts:
        appender(post, 'babuk')
    
def ransomexx():
    stdlog('parser: ' + 'ransomexx')
    # grep 'card-title' source/ransomexx-*.html --no-filename | cut -d '>' -f2 | sed -e s/'<\/h5'// -e 's/^ *//g' -e 's/[[:space:]]*$//' -e 's/&amp;/\&/g'
    parser = '''
    grep '<h2 class="entry-title" itemprop="headline">' source/ransomexx-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomexx: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomexx')

def cuba():
    stdlog('parser: ' + 'cuba')
    # grep '<p>' source/cuba-*.html --no-filename | cut -d '>' -f3 | cut -d '<' -f1
    # grep '<a href="http://' source/cuba-cuba4i* | cut -d '/' -f 4 | sort -u
    parser = '''
    grep --no-filename '<a href="/company/' source/cuba-*.html | cut -d '/' -f 3 | cut -d '"' -f 1 | sort --uniq | grep -v company
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cuba: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cuba')

def pay2key():
    stdlog('parser: ' + 'pay2key')
    parser = '''
    grep 'h3><a href' source/pay2key-*.html --no-filename | cut -d '>' -f3 | sed -e s/'<\/a'//
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('pay2key: ' + 'parsing fail')
    for post in posts:
        appender(post, 'pay2key')

def azroteam():
    stdlog('parser: ' + 'azroteam')
    parser = '''
    grep "h3" -A1 source/aztroteam-*.html --no-filename | grep -v h3 | awk -v n=4 'NR%n==1' | sed -e 's/^[ \t]*//' -e 's/&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('azroteam: ' + 'parsing fail')
    for post in posts:
        appender(post, 'azroteam')

def lockdata():
    stdlog('parser: ' + 'lockdata')
    parser = '''
    grep '<a href="/view.php?' source/lockdata-*.html --no-filename | cut -d '>' -f2 | cut -d '<' -f1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lockdata: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lockdata')
    
def blacktor():
    stdlog('parser: ' + 'blacktor')
    # sed -n '/tr/{n;p;}' source/bl@cktor-*.html | grep 'td' | cut -d '>' -f2 | cut -d '<' -f1
    parser = '''
    grep '>Details</a></td>' source/blacktor-*.html --no-filename | cut -f2 -d '"' | cut -f 2- -d- | cut -f 1 -d .
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blacktor: ' + 'parsing fail')
    for post in posts:
        appender(post, 'blacktor')
    
def darkleakmarket():
    stdlog('parser: ' + 'darkleakmarket')
    parser = '''
    grep 'page.php' source/darkleakmarket-*.html --no-filename | sed -e 's/^[ \t]*//' | cut -d '>' -f3 | sed '/^</d' | cut -d '<' -f1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('darkleakmarket: ' + 'parsing fail')
    for post in posts:
        appender(post, 'darkleakmarket')

def blackmatter():
    stdlog('parser: ' + 'blackmatter')
    parser = '''
    grep '<h4 class="post-announce-name" title="' source/blackmatter-*.html --no-filename | cut -d '"' -f4 | sort -u
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blackmatter: ' + 'parsing fail')
    for post in posts:
        appender(post, 'blackmatter')

def payloadbin():
    stdlog('parser: ' + 'payloadbin')
    parser = '''
    grep '<h4 class="h4' source/payloadbin-*.html --no-filename | cut -d '>' -f3 | cut -d '<' -f 1 | perl -MHTML::Entities -ne 'print decode_entities($_)'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('payloadbin: ' + 'parsing fail')
    for post in posts:
        appender(post, 'payloadbin')

def groove():
    stdlog('parser: ' + 'groove')
    parser = '''
    egrep -o 'class="title">([[:alnum:]]| |\.)+</a>' source/groove-*.html | cut -d '>' -f2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('groove: ' + 'parsing fail')
    for post in posts:
        appender(post, 'groove')

def karma():
    stdlog('parser: ' + 'karma')
    parser = '''
    grep "h2" source/karma-*.html --no-filename | cut -d '>' -f 3 | cut -d '<' -f 1 | sed '/^$/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('karma: ' + 'parsing fail')
    for post in posts:
        appender(post, 'karma')

def blackbyte():
    stdlog('parser: ' + 'blackbyte')
    # grep "h1" source/blackbyte-*.html --no-filename | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//'
    # grep "display-4" source/blackbyte-*.html --no-filename | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^[ \t]*//' -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep '<h1 class="h_font"' source/blackbyte-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    # grep --no-filename 'class="h_font"' source/blackbyte-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//'
    parser = '''
    grep --no-filename 'class="target-name"' source/blackbyte-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//' 
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blackbyte: ' + 'parsing fail')
    for post in posts:
        appender(post, 'blackbyte')

def spook():
    stdlog('parser: ' + 'spook')
    parser = '''
    grep 'h2 class' source/spook-*.html --no-filename | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e '/^$/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('spook: ' + 'parsing fail')
    for post in posts:
        appender(post, 'spook')

def quantum():
    stdlog('parser: ' + 'quantum')
    parser = '''
    awk '/h2/{getline; print}' source/quantum-*.html | sed -e 's/^ *//g' -e '/<\/a>/d' -e 's/&amp;/\&/g' | perl -MHTML::Entities -ne 'print decode_entities($_)'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('quantum: ' + 'parsing fail')
    for post in posts:
        appender(post, 'quantum')

def atomsilo():
    stdlog('parser: ' + 'atomsilo')
    parser = '''
    grep "h4" source/atomsilo-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('atomsilo: ' + 'parsing fail')
    for post in posts:
        appender(post, 'atomsilo')
        
def lv():
    stdlog('parser: ' + 'lv')
    # %s "blog-post-title.*?</a>" source/lv-rbvuetun*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    parser = '''
    jq -r '.posts[].title' source/lv-rbvuetun*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lv: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lv')

def midas():
    stdlog('parser: ' + 'midas')
    parser = '''
    grep "/h3" source/midas-*.html --no-filename | sed -e 's/<\/h3>//' -e 's/^ *//g' -e '/^$/d' -e 's/^ *//g' -e 's/[[:space:]]*$//' -e '/^$/d' -e 's/&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('midas: ' + 'parsing fail')
    for post in posts:
        appender(post, 'midas')

def snatch():
    stdlog('parser: ' + 'snatch')
    parser = '''
    %s "a-b-n-name.*?</div>" source/snatch-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sort | uniq | sed 's/&amp;/\&/g'
    ''' % (fancygrep)
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('snatch: ' + 'parsing fail')
    for post in posts:
        appender(post, 'snatch')

def rook():
    stdlog('parser: ' + 'rook')
    parser = '''
    grep 'class="post-title"' source/rook-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed '/^&#34/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('rook: ' + 'parsing fail')
    for post in posts:
        appender(post, 'rook')

def cryp70n1c0d3():
    stdlog('parser: ' + 'cryp70n1c0d3')
    parser = '''
    grep '<td class="selection"' source/cryp70n1c0d3-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cryp70n1c0d3: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cryp70n1c0d3')

def mosesstaff():
    stdlog('parser: ' + 'mosesstaff')
    parser = '''
    grep '<h2 class="entry-title">' source/moses-moses-staff.html -A 3 --no-filename | grep '</a>' | sed 's/^ *//g' | cut -d '<' -f 1 | sed 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('mosesstaff: ' + 'parsing fail')
    for post in posts:
        appender(post, 'mosesstaff')

def alphv():
    stdlog('parser: ' + 'alphv')
    # egrep -o 'class="mat-h2">([[:alnum:]]| |\.)+</h2>' source/alphv-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    # grep -o 'class="mat-h2">[^<>]*<\/h2>' source/alphv-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' -e '/No articles here yet, check back later./d'
    parser = '''
    jq -r '.items[].title' source/alphv-alphvuzxyxv6yl*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('alphv: ' + 'parsing fail')
    for post in posts:
        appender(post, 'alphv')

def nightsky():
    stdlog('parser: ' + 'nightsky')
    parser = '''
    grep 'class="mdui-card-primary-title"' source/nightsky-*.html --no-filename | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('nightsky: ' + 'parsing fail')
    for post in posts:
        appender(post, 'nightsky')

def vicesociety():
    stdlog('parser: ' + 'vicesociety')
    # grep '<tr><td valign="top"><br><font size="4" color="#FFFFFF"><b>' source/vicesociety-*.html --no-filename | cut -d '>' -f 6 | cut -d '<' -f 1 | sed -e '/ato District Health Boa/d' -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort --uniq
    parser = '''
    grep '<tr><td valign="top"><br><font color="#FFFFFF" size="4">' source/vicesociety-*.html --no-filename | cut -d '>' -f 6 | cut -d '<' -f 1 | sed -e '/ato District Health Boa/d' -e 's/^ *//g' -e 's/[[:space:]]*$//' -e 's/&amp;/\&/g' | sort --uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('vicesociety: ' + 'parsing fail')
    for post in posts:
        appender(post, 'vicesociety')

def pandora():
    stdlog('parser: ' + 'pandora')
    parser = '''
    grep '<span class="post-title gt-c-content-color-first">' source/pandora-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed 's/&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('pandora: ' + 'parsing fail')
    for post in posts:
        appender(post, 'pandora')

def stormous():
    stdlog('parser: ' + 'stormous')
    # grep '<p> <h3> <font color="' source/stormous-*.html | grep '</h3>' | cut -d '>' -f 4 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep '<h3>' source/stormous-*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | grep "^<h3> <font" | cut -d '>' -f 3 | cut -d '<' -f 1 | sed 's/[[:space:]]*$//'
    # awk '/<h3>/{getline; print}' source/stormous-*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep 'class="h1"' source/stormous-h3*.html | cut -d '>' -f 4 | cut -d '<' -f 1 | sort --uniq | sed -e '/^Percentage/d' -e '/^Payment/d' -e '/^Click here/d'
    # grep --no-filename ' <a href="">  <h3>' source/stormous-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    ###
    # descripotion [current] : grep --no-filename '<p class="description" style="color: rgb(59, 52, 52);"> ' source/stormous-*.html | cut -d '>' -f 2 | sed -e 's/\.[^.]*$//' -e 's/^ *//'
    # grep --no-filename '<td><center><a href="#"  width="120px"><img src="' source/stormous-*.html | cut -d '"' -f 6 | cut -d '/' -f 3 | sed 's/\.[^.]*$//' | grep -v '^$' && grep '<td><a href="' source/stormous-ransekgbpi*.html | cut -d '"' -f 2 | sort | uniq
    parser = '''
    grep --no-filename -Eo '<td>www\.[^<]*</td>' source/stormous-*.html | sed -E 's/<td>(www\.[^<]*)<\/td>/\\1/'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('stormous: ' + 'parsing fail')
    for post in posts:
        appender(post, 'stormous')

def leaktheanalyst():
    stdlog('parser: ' + 'leaktheanalyst')
    parser = '''
    grep '<label class="news-headers">' source/leaktheanalyst-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/Section //' -e 's/#//' -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort -n | uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('leaktheanalyst: ' + 'parsing fail')
    for post in posts:
        appender(post, 'leaktheanalyst')

def blackbasta():
    stdlog('parser: ' + 'blackbasta')
    # egrep -o 'fqd.onion/\?id=([[:alnum:]]| |\.)+"' source/blackbasta-*.html | cut -d = -f 2 | cut -d '"' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep '.onion/?id=' source/blackbasta-st*.html | cut -d '>' -f 52 | cut -d '<' -f 1 | sed -e 's/\&amp/\&/g' -e 's/\&;/\&/g'
    # grep '.onion/?id=' source/blackbasta-st*.html | cut -d '>' -f 52 | cut -d '=' -f 5 | cut -d '"' -f 1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//'
    # cat source/blackbasta-*.html | grep -Eo '\?id=[^"]+' | awk -F'=' '{print $2}' | sed -e 's/\&amp;/\&/g'
    # grep '<strong>SITE:</strong> <em>' source/blackbasta-*.html | cut -d '>' -f 5 | cut -d '<' -f 1
    parser = '''
    grep '<p data-v-md-line="3"><em>' source/blackbasta-stnii*.html  | cut -d '>' -f 4 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blackbasta: ' + 'parsing fail')
    for post in posts:
        appender(post, 'blackbasta')

def onyx():
    stdlog('parser: ' + 'onyx')
    # grep '<h6 class=' source/onyx-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e '/Connect with us/d' -e 's/^ *//g' -e 's/[[:space:]]*$//'
    parser = '''
    grep '<h6>' source/onyx-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e '/^[[:space:]]*$/d' -e '/Connect with us/d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('onyx: ' + 'parsing fail')
    for post in posts:
        appender(post, 'onyx')

def mindware():
    stdlog('parser: ' + 'mindware')
    parser = '''
    grep '<div class="card-header">' source/mindware-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('mindware: ' + 'parsing fail')
    for post in posts:
        appender(post, 'mindware')

def ransomhouse():
    stdlog('parser: ' + 'ransomhouse')
    parser = '''
    egrep -o "class=\"cls_recordTop\"><p>([A-Za-z0-9 ,\'.-])+</p>" source/ransomhouse-xw7au5p*.html | cut -d '>' -f 3 | cut -d '<' -f 1 && jq -r '.data[].header' source/ransomhouse-zoh*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomhouse: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomhouse')

def cheers():
    stdlog('parser: ' + 'cheers')
    parser = '''
    grep '<a href="' source/cheers-*.html | grep -v title | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e '/Cheers/d' -e '/Home/d' -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cheers: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cheers')

def lockbit3():
    stdlog('parser: ' + 'lockbit3')
    parser = '''
    grep '<div class="post-title">' source/lockbit3-*.html -C 1 --no-filename | grep '</div>' | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort --uniq | tr '[:upper:]' '[:lower:]'
    '''
    url_parser = '''
    grep '<a href' source/lockbit3-*.html --no-filename | cut -d '"' -f2
    '''
    posts = runshellcmd(parser)
    urls = runshellcmd(url_parser)
    if len(posts) == 1:
        errlog('lockbit3: ' + 'parsing fail')
    for post, url in zip(posts, urls):
        appender(post, 'lockbit3', url)

        
def lockbit3fs():
    stdlog('parser: ' + 'lockbit3fs')
    # a rather crude parser that tries to exclude based on existing indexed posts on leaksites to catch others
    parser = '''
    grep --no-filename '<tr><td class="link">' source/lockbit3_fs-*.html | cut -d '"' -f 6 | sort | uniq | grep -viFx "$(jq -r '.[] | select(.group_name == "lockbit2" or .group_name == "lockbit3") | .post_title | ascii_downcase' posts.json)"
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lockbit3_fs: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lockbit3_fs')

def yanluowang():
    stdlog('parser: ' + 'yanluowang')
    parser = '''
    grep '<a href="/posts' source/yanluowang-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | perl -MHTML::Entities -ne 'print decode_entities($_)'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('yanluowang: ' + 'parsing fail')
    for post in posts:
        appender(post, 'yanluowang')

def omega():
    stdlog('parser: ' + '0mega')
    parser = '''
    grep "<tr class='trow'>" -C 1 source/0mega-*.html | grep '<td>' | cut -d '>' -f 2 | cut -d '<' -f 1 | sort --uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('0mega: ' + 'parsing fail')
    for post in posts:
        appender(post, '0mega')

def bianlian():
    stdlog('parser: ' + 'bianlian')
    # sed -n '/<a href="\/companies\//,/<\/a>/p' source/bianlian-*.html | egrep -o "([A-Za-z0-9 ,\'.-])+</a>" | cut -d '<' -f 1 | sed -e '/Contacts/d'
    parser = '''
    sed -n '/<a href="\/companies\//,/<\/a>/p' source/bianlian-*.html | sed 's/&amp;/and/' | egrep -o "([A-Za-z0-9 ,*\'.-])+</a>" | cut -d '<' -f 1 | sed -e '/Contacts/d' -e '/BianLian/d' -e '/Home/d' | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('bianlian: ' + 'parsing fail')
    for post in posts:
        appender(post, 'bianlian')

def redalert():
    stdlog('parser: ' + 'redalert')
    parser = '''
    egrep -o "<h3>([A-Za-z0-9 ,\'.-])+</h3>" source/redalert-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('redalert: ' + 'parsing fail')
    for post in posts:
        appender(post, 'redalert')

def daixin():
    stdlog('parser: ' + 'daixin')
    parser = '''
    grep '<h4 class="border-danger' source/daixin-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e '/^$/d' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('daixin: ' + 'parsing fail')
    for post in posts:
        appender(post, 'daixin')

def icefire():
    stdlog('parser: ' + 'icefire')
    parser = '''
    grep align-middle -C 2 source/icefire-*.html | grep span | grep -v '\*\*\*\*' | grep -v updating | grep '\*\.' | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('icefire: ' + 'parsing fail')
    for post in posts:
        appender(post, 'icefire')

def donutleaks():
    stdlog('parser: ' + 'donutleaks')
    parser = '''
    grep '<h2 class="post-title">' source/donutleaks-*.html --no-filename | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/\&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('donutleaks: ' + 'parsing fail')
    for post in posts:
        appender(post, 'donutleaks')
        
def sparta():
    stdlog('parser: ' + 'sparta')
    parser = '''
    grep 'class="card-header d-flex justify-content-between"><span>' source/sparta-*.html | cut -d '>' -f 4 | cut -d '<' -f 1 | sed -e '/^[[:space:]]*$/d' && grep '<div class="card-header d-flex justify-content-between"><span>' source/sparta-*.html | grep -v '<h2>' | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('sparta: ' + 'parsing fail')
    for post in posts:
        appender(post, 'sparta')

def qilin():
    stdlog('parser: ' + 'qilin')
    # kbsq[...]faad.onion/api/public/blog/list
    # # jq '.[].target_utl' -r source/qilin-kb*.html || true
    # grep 'class="item_box-info__link"' source/qilin-kb*.html | cut -d '"' -f 2 | sed '/#/d'
    parser = '''
    grep '<a href="/site/view?uuid=' source/qilin-kbsq*.html | grep item_box | cut -d '<' -f 2 | cut -d '>' -f 2
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('qilin: ' + 'parsing fail')
    for post in posts:
        appender(post, 'qilin')

def shaoleaks():
    stdlog('parser: ' + 'shaoleaks')
    parser = '''
    grep '<h2 class="entry-title' source/shaoleaks-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('shaoleaks: ' + 'parsing fail')
    for post in posts:
        appender(post, 'shaoleaks')

def mallox():
    stdlog('parser: ' + 'mallox')
    # grep 'class="card-title"' source/mallox-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    parser = '''
    sed -n '/fs-3 fw-bold text-gray-900 mb-2/{n;s/^[[:space:]]*//;s/[[:space:]]*<\/div>.*$//p;}' source/mallox-*.html | sort -u
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('mallox: ' + 'parsing fail')
    for post in posts:
        appender(post, 'mallox')
    
def royal():
    stdlog('parser: ' + 'royal')
    parser = '''
    jq -r '.data[].url' source/royal-royal4ezp7xr*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('royal: ' + 'parsing fail')
    for post in posts:
        appender(post, 'royal')

def projectrelic():
    stdlog('parser: ' + 'projectrelic')
    parser = '''
    grep --no-filename '<div class="website">' source/projectrelic-*.html | cut -d '"' -f 4
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('projectrelic: ' + 'parsing fail')
    for post in posts:
        appender(post, 'projectrelic')

def ransomblog_noname():
    stdlog('parser: ' + 'ransomblog_noname')
    parser = '''
    grep --no-filename '<h2 class="entry-title default-max-width">' source/ransomblog_noname-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomblog_noname: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomblog_noname')
        
def medusa():
    stdlog('parser: ' + 'medusa')
    # cat source/medusa-medusaxko7*.html | jq -r '.list[].company_name' || true
    parser = '''
    cat source/medusa-xf*.html | jq -r '.list[].company_name' | perl -MHTML::Entities -ne 'print decode_entities($_)' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('medusa: ' + 'parsing fail')
    for post in posts:
        appender(post, 'medusa')

def nokoyawa():
    stdlog('parser: ' + 'nokoyawa')
    # awk '/<h1/{getline; print}' source/nokoyawa-*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    parser = '''
    jq -r '.payload[].title' source/nokoyawa-noko65rm*.html | sed 's/%20/ /g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('nokoyawa: ' + 'parsing fail')
    for post in posts:
        appender(post, 'nokoyawa')

def dataleak():
    stdlog('parser: ' + 'dataleak')
    parser = '''
    grep '<h2 class="post-title">' source/dataleak-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('dataleak: ' + 'parsing fail')
    for post in posts:
        appender(post, 'dataleak')

def monti():
    stdlog('parser: ' + 'monti')
    parser = '''
    grep '<h5 style="color:#dbdbdb" >' source/monti-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | grep -v test | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('monti: ' + 'parsing fail')
    for post in posts:
        appender(post, 'monti')

def play():
    stdlog('parser: ' + 'play')
    # %s --no-filename '(?<=\\"\\").*?(?=div)' source/play-*.html | tr -d '<>' | tr -d \\'
    parser = '''
    cat source/play-*.html | tr '>' '\n' | grep -A 1 'onclick="viewtopic' | grep -v 'click to open' | grep -v '\-\-' | cut -d '<' -f 1 | sort -u
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('play: ' + 'parsing fail')
    for post in posts:
        appender(post, 'play')

def karakurt():
    stdlog('parser: ' + 'karakurt')
    parser = '''
    grep '<a href="/companies/' source/karakurt-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e '/^[[:space:]]*$/d' -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('karakurt: ' + 'parsing fail')
    for post in posts:
        appender(post, 'karakurt')

def unsafeleak():
    stdlog('parser: ' + 'unsafeleak')
    parser = '''
    egrep -o "<h4>([A-Za-z0-9 ,\'.-])+</h4>" source/unsafeleak-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('unsafeleak: ' + 'parsing fail')
    for post in posts:
        appender(post, 'unsafeleak')

def freecivilian():
    stdlog('parser: ' + 'freecivilian')
    # grep "class=\\"a_href\\">" source/freecivilian-*.html |  sed 's/<[^>]*>//g; s/^[ \t]*//; s/[ \t]*$//; s/+ //;'
    parser = '''
    grep '<a class="a_href">' source/freecivilian-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('freecivilian: ' + 'parsing fail')
    for post in posts:
        appender(post, 'freecivilian')

def vendetta():
    stdlog('parser: ' + 'vendetta')
    parser = '''
    grep --no-filename '<a href="/company/' source/vendetta-*.html | cut -d '/' -f 3 | cut -d '"' -f 1 | sort --uniq | grep -v company
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('vendetta: ' + 'parsing fail')
    for post in posts:
        appender(post, 'vendetta')

def abyss():
    stdlog('parser: ' + 'abyss')
    parser = '''
    grep "'title'" source/abyss-*.html | cut -d "'" -f 4
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('abyss: ' + 'parsing fail')
    for post in posts:
        appender(post, 'abyss')

def moneymessage():
    stdlog('parser: ' + 'moneymessage')
    parser = '''
    cat source/moneymessage-*.html | jq -r 'map(select(.data.name != null) | .data.name) | join(" ")' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('moneymessage: ' + 'parsing fail')
    for post in posts:
        appender(post, 'moneymessage')

def dunghill_leak():
    stdlog('parser: ' + 'dunghill_leak')
    # awk '/<div class="ibody_title">/{print $0; getline; print $0}' source/dunghill_leak-*.html | sed -e 'N;s/\n//g' -e 's/<div class="ibody_title">//g' -e 's/<\/div>//g' -e 's/[[:space:]]*<\/a>.*$//g' -e 's/[[:space:]]\+/ /g' -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep -C 1 '<div class="ibody_title">' source/dunghill_leak-*.html | grep -v '</div>' | grep -v '<div class="ibody_title">' | grep -v '\-\-' | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | grep -v '</a>'
    parser = '''
    grep -C 3 '<div class="ibody_body">' source/dunghill_leak-*.html | grep strong | sed -E 's/.*<strong>([^<]+)<\/strong>.*/\\1/'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('dunghill_leak: ' + 'parsing fail')
    for post in posts:
        appender(post, 'dunghill_leak')

def trigona():
    stdlog('parser: ' + 'trigona')
    # awk -vRS='</a><a class="auction-item-info__external"' '{gsub(/.*<div class="auction-item-info__title"> <a href="[^"]*" title="">|<\/a>.*/,""); print}' source/trigona-*.html | grep -v href | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
    # grep -o -E '<a href="/leak/[0-9]+" title="">[^<]*' source/trigona-*.html | sed -E 's/<a href="\/leak\/[0-9]+" title="">//'
    # grep -o '<a [^>]*title="[^"]*"' source/trigona-*.html | grep 'path=' | cut -d '=' -f 3 | cut -d '"' -f 1
    # jq -r '.data.leaks[].external_link' source/trigona-trigonax2*.html || true
    parser = '''
    jq -r '.data.leaks[].external_link' source/trigona-krs*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('trigona: ' + 'parsing fail')
    for post in posts:
        appender(post, 'trigona')

def crosslock():
    stdlog('parser: ' + 'crosslock')
    parser = '''
    grep '<div class="post-date">' source/crosslock-*.html --no-filename | grep -o 'a href.*' | cut -d'>' -f2 | sed 's/<\/a//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('crosslock: ' + 'parsing fail')
    for post in posts:
        appender(post, 'crosslock')

def akira():
    stdlog('parser: ' + 'akira')
    # gsub used as title fields contain newlines
    parser = '''
    jq -j '.[] | .title |= gsub("\n"; " ") | .title, "\n"' source/akira-*.html | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('akira: ' + 'parsing fail')
    for post in posts:
        appender(post, 'akira')

def cryptnet():
    stdlog('parser: ' + 'cryptnet')
    parser = '''
    grep '<h3 class="blog-subject">' source/cryptnet-blog*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cryptnet: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cryptnet')

def ragroup():
    stdlog('parser: ' + 'ragroup')
    # grep --no-filename '<a href="/posts/' source/ragroup-*.html | cut -d '/' -f 3 | cut -d '"' -f 1
    # grep --no-filename '<div class="portfolio-content">' source/ragroup-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    parser = '''
    grep --no-filename '<div class="portfolio-content">' source/ragroup-*.html | grep -v PUBLISHED | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ragroup: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ragroup')

def eightbase():
    stdlog('parser: ' + '8base')
    # awk '/class="stretched-link">/{getline; print}' source/8base-*.html | sed -e 's/^[ \t]*//' | sort | uniq
    parser = '''
    awk '/class="stretched-link">/{getline; print}' source/8base-*.html | sed -e 's/^[ \t]*//' | perl -MHTML::Entities -ne 'print decode_entities(decode_entities($_))' | sort | uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('8base: ' + 'parsing fail')
    for post in posts:
        appender(post, '8base')

def malas():
    stdlog('parser: ' + 'malas')
    parser = '''
    grep '<a class="link" href=' source/malas-*.html  --no-filename | cut -d '>' -f2
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('malas: ' + 'parsing fail')
    for post in posts:
        appender(post, 'malas')

def blacksuit():
    stdlog('parser: ' + 'blacksuit')
    parser = "sed 's/>/>\\n/g' source/blacksuit-*.html | grep -A 1 '<div class=\"url\">' | grep href | cut -d '\"' -f 2"
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blacksuit: ' + 'parsing fail')
    for post in posts:  
        appender(post, 'blacksuit')

def rancoz():
    stdlog('parser: ' + 'rancoz')
    parser = '''
    grep -C 1 "<tr class='trow'>" source/rancoz-*.html | grep '<td>' | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('rancoz: ' + 'parsing fail')
    for post in posts:
        appender(post, 'rancoz')

def darkrace():
    stdlog('parser: ' + 'darkrace')
    parser = '''
    egrep -o '<a class="post-title-link" href="/[^"]+">[^<]+' source/darkrace-*.html | cut -d'>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('darkrace: ' + 'parsing fail')
    for post in posts:
        appender(post, 'darkrace')

def rhysida():
    stdlog('parser: ' + 'rhysida')
    parser = '''
    grep "m-2 h4" source/rhysida-* | cut -d '>' -f 3 | cut -d '<' -f 1 
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('rhysida: ' + 'parsing fail')
    for post in posts:
        appender(post, 'rhysida')
        
def noescape():
    stdlog('parser: ' + 'noescape')
    # grep -oe "target=\\"_blank\\">[^<]*" source/noescape*wzttad.html | cut -d'>' -f2
    parser = '''
    grep -o '<a[^>]*title="[^"]*"[^>]*>' source/noescape-*wzttad.html | sed -e 's/<a[^>]*title="//' -e 's/".*//' | awk -F'"' '{print $1}' | awk -F'"' '!/Twitter/{print $1}'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('noescape: ' + 'parsing fail')
    for post in posts:
        appender(post, 'noescape')

def cactus():
    stdlog('parser: ' + 'cactus')
    parser = '''
    %s '<a .*? href=".*?/posts/.*?".*?</h2></a>' source/cactus-*.html | %s '<h2.*?>(.*?)</h2>' | cut -d'>' -f2 | cut -d'<' -f1
    ''' % (fancygrep, fancygrep)
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cactus: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cactus')

def knight():
    stdlog('parser: ' + 'knight')
    # jq -r '.pages[].name' source/knight-knight3xppu*.html || true
    parser = '''
    jq -r '.posts[].title' source/knight-knight3*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('knight: ' + 'parsing fail')
    for post in posts:
        appender(post, 'knight')

def incransom():
    stdlog('parser: ' + 'incransom')
    # jq -r '.payload[].title' source/incransom-incback*.html | sed -e 's/%20/ /' || true
    parser = '''
    jq -r '.payload[].title' source/incransom-incbackrlasjes*.html | perl -MURI::Escape -ne 'print uri_unescape($_)' | sort | uniq || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('incransom: ' + 'parsing fail')
    for post in posts:
        appender(post, 'incransom')

def metaencryptor():
    stdlog('parser: ' + 'metaencryptor')
    parser = '''
    grep '<a class="btn btn-secondary btn-sm" href="' source/metaencryptor-*.html | cut -d '>' -f 18 | grep btn-sm | cut -d '"' -f 4
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('metaencryptor: ' + 'parsing fail')
    for post in posts:
        appender(post, 'metaencryptor')

def cloak():
    stdlog('parser: ' + 'cloak')
    parser = '''
    grep '<h2 class="main__name">' source/cloak-cloak7jp*.html --no-filename | cut -d ">" -f2 | cut -d '<' -f 1 && grep --no-filename -A 1 '<div class="card-body">' source/cloak-cloak.html | grep '<p class="card-text">' | cut -d '>' -f 2 | cut -d '<' -f 1 | grep -v test || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cloak: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cloak')

def ransomedvc():
    stdlog('parser: ' + 'ransomedvc')
    # grep -A 1 '<div class="card">' source/ransomedvc-f6amq3izz*.html | grep '<b><u>' | cut -d '>' -f 3 | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//'
    # grep 'class="alignwide wp-block-post-title' source/ransomedvc-f6amq3*ad.html | cut -d '>' -f 4 | cut -d '<' -f 1
    # grep --no-filename -A 1 '<div class="card">' source/ransomedvc-*.html | grep '#ff5353' | cut -d '>' -f 3 | cut -d '<' -f 1 | sort | uniq
    parser = '''
    grep --no-filename '<b><u>' source/ransomedvc-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 | sort -u
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomedvc: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomedvc')

def ciphbit():
    stdlog('parser: ' + 'ciphbit')
    parser = '''
    grep '<h2><a class="title"' source/ciphbit-*.html | cut -d '"' -f 4
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ciphbit: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ciphbit')

def threeam():
    stdlog('parser: ' + 'threeam')
    # grep -A 1 '<div class="p ost-title-block">' source/threeam-*.html | grep '<div>' | cut -d '>' -f 2 | cut -d '<' -f 1
    # cat source/threeam-*.html | awk '{while (match($0, /<div id="post-title" class="post-title f_left">[^<]+<\/div>/)) {print substr($0, RSTART, RLENGTH); $0 = substr($0, RSTART + RLENGTH); fflush()}}' | cut -d '>' -f 2 | cut -d '<' -f 1
    parser = '''
    perl -lne 'while(/<div id="post-title" class="post-title f_left">([^<]+)<\/div>/g) { print $1 }' source/threeam-*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('threeam: ' + 'parsing fail')
    for post in posts:
        appender(post, 'threeam')

def cryptbb():
    stdlog('parser: ' + 'cryptbb')
    parser = '''
    grep -A 1 'class="stretched-link">' source/cryptbb-*.html | grep -v '<a href="' | grep -v '\-\-' | sed -e '/^[[:space:]]*$/d' -e 's/^ *//g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cryptbb: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cryptbb')

def losttrust():
    stdlog('parser: ' + 'losttrust')
    parser = '''
    grep -o '<div class="card-header">[^<]*</div>' source/losttrust-*.html  | sed -e 's/<[^>]*>//g' -e 's/&amp;/\&/g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('losttrust: ' + 'parsing fail')
    for post in posts:
        appender(post, 'losttrust')

def hunters():
    stdlog('parser: ' + 'hunters')
    parser = '''
    jq -r '.[].title' source/hunters-hunters55*.html | sort -u || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('hunters: ' + 'parsing fail')
    for post in posts:
        appender(post, 'hunters')

def meow():
    stdlog('parser: ' + 'meow')
    parser = '''
    jq -r '.data[].title' source/meow-totos*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('meow: ' + 'parsing fail')
    for post in posts:
        appender(post, 'meow')

def dragonforce():
    stdlog('parser: ' + 'dragonforce')
    # grep -o 'href="https://[^"]*' source/dragonforce-*.html | sed 's/href="//'
    parser = '''
    cat source/dragonforce-z3wqggtxft*.html | jq ".data.publications.[].site" -r || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('dragonforce: ' + 'parsing fail')
    for post in posts:
        appender(post, 'dragonforce')
  
def werewolves():
    stdlog('parser: ' + 'werewolves')
    parser = '''
    grep --no-filename '<!-- </a> -->' source/werewolves-*.html | cut -d '<' -f 1 | sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort | uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('werewolves: ' + 'parsing fail')
    for post in posts:
        appender(post, 'werewolves')

def malekteam():
    stdlog('parser: ' + 'malekteam')
    parser = '''
    grep --no-filename '<div class="timeline_date-text"><span class="text-danger">' source/malekteam-*.html | cut -d '>' -f 4 | cut -d '<' -f 1 |  sed -e 's/^ *//g' -e 's/[[:space:]]*$//' | sort | uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('malekteam: ' + 'parsing fail')
    for post in posts:
        appender(post, 'malekteam')
        
def insane():
    stdlog('parser: ' + 'insane')
    parser = '''
    grep --no-filename 'class="button button2"' source/insane-*.html | cut -d '>' -f 5 | cut -d '<' -f 1 | sort | uniq | grep -Ev 'A black man|Going Insane Ransomware Main page|Cat'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('insane: ' + 'parsing fail')
    for post in posts:
        appender(post, 'insane')

def slug():
    stdlog('parser: ' + 'slug')
    parser = '''
    grep ' <title type="html">' source/slug-*.html | cut -d '[' -f 3 | cut -d ']' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('slug: ' + 'parsing fail')
    for post in posts:
        appender(post, 'slug')
        
def ransomblog_noname2():
    stdlog('parser: ' + 'ransomblog_noname2')
    parser = '''
    cat source/ransomblog_noname2-*.html | tr '>' '\n' | grep -A 2 'target="_self" rel="bookmark noopener noreferrer"' | grep -Ev '.onion/wp/|\[NEGOTIATED\]</a|</h4|\-\-' | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomblog_noname2: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomblog_noname2')

def alphalocker():
    stdlog('parser: ' + 'alphalocker')
    # grep '<a href="blog_1-11"' source/alphalocker-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | grep -v Read || true
    parser = '''
    grep '<div class="news_title" style="display:inline-block; width:100%;">' -C 2 source/alphalocker-mydatae2d*.html | grep '<a href="blog_1' | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('alphalocker: ' + 'parsing fail')
    for post in posts:
        appender(post, 'alphalocker')

def ransomhub():
    stdlog('parser: ' + 'ransomhub')
    # grep '<h5 class="card-title">' source/ransomhub-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 | perl -MHTML::Entities -ne 'print decode_entities($_)'
    parser = '''
    grep '<div class="card-title text-center">' source/ransomhub-ransomxifxw*.html | cut -d '>' -f 3 | cut -d '<' -f 1 && grep '<tr><td class="link">' source/ransomhub-fp*.html | cut -d '"' -f 4 | sort --uniq
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomhub: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomhub')

def mogilevich():
    stdlog('parser: ' + 'mogilevich')
    parser = '''
    grep '<h3>' source/mogilevich-*.html -A 1 | grep 'style="color: white;' | cut -d '"' -f 2
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('mogilevich: ' + 'parsing fail')
    for post in posts:
        appender(post, 'mogilevich')

def blackout():
    stdlog('parser: ' + 'blackout')
    parser = '''
    grep -oE '<a[^>]*class="[^"]*link-offset-2 link-underline link-underline-opacity-0 text-white[^"]*"[^>]*>[^<]+</a>' source/blackout-*.html | sed -E 's/.*>([^<]+)<\/a>/\\1/'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('blackout: ' + 'parsing fail')
    for post in posts:
        appender(post, 'blackout')

def donex():
    stdlog('parser: ' + 'donex')
    parser = '''
    grep '<a class="post-title"' source/donex-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | tr '[:upper:]' '[:lower:]' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('donex: ' + 'parsing fail')
    for post in posts:
        appender(post, 'donex')

def killsecurity():
    stdlog('parser: ' + 'killsecurity')
    parser = '''
    grep '<div class="post-title">' source/killsecurity-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('killsecurity: ' + 'parsing fail')
    for post in posts:
        appender(post, 'killsecurity')

def redransomware():
    stdlog('parser: ' + 'redransomware')
    parser = '''
    grep '<h4 class="card-header">' source/redransomware-*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('redransomware: ' + 'parsing fail')
    for post in posts:
        appender(post, 'redransomware')

def darkvault():
    stdlog('parser: ' + 'darkvault')
    parser = '''
    cat source/darkvault-*.html | awk 'BEGIN{RS="<div class=\\"post-title\\">"; FS="</div>"} NR>1 {print $1}' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('darkvault: ' + 'parsing fail')
    for post in posts:
        appender(post, 'darkvault')

def hellogookie():
    stdlog('parser: ' + 'hellogookie')
    parser = '''
    awk '/<h5 class="card-title">/{getline; gsub(/^[[:space:]]+|[[:space:]]+$/, ""); print}' source/hellogookie-*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('hellogookie: ' + 'parsing fail')
    for post in posts:
        appender(post, 'hellogookie')

def apt73():
    stdlog('parser: ' + 'apt73')
    parser = '''
    grep "class='segment__text__off'" source/apt73-*.html | sed -n "s/.*<div class='segment__text__off'>\([^<]*\)<\/div.*/\\1/p"
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('apt73: ' + 'parsing fail')
    for post in posts:
        appender(post, 'apt73')

def qiulong():
    stdlog('parser: ' + 'qiulong')
    parser = '''
    grep '<h1 class="entry-title">' source/qiulong-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('qiulong: ' + 'parsing fail')
    for post in posts:
        appender(post, 'qiulong')

def embargo():
    stdlog('parser: ' + 'embargo')
    parser = '''
    awk 'BEGIN{RS="<div class=\\"text-2xl font-bold\\">"; FS="</div>"} NR>1 {print $1}' source/embargo-embargobe*.html || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('embargo: ' + 'parsing fail')
    for post in posts:
        appender(post, 'embargo')

def dAn0n():
    stdlog('parser: ' + 'dAn0n')
    # '<h2 class="card-title">'
    # grep '<h4 class="card-title">' source/dAn0n-2c7nd*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | perl -MURI::Escape -ne 'print uri_unescape($_)' | perl -MURI::Escape -ne 'print uri_unescape($_)'
    parser = '''
    grep '<h6 class="card-title"' source/dAn0n-2c7nd*.html | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('dAn0n: ' + 'parsing fail')
    for post in posts:
        appender(post, 'dAn0n')

def underground():
    stdlog('parser: ' + 'underground')
    parser = '''
    grep -A 1 '<span>Name: </span>' source/underground-*.html | grep '<p>' | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('underground: ' + 'parsing fail')
    for post in posts:
        appender(post, 'underground')

def spacebears():
    stdlog('parser: ' + 'spacebears')
    parser = '''
    grep href source/spacebears-*.html | grep '.onion/companies/' | cut -d '>' -f 2 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('spacebears: ' + 'parsing fail')
    for post in posts:
        appender(post, 'spacebears')

def flocker():
    stdlog('parser: ' + 'flocker')
    parser = '''
    grep '<h2 class="entry-title ast-blog-single-element"' source/flocker-flock*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('flocker: ' + 'parsing fail')
    for post in posts:
        appender(post, 'flocker')

def arcusmedia():
    stdlog('parser: ' + 'arcusmedia')
    parser = '''
    grep '<h2 class="entry-title mb-half-gutter last:mb-0">' source/arcusmedia-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('arcusmedia: ' + 'parsing fail')
    for post in posts:
        appender(post, 'arcusmedia')

def trinity():
    stdlog('parser: ' + 'trinity')
    parser = '''
    grep -A 1 '<strong>Company name:</strong>' source/trinity-*.html | grep -v '<strong>' | grep -v '<p>' | grep -v -- '--' | sed -e 's/^ *//g'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('trinity: ' + 'parsing fail')
    for post in posts:
        appender(post, 'trinity')

def sensayq():
    stdlog('parser: ' + 'sensayq')
    parser = '''
    grep '<div class="cls_recordTop">' source/sensayq-*.html | cut -d '>' -f 3 | cut -d '<' -f 1
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('sensayq: ' + 'parsing fail')
    for post in posts:
        appender(post, 'sensayq')

def cicada3301():
    stdlog('parser: ' + 'cicada3301')
    parser = '''
    grep -C 1 'tracking-widest">web:</span>' source/cicada3301-*.html | grep href | cut -d '"' -f 2
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('cicada3301: ' + 'parsing fail')
    for post in posts:
        appender(post, 'cicada3301')

def pryx():
    stdlog('parser: ' + 'pryx')
    parser = '''
    grep '<td><a href="' source/pryx-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 | sed 's/\[\*\] //g' | grep -v soon || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('pryx: ' + 'parsing fail')
    for post in posts:
        appender(post, 'pryx')

def braincipher():
    stdlog('parser: ' + 'braincipher')
    parser = '''
    grep 'class="h5">' source/braincipher-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 | sort -u | sed '/More important than money, only honor./d' | sed '/Space for your advertising./d' | sed '/Very expensive advertising./d'
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('braincipher: ' + 'parsing fail')
    for post in posts:
        appender(post, 'braincipher')

def FOG():
    stdlog('parser: ' + 'FOG')
    parser = '''
    grep '<p class="pb-4 text-lg font-bold">' source/FOG-*.html | cut -d '>' -f 10 | cut -d '<' -f 1 | grep -v 00 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('FOG: ' + 'parsing fail')
    for post in posts:
        appender(post, 'FOG')
        
def handala():
    stdlog('parser: ' + 'handala')
    parser = '''
    grep '<h2 class="wp-block-post-title">' source/handala-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('handala: ' + 'parsing fail')
    for post in posts:
        appender(post, 'handala')

def eldorado():
    stdlog('parser: ' + 'eldorado')
    parser = '''
    grep '<h1 class="text-xl mb-2 text-decoration-underline">' source/eldorado-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('eldorado: ' + 'parsing fail')
    for post in posts:
        appender(post, 'eldorado')

def vanirgroup():
    stdlog('parser: ' + 'vanirgroup')
    parser = '''
    grep '</pre></p></div><p data-v-' source/vanirgroup-*.html | awk 'match($0, /projectName:"[^"]+"/) {while (match($0, /projectName:"[^"]+"/)) {print substr($0, RSTART+13, RLENGTH-14); $0 = substr($0, RSTART+RLENGTH)}}' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('vanirgroup: ' + 'parsing fail')
    for post in posts:
        appender(post, 'vanirgroup')

def ransomcortex():
    stdlog('parser: ' + 'ransomcortex')
    parser = '''
    grep '<h2 class="entry-title">' source/ransomcortex-*.html | cut -d '>' -f 3 | cut -d '<' -f 1 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('ransomcortex: ' + 'parsing fail')
    for post in posts:
        appender(post, 'ransomcortex')

def madliberator():
    stdlog('parser: ' + 'madliberator')
    parser = '''
    grep '<span class="blog-cat">' source/madliberator-*.html | cut -d '>' -f 2 | cut -d '<' -f 1 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('madliberator: ' + 'parsing fail')
    for post in posts:
        appender(post, 'madliberator')

def dispossessor():
    stdlog('parser: ' + 'dispossessor')
    parser = '''
    cat source/dispossessor-e27z5*.html | jq '.data.items[].company_name' -r || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('dispossessor: ' + 'parsing fail')
    for post in posts:
        appender(post, 'dispossessor')

def nullbulge():
    stdlog('parser: ' + 'nullbulge')
    parser = '''
    grep '<div class="elem">' -A1 source/nullbulge-nullbulge.html | grep '<h6 class="hacked__font">' | cut -d '>' -f 2 | cut -d '<' -f 1 || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('nullbulge: ' + 'parsing fail')
    for post in posts:
        appender(post, 'nullbulge')

def lynxblog():
    stdlog('parser: ' + 'lynxblog')
    parser = '''
    jq -r '.payload.announcements[].company.company_name' source/lynx-lynxblog.html | perl -MURI::Escape -ne 'print uri_unescape($_)' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('lynxblog: ' + 'parsing fail')
    for post in posts:
        appender(post, 'lynxblog')

def helldown():
    stdlog('parser: ' + 'helldown')
    parser = '''
    grep '<p class="card-summary">' source/helldown*.html | sed -e 's/<[^>]*>//g' -e 's/^[ \t]*//' | grep -v 'password is required to continue reading.' || true
    '''
    posts = runshellcmd(parser)
    if len(posts) == 1:
        errlog('helldown: ' + 'parsing fail')
    for post in posts:
        appender(post, 'helldown')
