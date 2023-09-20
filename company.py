from flask import Flask, Blueprint, render_template, request, redirect, url_for, session
from werkzeug.exceptions import BadRequest
from pymysql import connections
import os
import boto3
from config import *
import re
import datetime
from functools import wraps

company_bp = Blueprint('company', __name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)
output = {}
table = 'company'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('student.studhome'))
        return f(*args, **kwargs)
    return decorated_function

@company_bp.route("/", methods=['GET', 'POST'])
def home():
    return render_template('company.html')

@company_bp.route("/validate", methods=['GET', 'POST'])
def valLogin():
    email = request.form['email']

    cursor = db_conn.cursor()
    query = "SELECT email, company_id FROM company WHERE email = %s"
    cursor.execute(query, (email,))
    user_data = cursor.fetchone()

    cursor.close()
    if user_data:
        session['company_user_id'] = user_data[1]
        return redirect(url_for('company.profile'))
    else:
        return "User not found"

@company_bp.route("/logout", methods=['GET'])
def logout():
    session.pop('company_user_id', None)
    return redirect(url_for('company.home'))

@company_bp.route("/profile", methods=['GET', 'POST'])
def profile():
    try:
        updating = request.form['value']
    except BadRequest:
        updating = None 
    username = session['company_user_id']
    cursor = db_conn.cursor()
    query = "SELECT * FROM company WHERE company_id = %s"
    cursor.execute(query, (username,))
    user_data1 = cursor.fetchone()

    user_data = {
        'company_name' : user_data1[1],
        'email' : user_data1[3],
        'tel_num' : user_data1[4],
        'address' : user_data1[2]
    }
    cursor.close()
    if user_data1[5] and updating is None:
        return redirect(url_for('company.dashboard'))
    return render_template('companyDetail.html', **user_data)

@company_bp.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    username = session['company_user_id']
    cursor = db_conn.cursor()
    query = "SELECT * FROM company WHERE company_id = %s"
    cursor.execute(query, (username,))
    user_data1 = cursor.fetchone()

    user_data = {
        'company_name' : user_data1[1],
        'email' : user_data1[3],
        'address' : user_data1[2],
        'hq' : user_data1[6],
        'hr' : user_data1[7],
        'pic': user_data1[9]
    }

    query = "SELECT job_title, position, education, allowance, job_id FROM job_portal WHERE company_id = %s"
    cursor.execute(query, (user_data1[0],))
    user_data2 = cursor.fetchall()
    cursor.close()

    user_data_list = []
    for row in user_data2:
        user_data_dict = {
            "job_title" : row[0],
            "position" : row[1],
            "education" : row[2],
            "allowance" : row[3],
            "id" : row[4]
        }
        user_data_list.append(user_data_dict)
    legal_link = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + user_data1[0] + "_legal_file.pdf"
    epf_link = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + user_data1[0] + "_epf_file.pdf"
    return render_template('companyDashboard.html', **user_data, data_list=user_data_list, legal_pdf=legal_link, epf_pdf=epf_link)

@company_bp.route("/submitDetail", methods=['POST'])
def details():
    userid = session['company_user_id']
    hq = request.form['hq']
    hr = request.form['hr']
    pic = request.form['pic']
    legal = request.files['legal']
    epf = request.files['epf']

    cursor = db_conn.cursor()
    update_sql = "UPDATE company SET hq = %s, hr_contact = %s, person_incharge = %s, uploaded = %s WHERE company_id = %s"
    cursor.execute(update_sql, (hq, hr, pic, 1, userid))
    db_conn.commit()
    cursor.close()
    
    legal_file_name = "com-id-" + str(userid) + "_legal_file" + os.path.splitext(legal.filename)[1]
    epf_file_name = "com-id-" + str(userid) + "_epf_file" + os.path.splitext(epf.filename)[1]
    s3 = boto3.resource('s3')
    s3.Bucket(custombucket).put_object(Key=legal_file_name, Body=legal, ContentType="application/pdf")
    s3.Bucket(custombucket).put_object(Key=epf_file_name, Body=epf, ContentType="application/pdf")
    return redirect(url_for('company.profile'))

@company_bp.route("/jobsDetails", methods=['GET', 'POST'])
def jobDetails():
    try:
        session["company_updating"] = request.form['update']
        session["company_job_id"] = request.form['job_id']
    except BadRequest:
        session["company_updating"] = None 
        session["company_job_id"] = None
    return render_template('companyJobDetail.html')

