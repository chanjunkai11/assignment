from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify
from pymysql import connections
import os
from config import *
import datetime
import boto3
import botocore.exceptions

admin_bp = Blueprint('admin', __name__)

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
table = 'admin'

@admin_bp.route("/", methods=['GET', 'POST'])
def home():
    return render_template('admin.html')

@admin_bp.route("/validate", methods=['GET', 'POST'])
def valLogin():
    email = request.form['email']

    cursor = db_conn.cursor()
    query = "SELECT email, admin_id FROM admin WHERE email = %s"
    cursor.execute(query, (email,))
    user_data = cursor.fetchone()

    cursor.close()
    if user_data:
        return redirect(url_for('admin.profile', username=user_data[1]))
    else:
        return "User not found"

@admin_bp.route("/register", methods=['GET', 'POST'])
def registerPage():
    return render_template('admin_register.html')

@admin_bp.route("/renew", methods=['GET', 'POST'])
def forgetPassword():
    return render_template('forgetPassword.html')

@admin_bp.route("/registerAcc", methods=['POST'])
def registerAcc():
    id = request.form['admin_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']

    insert_sql = "INSERT INTO admin VALUES (%s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (id, first_name, last_name, email))
        db_conn.commit()
    finally:
        cursor.close()

    return redirect(url_for('admin.home'))

@admin_bp.route("/profile/<username>")
def profile(username):
    cursor = db_conn.cursor()
    admin_name = "SELECT CONCAT(last_name, ' ', first_name) AS full_name FROM admin WHERE admin_id = %s"
    com_query = "SELECT company_name, company_id, address, approved_status FROM company"
    cursor.execute(admin_name, (username,))
    name = cursor.fetchone()

    cursor.execute(com_query)
    user_data1 = cursor.fetchall()
    cursor.close()

    user_data_list = []
    for row in user_data1:
        user_data_dict = {
            "name": row[0],
            "id": row[1],
            "address": row[2],
            "user_role" : row[3]
        }
        user_data_list.append(user_data_dict)
    return render_template('adminDashboard.html', admin_name=name[0], data_list=user_data_list)

@admin_bp.route("/Companyprofile/<username>")
def lecView(username):
    cursor = db_conn.cursor()
    query = "SELECT * FROM company WHERE company_id = %s"
    cursor.execute(query, (username,))
    user_data1 = cursor.fetchone()

    user_data = {
        'company_name' : user_data1[1],
        'id' : user_data1[0],
        'email' : user_data1[3],
        'tel_num' : user_data1[4],
        'address' : user_data1[2],
        'hq' : user_data1[6],
        'hr' : user_data1[7],
    }
    company_img = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + str(user_data1[0]) + "_pfp_img.png"
    key = "com-id-" + str(user_data1[0]) + "_pfp_img.png"
    s3 = boto3.resource('s3')
    try:
        s3.Object(bucket, key).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            company_img = "/assets/img/noprofil.jpg"
    legal_link = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + user_data1[0] + "_legal_file.pdf"
    epf_link = "https://" + bucket + ".s3.amazonaws.com/" + "com-id-" + user_data1[0] + "_epf_file.pdf"
    return render_template('adminCompanyView.html', **user_data,legal_pdf=legal_link, epf_pdf=epf_link, pfp = company_img)

@admin_bp.route('/update_status', methods=['POST'])
def update_status():
    student_id = request.form.get('company_id')
    new_status = request.form.get('status')

    cursor = db_conn.cursor()
    update_sql = "UPDATE company SET approved_status = %s WHERE company_id = %s"
    cursor.execute(update_sql, (new_status, student_id))
    db_conn.commit()
    cursor.close()
    response = {'message': 'Status updated successfully'}
    return jsonify(response)

def format_timedelta(td):
    # Extract hours, minutes, and seconds components
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as HH:MM:SS with leading zeros
    formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

    return formatted_time
