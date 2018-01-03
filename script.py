# -*- coding: utf-8 -*-

import sys
from getpass import getpass

from settings import *

from database.models import Message, export_sources

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpc_error_list import UsernameNotOccupiedError, FloodWaitError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerChannel, InputChannel, InputPeerChat


def get_all_chat_messages(channel_name, client):
    """
    Функция для получения всех сообщений из канала. Максимально 100 сообщений за раз.
    :param channel_name: имя канала (например durov)
    :param client: объект клиента
    :return: объекты сообщений
    """
    chat_object = get_chat_info(channel_name, client)
    input_channel = InputChannel(chat_object['chat_id'], chat_object['access_hash'])
    channel = client.invoke(GetFullChannelRequest(input_channel)).__dict__
    chat_peer = InputPeerChannel(channel['full_chat'].id, chat_object['access_hash'])

    all_messages = []
    offset = 0
    new_messages = client.invoke(GetHistoryRequest(chat_peer, 0, None, offset, 0, 0, 0)).messages

    while len(new_messages) is not 0 and offset <= LIMIT:
        offset += 100

        for new_message in new_messages:
            all_messages.append(new_message.__dict__)

        new_messages = client.invoke(GetHistoryRequest(chat_peer, 0, None, offset, 0, 0, 0)).messages

    return all_messages


def get_chat_info(username, client):
    """
    Функция для получения информации о чате
    :param username: имя пользователя
    :param client: объект клиента
    :return:
    """
    try:
        chat = client(ResolveUsernameRequest(username))
    except UsernameNotOccupiedError:
        print('Chat/channel not found!')
        sys.exit()
    result = {
        'chat_id': chat.peer.channel_id,
        'access_hash': chat.chats[0].access_hash
    }
    return result


def auth(app_id, app_hash):
    """
    Функция для авторизации пользователя
    :param app_id: ID приложения
    :param app_hash: Hash приложения
    :return: объект клиента
    """
    client = TelegramClient('user-session', app_id, app_hash)
    client.connect()

    if not client.is_user_authorized():
        try:
            client.send_code_request(PHONE)
            print('Sending a code...')
            client.sign_in(PHONE, code=input('Enter code: '))
        except FloodWaitError as FloodError:
            print('Flood wait: {}.'.format(FloodError))
            sys.exit()
        except SessionPasswordNeededError:
            client.sign_in(password=getpass('Enter password: '))

    return client


def main():
    print('Starting script...')
    client = auth(API_ID, API_HASH)
    print('Auth - successfully!')

    sources = export_sources()
    print('Getting sourses...\nGot {} sources'.format(len(sources)))

    for source in sources:
        print('Getting {} messages...'.format(source.username))
        messages = get_all_chat_messages(source.username, client)
        print('Got {} messages.\nSaving {} messages...'.format(len(messages), source.username))

        for message in messages:
            try:
                Message.get_or_create(
                    source_id=source._get_pk_value(),
                    message_id=message['id'],
                    message=message['message'],
                    date=message['date'],
                    media='Yes' if message['media'] else 'No'
                )
            except KeyError:
                pass

    print('Done!')


if __name__ == '__main__':
    main()
