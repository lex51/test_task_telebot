#!/usr/bin/env python3
import telebot
import requests  
import json
from tinydb import TinyDB, Query 
import os
import re
from pydub import AudioSegment 
from zipfile import ZipFile
import cv2
import config

tele_token = config.token

bot = telebot.TeleBot(tele_token)

@bot.message_handler(content_types=['audio', 'voice'])
def get_aud_messages(message):

    url = f'https://api.telegram.org/bot{tele_token}/getFile?file_id={message.voice.file_id}'
    file_path = requests.get(url).json()['result']['file_path']
    down_url = f'https://api.telegram.org/file/bot{tele_token}/{file_path}'
    file = requests.get(down_url)
    file_name = f'{os.getcwd()}/aud/{message.message_id}.ogg'

    with open(file_name, 'wb') as f:

        f.write(file.content)
    
    with TinyDB('db.json') as db:
        table = db.table('audio')
        table.insert({
            'user_id': message.from_user.id,
            'msg_id': message.message_id,
            'msg_voice_id': message.voice.file_id
        })
        message_count = len(table.search(Query().user_id == message.from_user.id))
        sound = AudioSegment.from_ogg(file_name)
        sound.export(f'aud_wav/{message.from_user.id}_audio_message_{message_count}.wav', format="wav")

    bot.send_message(
        message.from_user.id,
        "Я сохранил Ваше голосовое сообщение. Наберите /all_sounds для подробной информации")


@bot.message_handler(commands=['all_sounds'])
def response(message):
    with TinyDB('db.json') as db:
        table = db.table('audio')
        count = len(table.search(Query().user_id == message.from_user.id))  

    bot.reply_to(
        message,
        f'Вы прислали {count} голосовых сообщений, поздравляю ) Наберите /all_sounds_get что бы их все увидеть и скачать архив с wav-файлами')


@bot.message_handler(commands=['all_sounds_get'])
def all_sounds_get(message):
    with TinyDB('db.json') as db:
        table = db.table('audio')

        voice_list = [i['msg_voice_id'] for i in table.search(Query().user_id == message.from_user.id)] 
    wav_voice_list = [i for i in os.listdir('aud_wav/') if re.match(str(message.from_user.id), i)]  

    for i in voice_list:
        bot.send_voice(message.chat.id, i)

    with ZipFile(f'{message.from_user.id}.zip', 'w') as zipObj:
        for i in wav_voice_list:
            zipObj.write(f'aud_wav/{i}')

    bot.send_message(message.chat.id, f'Список перекодированных файлов на диске: {" ".join(wav_voice_list)}')
    with open(f'{message.from_user.id}.zip', 'rb') as f:
        bot.send_document(message.chat.id, f)
    bot.send_message(message.chat.id, 'Это все Ваши голосовые сообщения.')

@bot.message_handler(content_types=['photo'])#, 'document'])
def get_img_messages(message):
    for image in message.photo:
        url = f'https://api.telegram.org/bot{tele_token}/getFile?file_id={image.file_id}'
        print(url)
        file_path = requests.get(url).json()['result']['file_path']
        down_url = f'https://api.telegram.org/file/bot{tele_token}/{file_path}'
        file = requests.get(down_url)
        file_name = f'{os.getcwd()}/images/{message.from_user.id}_{file_path.split("/")[1]}'

        with open(file_name, 'wb') as f:

            f.write(file.content)
        try:
            img = cv2.imread(file_name)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.3,
                minNeighbors=3,
                minSize=(30, 30)
            )
            if faces.any():
                print('Sucses')
                with TinyDB('db.json') as db:
                    table = db.table('images')
                    
                    table.insert({
                        'user_id': message.from_user.id,
                        'msg_id': message.message_id,
                        'msg_image_id': image.file_id
                    })
                bot.send_message(
                   message.from_user.id,
                        "Я обнаружил на картинке лицо. Наберите /all_images_get для подробной информации")
        except BaseException as BE:
            print(BE)

@bot.message_handler(commands=['all_images_get'])
def all_faceim_get(message):
    with TinyDB('db.json') as db:
        table = db.table('images')

        faceim_list = [i['msg_image_id'] for i in table.search(Query().user_id == message.from_user.id)] 

    for i in faceim_list:
        bot.send_photo(message.chat.id, i)

    bot.send_message(message.chat.id, 'Это все Ваши присланные фотографии с лицами.')



bot.polling(none_stop=True, interval=0)

