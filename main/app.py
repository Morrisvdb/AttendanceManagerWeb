from flask import request, render_template, make_response, redirect, url_for, abort
from __init__ import app, API_URL
import requests
from functools import wraps
import datetime
import re

# TODO: Improve error handeling. --> not 404.html for everything :facepalm:
# TODO: update the meeting view to include people and move the attendance button to the view instead of the edit
# TODO: Make seperate pre-meeting and in-meeting attendance change screens

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
        r = requests.get(API_URL+"/user", headers=headers)
        
        
        if r.status_code == 200:
            return f(*args, **kwargs)
            # return f(*args, **kwargs, user = r.json()['user'], key = AuthKey)
        else:
            return render_template('login_required.html')

    return decorated_function

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", url=request.url)

@app.route("/")
@get_user
def home(user, key):
    return render_template("home.html", user=user)

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
        r = requests.post(API_URL + "/signup", json=json)
        if r.status_code == 201:
            return redirect(url_for('login'))
        elif r.status_code == 409:
            return render_template('signup.html', error="Username already in use")
        elif r.status_code == 422:
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
        r = requests.post(API_URL + "/login", json=json)
        if r.status_code == 200:
            if 'key' in r.json():
                key = r.json()['key']
            else:
                return render_template('login.html', error="Unexpected response from server.")
            url = url_for('home')
            resp = make_response(redirect(url))
            resp.set_cookie('Authorization', key)
            return resp
        elif r.status_code == 404 or r.status_code == 401:
            return render_template('login.html', error="Password or Username incorrect.")
        else:
            return render_template('login.html')
    
    return render_template("login.html")

# TODO: Logout route
@app.route("/logout")
@login_required
@get_user
def logout(user, key):
    r = requests.delete(API_URL+'/login', headers={'Authorization': key})
    if r.status_code == 200:
        resp = make_response(redirect(url_for('home')))
        resp.set_cookie("Authorization", "", expires=0)
        return resp
    else:
        return url_for('home')
    
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
        r = requests.delete(API_URL+'/user', headers={'Authorization': key})
        if r.status_code == 204:
            return redirect(url_for('home'))
        else:
            return redirect(url_for('profile'))
    else:
        return redirect(url_for('profile'))
        
        
        
@app.route('/groups')
@login_required
@get_user
def groups(user, key):
    
    r = requests.get(API_URL+"/groups", headers={"Authorization": key})
    if r.status_code == 200:
        groups = r.json()    
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
        r = requests.post(API_URL+'/groups', json=json, headers={"Authorization": key})
        if r.status_code == 201:
            return redirect(url_for('groups'))
        elif r.status_code == 409:
            return render_template('create_group.html', error="Session is invalid or has expired", user=user) 
        elif r.status_code == 422:
            return render_template('create_group.html', error="Incomplete request", user=user)
        
        
    return render_template('create_group.html', user=user)

@app.route('/groups/view/<int:group_id>')
@login_required
@get_user
def view_group(group_id, user, key):
    r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 200:
        if len(r.json()['meetings']) > 0:
            next_meeting = r.json()['meetings'][-1]

            next_meeting = requests.get(API_URL+"/meetings/" + str(next_meeting), headers={"Authorization": key})

            if next_meeting.status_code == 200:
                next_meeting = next_meeting.json()['meeting']
                next_meeting['date_time'] = datetime.datetime.strptime(next_meeting['date_time'], format("%Y-%m-%dT%H:%M:%S"))
            else:
                next_meeting = None
        else:
            next_meeting = None

        return render_template('view_group.html', group = r.json(), next_meeting=next_meeting, user=user)
    else:
        return redirect(url_for('groups'))

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
        r = requests.put(API_URL+'/groups/'+str(group_id), headers={"Authorization": key}, json=json)
        if r.status_code == 200:
            return redirect(url_for('view_group', group_id=group_id))
        elif r.status_code == 404:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Group not found", group = r.json(), user=user)
        elif r.status_code == 422:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Group not found", group = r.json(), user=user)
        elif r.status_code == 409:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Cannot rename group, you already have a group with that name.", group = r.json(), user=user)
            
    r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 200:
        return render_template('edit_group.html', group = r.json(), user=user)

