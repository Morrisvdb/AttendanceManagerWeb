from flask import request, render_template, make_response, redirect, url_for, abort, g, session, jsonify
from flask_babel import _
from user_agents import parse
from main.__init__ import app, API_URL
import requests
from functools import wraps
import datetime
import re
import base64


# TODO: Improve error handeling. --> not 404.html for everything :facepalm:

def get_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        AuthKey = request.cookies.get("Authorization")
        headers = {"Authorization": AuthKey}
        r = requests.get(API_URL+"/user", headers=headers)
        
        
        if r.status_code == 200:
            return f(*args, **kwargs, user = r.json()['user'], key = AuthKey)
        else:
            return f(*args, **kwargs, user = None, key = None)

    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        AuthKey = request.cookies.get("Authorization")
        headers = {"Authorization": AuthKey}
        auth_request = requests.get(API_URL+"/user", headers=headers)
        
        
        if auth_request.status_code == 200:
            return f(*args, **kwargs)
        else:
            return render_template('login_required.html')

    return decorated_function

# Share the device type with jinja
@app.before_request
def detect_device():
    ua_string = request.headers.get('User-Agent', '')
    ua = parse(ua_string)
    g.device = {
        'is_mobile': ua.is_mobile,
        'is_tablet': ua.is_tablet,
        'is_pc': ua.is_pc,
        'browser': ua.browser.family,
        'os': ua.os.family,
    }

@app.context_processor
def inject_device():
    return {'device': getattr(g, 'device', {})}

# Help prevent the annoying flicker that happens when the js loads the theme after DOM load
@app.context_processor
def inject_theme():
    theme = request.cookies.get("theme", "light")
    return {"theme": theme}

@app.errorhandler(400)
def bad_request(e):
    return render_template('400.html')

@app.errorhandler(401)
def not_found(e):
    return render_template("401.html")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")

@app.errorhandler(409)
def not_found(e):
    return render_template("409.html")


@app.route("/")
@get_user
def home(user, key):
    return render_template("home.html", user=user)

@app.route('/locale/<string:locale>', methods=['POST'])
@get_user
def change_locale(user, key, locale):
    """Changes the locale of the current browser to the given string. 
    If the user is logged in it will also add the locale to their profile

    Args:
        locale (string): The locale to change to. Is of app config BABEL_SUPPORTED_LOCALES
    """
    if locale not in app.config['BABEL_SUPPORTED_LOCALES']:
        return abort(400)
            
    if user is None:
        resp = make_response()
        resp.set_cookie('locale', locale)
        return resp
    
    headers = {"Authorization": key}
    
    user_put_request = requests.post(API_URL+"/user", headers=headers, json={"locale": locale})
    if user_put_request.status_code != 200:
        return abort(user_put_request.status_code)
    
    return {'status': 'ok'}, 200

@app.route('/theme/toggle', methods=['POST'])
@get_user
def toggle_theme(user, key):
    current_theme = request.cookies.get('theme')
    new_theme = "light" if current_theme == 'dark' else "dark"
    
    resp = make_response()
    resp.set_cookie('theme', new_theme)
    return resp
    
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if not(username and password1 and password2 and email):
            return render_template('signup.html', error=_("Missing arguments"))

        if password1 != password2:
            return render_template('signup.html', error=_("Passwords do not match"))

        json = {
            "username": username,
            "email": email,
            "password": password1
        }
        signup_request = requests.post(API_URL + "/signup", json=json)
        if signup_request.status_code == 201:
            return redirect(url_for('login'))
        elif signup_request.status_code == 400:
            return render_template('signup.html', error=_("Invalid Email"))
        elif signup_request.status_code == 409:
            return render_template('signup.html', error=_("Username already in use"))
        elif signup_request.status_code == 422:
            return render_template('signup.html', error=_("Malformed request"))
        else:
            return abort(signup_request.status_code)
            
    
    return render_template("signup.html")

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        json = {
            "username": username,
            "password": password
        }
        login_request = requests.post(API_URL + "/login", json=json)
        if login_request.status_code == 200:
            if 'key' in login_request.json():
                key = login_request.json()['key']
            else:
                return render_template('login.html', error="Unexpected response from server.")
            url = url_for('home')
            resp = make_response(redirect(url))
            resp.set_cookie('Authorization', key)
            return resp
        elif login_request.status_code == 404 or login_request.status_code == 401:
            return render_template('login.html', error="Password or Username incorrect.")
        else:
            return render_template('login.html')
    
    return render_template("login.html")

