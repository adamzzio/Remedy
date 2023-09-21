# ===== Import Library ======
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
import pandas as pd
import numpy as np
import json
import plotly
import plotly.express as px
import re
import string
from wordcloud import WordCloud
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from mpstemmer import MPStemmer
nltk.download('punkt')
nltk.download('stopwords')
import pickle as pkl

# ===== Load Model & Vectorizer =====
filename_model_pretest = 'static/model/model_rf_pretest_remedy.sav'
filename_tfidf_pretest = 'static/model/tfidf_pretest_remedy.pickle'
filename_model_posttest = 'static/model/model_rf_posttest_remedy.sav'
filename_tfidf_posttest = 'static/model/tfidf_posttest_remedy.pickle'

def load_model():
    model_pretest = pkl.load(open(filename_model_pretest, 'rb'))
    tfidf_pretest = pkl.load(open(filename_tfidf_pretest, 'rb'))
    model_posttest = pkl.load(open(filename_model_posttest, 'rb'))
    tfidf_posttest = pkl.load(open(filename_tfidf_posttest, 'rb'))
    return model_pretest, tfidf_pretest, model_posttest, tfidf_posttest

model_pretest, tfidf_pretest, model_posttest, tfidf_posttest = load_model()

# ===== Text Cleaning =====
# Initialize MPStemmer Instance
stemmer = MPStemmer()
# Set Indonesian Stopwords
list_stopwords = stopwords.words('indonesian')
list_stopwords = set(list_stopwords)

def remove_mention(text):
  return re.sub(r'@[A-Za-z0-9]+\s?', '', str(text))
def remove_hashtag(text):
  return re.sub(r'#[A-Za-z0-9]+\s?', '', str(text))
def remove_https(text):
  return re.sub(r'https:\/\/.*', '', str(text))
def remove_number(text):
  return re.sub(r'\d+', '', str(text))
def remove_punc(text):
  return text.translate(str.maketrans('','',string.punctuation+"“"+"🫶"))
def remove_whitespace(text):
  return text.strip()
def remove_whitespace_multi(text):
  return re.sub('\s+', ' ', text)
def remove_single_char(text):
  return re.sub(r'\b[a-zA-Z]\b', '', text)
def word_tokenize_wrapper(text):
  return word_tokenize(text)
def stemming(words):
  return [stemmer.stem(word) for word in words]
def remove_stopwords(words):
  return [word for word in words if word not in list_stopwords]

# ===== Initialize Flask App ======
app = Flask(__name__, static_url_path='/static')

# # ===== Set Connection to MySQL DB ======
app.secret_key = 'remedy-v1'
app.config['MYSQL_HOST'] ='localhost'
app.config['MYSQL_USER'] ='root'
app.config['MYSQL_PASSWORD'] =''
app.config['MYSQL_DB'] ='remedy_pkmkc'
mysql = MySQL(app)

# ===== Set Landing Page ======
@app.route('/')
def home():
    return render_template('home.html')

# ===== Set Infopedia Page 1 ======
@app.route('/berita1')
def berita1():
    return render_template('berita1.html')

# ===== Set Infopedia Page 2 ======
@app.route('/berita2')
def berita2():
    return render_template('berita2.html')

# ===== Set Infopedia Page 3 ======
@app.route('/berita3')
def berita3():
    return render_template('berita3.html')

# ===== Set Login Page ======
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # cek data username
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM role WHERE username=%s', (username,))
        akun = cursor.fetchone()
        if akun is None:
            flash('Login Gagal, Cek Username Anda', 'danger')
        elif not check_password_hash(akun[4], password):
            flash('Login Gagal, Cek Password Anda', 'danger')
            # flash(akun, 'danger')
            # flash(akun[1], 'danger')
        else:
            session['loggedin'] = True
            session['id'] = akun[0]
            session['name'] = akun[1]
            session['email'] = akun[2]
            session['username'] = akun[3]
            session['level'] = akun[5]
            return redirect(url_for('main'))
    return render_template('login.html')

# ===== Set Register Page ======
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        nama = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        level = request.form['level']

        # cek username atau email
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM role WHERE username=%s OR email=%s', (username, email,))
        akun = cursor.fetchone()
        if akun is None:
            cursor.execute('INSERT INTO role VALUES (NULL, %s, %s, %s, %s, %s)',
                           (nama, email, username, generate_password_hash(password), level))
            mysql.connection.commit()
            flash('Registrasi Berhasil', 'success')
        else:
            flash('Username atau email sudah ada', 'danger')

    return render_template('register.html')

# ===== Set Register Page Ghost Mode ======
@app.route('/register_ghost_mode_for_admin', methods=('GET', 'POST'))
def register_ghost_mode():
    if request.method == 'POST':
        nama = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        level = request.form['level']

        # cek username atau email
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM role WHERE username=%s OR email=%s', (username, email,))
        akun = cursor.fetchone()
        if akun is None:
            cursor.execute('INSERT INTO role VALUES (NULL, %s, %s, %s, %s, %s)',
                           (nama, email, username, generate_password_hash(password), level))
            mysql.connection.commit()
            flash('Registrasi Berhasil', 'success')
        else:
            flash('Username atau email sudah ada', 'danger')

    return render_template('register_admin_only.html')

# ===== Set Forgot Password Page =====
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email FROM role WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            return redirect(url_for('reset_password', user_id=user[0]))
        else:
            flash('Email not found', 'error')

    return render_template('forgot_password.html')

# ===== Set Reset Password Page =====
@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            hash_password = generate_password_hash(new_password)

            cur = mysql.connection.cursor()
            cur.execute("UPDATE role SET password = %s WHERE id = %s", (hash_password, user_id))
            mysql.connection.commit()
            cur.close()

            flash('Password updated successfully', 'success')
            return redirect(url_for('login'))
        else:
            flash('Password tidak sama', 'danger')

    return render_template('reset_password.html')

# ===== Set Main Page ======
@app.route('/main')
def main():
    if 'loggedin' in session:
        return render_template('main.html')
    flash('Harap Login dulu','danger')
    return redirect(url_for('login'))

