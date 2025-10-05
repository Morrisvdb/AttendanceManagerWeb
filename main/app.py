from flask import request, render_template, make_response, redirect, url_for
from __init__ import app, API_URL
import requests
from functools import wraps
import datetime

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
    raise NotImplementedError
        
@app.route('/groups')
@login_required
@get_user
def groups(user, key):
    
    r = requests.get(API_URL+"/groups", headers={"Authorization": key})
    if r.status_code == 200:
        groups = r.json()
        print(groups)
    
        return render_template('groups.html', groups = groups)
    
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
            return render_template('create_group.html')
        json = {
            "group_name": group_name,
            "frequency": frequency,
            "start_day": start_day,
            "time": time
        }
        r = requests.post(API_URL+'/groups', json=json, headers={"Authorization": key})
        print(r.json())
        if r.status_code == 201:
            return redirect(url_for('groups'))
        elif r.status_code == 409:
            return render_template('create_group.html', error="Session is invalid or has expired") 
        elif r.status_code == 422:
            return render_template('create_group.html', error="Incomplete request")
        
        
    return render_template('create_group.html')

@app.route('/groups/view/<int:group_id>')
@login_required
@get_user
def view_group(group_id, user, key):
    r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 200:
        next_meeting = r.json()['meetings'][-1]

        next_meeting = requests.get(API_URL+"/meetings/" + str(next_meeting), headers={"Authorization": key})

        if next_meeting.status_code == 200:
            next_meeting = next_meeting.json()['meeting']
            next_meeting['date_time'] = datetime.datetime.strptime(next_meeting['date_time'], format("%Y-%m-%dT%H:%M:%S"))
        else:
            next_meeting = None

        return render_template('view_group.html', group = r.json(), next_meeting=next_meeting)
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
            return render_template('create_group.html')
        json = {
            "group_name": group_name,
            "frequency": frequency,
            "start_day": start_day,
            "time": time
        }
        r = requests.put(API_URL+'/groups/'+str(group_id), headers={"Authorization": key}, json=json)
        print(r.status_code)
        if r.status_code == 200:
            return redirect(url_for('view_group', group_id=group_id))
        elif r.status_code == 404:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Group not found", group = r.json())
        elif r.status_code == 422:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Group not found", group = r.json())
        elif r.status_code == 409:
            r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
            return render_template('edit_group.html', error="Cannot rename group, you already have a group with that name.", group = r.json())
            
    r = requests.get(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 200:
        return render_template('edit_group.html', group = r.json())

@app.route('/groups/delete/<int:group_id>', methods = ['GET'])
@login_required
@get_user
def delete_group(group_id, user, key):
    r = requests.delete(API_URL+"/groups/"+str(group_id), headers={"Authorization": key})
    if r.status_code == 204:
        return redirect(url_for("groups"))
    
    return redirect(url_for("view_group", group_id = group_id))     

# TODO: Add meeting routes and attendance marking.   

if __name__ == '__main__':
    app.run(port=5002)