@company_bp.route("/jobsDetails/<job_id>", methods=['GET', 'POST'])
def jobView(job_id):
    cursor = db_conn.cursor()
    select_sql = "SELECT * from job_portal WHERE job_id = %s"
    cursor.execute(select_sql, (job_id))
    user_data2 = cursor.fetchone()
    select_sql = "SELECT COUNT(*) FROM job_portal WHERE company_id = %s"
    cursor.execute(select_sql, (user_data2[1]))
    num = cursor.fetchone()
    number_1 = num[0]
    cursor.close()
    hours = int(user_data2[8])
    minutes = int((user_data2[8] - hours) * 60)
    hours = f"{hours} hour(s) {minutes} minutes"
    accomodation_value = True if user_data2[3] else False
    transport_value = True if user_data2[4] else False
    laptop_value = True if user_data2[5] else False
    user_data = {
        'education' : user_data2[2],
        'job_title' : user_data2[11],
        'position' : user_data2[12],
        'accomodation' : accomodation_value,
        'transport' : transport_value,
        'laptop': laptop_value,
        'start_time': format_timedelta(user_data2[6]),
        'end_time' : format_timedelta(user_data2[7]),
        'hours': hours,
        'environment' : user_data2[9],
        'allowance' : user_data2[10],
        'job_id' : job_id
    }
    file_name = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + str(user_data2[1]) + "_job_desc_file" + str(number_1) + ".txt"
    return render_template('companyJobDetailUpdate.html', **user_data, job_txt=file_name)

@company_bp.route("/SubmitjobsDetails", methods=['GET', 'POST'])
def submitJobs():
    education = request.form['education']
    accomodation = request.form['accomodation']
    job_title = request.form['job_title']
    position = request.form['position']
    transport = request.form['transport']
    laptop = request.form['laptop']
    appt_start = request.form['appt_start']
    appt_end = request.form['appt_end']
    hours = request.form['hours']
    environment = request.form['environment']
    allowance = request.form['allowance']
    txt = request.files['jobdes']
    accomodation_value = 1 if accomodation.lower() == "yes" else 0
    transport_value = 1 if transport.lower() == "yes" else 0
    laptop_value = 1 if laptop.lower() == "yes" else 0
    match = re.search(r'(\d+) hour\(s\)\s(\d+) minutes', hours)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        hours = round(hours + minutes / 60.0, 2)

    cursor = db_conn.cursor()
    if session["company_updating"] is not None:
        update_sql = "UPDATE job_portal SET education = %s, accomodation = %s, transport = %s, laptop = %s, start_time = %s, end_time = %s, hours = %s, environment = %s, allowance = %s, job_title = %s, position = %s WHERE job_id = %s"
        cursor.execute(update_sql, (education, accomodation_value, transport_value, laptop_value, appt_start, appt_end, hours, environment, allowance, job_title, position, session["company_job_id"]))
        db_conn.commit()
    else:
        select_sql = "SELECT COUNT(*) FROM job_portal WHERE company_id = %s"
        cursor.execute(select_sql, (session['company_user_id']))
        num = cursor.fetchone()
        session['company_job_id'] = num[0]
        insert_sql = "INSERT INTO job_portal (company_id, education, accomodation, transport, laptop, start_time, end_time, hours, environment, allowance, job_title, position) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_sql, (session['company_user_id'], education, accomodation_value, transport_value, laptop_value, appt_start, appt_end, hours, environment, allowance, job_title, position))
        db_conn.commit()
        
    cursor.close()
    file_name = "com-id-" + str(session['company_user_id']) + "_job_desc_file" + str(session['company_job_id']+1) + os.path.splitext(txt.filename)[1]
    s3 = boto3.resource('s3')
    s3.Bucket(custombucket).put_object(Key=file_name, Body=txt, ContentType="text/plain")
    return redirect(url_for('company.dashboard'))

@company_bp.route("/register", methods=['GET', 'POST'])
def registerPage():
    return render_template('company_register.html')

@company_bp.route("/renew", methods=['GET', 'POST'])
def forgetPassword():
    return render_template('forgetPassword.html')

@company_bp.route("/registerAcc", methods=['POST'])
def registerAcc():
    id = get_last_company_id()
    name = request.form['name']
    address = request.form['address']
    tel_num = request.form['tel_num']
    email = request.form['email']
    
    insert_sql = "INSERT INTO company (company_id, company_name, address, email, tel_num) VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()
    cursor.execute(insert_sql, (id, name, address, email, tel_num))
    db_conn.commit()
    cursor.close()

    return redirect(url_for('company.home'))

def get_last_company_id():
    cursor = db_conn.cursor()
    query = "SELECT MAX(company_id) FROM company"
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    last_id = result[0] if result[0] is not None else 0
    if type(last_id) != int:
        last_id = int(last_id[1:])
    new_numeric_part = last_id + 1
    new_id = f'C{new_numeric_part:04}'
    return new_id

def format_timedelta(td):
    # Extract hours, minutes, and seconds components
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as HH:MM:SS with leading zeros
    formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

    return formatted_time