# TODO: Logout route
@app.route("/logout")
@login_required
@get_user
def logout(user, key):
    logout_request = requests.delete(API_URL+'/login', headers={'Authorization': key})
    if logout_request.status_code != 200:
        return abort(logout_request.status_code)
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie("Authorization", "", expires=0)
    return resp
    
@app.route('/profile')
@login_required
@get_user
def profile(user, key):
    return render_template('profile.html', user=user, key=key)

@app.route('/profile/edit', methods=['POST', 'GET'])
@login_required
@get_user
def edit_profile(user, key):
    if request.method == 'POST':
        username = request.form.get('username')
        password_old = request.form.get('password_old')
        password_new = request.form.get('password_new')
        profile_picture = request.files.get('profile_picture')
                
        data = {}
        
        if username is not None and len(username) > 0:
            if len(username) < 80:
                data['username'] = username
            else:
                return render_template('edit_profile.html', user=user, error="Your username is too long. The limit it 80 characters")
        
        if password_old is not None and password_new is not None and len(password_new) > 0:
            data['password'] = password_new
        
        if profile_picture is not None:
            data['profile_picture'] = base64.b64encode(profile_picture.stream.read()).decode("utf-8")
            
        headers = {"Authorization": key}
        edit_profile_request = requests.post(API_URL+'/user', headers=headers, json=data)
        status_code = edit_profile_request.status_code
        if status_code != 200:
            if status_code == 409:
                return render_template('edit_profile.html', user=user, error="This username is already in use.")
            if status_code == 401:
                return render_template('edit_profile.html', user=user, error="The old password is incorrect")
            return abort(edit_profile_request.status_code)
        
        return redirect(url_for("profile"))
            
            
        
    return render_template('edit_profile.html', user=user)
        
@app.route('/profile/delete/<isConfirmed>')
@login_required
@get_user
def delete_profile(user, key, isConfirmed):
    if isConfirmed:
        profile_delete_request = requests.delete(API_URL+'/user', headers={'Authorization': key})
        if profile_delete_request.status_code != 204:
            return abort(profile_delete_request)
        return redirect(url_for('home'))
    else:
        return redirect(url_for('profile'))
        
@app.route('/user/email/verify', methods=['GET'])
@login_required
@get_user
def verify_email(user, key):
    headers = {'Authorization': key}
    data = {"resend": False}
    email_request = requests.get(API_URL+'/user/email', headers=headers, json=data)
    if email_request.status_code != 200:
        return abort(email_request.status_code)
    
    expires = email_request.json().get('expires')
    
    return render_template('verify_email.html', user=user, expires=expires)
    
@app.route('/user/email/verify/resend', methods=['GET', 'POST'])
@login_required
@get_user
def verify_email_resend(user, key):
    headers = {'Authorization': key}
    data = {"resend": True}
    email_request = requests.get(API_URL+'/user/email', headers=headers, json=data)
    if email_request.status_code != 200:
        return abort(email_request.status_code)
    
    return redirect(url_for('verify_email'))
    
@app.route('/user/email/verify/<email_key>')
@login_required
@get_user
def verify_email_key(user, key, email_key):
    ...
        
@app.route('/groups')
@login_required
@get_user
def groups(user, key):
    group_request = requests.get(API_URL+"/groups", headers={"Authorization": key})
    if group_request.status_code != 200:
        return abort(group_request.status_code)
        
    groups = group_request.json()    
    return render_template('groups.html', groups = groups, user=user)
    
