#! python3

import mysql
import mysql.connector

# used to connect to database
db_config = {
  'user'     : 'username',
  'password' : 'password',
  'host'     : 'database.url.com',
  'database' : 'database_name'
}

# all session data is stored in here
class Session():
    def __init__(self):
        self.logged_in = False
        self.username = None          # set when user logs in
        self.user_id = None           # set when user logs in
        self.thread_id = None         # set when user opens a thread
        self.thread_title = None      # set when user opens a thread
        self.viewing_user_id = None   # set when user is viewing a user profile
        self.viewing_user_name = None # set when user is viewing a user profile
        self.db_con = None            # stores the current connection to the db
        self.db_cur = None            # stores the db cursur

session = Session() # the current user session

def init_db_connection():
    ''' connects to database and sets up session variable '''
    con = mysql.connector.connect(**db_config)
    session.db_con = con
    session.db_cur = con.cursor()

def header(title):
    ''' pretty prints a title for each screen '''
    user = session.username
    greeting = "Logged In: " + user if user else "Not Logged In"
    print("{:-^40}-{:-^25}-".format(title, greeting))

def notify_user(msg=""):
    ''' prints the given message and waits for user to press enter '''
    input("{} (Enter to Continue)".format(msg))

def logout():
    ''' logs the user out of this session '''
    notify_user("Logging Out")
    session.username = None
    session.logged_in = False
    return ['main', 'logged out']

def log_user_in(username, user_id):
    ''' logs user into this session '''
    notify_user('Welcome {}'.format(username))
    session.logged_in = True
    session.username = username
    session.user_id = user_id

def login():
    ''' lets the user log in '''
    header("Login")
    username = input("Enter Username: ")
    query = "select U.uid, U.name from User as U where U.name = %s limit 1;"
    session.db_cur.execute(query, (username,))
    
    result = list(session.db_cur)
    if len(result) > 0:
        uid, name = result[0]
        log_user_in(username, uid)
        return ['main', 'logged in']
    else:
        notify_user("That username is not registered, maybe create a new account?")
        return ['main', 'logged out']

def create_account():
    ''' Allows a user to create an account '''
    
    header("Create Account")
    username = input("Enter Username: ")
    query = "select U.name from User as U where U.name = %s limit 1;"
    session.db_cur.execute(query, (username,))
    result = list(session.db_cur)
    if len(result) > 0:
        notify_user('Sorry this username is taken, try logging in with this username')
        return ['main', 'logged out']
    else:
        query = "insert into User (name) values (%s);"
        session.db_cur.execute(query, (username,))
        log_user_in(username, session.db_cur.lastrowid)
        session.db_con.commit()
        return ['main', 'logged in']

def show_thread_list(thread_list):
    ''' Pretty prints the given data '''
    
    seen = set()
    pruned = []
    for (tid, title, upvotes) in thread_list:
        if title not in seen:
            pruned.append((tid, title, upvotes))
            seen.add(title)
            
    print("{:^3} | {:^7} | {}".format("ID", "Upvotes", "Text"))
    for (tid, title, upvotes) in pruned:
        print("{:^3} | {:^7} | {}".format(tid, upvotes, title))

def show_top_threads():
    ''' Display threads sorted by upvotes '''
    header("Top Threads")
    query = ("select T.thread_id, T.title, T.upvotes "
             "from Thread as T order by T.upvotes desc")
    session.db_cur.execute(query)
    result = list(session.db_cur)
    show_thread_list(result)
    notify_user()
    return ['main', 'logged in']

def show_threads_with_artist():
    ''' Display Threads with art created by an artist '''
    header("Find Threads With Artist")
    artist = input("Which artist? : ")
    query = ("select T.thread_id, T.title, T.upvotes "
             "from Thread as T, Artist as A, Art "
             "where T.art_id_topic = Art.art_id and "
             "Art.artist_id = A.artist_id and "
             "A.name = %s")
    
    session.db_cur.execute(query, (artist,))
    result = list(session.db_cur)
    if len(result) == 0:
        notify_user("Sorry there are no threads with that artist :(")
    else:
        show_thread_list(result)
        notify_user()
    return ['main', 'logged in']

def show_newest_threads():
    ''' Display the thread sorted by art creation date '''
    header("Newest Art Thread")
    query = ("select T.thread_id, T.title, T.upvotes "
             "from Thread as T, Art "
             "where T.art_id_topic = Art.art_id "
             "order by Art.date desc;")
    
    session.db_cur.execute(query)
    result = list(session.db_cur)
    show_thread_list(result)
    notify_user()
    return ['main', 'logged in']

