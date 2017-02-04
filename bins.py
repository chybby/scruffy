from __future__ import (
    absolute_import,
    print_function,
)

import json
import requests

from config import (
    VERIFY_TOKEN,
    PAGE_ACCESS_TOKEN,
)

from flask import (
    Flask,
    make_response,
    request,
)

app = Flask(__name__)
app.config.from_object('config')

POSTBACK_DONE = 'DONE'
POSTBACK_PASS = 'PASS'
POSTBACK_REMIND = 'REMIND'


def load_state():
    with open('state.json', 'r') as state_file:
        return json.loads(state_file.read())


state = load_state()


@app.after_request
def save_state(response):
    with open('state.json', 'w') as state_file:
        state_file.write(json.dumps(state))
    return response


def call_send_API(message_data):
    rs = requests.post('https://graph.facebook.com/v2.6/me/messages',
                       params={'access_token': PAGE_ACCESS_TOKEN},
                       json=message_data)

    if rs.status_code == requests.codes.ok:
        data = rs.json()
        recipient_id = int(data['recipient_id'])
        message_id = data['message_id']
        print('Successfully sent message to %d with id %s' % (recipient_id,
                                                              message_id))
    else:
        print('Unsuccessfully sent message (%d)', rs.status_code)


def send_bin_notification(recipient_id):
    message_data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'button',
                    'text': 'It\'s your turn to take the bins out today!',
                    'buttons': [
                        {
                            'type': 'postback',
                            'title': 'Ok, done',
                            'payload': POSTBACK_DONE,
                        },
                        {
                            'type': 'postback',
                            'title': 'I can\'t today',
                            'payload': POSTBACK_PASS,
                        },
                        {
                            'type': 'postback',
                            'title': 'Remind me later',
                            'payload': POSTBACK_REMIND,
                        },
                    ]
                }
            }
        }
    }

    call_send_API(message_data)


def send_text_message(recipient_id, text):
    message_data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': text
        }
    }

    call_send_API(message_data)


def process_message(message):
    print(message)
    sender_id = int(message['sender']['id'])
    recipient_id = int(message['recipient']['id'])
    time_of_message = int(message['timestamp'])
    message_id = message['message']['mid']
    message_text = message['message'].get('text')
    message_attatchments = message['message'].get('attachments')

    print('Message from %d to %d at %d with text \'%s\'' % (sender_id,
                                                            recipient_id,
                                                            time_of_message,
                                                            message_text))

    send_text_message(sender_id, 'not ready yet bro')
    send_bin_notification(sender_id)


def process_postback(message):
    sender_id = int(message['sender']['id'])
    recipient_id = int(message['recipient']['id'])
    time_of_postback = int(message['timestamp'])
    payload = message['postback']['payload']

    if payload == POSTBACK_DONE:
        send_text_message(sender_id, 'Thanks buddy')
    elif payload == POSTBACK_PASS:
        send_text_message(sender_id, 'Someone else will have to do it today')
    elif payload == POSTBACK_REMIND:
        send_text_message(sender_id, 'Ok, I\'ll remind you this evening')


@app.route('/')
def index():
    app.logger.error('Info')
    return 'Hello World!'


@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json()
    if (data['object'] == 'page'):
        for entry in data['entry']:
            page_id = entry['id']
            time_of_event = entry['time']

            for message in entry['messaging']:
                if 'message' in message:
                    process_message(message)
                elif 'postback' in message:
                    process_postback(message)

    return ''


@app.route('/webhook', methods=['GET'])
def validate_webhook():
    if (request.args['hub.mode'] == 'subscribe' and
        request.args['hub.verify_token'] == VERIFY_TOKEN):
        # Validating webhook
        return request.args['hub.challenge']

    # Show web ui
    return "There'll be a web ui here someday"


if __name__ == '__main__':
    app.run()