@app.route('/groups/create', methods=['GET', 'POST'])
@login_required
@get_user
def create_group(user, key):
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        frequency = request.form.get('frequency')
        start_day = request.form.get('start_day')
        time = request.form.get('time')
        if group_name is None or frequency is None or start_day is None or time is None:
            return render_template('create_group.html', user=user)
        json = {
            "group_name": group_name,
            "frequency": frequency,
            "start_day": start_day,
            "time": time
        }
        group_request = requests.post(API_URL+'/groups', json=json, headers={"Authorization": key})
        if group_request.status_code == 201:
            return redirect(url_for('groups'))
        elif group_request.status_code == 409:
            return render_template('create_group.html', error="Session is invalid or has expired", user=user) 
        elif group_request.status_code == 422:
            return render_template('create_group.html', error="Incomplete request", user=user)
        else:
            return abort(group_request.status_code)
        
        
    return render_template('create_group.html', user=user)

@app.route('/groups/view/<int:group_id>')
@login_required
@get_user
def view_group(group_id, user, key):
    group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if group_request.status_code == 200:
        if len(group_request.json()['meetings']) > 0:
            next_meeting = group_request.json()['meetings'][-1]

            next_meeting = requests.get(API_URL+"/meetings/" + str(next_meeting), headers={"Authorization": key})

            if next_meeting.status_code == 200:
                next_meeting = next_meeting.json()['meeting']
                next_meeting['date_time'] = datetime.datetime.strptime(next_meeting['date_time'], format("%Y-%m-%dT%H:%M:%S"))
            else:
                next_meeting = None
        else:
            next_meeting = None

        return render_template('view_group.html', group = group_request.json(), next_meeting=next_meeting, user=user)
    else:
        return abort(group_request.status_code)
    
@app.route('/groups/material/view/log/<int:group_id>')
@login_required
@get_user
def view_group_material_log(user, key, group_id=None):
    headers = {"Authorization": key}
    payload = {"group_id": group_id}
    
    group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if group_request.status_code != 200:
        return abort(group_request.status_code)
    
    group = group_request.json()
    
    people_request = requests.get(API_URL+"/people", json=payload, headers=headers)
    if people_request.status_code != 200:
        return abort(people_request.status_code)
    people = people_request.json()['people']
    
    
    return render_template('view_group_material_log.html', user=user, people=people, group=group)

@app.route('/groups/<int:group_id>/tasks/view')
@login_required
@get_user
def group_tasks(user, key, group_id):
    headers = {'Authorization': key}
    group_request = requests.get(API_URL+'/groups/'+str(group_id), headers={"Authorization": key})
    if group_request.status_code != 200:
        return abort(group_request.status_code)
    
    group = group_request.json()
    
    data = {'group_id': group_id}
    tasks_request = requests.get(API_URL+'/tasks', json=data, headers=headers)
    if tasks_request.status_code != 200:
        return abort(tasks_request.status_code)
    
    tasks = tasks_request.json().get('tasks')

    
    return render_template('group_tasks.html', user=user, tasks=tasks, group=group)

@app.route('/groups/<int:group_id>/tasks/create', methods=['GET', 'POST'])
@login_required
@get_user
def create_task(user, key, group_id):
    headers = {'Authorization': key}
    if request.method == 'POST':
        name = request.form.get('task_name')
        rotate = request.form.get('rotate')
        number = request.form.get('number')
        people = request.form.getlist('people-select')
                
        data = {
            "name": name,
            "amount": number,
            "rotate": rotate,
            "people": people
        }
        
        create_task_request = requests.post(API_URL+'/tasks/'+str(group_id), json=data, headers=headers)
        if create_task_request.status_code != 201:
            return abort(create_task_request.status_code)
        
        return redirect(url_for('group_tasks', group_id=group_id))
    
    group_request = requests.get(API_URL+'/groups/'+str(group_id), headers={"Authorization": key})
    if group_request.status_code != 200:
        return abort(group_request.status_code)
    
    group = group_request.json()
    
    data = {"group_id": group['id']}
    people_request = requests.get(API_URL+'/people', headers=headers, json=data)
    if people_request.status_code != 200:
        return abort(people_request.status_code)
    people = people_request.json()['people']
    
    return render_template('create_task.html', group=group, people=people)

