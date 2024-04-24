import io, os, telebot, requests
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
AWS_GATEWAY_URL = os.environ.get('AWS_GATEWAY_URL', '')

bot = telebot.TeleBot(BOT_TOKEN)

# -- Get latest measurements from sensors -- #
def get_latest_sensor_data(message: telebot.types.Message):
    response = requests.get(f'{AWS_GATEWAY_URL}latestSensorData')
    if response.status_code == 200:
        response_body = response.json()
        output_msg: str = "Latest sensor data:\n\n"
        for pot in response_body:
            output_msg += f"PotID: {pot['PotID']}\nTemperature: {pot['temperature']}\nHumidity: {pot['humidity']}\nLight: {pot['light']}\n\n"
        bot.send_message(message.chat.id, output_msg)
    else:
        bot.send_message(message.chat.id, 'An error occurred while fetching the latest sensor data.')
    send_welcome(message)
# ------------------------------------------ #

# -- Get actuators status -- #
def get_actuators_status(message: telebot.types.Message):
    response = requests.get(f'{AWS_GATEWAY_URL}actuatorStatus')
    if response.status_code == 200:
        response_body = response.json()
        output_msg: str = "Actuators status:\n\n"
        for pot in response_body:
            output_msg += f"PotID: {pot['PotID']}\nLatest Irrigation: {pot['latestIrrigation']}\nCover Status: {pot['coverStatus']}\n\n"
        bot.send_message(message.chat.id, output_msg)
    else:
        bot.send_message(message.chat.id, 'An error occurred while fetching the actuators status.')
    send_welcome(message)
# ------------------------- #

# -- Generate a report -- #
def generate_report(message: telebot.types.Message):
    response = requests.get(f'{AWS_GATEWAY_URL}generateReport')
    if response.status_code == 200:
        output_msg: str = "Here is the just generated report:\n\n"
        for pot in response.json():
            output_msg += f"PotID: {pot['PotID']}\nTemperature: {pot['temperature']}\nHumidity: {pot['humidity']}\nLight: {pot['light']}\nLatest Irrigation: {pot['latestIrrigation']}\nCover Status: {pot['coverStatus']}\n\n"
        output_msg += "The report has been saved to the S3 bucket.\nWould you like to download it?"
        
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*['Yes', 'No'])
        sent_msg = bot.send_message(message.chat.id, output_msg, reply_markup=markup)
        bot.register_next_step_handler(sent_msg, download_report_handler)
    else:
        bot.send_message(message.chat.id, 'An error occurred while generating the report.')
        send_welcome(message)
    
def download_report_handler(message: telebot.types.Message):
    resp = message.text.lower() if message.text is not None else ''
    if resp == 'yes':
        response = requests.get(f'{AWS_GATEWAY_URL}downloadReport')
        if response.status_code == 200:
            send_report(message, response.json())
        else:
            bot.send_message(message.chat.id, 'An error occurred while downloading the report.')
    send_welcome(message)
    
def send_report(message, report: dict):
    myFile = io.BytesIO(report['bytes'].encode('utf-8'))
    myFile.name = report['key']
    bot.send_document(message.chat.id, myFile)
# ----------------------- #

# -- Get all reports -- #
def get_all_reports(message: telebot.types.Message):
    response = requests.get(f'{AWS_GATEWAY_URL}downloadAllReports')
    if response.status_code == 200 and response.json() is not None:
        bot.send_message(message.chat.id, 'Here are all the reports:\n\n')
        for report in response.json():
            send_report(message, report)
    else:
        bot.send_message(message.chat.id, 'An error occurred while fetching all reports.')
    send_welcome(message)

