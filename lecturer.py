from flask import Flask, Blueprint, render_template, request, redirect, url_for
from pymysql import connections
import os
from config import *

lecturer_bp = Blueprint('lecturer', __name__)

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
table = 'lecturer'

@lecturer_bp.route("/", methods=['GET', 'POST'])
def lechome():
    return render_template('lecturer.html')

@lecturer_bp.route("/renew", methods=['GET', 'POST'])
def forgetPassword():
    return render_template('forgetPassword.html')

@lecturer_bp.route("/validate", methods=['GET', 'POST'])
def valLogin():
    email = request.form['email']

    cursor = db_conn.cursor()
    query = "SELECT email, lec_id FROM lecturer WHERE email = %s"
    cursor.execute(query, (email,))
    user_data = cursor.fetchone()

    cursor.close()
    if user_data:
        return redirect(url_for('lecturer.profile', username=user_data[1]))
    else:
        return "User not found"

@lecturer_bp.route("/profile/<username>")
def profile(username):
    cursor = db_conn.cursor()
    lec_name = "SELECT CONCAT(last_name, ' ', first_name) AS full_name FROM lecturer WHERE lec_id = %s"
    stud_query = "SELECT CONCAT(student.last_name, ' ', student.first_name), student.stud_id, student.email, student.tel_num, company.company_name FROM lecturer INNER JOIN student ON student.supervisor_id = lecturer.lec_id INNER JOIN company ON student.company_id = company.company_id WHERE lec_id = %s AND student.uploaded = %s"
    cursor.execute(lec_name, (username,))
    name = cursor.fetchone()

    cursor.execute(stud_query, (username, 1))
    user_data1 = cursor.fetchall()
    cursor.close()
    
    user_data_list = []
    for row in user_data1:
        user_data_dict = {
            "name": row[0],
            "id": row[1],
            "email": row[2],
            "phone": row[3],
            "company": row[4]
        }
        user_data_list.append(user_data_dict)
    return render_template('lecturerDashboard.html', lecturer_name=name[0], data_list=user_data_list)

@lecturer_bp.route("/Studprofile/<username>")
def lecView(username):
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

    resume_link = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + user_data1[0] + "_resume_file.pdf"
    com_link = "https://" + bucket + ".s3.amazonaws.com/" + "stud-id-" + user_data1[0] + "_form_file.pdf"
    return render_template('lecturerStudentView.html', **{**user_data, **user_data2, **user_data3}, name=name, resume_pdf=resume_link, company_pdf=com_link)

@lecturer_bp.route('/update_status', methods=['POST'])
def update_status():
    student_id = request.form.get('student_id')
    new_status = request.form.get('status')

    cursor = db_conn.cursor()
    update_sql = "UPDATE student SET approved_status = %s WHERE stud_id = %s"
    cursor.execute(update_sql, (new_status, student_id))
    db_conn.commit()
    cursor.close()
    response = {'message': 'Status updated successfully'}
    return jsonify(response)
