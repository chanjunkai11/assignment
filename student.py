from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session
from werkzeug.exceptions import BadRequest
from pymysql import connections
import os
import boto3
import botocore.exceptions
from itertools import chain
from config import *
from functools import wraps
from datetime import timedelta

student_bp = Blueprint('student', __name__)

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
table = 'student'
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('student.studhome'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route("/", methods=['GET', 'POST'])
def studhome():
    if 'user_id' in session:
        return redirect(url_for('student.profile'))
    return render_template('student.html')

@student_bp.route("/validate", methods=['GET', 'POST'])
def valLogin():
    email = request.form['email']

    cursor = db_conn.cursor()
    query = "SELECT email, stud_id FROM student WHERE email = %s"
    cursor.execute(query, (email,))
    user_data = cursor.fetchone()

    cursor.close()
    if user_data:
        session['user_id'] = user_data[1]
        return redirect(url_for('student.studJob'))
    else:
        return "User not found"

@student_bp.route("/logout", methods=['GET'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('student.studhome'))

@student_bp.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    username = session["user_id"]
    try:
        updating = request.form['update']
    except BadRequest:
        updating = None

    cursor = db_conn.cursor()
    query = "SELECT * FROM student WHERE stud_id = %s"
    cursor.execute(query, (username,))
    user_data1 = cursor.fetchone()

    name = user_data1[1] + " " + user_data1[2]
    user_data = {
        'first_name' : user_data1[1],
        'last_name' : user_data1[2],
        'id' : user_data1[0],
        'ic' : user_data1[6],
        'email' : user_data1[5],
        'tel_num' : user_data1[4],
        'address' : user_data1[3]
    }

    if user_data1[9] and updating is None:
        query = "SELECT CONCAT(first_name, ' ', last_name) AS full_name, email FROM lecturer WHERE lec_id = %s"
        cursor.execute(query, (user_data1[7],))
        user_data2 = cursor.fetchone()

        query = "SELECT company_name, email, address FROM company WHERE company_id = %s"
        cursor.execute(query, (user_data1[8],))
        user_data3 = cursor.fetchone()
        cursor.close()

        user_data2 = {
            "supervisor_name" : user_data2[0],
            "supervisor_email" : user_data2[1],
        }
        user_data3 = {
            "company_name" : user_data3[0],
            "company_email" : user_data3[1],
            "company_address" : user_data3[2],
        }

        pfp = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + user_data1[0] + "_pfp.png"
        resume_link = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + user_data1[0] + "_resume_file.pdf"
        com_link = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + user_data1[0] + "_form_file.pdf"
        return render_template('studentDashboardUpdate.html', **{**user_data, **user_data2, **user_data3}, name=name, resume_pdf=resume_link, company_pdf=com_link, pfp=pfp)
    
    query = "SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM lecturer"
    cursor.execute(query)
    user_data2 = cursor.fetchall()

    query = "SELECT company_name FROM company"
    cursor.execute(query)
    user_data3 = cursor.fetchall()

    cursor.close()
    user_data2 = list(chain.from_iterable(user_data2))
    user_data3 = list(chain.from_iterable(user_data3))
    return render_template('studentDashboard.html', **user_data, lecturers=user_data2, companies=user_data3, name=name)

@student_bp.route("/submitDetail", methods=['POST'])
@login_required
def details():
    userid = session['user_id']
    supervisor = request.form['supervisor_name']
    companmy_name = request.form['company_name']
    resume = request.files['resume']
    com_form = request.files['form']
    pfp = request.files['pfp']

    select_supervisor = "SELECT lec_id FROM lecturer WHERE CONCAT(first_name, ' ', last_name) = %s"
    select_company = "SELECT company_id FROM company WHERE company_name = %s"
    update_sql = "UPDATE student SET supervisor_id = %s, company_id = %s, uploaded = %s WHERE stud_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(select_supervisor, (supervisor,))
    user_data1 = cursor.fetchone()

    cursor.execute(select_company, (companmy_name,))
    user_data2 = cursor.fetchone()

    cursor.execute(update_sql, (user_data1[0], user_data2[0], 1, userid))
    db_conn.commit()
    cursor.close()
    
    stud_resume_file_name = "stud-id-" + str(userid) + "_resume_file" + os.path.splitext(resume.filename)[1]
    stud_form_file_name = "stud-id-" + str(userid) + "_form_file" + os.path.splitext(com_form.filename)[1]
    pfp_file_name = "stud-id-" + str(userid) + "_pfp" + os.path.splitext(pfp.filename)[1]
    s3 = boto3.resource('s3')
    s3.Bucket(custombucket).put_object(Key=stud_resume_file_name, Body=resume, ContentType="application/pdf")
    s3.Bucket(custombucket).put_object(Key=stud_form_file_name, Body=com_form, ContentType="application/pdf")
    s3.Bucket(custombucket).put_object(Key=pfp_file_name, Body=pfp, ContentType="img/png")
    return redirect(url_for('student.profile'))

@student_bp.route('/get_lecturer_email')
def get_lecturer_email():
    selected_lecturer = request.args.get('lecturer')
    cursor = db_conn.cursor()
    query = "SELECT email FROM lecturer WHERE CONCAT(first_name, ' ', last_name) = %s"
    cursor.execute(query, (selected_lecturer,))
    user_data1 = cursor.fetchone()
    cursor.close()    
    return jsonify({'email': user_data1[0]})

@student_bp.route('/get_company')
def get_company():
    selected_lecturer = request.args.get('company')
    cursor = db_conn.cursor()
    query = "SELECT email, address FROM company WHERE company_name = %s"
    cursor.execute(query, (selected_lecturer,))
    user_data1 = cursor.fetchone()
    cursor.close()    
    return jsonify({'email': user_data1[0], 'address': user_data1[1]})

@student_bp.route("/register", methods=['GET', 'POST'])
def registerPage():
    return render_template('student_register.html')

@student_bp.route("/renew", methods=['GET', 'POST'])
def forgetPassword():
    return render_template('forgetPassword.html')

@student_bp.route("/registerAcc", methods=['POST'])
def registerAcc():
    stud_id = request.form['stud_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    address = request.form['address']
    tel_num = request.form['tel_num']
    email = request.form['email']
    ic = request.form['ic']

    insert_sql = "INSERT INTO student (stud_id, first_name, last_name, address, tel_num, email, IC) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    cursor.execute(insert_sql, (stud_id, first_name, last_name, address, tel_num, email, ic))
    db_conn.commit()
    cursor.close()

    return redirect(url_for('student.studhome'))

@student_bp.route("/jobBrowsing", methods=['GET', 'POST'])
def studJob():
    select_sql = "SELECT company.company_name, company.company_id, job_portal.job_title, job_portal.job_id FROM job_portal INNER JOIN company ON job_portal.company_id = company.id"
    cursor = db_conn.cursor()
    cursor.execute(select_sql)
    user_data = cursor.fetchall()

    select_sql = "SELECT CONCAT(first_name, ' ', last_name) FROM student WHERE stud_id = %s"
    cursor.execute(select_sql, (session["user_id"]))
    user_data2 = cursor.fetchone()
    cursor.close()

    user_data_list = []
    for row in user_data:
        company_img = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + row[1] + "_pfp_img.png"
        user_data_dict = {
            "company_name": row[0],
            "job_title": row[2],
            "job_link": row[3],
            "company_img" : company_img
        }
        user_data_list.append(user_data_dict)
    s3 = boto3.resource('s3')
    s3_object_url = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + str(session["user_id"]) + "_pfp.png"
    try:
        s3.head_object(Bucket=s3_bucket_name, Key=s3_object_key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3_object_url = '/assets/img/noprofil.jpg'
    return render_template('studentView.html', card_data=user_data_list, student_name=user_data2[0], stud_pfp=s3_object_url)