@app.route('/groups/tasks/<task_id>/edit', methods=['GET', 'POST'])
@login_required
@get_user
def task_edit(user, key, task_id):
    headers = {"Authorization": key}
    
    if request.method == 'POST':
        name = request.form.get('task_name')
        rotate = True if request.form.get('rotate') == 'on' else False
        number = request.form.get('number')
        people = request.form.getlist('people-select')
        
        data = {
            "task_id": task_id,
            "name": name,
            "rotate": rotate,
            "amount": number,
            "people": people
            }
        
        task_put_request = requests.put(API_URL+'/tasks', json=data, headers=headers)
        if task_put_request.status_code != 200:
            return abort(task_put_request.status_code)
        
        return redirect(url_for("group_tasks", group_id=task_put_request.json().get('task').get('group_id')))
    
    data = {"task_id": task_id}
    task_get_request = requests.get(API_URL+'/tasks', json=data, headers=headers)
    if task_get_request.status_code != 200:
        return abort(task_get_request.status_code)
    
    task = task_get_request.json().get('task')
    
    group_id = task.get('group_id')
    data = {'group_id': group_id}
    people_get_request = requests.get(API_URL+'/people', json=data, headers=headers)
    if people_get_request.status_code != 200:
        return abort(people_get_request.status_code)
    
    people = people_get_request.json().get('people')
    
    return render_template('edit_task.html', user=user, task=task, people=people)
    
@app.route('/task/delete/<task_id>') # Don't cast to int to prevent error when inserting placeholder in js
@login_required
@get_user
def delete_task(user, key, task_id):
    headers = {"Authorization": key}
    get_task_request = requests.get(API_URL+'/tasks', headers=headers, json={'task_id': task_id})
    
    if get_task_request.status_code != 200:
        return abort(get_task_request.status_code)
    
    task = get_task_request.json().get('task')
    group_id = task.get('group_id')
    
    delete_task_request = requests.delete(API_URL+'/tasks', headers=headers, json={'task_id': task_id})
    if delete_task_request.status_code != 204:
        return abort(delete_task_request.status_code)
    
    return redirect(url_for('group_tasks', group_id=group_id))
    
@app.route('/group/<int:group_id>/tasks/distribute')
@login_required
@get_user
def distribute_tasks(user, key, group_id):
    headers = {'Authorization': key}

    distr_tasks_request = requests.get(API_URL+'/group/'+str(group_id)+'/tasks/distribute', headers=headers)
    if distr_tasks_request.status_code != 200:
        return abort(distr_tasks_request.status_code)
    
    assignments = distr_tasks_request.json().get('assignments')
    
    group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if group_request.status_code != 200:
        return abort(group_request.status_code)
    
    group = group_request.json()
    
    payload = {'group_id': group_id}
    people_request = requests.get(API_URL+'/people', json=payload, headers=headers)
    if people_request.status_code != 200:
        return abort(people_request.status_code)
    people = people_request.json()['people']
    
    data = {'group_id': group_id}
    task_get_request = requests.get(API_URL+'/tasks', json=data, headers=headers)
    if task_get_request.status_code != 200:
        return abort(task_get_request.status_code)
    
    tasks = task_get_request.json().get('tasks')
    
    complete_assignments = []
                    
    for assignment in assignments:
        person_id = assignment
        task_id = assignments[person_id]
        
        entry = {}
        person = next((person for person in people if str(person["id"]) == str(person_id)), None)
                
        entry['person'] = person
        task = next((task for task in tasks if task["id"] == task_id), None)
        entry['task'] = task
        complete_assignments.append(entry)
        
        
    groups_by_task = {}
    for entry in complete_assignments:
        tid = int(entry['task']['id'])
        groups_by_task.setdefault(tid, []).append(entry)

    # Create ordered list of lists
    assignments_by_task = [groups_by_task[tid] for tid in sorted(groups_by_task.keys())]

    meeting = group['next_meeting']
    meeting['group'] = group

    return render_template("display_assignments.html", user=user, assignments=assignments_by_task, meeting=meeting, group_id=group_id)