def insert_new_artist():
    ''' Allows a user to define and insert a new artist '''
    artist = input("Artist Name: ")
    birth_date = input("artist birth date? (YYYY-MM-DD): ")
    death_date = input("artist death date? (YYYY-MM-DD or NULL alive): ")
    
    if death_date == 'NULL':
        death_date = None
        
    portrait_url = input("artist portrait url: ")

    query = ("insert into Artist (name, birth_date, death_date, portrait_url) "
             "values (%s, %s, %s, %s);")

    session.db_cur.execute(query,
                           (artist, birth_date, death_date, portrait_url))
    session.db_con.commit()
    return session.db_cur.lastrowid

def insert_new_art():
    ''' Allows a user to define a new art piece '''
    art_piece = input("Art Piece Title: ")
    creation_date = input("When was this piece created? (YYYY-MM-DD or NULL): ")
    if creation_date == 'NULL':
        creation_date = None
        
    img_url = input("image url: ")
    
    new_artist = input("Is this a new artist? (Y/N): ")
    if new_artist.lower() == 'y':
        artist_id = insert_new_artist()
    else:
        # We iterate through existing artists and allow the user to choose
        query = "select A.artist_id, A.name from Artist as A;"
        session.db_cur.execute(query)
        for (aid, name) in list(session.db_cur):
            choice = input("Is this the artist? {} (Y/N):".format(name))
            if choice.lower() == 'y':
                artist_id = aid
                break
        else:
            notify_user("I guess it's a new artist... ")
            artist_id = insert_new_artist()

    query = ("insert into Art (title, date, img_url, artist_id) "
             "values (%s, %s, %s, %s);")
    session.db_cur.execute(query,
                           (art_piece, creation_date, img_url, artist_id))
    session.db_con.commit()
    return session.db_cur.lastrowid

def make_thread():
    ''' Allows users to create a new thread '''
    header("Create Thread")
    title = input("Thread Title: ")
    new_art = input("Is this a new art piece? (Y/N): ")
    
    if new_art.lower() == 'y':
        art_id = insert_new_art()
    else:
        # We iterate through existing art pieces until user selects one
        session.db_cur.execute("select A.art_id, A.title from Art as A")
        for (aid, art_title) in list(session.db_cur):
            choice = input("Is this the art piece? {} (Y/N):".format(art_title))
            if choice.lower() == 'y':
                art_id = aid
                break
        else:
            notify_user("I guess it's a new art piece... ")
            art_id = insert_new_art()

    query = ("insert into Thread "
             "(title, upvotes, art_id_topic, thread_creator_id) "
             "values (%s, 0, %s, %s)")
    session.db_cur.execute(query, (title, art_id, session.user_id))
    session.db_con.commit()
    notify_user('Thread Created!')
    return ['main', 'logged in']

def open_thread():
    ''' Allows user to open a thread to view comments and metadata '''
    header("Open Thread")
    tid = input("thread id: ")
    query = "select T.title from Thread as T where T.thread_id = %s"
    session.db_cur.execute(query, (tid,))
    result = list(session.db_cur)
    if len(result) == 0:
        notify_user("There is no thread with that id")
        return ['main', 'logged in']
    else:
        session.inside_thread = True
        session.thread_id = tid
        session.thread_title = result[0][0]
        return ['main', 'logged in', 'open thread']

def show_thread_art():
    ''' Displays the art being discussed in the current open thread '''
    header("Thread Art")
    query = ("Select A.title from Thread as T, Art as A "
             "where T.thread_id = %s and T.art_id_topic = A.art_id")
    session.db_cur.execute(query, (session.thread_id,))
    result = list(session.db_cur)
    notify_user(result[0][0])
    return ['main', 'logged in', 'open thread']

def show_thread_artist():
    ''' Displays the artist that created the art being discussed in the current open thread '''
    header("Thread Artist")
    query = ("Select A.name from Thread as T, Art, Artist as A "
             "where T.thread_id = %s and T.art_id_topic = Art.art_id "
             "and A.artist_id = Art.artist_id")
    session.db_cur.execute(query, (session.thread_id,))
    result = list(session.db_cur)
    notify_user(result[0][0])
    return ['main', 'logged in', 'open thread']
    pass

def show_top_comments_in_thread():
    ''' Display comments in thread sorted by votes '''
    header("Comments")
    query = ('Select C.comment_id, C.text, C.upvotes '
             'from Thread as T, Comment as C '
             'where T.title = %s and T.thread_id = C.thread_id '
             'order by C.upvotes desc;')
    session.db_cur.execute(query, (session.thread_title,))
    result = list(session.db_cur)
    show_thread_list(result)
    notify_user()
    return ['main', 'logged in', 'open thread']

def update_votes(amount):
    ''' updates the upvotes of the open thread by the given amount '''
    header("Upvoting!")
    query = 'select T.upvotes from Thread as T where T.thread_id = %s;'
    session.db_cur.execute(query, (session.thread_id,))
    result = list(session.db_cur)
    upvotes = result[0][0]
    updated = upvotes + amount
    query = "update Thread set upvotes=%s where Thread.thread_id = %s"
    session.db_cur.execute(query, (updated, session.thread_id))
    session.db_con.commit()
    notify_user("upvote count is now {}".format(updated))