# -- Actuate an actuator now -- #
def actuate_actuator_handler(message: telebot.types.Message):
    sent_msg = bot.send_message(message.chat.id, 'Please enter the pot ID of the pot you want to actuate', reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(sent_msg, actuator_potID_handler)

def actuator_potID_handler(message: telebot.types.Message):
    try:
        potID = message.text if message.text is not None else ''
        int(potID)
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*[
            types.KeyboardButton('Irrigator'),
            types.KeyboardButton('Cover')
        ])
        sent_msg = bot.send_message(message.chat.id, 'What actuator do you want to actuate?', reply_markup=markup)
        bot.register_next_step_handler(sent_msg, actuator_type_handler, potID)
    except ValueError as e:
        bot.send_message(message.chat.id, 'Pot ID must be a number. Please try again.')
        send_welcome(message)

def actuator_type_handler(message: telebot.types.Message, potID: str):
    actuator_type = message.text.lower() if message.text is not None else ''
    if actuator_type == 'cover':
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*[
            types.KeyboardButton('Open'),
            types.KeyboardButton('Close')
        ])
        sent_msg = bot.send_message(message.chat.id, 'Please enter the new state of the cover (open/close)', reply_markup=markup)
        bot.register_next_step_handler(sent_msg, actuator_cover_handler, potID, actuator_type)
    elif actuator_type == 'irrigator':
        actuator_final_handler(message, potID, actuator_type)
    else:
        bot.send_message(message.chat.id, 'Invalid option. Please try again.')
        send_welcome(message)
               
def actuator_cover_handler(message: telebot.types.Message, potID: str, actuator_type: str):
    new_state = message.text.lower() if message.text is not None else ''
    if new_state not in ['open', 'close']:
        bot.send_message(message.chat.id, 'Invalid option. Please try again.')
        send_welcome(message)
    else:
        actuator_final_handler(message, potID, actuator_type, new_state)
            
def actuator_final_handler(message: telebot.types.Message, potID: str, actuator_type: str, statusAfterUpdate: str = '_'):
    response = requests.get(f'{AWS_GATEWAY_URL}actuateNow?potid={potID}&actuator={actuator_type}&statusAfterUpdate={statusAfterUpdate}')
    if response.status_code == 200:
        bot.send_message(message.chat.id, response.json())
    else:
        bot.send_message(message.chat.id, 'An error occurred while generating the report.')
    send_welcome(message)
# ----------------------------- #

def action_handler(message: telebot.types.Message):
    if message.text == 'Get latest measurements from sensors':
        get_latest_sensor_data(message)
    elif message.text == 'Get actuators status':
        get_actuators_status(message)
    elif message.text == 'Generate a report':
        generate_report(message)
    elif message.text == 'Actuate an actuator now':
        actuate_actuator_handler(message)
    elif message.text == 'Get all reports':
        get_all_reports(message)
    else:
        bot.send_message(message.chat.id, 'Invalid option. Please select one of the options below.')
        send_welcome(message)


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message: telebot.types.Message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons_list: list[types.KeyboardButton] = [
        types.KeyboardButton('Get latest measurements from sensors'),
        types.KeyboardButton('Get actuators status'),
        types.KeyboardButton('Generate a report'),
        types.KeyboardButton('Actuate an actuator now'),
        types.KeyboardButton('Get all reports')
    ]
    markup.add(*buttons_list)
    sent_msg = bot.send_message(message.chat.id, "What do you want to do?", reply_markup=markup)
    bot.register_next_step_handler(sent_msg, action_handler)

@bot.message_handler(commands=['latestMeasurements'])
def get_latest_sensor_data_command(message: telebot.types.Message):
    get_latest_sensor_data(message)
    
@bot.message_handler(commands=['actuatorStatus'])
def get_actuators_status_command(message: telebot.types.Message):
    get_actuators_status(message)
    
@bot.message_handler(commands=['generateReport'])
def generate_report_command(message: telebot.types.Message):
    generate_report(message)
    
@bot.message_handler(commands=['actuateActuator'])
def actuate_actuator_command(message: telebot.types.Message):
    actuate_actuator_handler(message)
    
@bot.message_handler(commands=['getAllReports'])
def get_all_reports_command(message: telebot.types.Message):
    get_all_reports(message)

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()