@app.route('/group/<int:group_id>/tasks/reset_seed')
@login_required
@get_user
def reset_task_seed(group_id, user, key):
    headers = {'Authorization': key}
    data = {'reset_seed': True}
    reset_task_seed_request = requests.post(API_URL+'/group/'+str(group_id)+'/tasks/distribute', headers=headers, json=data)
    if reset_task_seed_request.status_code != 204:
        return abort(reset_task_seed_request.status_code)
    
    return redirect(url_for('distribute_tasks', group_id=group_id))


@app.route('/groups/edit/<int:group_id>', methods=['GET', 'POST'])
@login_required
@get_user
def edit_group(group_id, user, key):
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        frequency = request.form.get('frequency')
        start_day = request.form.get('start_day')
        time = request.form.get('time')
        if group_name is None or frequency is None or start_day is None or time is None:
            return render_template('create_group.html', user=user)
        json = {
            "group_name": group_name,
            "frequency": frequency,
            "start_day": start_day,
            "time": time
        }
        group_request = requests.put(API_URL+'/groups/'+str(group_id), headers={"Authorization": key}, json=json)
        if group_request.status_code == 409:
            group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Cannot rename group, you already have a group with that name.", group = group_request.json(), user=user)
        
        if group_request.status_code != 200:
            return abort(group_request.status_code)
        return redirect(url_for('view_group', group_id=group_id))
            
    group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if group_request.status_code == 200:
        return render_template('edit_group.html', group = group_request.json(), user=user)