def upvote_thread():
    ''' Upvote the open thread '''
    update_votes(1)
    return ['main', 'logged in', 'open thread']

def downvote_thread():
    ''' Downvote the open thread '''
    update_votes(-1)
    return ['main', 'logged in', 'open thread']

def leave_thread():
    ''' Leave the current thread '''
    session.inside_thread = False
    session.thread_id = None
    session.thread_title = None
    return ['main', 'logged in']

def show_user():
    ''' Allows user to open a user profile '''
    header("User")
    user = input("Enter a user name: ")
    
    query = "select U.uid, U.name from User as U where U.name = %s;"
    session.db_cur.execute(query, (user,))
    result = list(session.db_cur)
    if len(result) == 0:
        print("there is no user with that name")
        return ['main', 'logged in']
    else:
        uid, uname = result[0]
        session.viewing_user_id = uid
        session.viewing_user_name = uname
        return ['main', 'logged in', 'view user']
        

def show_comments_by_user():
    ''' Show comments by the user currently being viewed '''
    query = ('Select C.comment_id, C.text, C.upvotes from Comment as C '
             'where C.poster_id = %s order by C.upvotes desc')

    session.db_cur.execute(query, (session.viewing_user_id,))
    result = list(session.db_cur)
    show_thread_list(result)
    notify_user()
    return ['main', 'logged in', 'view user']

def show_posts_by_user():
    ''' Show threads by the user currently being viewed ''' 
    query = ('Select T.thread_id, T.title, T.upvotes from Thread as T '
             'where T.thread_creator_id = %s order by T.upvotes desc')

    session.db_cur.execute(query, (session.viewing_user_id,))
    result = list(session.db_cur)
    show_thread_list(result)
    notify_user()
    return ['main', 'logged in', 'view user']

def leave_user():
    ''' leave the currently viewed user profile '''
    session.viewing_user_id = None
    session.viewing_user_name = None
    return ['main', 'logged in']
    

# Here we define the menu structure
menu = {
    "main" : {
        "logged in" : {
            "Show Top Threads" : {'action': show_top_threads },
            "Show Threads With Artist" : {"action" : show_threads_with_artist},
            "Show Newest Threads" : { "action" : show_newest_threads },
            "make thread" : { "action" : make_thread },
            "logout" : {"action" : logout },
            "open thread" : {
                "action" : open_thread,
                "Show Art" : { "action" : show_thread_art },
                "Show Artist" : { "action" : show_thread_artist }, 
                "Show Top Comments" : {"action" : show_top_comments_in_thread},
                "upvote thread" : { "action" : upvote_thread },
                "downvote thread" : { "action" : downvote_thread },
                "leave thread" : {"action" : leave_thread }
            },
            "view user" : {
                "action" : show_user,
                "show comments by user" : {'action' : show_comments_by_user},
                "show posts by this user" : { 'action' : show_posts_by_user },
                "leave user" : { 'action' : leave_user }
            }
        },
        "logged out" : {
            "login" : { "action" : login },
            "create account" : { "action" : create_account }
        }
    }
}

def print_choice(index, name):
    ''' Pretty prints a choice with it's index '''
    print("("+str(index)+")", name)

def prompt_user(choices):
    ''' Prompts user for a choice '''
    header("Available Actions")
    for i, key in enumerate(choices):
        print_choice(i, key)
    print()
    print_choice(len(choices), "quit")
    print()
    choice_string = input("Enter Choice: ")

    try:
        choice = int(choice_string)
    except ValueError as e:
        print("Invalid Choice")
        return get_action(path)
        
    
    if choice == len(choices): # chose to exit
        cleanup_and_exit();
    
    if not (0 <= choice <= len(choices)):
        print("Invalid Choice")
        return get_action(path)
    
    return choice

def follow_menu_path(path):
    ''' Follows the path in the menu structure '''
    m = menu
    for p in path:
        m = m[p]
    return m

def get_action(path = ["main"]):
    ''' Retrieves the action function from the menu structure  defined by the path '''
    
    m = follow_menu_path(path)
    choices = []
    for c in sorted(list(m)):
        if c != 'action':
            choices.append(c)

    choice = prompt_user(choices)
    
    chosen_item = choices[choice]
    action = m[chosen_item]['action']
    return action

def cleanup_and_exit():
    ''' Closes active db connections and cursors and exits '''
    print("Goodbye!")
    if session.db_con:
        session.db_con.commit()
        session.db_con.close()
    if session.db_cur:
        session.db_cur.close()
    exit()

def main():
    init_db_connection()

    path = ['main']
    while path[-1] != 'quit':
        if not session.logged_in:
            path = ['main', 'logged out']
        
        action = get_action(path)
        path = action()
    cleanup_and_exit()

if __name__ == "__main__":
    main()
