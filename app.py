import mysql.connector
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pyzbar import pyzbar
from PIL import Image

# Inisialisasi bot dengan Telegram Bot API Token
updater = Updater(token='x', use_context=True)
dispatcher = updater.dispatcher

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

def view_data(update, context):
    # Terhubung ke database
    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        # Query untuk mengambil data dari tabel
        query = "SELECT * FROM kode_scan where kode = '11w2001076100070'"
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

                # Kirim pesan ke pengguna Telegram
                context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak ditemukan data dengan kode barcode tersebut.")

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            cursor.close()
            cnx.close()
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak dapat menemukan QR barcode pada gambar.")


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

viewdata_handler = CommandHandler('viewdata', view_data)
dispatcher.add_handler(viewdata_handler)

scanqr_handler = MessageHandler(Filters.photo, scan_qr)
dispatcher.add_handler(scanqr_handler)

updater.start_polling()

# Cetak pesan bahwa program telah berjalan
print("Program berjalan. Ketik /viewdata untuk melihat data dari database.")
