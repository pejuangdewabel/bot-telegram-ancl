from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from pyzbar import pyzbar
from PIL import Image
import mysql.connector
from datetime import datetime
import csv

# Inisialisasi bot dengan Telegram Bot API Token
updater = Updater(token='xxxxxxx', use_context=True)
dispatcher = updater.dispatcher

# Path file log CSV
log_file_path = 'request_log.csv'

def connect_to_mysql():
    # Konfigurasi koneksi database MySQL
    config = {
        'user': 'x',
        'password': 'x',
        'host': 'x',
        'database': 'x'
    }
    # Koneksi ke database
    cnx = mysql.connector.connect(**config)
    return cnx

def check_username(username):
    # Daftar username yang diizinkan
    allowed_usernames = ['josepkarim']

    if username in allowed_usernames:
        return True
    else:
        return False

def view_data(update, context):
    username = update.message.from_user.username
    if not check_username(username):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Anda tidak diizinkan mengakses data.")
        return
    
    # Terhubung ke database
    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        # Query untuk mengambil data dari tabel
        query = "SELECT * FROM kode_scan WHERE kode = '11w2001076100070'"
        cursor.execute(query)
        results = cursor.fetchall()

        # Membuat header tabel
        headers = [desc[0] for desc in cursor.description]

        # Format data dalam bentuk tabel
        response = "Data:\n"
        for row in results:
            for i in range(len(headers)):
                response += f"{headers[i]}: {row[i]}\n"  # Menampilkan nama field dan isi datanya
            response += "\n"

        # Kirim pesan ke pengguna Telegram
        context.bot.send_message(chat_id=update.effective_chat.id, text=response)

        # Cetak pesan sukses ke console log
        print("Data berhasil ditampilkan!")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        cursor.close()
        cnx.close()

def scan_qr(update, context):
    # Memeriksa username pengguna
    username = update.message.from_user.username
    if not check_username(username):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Anda tidak diizinkan mengakses data.")
        return

    # Mendapatkan objek gambar dari pesan yang dikirim
    image_obj = context.bot.getFile(update.message.photo[-1].file_id)

    # Mendownload gambar ke dalam file
    file_path = 'image.jpg'
    image_obj.download(file_path)

    # Membaca barcode dari gambar
    barcode_data = decode_qr_barcode(file_path)

    # Mencari data dengan query MySQL berdasarkan kode barcode
    if barcode_data:
        # Terhubung ke database
        cnx = connect_to_mysql()
        cursor = cnx.cursor()

        try:
            # Query untuk mencari data berdasarkan kode barcode
            query = f"SELECT * FROM kode_scan WHERE kode = '{barcode_data}'"
            cursor.execute(query)
            result = cursor.fetchone()

            if result:
                # Membuat header tabel
                headers = [desc[0] for desc in cursor.description]

                # Format data dalam bentuk tabel
                response = "Data:\n"
                for i in range(len(headers)):
                    response += f"{headers[i]}: {result[i]}\n"  # Menampilkan nama field dan isi datanya

                # Mengecek username Telegram yang diizinkan
                if check_username(username):
                    # Membuat inline keyboard markup
                    keyboard = [
                        [InlineKeyboardButton("Aktivasi Ulang", callback_data=f"aktivasi_ulang:{barcode_data}"),
                         InlineKeyboardButton("Batal", callback_data="batal")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    # Kirim pesan ke pengguna Telegram
                    message = context.bot.send_message(chat_id=update.effective_chat.id, text=response, reply_markup=reply_markup)

                    # Simpan ID pesan untuk digunakan saat mengedit pesan
                    context.user_data['message_id'] = message.message_id

                    # Catat permintaan dalam log CSV
                    log_request(barcode_data, username, update.effective_chat.id)

                else:
                    # Kirim pesan bahwa username tidak diizinkan
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Maaf, Anda tidak diizinkan untuk melakukan aktivasi ulang.")

            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak ditemukan data dengan kode barcode tersebut.")

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            cursor.close()
            cnx.close()
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak dapat menemukan QR barcode pada gambar.")

def button_callback(update, context):
    query = update.callback_query
    query_data = query.data

    if query_data.startswith("aktivasi_ulang"):
        barcode_data = query_data.split(":")[1]
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = f"{current_date} 23:59:59"

        # Lakukan proses aktivasi ulang berdasarkan barcode_data
        # Update query dari ID yang ada di barcode
        query = "UPDATE kode_scan SET akhir_berlaku = '{}' WHERE kode = '{}';".format(current_datetime, barcode_data)
        # Eksekusi query ke database
        execute_query(query)

        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Aktivasi ulang berhasil dilakukan untuk barcode: {barcode_data}")
        # Hapus tombol pada pesan
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id, message_id=update.callback_query.message.message_id, reply_markup=None)

        # Catat permintaan dalam log CSV
        username = update.callback_query.from_user.username
        log_request(barcode_data, username, update.effective_chat.id)

    elif query_data == "batal":
        context.bot.send_message(chat_id=update.effective_chat.id, text="Proses batal dilakukan.")
        # Hapus tombol pada pesan
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id, message_id=update.callback_query.message.message_id, reply_markup=None)

        # Catat permintaan dalam log CSV
        username = update.callback_query.from_user.username
        log_request("Batal", username, update.effective_chat.id)


def decode_qr_barcode(image_path):
    # Membuka gambar menggunakan PIL
    image = Image.open(image_path)

    # Membaca barcode menggunakan pyzbar
    barcodes = pyzbar.decode(image)

    if barcodes:
        # Mengambil data barcode pertama
        barcode = barcodes[0]
        barcode_data = barcode.data.decode("utf-8")
        return barcode_data

    return None

def execute_query(query):
    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        cursor.execute(query)
        cnx.commit()
        print("Query executed successfully.")
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        cnx.rollback()
    finally:
        cursor.close()
        cnx.close()

def log_request(barcode_data, username, chat_id):
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Menulis data permintaan ke dalam file log CSV
    with open(log_file_path, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([barcode_data, username, chat_id, current_date])

viewdata_handler = CommandHandler('viewdata', view_data)
dispatcher.add_handler(viewdata_handler)

scanqr_handler = MessageHandler(Filters.photo, scan_qr)
dispatcher.add_handler(scanqr_handler)

button_callback_handler = CallbackQueryHandler(button_callback)
dispatcher.add_handler(button_callback_handler)

updater.start_polling()

# Cetak pesan bahwa program telah berjalan
print("Program berjalan. Ketik /viewdata untuk melihat data dari database.")
