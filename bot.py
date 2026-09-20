import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Ini memori sementara
user_data = {}

@bot.message_handler(commands=['mulai', 'start'])
def send_welcome(message):
    bot.reply_to(message, "Selamat datang di IchiScan 0.1, bot untuk mengkonversi foto menjadi PDF, silahkan kirimkan foto-foto tugas anda yang ingin dikonversi jadi pdf.")

@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    chat_id = message.chat.id
    
    # ini buat nyimpen data user kalo belum ada
    if chat_id not in user_data:
        user_data[chat_id] = {'photos': []}

    # ngambil file_id dari foto yang resolusi tertinggi
    file_id = message.photo[-1].file_id
    user_data[chat_id]['photos'].append(file_id)

    # tombol selesai scan
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Selesai scan", callback_data="selesai_scan"))

    bot.reply_to(message, f"📸 {len(user_data[chat_id]['photos'])} halaman diterima. Ada lagi?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "selesai_scan")
def callback_query(call):
    chat_id = call.message.chat.id
    
    # buat cek foto udah ada atau belum
    if chat_id in user_data and len(user_data[chat_id]['photos']) > 0:
        # ini ngapus tombol selesai scan biar ga kepencet lagi
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        
        # ini nanya nama user
        msg = bot.send_message(chat_id, "Oke, sekarang silahkan isi Nama anda:")
        bot.register_next_step_handler(msg, proses_nama)
    else:
        bot.answer_callback_query(call.id, "Belum ada foto yang dikirim, silahkan kirim foto dulu sebelum selesai scan.")

# ini proses input nama, npm, kelas, dan matkul

def proses_nama(message):
    chat_id = message.chat.id
    # ini disimpen nama user di memori sementara, pake underscore biar aman
    user_data[chat_id]['nama'] = message.text.replace(" ", "_")
    
    msg = bot.send_message(chat_id, "Oke, sekarang ketik NPM (contoh: 123456789):")
    bot.register_next_step_handler(msg, proses_npm)

def proses_npm(message):
    chat_id = message.chat.id
    # ini disimpen npm user di memori sementara, pake underscore biar aman
    user_data[chat_id]['npm'] = message.text.replace(" ", "_")
    
    msg = bot.send_message(chat_id, "Oke, sekarang ketik Kelas (contoh: R5U):")
    bot.register_next_step_handler(msg, proses_kelas)

def proses_kelas(message):
    chat_id = message.chat.id
    # ini disimpen kelas user di memori sementara, pake underscore biar aman
    user_data[chat_id]['kelas'] = message.text.replace(" ", "_")
    
    msg = bot.send_message(chat_id, "Terakhir, ketik Mata Kuliah (contoh: Pemrograman Berbasis Objek):")
    bot.register_next_step_handler(msg, proses_matkul)

def proses_matkul(message):
    chat_id = message.chat.id
    # ini disimpen matkul user di memori sementara, pake underscore biar aman
    user_data[chat_id]['matkul'] = message.text.replace(" ", "_")
    
    # ambil data user
    data = user_data[chat_id]
    total_foto = len(data['photos'])
    
    # ini format nama file pdf sesuai inputan user
    nama_file = f"{data['nama']}_{data['npm']}_{data['kelas']}_{data['matkul']}.pdf"
    
    teks_konfirmasi = (
        "**Konfirmasi Dokumen**\n\n"
        f"👤 Nama: {data['nama']}\n"
        f"🆔 NPM: {data['npm']}\n"
        f"🏫 Kelas: {data['kelas']}\n"
        f"📚 Matkul: {data['matkul']}\n"
        f"📄 Halaman: {total_foto}\n\n"
        f"Nama file:\n`{nama_file}`"
    )
    
    # ini tombol buat PDF
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Buat PDF", callback_data="buat_pdf"))
    
    bot.send_message(chat_id, teks_konfirmasi, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "buat_pdf")
def proses_buat_pdf(call):
    chat_id = call.message.chat.id
    
    # ini ngasih tau user kalo lagi proses bikin PDF
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                          text="⏳ sedang memproses...")
    
    data = user_data.get(chat_id)
    if not data or not data.get('photos'):
        bot.send_message(chat_id, "mohon maaf, data tidak ditemukan. Silahkan mulai lagi dengan /mulai, /start.")
        return

    try:
        image_list = []
        # buat taruh semua foto yang udah dikirim user
        for file_id in data['photos']:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # diubah ke format RGB biar ga ada masalah pas dijadiin PDF
            img = Image.open(io.BytesIO(downloaded_file)).convert('RGB')
            image_list.append(img)
        
        # Bikin nama file PDF sesuai inputan user
        nama_file = f"{data['nama']}_{data['npm']}_{data['kelas']}_{data['matkul']}.pdf"
        
        # Bikin objek BytesIO buat nyimpen PDF di memori
        pdf_bytes = io.BytesIO()
        pdf_bytes.name = nama_file # ini biar nama file PDF sesuai inputan user
        
        # buat gabungin semua foto jadi satu PDF
        image_list[0].save(
            pdf_bytes, 
            format='PDF', 
            save_all=True, 
            append_images=image_list[1:]
        )
        
        # biar posisi pointer di awal biar bisa dibaca dari awal
        pdf_bytes.seek(0)
        
        # kirim PDF ke user
        bot.send_document(chat_id, document=pdf_bytes, caption="🔥 proses selesai! Silakan cek PDF yang sudah dibuat.")
        
        # hapus pesan konfirmasi biar ga kepencet lagi
        bot.delete_message(chat_id, call.message.message_id)
        
        # hapus data user dari memori sementara biar ga numpuk
        user_data.pop(chat_id, None)
        
    except Exception as e:
        bot.send_message(chat_id, f"Yah error : {e}")

print("Mesin bot udah nyala! Coba chat /start di Telegram lu.")
bot.polling()