# ===== Set Music Page ======
@app.route('/music')
def music():
    if 'loggedin' in session:
        return render_template('music_player.html')
    flash('Harap Login dulu','danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Profil User ======
@app.route('/main/profil_user')
def profil_user():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_user WHERE id_user = %s", (id,))
        data = cur.fetchone()
        cur.close()

        return render_template('profil_user.html', data_profil=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Profil Psikolog ======
@app.route('/main/profil_psikolog')
def profil_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Psikolog')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_psikolog WHERE id_psikolog = %s", (id,))
        data = cur.fetchone()
        cur.close()

        return render_template('profil_psikolog.html', data_psikolog=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Profil Fasilitator ======
@app.route('/main/profil_fasilitator')
def profil_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Fasilitator')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_fasilitator WHERE id_fasilitator = %s", (id,))
        data = cur.fetchone()
        cur.close()

        return render_template('profil_fasilitator.html', data_fasilitator=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Form Data Diri User ======
@app.route('/main/form_datadiri_user')
def form_datadiri_user():
    if (('loggedin' in session) & (session['level'] == 'User')):
        return render_template('form_datadiri_user.html')
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Form Data Diri Psikolog ======
@app.route('/main/form_datadiri_psikolog')
def form_datadiri_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Psikolog')):
        return render_template('form_datadiri_psikolog.html')
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Form Data Diri Fasilitator ======
@app.route('/main/form_datadiri_fasilitator')
def form_datadiri_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Fasilitator')):
        return render_template('form_datadiri_fasilitator.html')
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Form Screening ======
@app.route('/main/form_screening')
def screening():
    if (('loggedin' in session) & (session['level'] == 'User')):
        return render_template('form_screening.html')
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Form Kenali Diri ======
@app.route('/main/form_kenalidiri')
def kenalidiri():
    if (('loggedin' in session) & (session['level'] == 'User')):
        return render_template('form_kenalidiri.html', totalValue=0)
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi Journaling
@app.route('/main/terapi_journaling')
def journaling():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()
        return render_template('journaling.html', data_hasil=data_hasil)
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi Shambavi Mudra ======
@app.route('/main/terapi_shambavimudra')
def shambavi():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT shambavi1, shambavi2 FROM user_journey WHERE id_journey = %s", (id,))
        data_shambavi = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('shambavimudra.html', data_shambavi=data_shambavi,
                               data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi Mindfulness ======
@app.route('/main/terapi_mindfulness')
def mindfulness():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT mind1, mind2 FROM user_journey WHERE id_journey = %s", (id,))
        data_mind = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('mindfulness.html', data_mind=data_mind, data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi Doodling ======
@app.route('/main/terapi_doodling')
def doodling():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()
        return render_template('doodling.html', data_hasil=data_hasil)
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi MMR ======
@app.route('/main/terapi_mmr')
def mmr():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT mmr1, mmr2 FROM user_journey WHERE id_journey = %s", (id,))
        data_mmr = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('music_muscle.html', data_mmr=data_mmr, data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Terapi Expressive Writing ======
@app.route('/main/terapi_expwrite')
def expwrite():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT expwr1, expwr2, expwr3 FROM user_journey WHERE id_journey = %s", (id,))
        data_expwrite = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('expressive_writing.html', data_expwrite=data_expwrite,
                               data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Pre-Test ======
@app.route('/main/pretest')
def pretest():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()
        return render_template('pretest.html', data_hasil=data_hasil)
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Post-Test ======
@app.route('/main/posttest')
def posttest():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT pre_q1, pre_q2, pre_q3, pre_q4, pre_q5 FROM data_hasil WHERE id_hasil = %s", (id,))
        data_jawab_pretest = cur.fetchone()
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('posttest.html', data_jawab_pretest = data_jawab_pretest,
                               data_hasil=data_hasil)
    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Logout Page ======
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    session.pop('level', None)
    return redirect(url_for('home'))

# ===== CRUD | Insert & Update Data User =====
@app.route('/main/form_datadiri_user', methods=['POST'])
def user_data():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            nama = session['name']
            gender = request.form['gender']
            usia = request.form['age']
            alamat = request.form['alamat']
            pendidikan = request.form['pendidikan']
            instansi = request.form['instansi_edu']
            hp = request.form['hp']

            cur = mysql.connection.cursor()

            # Cek apakah data dengan id_user sudah ada di database
            cur.execute("SELECT * FROM datadiri_user WHERE id_user = %s", (id,))
            existing_data = cur.fetchone()

            if existing_data:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute(
                    "UPDATE datadiri_user SET nama=%s, gender=%s, usia=%s, alamat=%s, pendidikan=%s, instansi=%s, hp=%s WHERE id_user=%s",
                    (nama, gender, usia, alamat, pendidikan, instansi, hp, id))
                flash('Data Berhasil Disimpan', 'success')
            else:
                # Lakukan operasi INSERT untuk data baru
                cur.execute(
                    "INSERT INTO datadiri_user (id_user, nama, gender, usia, alamat, pendidikan, instansi, hp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (id, nama, gender, usia, alamat, pendidikan, instansi, hp))
                flash('Data Berhasil Disimpan', 'success')

            mysql.connection.commit()
            return redirect(url_for('profil_user'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Insert & Update Data Fasilitator =====
@app.route('/main/form_datadiri_fasilitator', methods=['POST'])
def fasilitator_data():
    if (('loggedin' in session) & (session['level'] == 'Fasilitator')):
        if request.method == 'POST':
            id = session['id']
            nama = session['name']
            alamat = request.form['alamat']
            kontak = request.form['kontak']
            cv = request.form['cv']
            status = 'Menunggu'

            cur = mysql.connection.cursor()

            # Cek apakah data dengan id_user sudah ada di database
            cur.execute("SELECT * FROM datadiri_fasilitator WHERE id_fasilitator = %s", (id,))
            existing_data = cur.fetchone()

            if existing_data:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute(
                    "UPDATE datadiri_fasilitator SET nama=%s, alamat=%s, kontak=%s, cv=%s WHERE id_fasilitator=%s",
                    (nama, alamat, kontak, cv, id))
                flash('Data Berhasil Disimpan', 'success')
            else:
                # Lakukan operasi INSERT untuk data baru
                cur.execute(
                    "INSERT INTO datadiri_fasilitator (id_fasilitator, nama, alamat, kontak, cv, status) VALUES (%s, %s, %s, %s, %s, %s)",
                    (id, nama, alamat, kontak, cv, status))
                flash('Data Berhasil Disimpan', 'success')

            mysql.connection.commit()
            return redirect(url_for('profil_fasilitator'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Insert & Update Data Psikolog =====
@app.route('/main/form_datadiri_psikolog', methods=['POST'])
def psikolog_data():
    if (('loggedin' in session) & (session['level'] == 'Psikolog')):
        if request.method == 'POST':
            id = session['id']
            nama = session['name']
            sipp = request.form['sipp']
            spesialisasi = request.form['spesialisasi']
            pengalaman = request.form['pengalaman']
            alamat = request.form['alamat']
            kontak = request.form['kontak']
            cv = request.form['cv']
            status = 'Menunggu'

            cur = mysql.connection.cursor()

            # Cek apakah data dengan id_user sudah ada di database
            cur.execute("SELECT * FROM datadiri_psikolog WHERE id_psikolog = %s", (id,))
            existing_data = cur.fetchone()

            if existing_data:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute(
                    "UPDATE datadiri_psikolog SET nama=%s, sipp=%s, spesialisasi=%s, pengalaman=%s, alamat=%s, kontak=%s, cv=%s WHERE id_psikolog=%s",
                    (nama, sipp, spesialisasi, pengalaman, alamat, kontak, cv, id))
                flash('Data Berhasil Disimpan', 'success')
            else:
                # Lakukan operasi INSERT untuk data baru
                cur.execute(
                    "INSERT INTO datadiri_psikolog (id_psikolog, nama, sipp, spesialisasi, pengalaman, alamat, kontak, cv, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (id, nama, sipp, spesialisasi, pengalaman, alamat, kontak, cv, status))
                flash('Data Berhasil Disimpan', 'success')

            mysql.connection.commit()
            return redirect(url_for('profil_psikolog'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | CRUD User ======
@app.route('/main/crud_user')
def crud_user():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_user ORDER BY id_user")
        data = cur.fetchall()
        cur.close()

        return render_template('crud_user.html', data_user=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | CRUD Fasilitator ======
@app.route('/main/crud_fasilitator')
def crud_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_fasilitator ORDER BY id_fasilitator")
        data = cur.fetchall()
        cur.close()

        return render_template('crud_fasilitator.html', data_fasilitator=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | CRUD Psikolog ======
@app.route('/main/crud_psikolog')
def crud_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_psikolog ORDER BY id_psikolog")
        data = cur.fetchall()
        cur.close()

        return render_template('crud_psikolog.html', data_psikolog=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Seleksi Fasilitator ======
@app.route('/main/seleksi_fasilitator')
def seleksi_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_fasilitator ORDER BY id_fasilitator")
        data = cur.fetchall()
        cur.close()

        return render_template('seleksi_fasilitator.html', data_seleksi_fasilitator=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Seleksi Psikolog ======
@app.route('/main/seleksi_psikolog')
def seleksi_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_psikolog ORDER BY id_psikolog")
        data = cur.fetchall()
        cur.close()

        return render_template('seleksi_psikolog.html', data_seleksi_psikolog=data)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Delete User ======
@app.route('/delete_user/<int:id>', methods=["GET"])
def delete_user(id):
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        # Cari id_user yang terkait di tabel datadiri_user
        cur.execute("SELECT id_user FROM datadiri_user WHERE id_user=%s", (id,))
        result_user = cur.fetchone()
        # Cari id_user yang terkait di tabel data_hasil
        cur.execute("SELECT id_hasil FROM data_hasil WHERE id_hasil=%s", (id,))
        result_hasil = cur.fetchone()
        # Cari id_user yang terkait di tabel user_feedback
        cur.execute("SELECT id_user FROM user_feedback WHERE id_user=%s", (id,))
        result_feedback = cur.fetchone()
        # Cari id_user yang terkait di tabel user_journey
        cur.execute("SELECT id_journey FROM user_journey WHERE id_journey=%s", (id,))
        result_journey = cur.fetchone()

        if result_user:
            # Ada baris terkait di tabel datadiri_user, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM datadiri_user WHERE id_user=%s", (id,))
        if result_hasil:
            # Ada baris terkait di tabel data_hasil, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM data_hasil WHERE id_hasil=%s", (id,))
        if result_feedback:
            # Ada baris terkait di tabel user_feedback, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM user_feedback WHERE id_user=%s", (id,))
        if result_journey:
            # Ada baris terkait di tabel user_journey, hapus baris tersebut terlebih dahulu
            cur.result_journey("DELETE FROM user_journey WHERE id_journey=%s", (id,))

        # Hapus baris dari tabel role setelah menghapus yang terkait di datadiri_user
        cur.execute("DELETE FROM role WHERE id=%s", (id,))
        flash('Data Berhasil Dihapus', 'danger')
        mysql.connection.commit()
        return redirect( url_for('crud_user'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Delete Psikolog ======
@app.route('/delete_psikolog/<int:id>', methods=["GET"])
def delete_psikolog(id):
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        # Cari id_psikolog yang terkait di tabel datadiri_psikolog
        cur.execute("SELECT id_psikolog FROM datadiri_psikolog WHERE id_psikolog=%s", (id,))
        result = cur.fetchone()

        if result:
            # Ada baris terkait di tabel datadiri_psikolog, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM datadiri_psikolog WHERE id_psikolog=%s", (id,))

        # Hapus baris dari tabel role setelah menghapus yang terkait di datadiri_psikolog
        cur.execute("DELETE FROM role WHERE id=%s", (id,))
        flash('Data Berhasil Dihapus', 'danger')
        mysql.connection.commit()
        return redirect( url_for('crud_psikolog'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Delete Fasilitator ======
@app.route('/delete_fasilitator/<int:id>', methods=["GET"])
def delete_fasilitator(id):
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        # Cari id_fasilitator yang terkait di tabel datadiri_fasilitator
        cur.execute("SELECT id_fasilitator FROM datadiri_fasilitator WHERE id_fasilitator=%s", (id,))
        result_fasilitator = cur.fetchone()
        # Cari id_fasilitator yang terkait di tabel data_komunitas
        cur.execute("SELECT id_fasilitator FROM data_komunitas WHERE id_fasilitator=%s", (id,))
        result_komunitas = cur.fetchone()

        if result_fasilitator:
            # Ada baris terkait di tabel datadiri_fasilitator, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM datadiri_fasilitator WHERE id_fasilitator=%s", (id,))
        if result_komunitas:
            # Ada baris terkait di tabel data_komunitas, hapus baris tersebut terlebih dahulu
            cur.execute("DELETE FROM data_komunitas WHERE id_fasilitator=%s", (id,))

        # Hapus baris dari tabel role setelah menghapus yang terkait di datadiri_fasilitator
        cur.execute("DELETE FROM role WHERE id=%s", (id,))
        flash('Data Berhasil Dihapus', 'danger')
        mysql.connection.commit()
        return redirect( url_for('crud_fasilitator'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Update Seleksi Psikolog ======
@app.route('/update_seleksi_psikolog', methods=['POST'])
def update_seleksi_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        if request.method == 'POST':
            id = request.form['id']
            status = request.form['status']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE datadiri_psikolog SET status=%s WHERE id_psikolog=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')
            mysql.connection.commit()
            return redirect(url_for('seleksi_psikolog'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Update Seleksi Fasilitator ======
@app.route('/update_seleksi_fasilitator', methods=['POST'])
def update_seleksi_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        if request.method == 'POST':
            id = request.form['id']
            status = request.form['status']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE datadiri_fasilitator SET status=%s WHERE id_fasilitator=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')
            mysql.connection.commit()

            return redirect(url_for('seleksi_fasilitator'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Katalog Psikolog ======
@app.route('/main/katalog')
def katalog_psikolog():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        status = 'Diterima'
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM datadiri_psikolog WHERE status = 'Diterima' ORDER BY id_psikolog")
        data = cur.fetchall()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('katalog_psikolog.html', data_katalog=data, data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Komunitas ======
@app.route('/main/komunitas')
def komunitas():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        status = 'Diterima'
        cur = mysql.connection.cursor()

        # Get the user's name using user_id from datadiri_user
        cur.execute("SELECT nama FROM datadiri_user WHERE id_user = %s", (id,))
        user_data = cur.fetchone()
        # get user journey
        cur.execute("SELECT * FROM user_journey WHERE id_journey = %s", (id,))
        data_sehatp = cur.fetchone()

        if user_data:
            user_nama = user_data[0]

            # Fetch data_komunitas using user's name to get group name
            cur.execute("SELECT grup FROM data_komunitas WHERE nama_user = %s", (user_nama,))
            data_grup = cur.fetchone()
            nama_grup = data_grup[0]
            cur.execute("SELECT * FROM data_komunitas WHERE grup = %s", (nama_grup,))
            data_komunitas_user = cur.fetchall()
            cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
            data_hasil = cur.fetchone()
            cur.close()

            return render_template('komunitas.html', data_komunitas_user=data_komunitas_user,
                                   data_hasil=data_hasil, data_sehatp=data_sehatp)
        else:
            cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
            data_hasil = cur.fetchone()
            flash('Informasi pengguna tidak ditemukan', 'danger')
            return render_template('komunitas.html', data_hasil=data_hasil, data_sehatp=data_sehatp)

        flash('Harap Login dulu', 'danger')
        return redirect(url_for('login'))

# ===== Set Main Page | Pemulihan ======
@app.route('/main/pemulihan')
def pemulihan():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id_hasil, kd_awal, kd_akhir, pre_skor, post_skor, status, tingkat FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.execute("SELECT jurnal, mmr1, mmr2, shambavi1, shambavi2 FROM data_pemulihan WHERE id_pemulihan = %s", (id,))
        data_pemulihan = cur.fetchone()
        cur.execute("SELECT * FROM user_journey WHERE id_journey = %s", (id,))
        data_sehatp = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil2 = cur.fetchone()

        tingkat_akhir = ''

        cur.close()

        if data_pemulihan and data_hasil:
            jurnal = data_pemulihan[0]
            mmr1 = data_pemulihan[1]
            mmr2 = data_pemulihan[2]
            shambavi1 = data_pemulihan[3]
            shambavi2 = data_pemulihan[4]
            id_hasil = data_hasil[0]
            kd_awal = data_hasil[1]
            kd_akhir = data_hasil[2]
            pre_skor = data_hasil[3]
            post_skor = data_hasil[4]
            status = data_hasil[5]
            tingkat = data_hasil[6]
            skor_beda = kd_awal - kd_akhir

            if kd_akhir < 0:
                tingkat_akhir = tingkat_akhir + 'Tidak Valid'
            elif (kd_akhir >= 0 and kd_akhir <= 10):
                tingkat_akhir = tingkat_akhir + 'Non-PTSD'
            elif (kd_akhir >= 11 and kd_akhir <= 20):
                tingkat_akhir = tingkat_akhir + 'PTSD Ringan'
            elif (kd_akhir >= 21 and kd_akhir <= 40):
                tingkat_akhir = tingkat_akhir + 'PTSD Sedang'
            elif (kd_akhir >= 41 and kd_akhir <= 80):
                tingkat_akhir = tingkat_akhir + 'PTSD Berat'
            else:
                tingkat_akhir = tingkat_akhir + 'Tidak Valid'

            return render_template('pemulihan.html', kd_awal=kd_awal, kd_akhir=kd_akhir, pre_skor=pre_skor,
                                   post_skor=post_skor, status=status, tingkat=tingkat, tingkat_akhir=tingkat_akhir,
                                   skor_beda=skor_beda, data_hasil=data_hasil, jurnal=jurnal, mmr1=mmr1, mmr2=mmr2,
                                   shambavi1=shambavi1, shambavi2=shambavi2, data_hasil2=data_hasil2,
                                   data_sehatp=data_sehatp)
        else:
            return render_template('pemulihan.html', data_hasil=data_hasil, data_hasil2=data_hasil2,
                                   data_sehatp=data_sehatp)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Update Sesi Pemulihan =====
@app.route('/main/pemulihan', methods=['POST'])
def update_pemulihan():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        sesi = request.form['pemulihan']
        status = 'Sudah'
        if sesi == 'journaling':
            cur.execute("UPDATE data_pemulihan SET jurnal=%s WHERE id_pemulihan=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')
        elif sesi == 'mmr1':
            cur.execute("UPDATE data_pemulihan SET mmr1=%s WHERE id_pemulihan=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')
        elif sesi == 'mmr2':
            cur.execute("UPDATE data_pemulihan SET mmr2=%s WHERE id_pemulihan=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')
        elif sesi == 'shambavi1':
            cur.execute("UPDATE data_pemulihan SET shambavi1=%s WHERE id_pemulihan=%s", (status, id))
            cur.execute("UPDATE data_pemulihan SET shambavi2=%s WHERE id_pemulihan=%s", (status, id))
            flash('Data Berhasil Di-Update', 'success')

        mysql.connection.commit()
        return redirect(url_for('pemulihan'))


# ===== Set Main Page | User Journey ======
@app.route('/main/user_journey')
def user_journey():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user_journey WHERE id_journey = %s", (id,))
        data_journey = cur.fetchone()
        cur.execute("SELECT pre_q1, post_q1 FROM data_hasil WHERE id_hasil = %s", (id,))
        data_prepost = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()
        cur.close()

        return render_template('user_journey.html', data_journey=data_journey, data_prepost=data_prepost,
                               data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | User Feedback
@app.route('/main/user_feedback')
def user_feedback():
    if (('loggedin' in session) & (session['level'] == 'User')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama FROM datadiri_psikolog WHERE status = 'Diterima'")
        psikolog_names = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT nama FROM datadiri_fasilitator WHERE status = 'Diterima'")
        fasilitator_names = [row[0] for row in cur.fetchall()]
        cur.close()

        return render_template('user_feedback.html', psikolog_names=psikolog_names,
                               fasilitator_names = fasilitator_names)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Insert User Feedback
@app.route('/main/user_feedback', methods=['POST'])
def insert_feedback():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            kategori = request.form['kategori']
            deskripsi = request.form['deskripsi']
            rating = request.form['rating']
            nama_psi = request.form['psikolog']
            deskripsi_psi = request.form['deskripsi_psikolog']
            rating_psi = request.form['rating_psikolog']
            nama_fast = request.form['fasilitator']
            deskripsi_fast = request.form['deskripsi_fasilitator']
            rating_fast = request.form['rating_fasilitator']

            cur = mysql.connection.cursor()

            cur.execute("INSERT INTO user_feedback (id_user, kategori, deskripsi, rating, nama_psikolog, deskripsi_psikolog, rating_psikolog, nama_fasilitator, deskripsi_fasilitator, rating_fasilitator) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (id, kategori, deskripsi, rating, nama_psi, deskripsi_psi, rating_psi, nama_fast, deskripsi_fast, rating_fast))

            flash('Feedback Anda berhasil disimpan', 'success')
            mysql.connection.commit()
            return redirect(url_for('user_feedback'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Insert Nilai Kenali Diri =====
@app.route('/main/form_kenalidiri', methods=['POST'])
def save_total_value():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            total_value = 0

            for i in range(1, 21):  # Loop melalui pertanyaan q1 sampai q5
                question_name = f'kd{i}'  # Membentuk nama field berdasarkan nomor pertanyaan
                question_value = int(request.form.get(question_name))
                total_value += question_value

            pre_q1 = 'Kosong'
            pre_q2 = 'Kosong'
            pre_q3 = 'Kosong'
            pre_q4 = 'Kosong'
            pre_q5 = 'Kosong'
            post_q1 = 'Kosong'
            post_q2 = 'Kosong'
            post_q3 = 'Kosong'

            sehatp = 'Belum'

            # Cek apakah data dengan id_user sudah ada di database
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM data_hasil WHERE id_hasil = %s", (id,))
            existing_data = cur.fetchone()

            if (0 <= total_value <= 10):
                status = "Non-PTSD"
                tingkat = "Non-PTSD"
            elif (11 <= total_value <= 20):
                status = "PTSD"
                tingkat = "PTSD Ringan"
            elif (21 <= total_value <= 40):
                status = "PTSD"
                tingkat = "PTSD Sedang"
            elif (41 <= total_value <= 80):
                status = "PTSD"
                tingkat = "PTSD Berat"
            else:
                status = "Tidak Diketahui"
                tingkat = "Tidak Diketahui"

            # Simpan data ke database
            if existing_data:
                if sesi == 'Pre-Test':
                    cur.execute(
                        "UPDATE data_hasil SET status=%s, tingkat=%s, kd_awal=%s WHERE id_hasil=%s",
                        (status, tingkat, total_value, id))
                else:
                    cur.execute(
                        "UPDATE data_hasil SET status=%s, tingkat=%s, kd_akhir=%s WHERE id_hasil=%s",
                        (status, tingkat, total_value, id))
            else:
                if sesi == 'Pre-Test':
                    cur.execute("INSERT INTO data_hasil (id_hasil, pre_q1, pre_q2, pre_q3, pre_q4, pre_q5, post_q1, post_q2, post_q3, kd_awal, kd_akhir, pre_skor, post_skor, status, tingkat) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (id, pre_q1, pre_q2, pre_q3, pre_q4, pre_q5, post_q1, post_q2, post_q3, total_value, 0, 0, 0, status, tingkat))
                    cur.execute("INSERT INTO user_journey (id_journey, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10, j11, mmr1, mmr2, shambavi1, shambavi2, mind1, mind2, doodling, expwr1, expwr2, expwr3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (id, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp))
                    cur.execute("INSERT INTO data_pemulihan (id_pemulihan, jurnal, mmr1, mmr2, shambavi1, shambavi2) VALUES (%s, %s, %s, %s, %s, %s)",
                                (id, sehatp, sehatp, sehatp, sehatp, sehatp))
                else:
                    cur.execute("INSERT INTO data_hasil (id_hasil, pre_q1, pre_q2, pre_q3, pre_q4, pre_q5, post_q1, post_q2, post_q3, kd_awal, kd_akhir, pre_skor, post_skor, status, tingkat) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (id, pre_q1, pre_q2, pre_q3, pre_q4, pre_q5, post_q1, post_q2, post_q3, 0, total_value, 0, 0, status, tingkat))
                    cur.execute("INSERT INTO user_journey (id_journey, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10, j11, mmr1, mmr2, shambavi1, shambavi2, mind1, mind2, doodling, expwr1, expwr2, expwr3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (id, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp, sehatp))


            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page | Summary Hasil ======
@app.route('/main/hasil')
def hasil():
    if (('loggedin' in session) & (session['level'] == 'User')):
        id = session['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT kd_awal, kd_akhir, pre_skor, post_skor FROM data_hasil WHERE id_hasil = %s", (id,))
        grafik_bar_hasil = cur.fetchone()
        cur.execute("SELECT status FROM data_hasil WHERE id_hasil = %s", (id,))
        data_hasil = cur.fetchone()

        if grafik_bar_hasil:
            kd_awal = grafik_bar_hasil[0]
            kd_akhir = grafik_bar_hasil[1]
            pre_skor = grafik_bar_hasil[2]
            post_skor = grafik_bar_hasil[3]

            # === BARCHART KENALI DIRI ===
            data_bar_kd = pd.DataFrame({'Jenis Test':['Pre-Test', 'Post-Test'],
                                        'Skor Kenali Diri':[kd_awal, kd_akhir]})
            data_bar_kd['Label'] = data_bar_kd['Skor Kenali Diri']
            data_bar_kd['Label'] = data_bar_kd['Label'].replace({0: 'Belum Tes'})

            fig_bar_kd = px.bar(data_bar_kd,
                                x='Jenis Test',
                                y="Skor Kenali Diri",
                                color_discrete_sequence=["#0083B8"] * len(data_bar_kd),
                                template="plotly_white",
                                text='Label')
            fig_bar_kd.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=(dict(showgrid=False))
            )
            # Mengatur batas sumbu Y
            fig_bar_kd.update_yaxes(range=[0, 90])
            fig_bar_kd.update_traces(textfont_size=14, textangle=0, textposition="outside")
            # Create graphJSON
            graphJSON_bar_kd = json.dumps(fig_bar_kd, cls=plotly.utils.PlotlyJSONEncoder)

            # === BARCHART PRE-POST ===
            data_bar_prepost = pd.DataFrame({'Jenis Test': ['Pre-Test', 'Post-Test'],
                                             'Skor': [pre_skor, post_skor]})
            data_bar_prepost['Label'] = data_bar_prepost['Skor'].astype('int')
            data_bar_prepost['Label'] = data_bar_prepost['Label'].replace({0:'Belum Tes',
                                                                           1:'Sangat Tidak Baik',
                                                                           2:'Tidak Baik',
                                                                           3:'Cukup',
                                                                           4:'Baik',
                                                                           5:'Sangat Baik'})

            fig_bar_prepost = px.bar(data_bar_prepost,
                                     x='Jenis Test',
                                     y="Skor",
                                     color_discrete_sequence=["#0083B8"] * len(data_bar_prepost),
                                     template="plotly_white",
                                     text='Label')
            fig_bar_prepost.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=(dict(showgrid=False))
            )
            # Mengatur batas sumbu Y
            fig_bar_prepost.update_yaxes(range=[0, 6])
            fig_bar_prepost.update_traces(textfont_size=14, textangle=0, textposition="outside")
            # Create graphJSON
            graphJSON_bar_prepost = json.dumps(fig_bar_prepost, cls=plotly.utils.PlotlyJSONEncoder)

            # Get pre-test & post-test
            cur.execute("SELECT pre_q1, pre_q2, pre_q3, pre_q4, pre_q5 FROM data_hasil WHERE id_hasil = %s", (id,))
            data_jawab_pretest = cur.fetchone()
            cur.execute("SELECT post_q1, post_q2, post_q3 FROM data_hasil WHERE id_hasil = %s", (id,))
            data_jawab_posttest = cur.fetchone()
            cur.close()

            return render_template('hasil.html', viz_kenalidiri=graphJSON_bar_kd, viz_prepost=graphJSON_bar_prepost,
                                   data_jawab_pretest = data_jawab_pretest, data_jawab_posttest = data_jawab_posttest,
                                   kd_awal = kd_awal, kd_akhir = kd_akhir, pre_skor = pre_skor, post_skor = post_skor,
                                   data_hasil=data_hasil)

        else:
            return render_template('hasil.html', data_hasil=data_hasil)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Insert & Update Pre-Test =====
@app.route('/main/pretest', methods=['POST'])
def insert_pretest():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            pre1 = request.form['pre1']
            pre2 = request.form['pre2']
            pre3 = request.form['pre3']
            pre4 = request.form['pre4']
            pre5 = request.form['pre5']

            # Combine pre1-pre5
            pre_answer = f"""
            Cerita:
            {pre1}

            Pikiran:
            {pre2}

            Emosi:
            {pre3}

            Perilaku:
            {pre4}

            Respons:
            {pre5}
            """

            df_result_pretest = pd.DataFrame({'Pre-Test': [pre_answer]})
            # Casefolding
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].str.lower()
            # Text Cleaning
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].astype(str).apply(lambda x: x.encode('latin-1', 'ignore').decode('latin-1'))
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_mention)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_hashtag)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_https)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_number)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_punc)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_whitespace)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_whitespace_multi)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_single_char)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(word_tokenize_wrapper)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(stemming)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].apply(remove_stopwords)
            df_result_pretest['Pre-Test'] = df_result_pretest['Pre-Test'].agg(lambda x: ','.join(map(str, x)))
            result_pretest = model_pretest.predict(tfidf_pretest.transform(df_result_pretest['Pre-Test'].values))
            result_proba_pretest = model_pretest.predict_proba(tfidf_pretest.transform(df_result_pretest['Pre-Test'].values))

            cur = mysql.connection.cursor()

            # Lakukan operasi UPDATE pada data yang sudah ada
            cur.execute("UPDATE data_hasil SET pre_q1=%s, pre_q2=%s, pre_q3=%s, pre_q4=%s, pre_q5=%s, pre_skor=%s WHERE id_hasil=%s",
                        (pre1, pre2, pre3, pre4, pre5, int(result_pretest), id))
            flash(
                'Selamat karena telah menyelesaikan Pre-Test, untuk melanjutkan langkah Anda serta untuk memantau perjalanan Anda, silakan kunjungi menu User Journey',
                'success')

            mysql.connection.commit()
            return redirect(url_for('hasil'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Insert & Show Post-Test =====
@app.route('/main/posttest', methods=['POST'])
def insert_posttest():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            post1 = request.form['post1']
            post2 = request.form['post2']
            post3 = request.form['post3']

            post_answer = f"""
            Pikiran:
            {post1}

            Perilaku:
            {post2}

            Manfaat:
            {post3}
            """

            df_result_posttest = pd.DataFrame({'Post-Test': [post_answer]})
            # Casefolding
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].str.lower()
            # Text Cleaning
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].astype(str).apply(lambda x: x.encode('latin-1', 'ignore').decode('latin-1'))
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_mention)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_hashtag)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_https)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_number)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_punc)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_whitespace)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_whitespace_multi)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_single_char)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(word_tokenize_wrapper)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(stemming)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].apply(remove_stopwords)
            df_result_posttest['Post-Test'] = df_result_posttest['Post-Test'].agg(lambda x: ','.join(map(str, x)))
            result_posttest = model_posttest.predict(tfidf_posttest.transform(df_result_posttest['Post-Test'].values))
            result_proba_posttest = model_posttest.predict_proba(tfidf_posttest.transform(df_result_posttest['Post-Test'].values))

            cur = mysql.connection.cursor()

            # Lakukan operasi UPDATE pada data yang sudah ada
            cur.execute("UPDATE data_hasil SET post_q1=%s, post_q2=%s, post_q3=%s, post_skor=%s WHERE id_hasil=%s",
                        (post1, post2, post3, int(result_posttest), id))

            mysql.connection.commit()
            return redirect(url_for('hasil'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Shambavi Mudra =====
@app.route('/main/terapi_shambavimudra', methods=['POST'])
def update_shambavi():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            if sesi == 'Sesi 1':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET shambavi1=%s WHERE id_journey=%s",
                            (status, id))
                flash('Selamat karena telah menyelesaikan terapi Shambavi Mudra Sesi 1, silakan lanjutkan ke terapi Journaling Sesi 3', 'success')
            else:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET shambavi2=%s WHERE id_journey=%s",
                            (status, id))
                flash('Selamat karena telah menyelesaikan terapi Shambavi Mudra Sesi 2, silakan lanjutkan ke terapi Journaling Sesi 10','success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Mindfulness =====
@app.route('/main/terapi_mindfulness', methods=['POST'])
def update_mindfulness():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            if sesi == 'Sesi 1':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET mind1=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Meditation & Mindfulness Sesi 1, silakan lanjutkan ke terapi Journaling Sesi 5',
                    'success')
            else:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET mind2=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Meditation & Mindfulness Sesi 2, silakan lanjutkan ke terapi Journaling Sesi 11',
                    'success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Doodling =====
@app.route('/main/terapi_doodling', methods=['POST'])
def update_doodling():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            # Lakukan operasi UPDATE pada data yang sudah ada
            cur.execute("UPDATE user_journey SET doodling=%s WHERE id_journey=%s",
                        (status, id))
            flash(
                'Selamat karena telah menyelesaikan terapi Doodling, silakan lanjutkan ke terapi Journaling Sesi 9',
                'success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Music & Muscle Relaxation =====
@app.route('/main/terapi_mmr', methods=['POST'])
def update_mmr():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            if sesi == 'Sesi 1':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET mmr1=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Music & Muscle Relaxation Sesi 1, silakan lanjutkan ke terapi Journaling Sesi 2',
                    'success')
            else:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET mmr2=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Music & Muscle Relaxation Sesi 2, silakan lanjutkan ke terapi Journaling Sesi 7',
                    'success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Journaling =====
@app.route('/main/terapi_journaling', methods=['POST'])
def update_journaling():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            if sesi == 'Sesi 1':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j1=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 1, silakan lanjutkan ke terapi Journaling Sesi 2',
                    'success')
            elif sesi == 'Sesi 2':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j2=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 2, silakan lanjutkan ke terapi Shambavi Mudra Sesi 1',
                    'success')
            elif sesi == 'Sesi 3':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j3=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 3, silakan lanjutkan ke terapi Expressive Writing Sesi 1',
                    'success')
            elif sesi == 'Sesi 4':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j4=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 4, silakan lanjutkan ke terapi Meditation & Mindfulness Sesi 1',
                    'success')
            elif sesi == 'Sesi 5':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j5=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 5, silakan lanjutkan ke terapi Expressive Writing Sesi 2',
                    'success')
            elif sesi == 'Sesi 6':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j6=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 6, silakan lanjutkan ke terapi Music & Muscle Relaxation Sesi 2',
                    'success')
            elif sesi == 'Sesi 7':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j7=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 7, silakan lanjutkan ke terapi Expresive Writing Sesi 3',
                    'success')
            elif sesi == 'Sesi 8':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j8=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 8, silakan lanjutkan ke terapi Doodling',
                    'success')
            elif sesi == 'Sesi 9':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j9=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 9, silakan lanjutkan ke terapi Shambavi Mudra Sesi 2',
                    'success')
            elif sesi == 'Sesi 10':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j10=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Journaling Sesi 10, silakan lanjutkan ke terapi Meditation & Mindfulness Sesi 2',
                    'success')
            elif sesi == 'Sesi 11':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET j11=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan seluruh rangkaian terapi, silakan lanjutkan dengan mengisi Post-Test',
                    'success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== CRUD | Update Status Expressive Writing =====
@app.route('/main/terapi_expwrite', methods=['POST'])
def update_expwrite():
    if (('loggedin' in session) & (session['level'] == 'User')):
        if request.method == 'POST':
            id = session['id']
            sesi = request.form['sesi']
            status = 'Sudah'

            cur = mysql.connection.cursor()

            if sesi == 'Sesi 1':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET expwr1=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Expressive Writing Sesi 1, silakan lanjutkan ke terapi Journaling Sesi 4',
                    'success')
            elif sesi == 'Sesi 2':
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET expwr2=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Expressive Writing Sesi 2, silakan lanjutkan ke terapi Journaling Sesi 6',
                    'success')
            else:
                # Lakukan operasi UPDATE pada data yang sudah ada
                cur.execute("UPDATE user_journey SET expwr3=%s WHERE id_journey=%s",
                            (status, id))
                flash(
                    'Selamat karena telah menyelesaikan terapi Expressive Writing Sesi 3, silakan lanjutkan ke terapi Journaling Sesi 8',
                    'success')

            mysql.connection.commit()
            return redirect(url_for('user_journey'))

    flash('Harap Login dulu', 'danger')

# ===== Set Main Page | Insert Link Grup =====
@app.route('/main/insert_link')
def link_komunitas():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama FROM datadiri_fasilitator WHERE status = 'Diterima'")
        fasilitator_names = [row[0] for row in cur.fetchall()]
        cur.close()

        return render_template('insert_link.html', fasilitator_names = fasilitator_names)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Insert Link Grup ======
@app.route('/main/insert_link', methods=['POST'])
def insert_link():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        if request.method == 'POST':
            nama_fasilitator = request.form['fasilitator']
            link = request.form['link']
            nama_grup = request.form['namagrup']
            status = 'Belum'

            cur = mysql.connection.cursor()
            # Check if fasilitator can handle another group
            cur.execute("SELECT COUNT(*) FROM data_komunitas WHERE nama_fasilitator = %s AND status = %s", (nama_fasilitator,status))
            existing_groups = cur.fetchone()[0]
            if existing_groups >= 1:
                flash("Fasilitator sudah menghandle grup sebelumnya.", "danger")

            # Select 8 random users with status "PTSD"
            cur.execute("SELECT id_hasil FROM data_hasil WHERE status = 'PTSD' ORDER BY RAND() LIMIT 8")
            selected_users = cur.fetchall()

            # Check if nama grup already exists
            cur.execute("SELECT COUNT(*) FROM data_komunitas WHERE grup = %s", (nama_grup,))
            existing_group_names = cur.fetchone()[0]
            if existing_group_names > 0:
                flash("Nama grup sudah ada, gunakan nama lain.", "danger")

            # Insert data into data_komunitas
            for user_id in selected_users:
                cur.execute("SELECT id_user, nama FROM datadiri_user WHERE id_user = %s", (user_id,))
                user_data = cur.fetchone()
                if user_data:
                    user_id, user_name = user_data
                    # Check if user is already in data_komunitas
                    cur.execute("SELECT COUNT(*) FROM data_komunitas WHERE nama_user = %s", (user_name,))
                    existing_user = cur.fetchone()[0]
                    if existing_user == 0:
                        cur.execute("INSERT INTO data_komunitas (nama_fasilitator, nama_user, grup, pertemuan, status, link) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (nama_fasilitator, user_name, nama_grup, 1, status, link))
                        mysql.connection.commit()

            cur.close()
            return redirect(url_for('link_komunitas'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Atur Komunitas ======
@app.route('/main/atur_komunitas')
def atur_komunitas():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama_fasilitator, COUNT(nama_user) AS jumlah_user, grup, status, link FROM data_komunitas GROUP BY nama_fasilitator, grup, status, link;")
        data_komunitas = cur.fetchall()
        cur.execute("SELECT nama_fasilitator, nama_user FROM data_komunitas")
        data_peserta = cur.fetchall()
        cur.close()

        return render_template('atur_komunitas.html', data_komunitas=data_komunitas, data_peserta=data_peserta)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Delete Komunitas ======
@app.route('/delete_komunitas/<string:nama>', methods=["GET"])
def delete_komunitas(nama):
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        # Cari dan delete nama grup
        cur.execute("DELETE FROM data_komunitas WHERE grup=%s", (nama,))
        flash("Data Berhasil Dihapus", "danger")
        mysql.connection.commit()
        return redirect( url_for('atur_komunitas'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Fasilitator Page | Komunitas ======
@app.route('/main/komunitas_fasilitator')
def komunitas_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Fasilitator')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama_fasilitator, COUNT(nama_user) AS jumlah_user, grup, link, pertemuan, status FROM data_komunitas GROUP BY nama_fasilitator, grup, link, pertemuan, status;")
        data_komunitas = cur.fetchall()
        cur.execute("SELECT nama_fasilitator, nama_user FROM data_komunitas")
        data_peserta = cur.fetchall()
        cur.close()

        return render_template('komunitas_fasilitator.html', data_komunitas=data_komunitas, data_peserta=data_peserta)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Fasilitator Page | Update Seleksi Psikolog ======
@app.route('/update_komunitas', methods=['POST'])
def update_komunitas():
    if (('loggedin' in session) & (session['level'] == 'Fasilitator')):
        if request.method == 'POST':
            nama = request.form['nama']
            pertemuan = int(request.form['pertemuan'])
            status = request.form['status']

            cur = mysql.connection.cursor()
            if ((pertemuan < 8) & (pertemuan >= 0)):
                update_pertemuan = pertemuan + 1
                cur.execute("UPDATE data_komunitas SET status=%s, pertemuan=%s WHERE grup=%s", (status, update_pertemuan, nama))
                flash("Selamat karena telah menyelesaikan 1 pertemuan dan menunaikan tugas Anda sebagai fasilitator, kami sangat mengapresiasi usaha yang Anda berikan selama ini.", "success")
            elif pertemuan == 8:
                cur.execute("UPDATE data_komunitas SET status=%s, pertemuan=%s WHERE grup=%s", (status, pertemuan, nama))
                flash(
                    "Selamat karena telah menyelesaikan semua pertemuan dan menunaikan tugas Anda sebagai fasilitator, kami sangat mengapresiasi usaha yang Anda berikan selama ini.",
                    "success")
            else:
                flash("Ada error sistem.", "danger")

            mysql.connection.commit()
            return redirect(url_for('komunitas_fasilitator'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Evaluasi Psikolog ======
@app.route('/main/evaluasi_psikolog')
def evaluasi_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama_psikolog, COUNT(*) AS jumlah_feedback, AVG(rating_psikolog) AS rata_rata_rating, deskripsi_psikolog FROM user_feedback WHERE nama_psikolog <> 'Tidak Ada' GROUP BY nama_psikolog;")
        data_eval_psikolog = cur.fetchall()
        cur.close()

        return render_template('eval_psikolog.html', data_eval_psikolog=data_eval_psikolog)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Update Evaluasi Psikolog ======
@app.route('/update_eval_psikolog', methods=['POST'])
def update_eval_psikolog():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        if request.method == 'POST':
            nama = request.form['nama']
            status = request.form['status']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE datadiri_psikolog SET status=%s WHERE nama=%s", (status, nama))
            flash(
                "Hasil evaluasi berhasil disimpan.",
                "success")
            mysql.connection.commit()
            return redirect(url_for('evaluasi_psikolog'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Evaluasi Fasilitator ======
@app.route('/main/evaluasi_fasilitator')
def evaluasi_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cur = mysql.connection.cursor()
        cur.execute("SELECT nama_fasilitator, COUNT(*) AS jumlah_feedback, AVG(rating_fasilitator) AS rata_rata_rating, deskripsi_fasilitator FROM user_feedback WHERE nama_psikolog <> 'Tidak Ada' GROUP BY nama_fasilitator;")
        data_eval_fasilitator = cur.fetchall()
        cur.close()

        return render_template('eval_fasilitator.html', data_eval_fasilitator=data_eval_fasilitator)

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Admin Page | Update Evaluasi Fasilitator ======
@app.route('/update_eval_fasilitator', methods=['POST'])
def update_eval_fasilitator():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        if request.method == 'POST':
            nama = request.form['nama']
            status = request.form['status']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE datadiri_fasilitator SET status=%s WHERE nama=%s", (status, nama))
            flash(
                "Hasil evaluasi berhasil disimpan.",
                "success")
            mysql.connection.commit()
            return redirect(url_for('evaluasi_fasilitator'))

    flash('Harap Login dulu', 'danger')
    return redirect(url_for('login'))

# ===== Set Main Page ======
@app.route('/main/evaluasi_web')
def evaluasi_web():
    if (('loggedin' in session) & (session['level'] == 'Admin')):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(rating), AVG(rating), kategori FROM user_feedback GROUP BY kategori")
        results = cursor.fetchall()

        # Create a DataFrame from the query results
        df = pd.DataFrame(results, columns=['count', 'avg', 'category'])

        # Convert 'avg' column to numeric
        df['avg'] = pd.to_numeric(df['avg'], errors='coerce')

        # Calculate total ratings and average rating
        total_ratings = df['count'].sum()
        avg_rating = (df['avg'] * df['count']).sum() / total_ratings
        avg_rating = round(avg_rating, 2)

        # Find the category with the highest and lowest average ratings
        max_category = df.loc[df['avg'].idxmax()]['category']
        min_category = df.loc[df['avg'].idxmin()]['category']

        # Get count user, psikolog, and fasilitator
        cursor.execute("SELECT COUNT(*) FROM datadiri_user")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM datadiri_psikolog")
        psikolog_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM datadiri_fasilitator")
        fasilitator_count = cursor.fetchone()[0]

        # Barchart - Jumlah Rating per Kategori
        # Get count of ratings for each category
        categories = ['Kinerja Teknis', 'Konten dan Informasi', 'Pengalaman Pengguna', 'Interaksi dengan AI',
                      'Keamanan dan Privasi', 'Dukungan dan Bantuan', 'Efektivitas Terapi', 'Umpan Balik Pengguna']
        ratings_counts = []

        for category in categories:
            cursor.execute(f"SELECT COUNT(rating) FROM user_feedback WHERE kategori = '{category}'")
            count = cursor.fetchone()[0]
            ratings_counts.append(count)

        # Create a DataFrame from the ratings counts
        ratings_df = pd.DataFrame({'category': categories, 'count': ratings_counts})

        # Sort DataFrame by 'count' column in descending order
        sorted_df = ratings_df.sort_values(by='count', ascending=False)

        # Create plot
        fig_bar_jumlah = px.bar(sorted_df, x='category', y='count', title=None,
                                labels={'count': 'Jumlah Rating', 'category': 'Kategori'}, text='count')
        fig_bar_jumlah.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=(dict(showgrid=False))
        )
        fig_bar_jumlah.update_traces(textfont_size=14, textangle=0, textposition="outside")
        fig_bar_jumlah.update_xaxes(tickangle=0, tickvals=list(range(len(categories))),
                         ticktext=[c.replace(" ", "<br>") for c in sorted_df['category']])

        graphJSON_jumlah = json.dumps(fig_bar_jumlah, cls=plotly.utils.PlotlyJSONEncoder)

        # Barchart - Rata-rata Rating per Kategori
        # Get avg of ratings for each category
        categories = ['Kinerja Teknis', 'Konten dan Informasi', 'Pengalaman Pengguna', 'Interaksi dengan AI',
                      'Keamanan dan Privasi', 'Dukungan dan Bantuan', 'Efektivitas Terapi', 'Umpan Balik Pengguna']
        ratings_avg = []

        for category in categories:
            cursor.execute(f"SELECT AVG(rating) FROM user_feedback WHERE kategori = '{category}'")
            avgs = cursor.fetchone()[0]
            ratings_avg.append(avgs)

        # Create a DataFrame from the ratings counts
        ratings_df = pd.DataFrame({'category': categories, 'avg': ratings_avg})
        # Fill NaN values with 0
        ratings_df['avg'].fillna(0, inplace=True)

        # Sort DataFrame by 'count' column in descending order
        sorted_df = ratings_df.sort_values(by='avg', ascending=False)

        # Create plot
        fig_bar_avgs = px.bar(sorted_df, x='category', y='avg', title=None,
                              labels={'avg': 'Rata-rata Rating', 'category': 'Kategori'}, text='avg')
        fig_bar_avgs.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=(dict(showgrid=False))
        )
        fig_bar_avgs.update_traces(textfont_size=14, textangle=0, textposition="outside")
        fig_bar_avgs.update_xaxes(tickangle=0, tickvals=list(range(len(categories))),
                                    ticktext=[c.replace(" ", "<br>") for c in sorted_df['category']])

        graphJSON_avgs = json.dumps(fig_bar_avgs, cls=plotly.utils.PlotlyJSONEncoder)

        # Wordcloud
        # Query to get feedback descriptions
        cursor.execute("SELECT deskripsi FROM user_feedback")
        feedback_descriptions = cursor.fetchall()

        # Create a DataFrame from feedback descriptions
        feedback_df = pd.DataFrame(feedback_descriptions, columns=['deskripsi'])

        # Preprocess text
        feedback_df['deskripsi'] = feedback_df['deskripsi'].str.lower()  # Convert to lowercase
        # Remove special characters and symbols
        feedback_df['deskripsi'] = feedback_df['deskripsi'].apply(lambda x: re.sub(r'[^a-zA-Z\s]', '', x))
        # Tokenize text
        feedback_df['deskripsi'] = feedback_df['deskripsi'].apply(lambda x: word_tokenize(x))
        # Remove stopwords
        stop_words = set(stopwords.words('indonesian'))
        feedback_df['deskripsi'] = feedback_df['deskripsi'].apply(lambda x: [word for word in x if word not in stop_words])

        # Combine tokenized words into a single list
        all_words = feedback_df['deskripsi'].sum()
        # Join the list of words into a single string
        text = ' '.join(all_words)
        # Create a WordCloud
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        # Create a figure using Plotly
        fig_wordcloud = px.imshow(wordcloud)
        # Convert plotly figure to JSON
        graphJSON_wordcloud = json.dumps(fig_wordcloud, cls=plotly.utils.PlotlyJSONEncoder)

        return render_template('eval_web.html', total_ratings=total_ratings, avg_rating=avg_rating,
                               max_category=max_category, min_category=min_category,
                               user_count=user_count, psikolog_count=psikolog_count, fasilitator_count=fasilitator_count,
                               graphJSON_jumlah = graphJSON_jumlah, graphJSON_avgs=graphJSON_avgs,
                               graphJSON_wordcloud=graphJSON_wordcloud)

    flash('Harap Login dulu','danger')
    return redirect(url_for('login'))

if __name__ == '__main__':
  app.run(debug=True)