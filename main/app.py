from flask import request, render_template, make_response, redirect, url_for, abort, g, session
from user_agents import parse
from main.__init__ import app, API_URL
import requests
from functools import wraps
import datetime
import re

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
    
    try:
        previous_url = session.pop('origin')
    except KeyError:
        previous_url = 'home'
        
    if user is None:
        resp = make_response()
        resp.set_cookie('locale', locale)
        return resp
    
    headers = {"Authorization": key}
    
    user_put_request = requests.post(API_URL+"/user", headers=headers, json={"locale": locale})
    if user_put_request.status_code != 200:
        return abort(user_put_request.status_code)
    
    return {'status': 'ok'}, 200
    
@app.route('/theme/toggle/<string:url>', methods=['POST'])
@get_user
def toggle_theme(user, key):
    theme = "dark" if request.cookies['theme'] != "dark" else "light"
        
    # if user is None:
    resp = make_response()
    resp.set_cookie('theme', theme)
    return resp
    
    # MAYBE TO ADD ACCOUNT STORED THEME LATER? COOKIE BASED FOR NOW
    # headers = {"Authorization": key}
    
    # user_put_request = requests.post(API_URL+"/user", headers=headers, json={"theme": theme})
    # if user_put_request.status_code != 200:
    #     return abort(user_put_request.status_code)
    
    # return redirect(url_for(previous_url))
    
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if not(username and password1 and password2):
            return render_template('signup.html', error="Not all boxes are filled in")

        if password1 != password2:
            return render_template('signup.html', error="Passwords do not match")

        json = {
            "username": username,
            "password": password1
        }
        signup_request = requests.post(API_URL + "/signup", json=json)
        if signup_request.status_code == 201:
            return redirect(url_for('login'))
        elif signup_request.status_code == 409:
            return render_template('signup.html', error="Username already in use")
        elif signup_request.status_code == 422:
            return render_template('signup.html', error="Malformed request")
            
    
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
                    print(meeting_attendance_request.json())
                    for person in people:
                        print(person)
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