@app.route('/groups/delete/<int:group_id>', methods = ['GET'])
@login_required
@get_user
def delete_group(group_id, user, key):
    r = requests.delete(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 204:
        return redirect(url_for("groups"))
    
    return redirect(url_for("view_group", group_id = group_id))     

@app.route('/meetings/<int:group_id>')
@login_required
@get_user
def group_meetings(user, key, group_id=None):
    headers = {"Authorization": key}
    if group_id is not None:
        r = requests.get(API_URL+'/groups/'+str(group_id), headers=headers)
        if r.status_code == 200:
            # print(r.json())
            data = {"group_id": group_id}
            r2 = requests.get(API_URL+'/meetings', json=data, headers=headers)
            if r2.status_code == 200:
                meetings = r2.json()['meetings']
                groups = r.json()
                # for meeting in meetings:
                #     print(meeting)
                    # meeting.date_time = datetime.datetime.strptime(meeting.date_time, format="%Y-%m-%dT%H:%M:%S")
                return render_template('meetings.html', group=r.json(), user=user, meetings=meetings, groups=groups)
            
    return render_template('404.html', user=user, url=request.url)
    # return render_template('meetings.html', user=user)
    
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
        # Let user filter meetings, default `future_only:True`
    
    
    
    headers = {"Authorization": key}
    data = {'future_only': future_only, 'canceled': canceled, 'group_id': group}
    
    groups_r = requests.get(API_URL+"/groups", headers=headers)
    if groups_r.status_code == 200:
        groups = groups_r.json()
    
    r = requests.get(API_URL+'/meetings', headers=headers, json=data)
    if r.status_code == 200:
        meetings = r.json()['meetings']
        
        for meeting in meetings:
            r2 = requests.get(API_URL+'/groups/'+str(meeting['group_id']), headers=headers)
            if r2.status_code == 200:
                meeting['group'] = r2.json()
    
        return render_template('meetings_upcomming.html', meetings = meetings, groups=groups, future_only=future_only, canceled=canceled, selected_group=group)
            
    return render_template('404.html', user=user, key=key)

@app.route('/meetings/edit/<int:meeting_id>', methods=['GET', 'POST'])
@login_required
@get_user
def edit_meeting(user, key, meeting_id=None):
    # TODO: fix preselected attendances - fix organiser set
    if request.method == 'POST':
        datetime_form = request.form.get('date_time')
        organisers = request.form.getlist('organiser')
        print(organisers)
    
    if meeting_id is not None:
        headers = {"Authorization": key}
        r = requests.get(API_URL+'/meetings/'+str(meeting_id), headers=headers)
        meeting = r.json()['meeting']
        if r.status_code == 200 and meeting:
            payload = {'group_id': meeting['group_id']}
            people_request = requests.get(API_URL+'/people', json=payload, headers=headers)
            if people_request.status_code == 200:
                people = people_request.json()['people']
                return render_template('edit_meeting.html', user=user, meeting=meeting, people=people)
            return abort(people_request.status_code)
    
        return abort(r.status_code)

    return abort(404)

@app.route('/meetings/attendance/post/<int:meeting_id>', methods=['POST'])
@login_required
@get_user
def meeting_attendance(user, key, meeting_id=None):
    if request.method == 'POST':
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
            payload = {'presence': presence}
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
        r = requests.get(API_URL+'/meetings/'+str(meeting_id), headers=headers)
        if r.status_code == 200:
            meeting = r.json()['meeting']
            
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
            return abort(r.status_code)
    
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
        r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
        if r.status_code == 200:
            r2 = requests.get(API_URL+'/people', headers={"Authorization": key}, json={'group_id': group_id})
            if r2.status_code == 200:
                people = r2.json()['people']
                people = sorted(sorted(people, key=lambda d: d['name']), key=lambda d: int(d['role']), reverse=True)
                return render_template('group_people.html', group = r.json(), user=user, people=people)
        
    return render_template('404.html', url=request.url, user=user)
  
@app.route('/person/<int:person_id>')
@login_required
@get_user
def view_person(user, key, person_id=None):
    if person_id is not None:
        r = requests.get(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
        if r.status_code == 200:
            return render_template('view_person.html', user=user, person=r.json()['person'])
        
    return render_template('404.html', user=user, url=request.url)
    
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
                    
        r = requests.post(API_URL+'/people', headers={"Authorization": key}, json={"people": people})
        
        if r.status_code == 201:
            return redirect(url_for('group_people', group_id=group_id))
        
        return render_template('404.html', error="Group Not Found", user=user)
    
    if group_id is not None:
        r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
        if r.status_code == 200:
            return render_template("create_person.html", group=r.json(), user=user)
        
    return render_template('404.html', url=request.url, user=user)

@app.route('/people/delete/<int:person_id>')
@login_required
@get_user
def delete_person(user, key, person_id=None):
    if person_id is not None:
        r = requests.get(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
        if r.status_code == 200:
            group_id = r.json()['person']['group_id']
            r2 = requests.delete(API_URL+'/people/'+str(person_id), headers={"Authorization": key})
            if r2.status_code == 204 or r2.status_code == 200:
                return redirect(url_for('group_people', group_id=group_id))
    
    return render_template('404.html', user=user, url=request.url)

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
        
        r = requests.put(API_URL+"/people/"+str(person_id), headers=headers, json=data)
        if r.status_code == 409:
            return render_template('edit_person.html', person=r.json()['person'], error="You already have someone with that name in this group.")
        elif r.status_code == 200:
            group_id = r.json()['person']['group_id']
            return redirect(url_for('group_people', group_id=group_id))
    
    if person_id is not None:
        r = requests.get(API_URL+'/people/'+str(person_id), headers=headers)
        if r.status_code == 200:
            return render_template('edit_person.html', person=r.json()['person'])
        
        
    return render_template("404.html", url=request.url, user=user)

if __name__ == '__main__':
    app.run(port=5002)