@app.route('/groups/delete/<int:group_id>', methods = ['GET'])
@login_required
@get_user
def delete_group(group_id, user, key):
    group_request = requests.delete(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if group_request.status_code == 204:
        return redirect(url_for("groups"))
    else:
        return abort(group_request.status_code)
    
    return redirect(url_for("view_group", group_id = group_id))     

@app.route('/meetings/<int:group_id>')
@login_required
@get_user
def group_meetings(user, key, group_id=None):
    headers = {"Authorization": key}
    if group_id is not None:
        group_request = requests.get(API_URL+'/groups/'+str(group_id), headers=headers)
        if group_request.status_code != 200:
            return abort(group_request.status_code)
        
        data = {"group_id": group_id}
        meeting_request = requests.get(API_URL+'/meetings', json=data, headers=headers)
        if meeting_request.status_code != 200:
            return abort(meeting_request.status_code)
        meetings = meeting_request.json()['meetings']
        groups = group_request.json()
        return render_template('meetings.html', group=groups, user=user, meetings=meetings, groups=groups)
        
    return abort(404)            
    
@app.route('/meetings/upcomming', methods=['GET', 'POST'])
@login_required
@get_user
def upcomming_meetings(user, key):
    future_only = True
    canceled = False
    group = None
    if request.method == 'POST':
        future_only = request.form.get('future_only')
        canceled = request.form.get('canceled')
        group = request.form.get('group')
        if group == 'all':
            group = None
    
    headers = {"Authorization": key}
    data = {'future_only': future_only, 'canceled': canceled, 'group_id': group}
    
    groups_request = requests.get(API_URL+"/groups", headers=headers)
    if groups_request.status_code == 200:
        groups = groups_request.json()
    
    meeting_request = requests.get(API_URL+'/meetings', headers=headers, json=data)
    if meeting_request.status_code == 200:
        meetings = meeting_request.json()['meetings']
        
        for meeting in meetings:
            r2 = requests.get(API_URL+'/groups/'+str(meeting['group_id']), headers=headers)
            if r2.status_code == 200:
                meeting['group'] = r2.json()
    
        return render_template('meetings_upcomming.html', meetings = meetings, groups=groups, future_only=future_only, canceled=canceled, selected_group=group)
            
    return abort(404)

@app.route('/meetings/edit/<int:meeting_id>', methods=['GET', 'POST'])
@login_required
@get_user
def edit_meeting(user, key, meeting_id=None):
    headers = {"Authorization": key}
    
    if request.method == 'POST':
        datetime_form = request.form.get('date_time')
        canceled = True if request.form.get('canceled') == 'on' else False
        organisers = request.form.getlist('organiser')
        payload = {'date_time': datetime_form, 'canceled': canceled}
        meeting_request = requests.put(API_URL+'/meetings/'+str(meeting_id), headers=headers, json=payload)
        if meeting_request.status_code != 202:
            return abort(meeting_request.status_code)
        
        meeting = meeting_request.json()['meeting']
        
        payload = {'group_id': meeting['id']}
        people_request = requests.get(API_URL+'/people', json=payload, headers=headers)
        if people_request.status_code != 200:
            return abort(people_request.status_code)
        people = people_request.json()['people']

        
        for person in people:
            payload = {"organiser": True if str(person['id']) in organisers else False}
            update_attendance_request = requests.post(API_URL+'/attendance/'+str(meeting_id)+"/"+str(person['id']), headers=headers, json=payload)
            if update_attendance_request.status_code != 201:
                return abort(update_attendance_request.status_code)
            
        return redirect(url_for('view_meeting', meeting_id = meeting_id))
        
    
    if request.method == 'GET':
        meeting_request = requests.get(API_URL+'/meetings/'+str(meeting_id), headers=headers)
        if meeting_request.status_code == 200:
            meeting = meeting_request.json()['meeting']
            payload = {'group_id': meeting['group_id']}
            people_request = requests.get(API_URL+'/people', json=payload, headers=headers)
            if people_request.status_code == 200:
                people = people_request.json()['people']
                
                attendance_request = requests.get(API_URL+'/attendance/'+str(meeting_id), headers=headers)
                if attendance_request.status_code == 200:
                    attendances = attendance_request.json()['attendances']
                    organisers = []
                    [organisers.append(person['id']) if person['organiser'] == True else None for person in attendances]
                    return render_template('edit_meeting.html', user=user, meeting=meeting, people=people, organisers=organisers)
                else:
                    return abort(attendance_request.status_code)
                
            return abort(people_request.status_code)
    
        return abort(meeting_request.status_code)

    return abort(404)

@app.route('/meetings/materials/post/<int:meeting_id>', methods=['POST'])
@login_required
@get_user
def meeting_materials(user, key, meeting_id=None):
    if request.method == 'POST':
        attendance_type = request.form.get('attendance_type')

        raw = request.form.to_dict(flat=False)
        presence_map = {}
        
        for key_str, vlist in raw.items():            
            m = re.match(r'^material\[(\d+)\]$', key_str)
            if not m:
                continue
            pid = int(m.group(1))
            last_val = vlist[-1] if vlist else '0'
            try:
                presence_map[pid] = int(last_val)
            except (ValueError, TypeError):
                presence_map[pid] = last_val
                
        headers = {"Authorization": key}
            
        for person_id, material in presence_map.items():            
            payload = {'material': material}
            attendance_request = requests.post(API_URL+'/attendance/'+str(meeting_id)+'/'+str(person_id), headers=headers, json=payload)
            if attendance_request.status_code != 201:
                return abort(attendance_request.status_code)
        
        return redirect(url_for('view_meeting', meeting_id = meeting_id))     
                
@app.route('/meetings/view/material/<int:meeting_id>')
@login_required
@get_user
def view_meeting_materials(user, key, meeting_id=None):
    if meeting_id is not None:
        headers = {"Authorization": key}
        meeting_request = requests.get(API_URL+'/meetings/'+str(meeting_id), headers=headers)
        if meeting_request.status_code == 200:
            meeting = meeting_request.json()['meeting']
            
            people_request = requests.get(API_URL+'/people', json={'group_id': meeting['group_id']}, headers=headers)
            if people_request.status_code == 200:
                people = people_request.json()['people']
                people = sorted(sorted(people, key=lambda d: d['name']), key=lambda d: int(d['role']), reverse=True) # Sort the higher roles before the lower ones

                meeting_attendance_request = requests.get(API_URL+'/attendance/'+str(meeting['id']), headers=headers)
                
                if meeting_attendance_request.status_code == 200:
                    for person in people:
                        for attendance in meeting_attendance_request.json()['attendances']:
                            print(person, attendance)
                            if attendance['person_id'] == person['id']:
                                person['attendance'] = attendance
                else:
                    return abort(meeting_attendance_request.status_code)
                        
                return render_template('view_meeting_materials.html', user=user, meeting=meeting, people=people)
            else:
                return abort(people_request.status_code)
        else:
            return abort(meeting_request.status_code)
    
    return abort(404)

@app.route('/person/<int:person_id>/materials/clear_checks')
@login_required
@get_user
def clear_checks(user, key, person_id=None):
    headers = {"Authorization": key}
    payload = {"material_count": 1}
    person_clear_request = requests.put(API_URL+'/people/'+str(person_id), headers=headers, json=payload)
    if person_clear_request.status_code != 200:
        return abort(person_clear_request.status_code)
    
    return redirect(url_for('view_group_material_log', group_id = person_clear_request.json()['person']['group_id']))

@app.route('/meetings/<int:meeting_id>/attendance/post', methods=['POST'])
@login_required
@get_user
def meeting_attendance(user, key, meeting_id=None):
    if request.method == 'POST':
        attendance_type = request.form.get('attendance_type')
                
        raw = request.form.to_dict(flat=False)
        presence_map = {}
        
        for key_str, vlist in raw.items():            
            m = re.match(r'^presence\[(\d+)\]$', key_str)
            if not m:
                continue
            pid = int(m.group(1))
            last_val = vlist[-1] if vlist else '0'
            try:
                presence_map[pid] = int(last_val)
            except (ValueError, TypeError):
                presence_map[pid] = last_val
                
        headers = {"Authorization": key}
            
        for person_id, presence in presence_map.items():
            attendance_request_get = requests.get(API_URL+'/attendance/'+str(meeting_id)+'/'+str(person_id), headers=headers)
            if attendance_request_get.status_code != 200:
                return abort(attendance_request_get.status_code)
            
            attendance = attendance_request_get.json()['attendance']
            
            payload = {'presence': presence}
            if attendance_type == "before":
                if presence == 0:
                    payload = {'presence': 3}
            else:
                if attendance['presence'] == 3:
                    payload = {'presence': 3}
                    
            attendance_request = requests.post(API_URL+'/attendance/'+str(meeting_id)+'/'+str(person_id), headers=headers, json=payload)
            if attendance_request.status_code != 201:
                return abort(attendance_request.status_code)
        
        return redirect(url_for('view_meeting', meeting_id = meeting_id))

@app.route('/meetings/view/<int:meeting_id>')
@login_required
@get_user
def view_meeting(user, key, meeting_id=None):
    if meeting_id is not None:
        headers = {"Authorization": key}
        meeting_request = requests.get(API_URL+'/meetings/'+str(meeting_id), headers=headers)
        if meeting_request.status_code == 200:
            meeting = meeting_request.json()['meeting']
            
            people_request = requests.get(API_URL+'/people', json={'group_id': meeting['group_id']}, headers=headers)
            if people_request.status_code == 200:
                people = people_request.json()['people']
                people = sorted(sorted(people, key=lambda d: d['name']), key=lambda d: int(d['role']), reverse=True) # Sort the higher roles before the lower ones

                
                meeting_attendance_request = requests.get(API_URL+'/attendance/'+str(meeting['id']), headers=headers)
                
                if meeting_attendance_request.status_code == 200:
                    for person in people:
                        for attendance in meeting_attendance_request.json()['attendances']:
                            if attendance['person_id'] == person['id']:
                                person['attendance'] = attendance
                else:
                    return abort(meeting_attendance_request.status_code)
                        
                return render_template('view_meeting.html', user=user, meeting=meeting, people=people)
            else:
                return abort(people_request.status_code)
        else:
            return abort(meeting_request.status_code)
    
    return abort(404)

@app.route('/meetings/<int:meeting_id>')
@login_required
@get_user
def meeting(meeting_id, user, key):
    return render_template('meeting.html', user=user)

@app.route('/people/<int:group_id>')
@login_required
@get_user
def group_people(user, key, group_id=None):
    if group_id is not None:
        groups_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
        if groups_request.status_code != 200:
            return abort(groups_request.status_code)
        groups = groups_request.json()
        people_request = requests.get(API_URL+'/people', headers={"Authorization": key}, json={'group_id': group_id})
        if people_request.status_code != 200:
            return abort(people_request.status_code)
        people = people_request.json()['people']
        people = sorted(sorted(people, key=lambda d: d['name']), key=lambda d: int(d['role']), reverse=True)
        return render_template('group_people.html', group = groups, user=user, people=people)
        
    return abort(404)
  
@app.route('/person/<int:person_id>')
@login_required
@get_user
def view_person(user, key, person_id=None):
    if person_id is not None:
        people_request = requests.get(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
        if people_request.status_code != 200:
            return abort(people_request.status_code)
        return render_template('view_person.html', user=user, person=people_request.json()['person'])
        
    return abort(404)
    
@app.route('/people/create/<int:group_id>', methods=['POST', 'GET'])
@login_required
@get_user
def create_person(user, key, group_id=None):
    if request.method == 'POST':
        names = request.form.get('names')
        role = request.form.get('role')
        
        # Filter the names and turn them into a list
        names = ','.join(name.strip() for name in names.split(','))
        names = names.translate(str.maketrans({',': '<split>', '\n': '<split>', '\r': ''}))
        names = names.split('<split>')
        names = list(filter(None, names))
        
        people = []
                
        for name in names:
            people.append({'person_name': name, 'group_id': group_id, 'role': int(role)})
                    
        people_request = requests.post(API_URL+'/people', headers={"Authorization": key}, json={"people": people})
        
        if people_request.status_code != 201:
            return abort(people_request.status_code)
        return redirect(url_for('group_people', group_id=group_id))
        
    
    if group_id is not None:
        group_request = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
        if group_request.status_code != 200:
            return abort(group_request.status_code)    
        return render_template("create_person.html", group=group_request.json(), user=user)
        
    return abort(404)

@app.route('/people/delete/<int:person_id>')
@login_required
@get_user
def delete_person(user, key, person_id=None):
    if person_id is not None:
        people_request = requests.get(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
        if people_request.status_code != 200:
            return abort(people_request.status_code)
        
        group_id = people_request.json()['person']['group_id']
        people_delete_request = requests.delete(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
        if people_delete_request.status_code != 204 or people_delete_request.status_code != 200:
            return abort(people_delete_request.status_code)
        
        return redirect(url_for('group_people', group_id=group_id))
    
    return abort(404)

@app.route('/people/edit/<int:person_id>', methods = ['GET', 'POST'])
@login_required
@get_user
def edit_person(user, key, person_id=None):
    headers = {"Authorization": key}
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        default_presence = request.form.get('default_presence')
        
        data = {    
            "person_name": name,
            "role": role,
            "default_presence": default_presence
        }
        
        people_put_request = requests.put(API_URL+"/people/"+str(person_id), headers=headers, json=data)
        if people_put_request.status_code == 409:
            return render_template('edit_person.html', person=people_put_request.json()['person'], error="You already have someone with that name in this group.")
        elif people_put_request.status_code == 200:
            group_id = people_put_request.json()['person']['group_id']
            return redirect(url_for('group_people', group_id=group_id))
        
        return abort(people_put_request.status_code)
    
    if person_id is not None:
        people_request = requests.get(API_URL+'/people/'+str(person_id), headers=headers)
        if people_request.status_code != 200:
            return abort(people_request.status_code)
        return render_template('edit_person.html', person=people_request.json()['person'])
        
        
    return abort(404)

if __name__ == '__main__':
    app.run(port=5002, host = "0.0.0.0")