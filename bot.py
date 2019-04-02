#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import subprocess
import uuid
import json
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

printers = {
    'Toqui': 'hp',
    'Salita': 'hp-335'
}

with open('config.json', 'r') as f:
    config = json.load(f)

PRINTER, DOC = range(2)
whitelist = config['WHITELIST']


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hola! soy anakena bot puedo realizar operaciones como '
                              'print, papel')
    logger.info(update.message)  # INIT: host the bot , send a /start , add chat_id (on this log) to whitelist


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('posibles comandos : \\print, \\papel')


def papel(pot, update):
    if update.message.chat_id not in whitelist:
        update.message.reply_text('No permitido')
        return
    cmd = ['/usr/local/bin/papel']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = proc.communicate()

    logger.info(f"User {update.message.from_user.first_name} send papel command.")

    update.message.reply_text(o.decode("ascii"))


def print(bot, update):
    reply_keyboard = [['Toqui'], ['Salita']]

    if update.message.chat_id not in whitelist:
        update.message.reply_text('No permitido')
        return ConversationHandler.END

    update.message.reply_text(
        'Seleccione impresora o envie /cancel.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return PRINTER


def printer(bot, update, user_data):
    _printer = update.message.text
    user_data['printer'] = _printer
    update.message.reply_text('Por favor envie un documento o envie /cancel', reply_markup=ReplyKeyboardRemove())
    return DOC


def doc(bot, update, user_data):
    file_id = update.message.document.file_id
    file = bot.getFile(file_id)
    ext = update.message.document.mime_type
    filename = str(uuid.uuid4())

    if ext != 'application/pdf':
        update.message.reply_text('El documento no es un pdf', reply_markup=ReplyKeyboardRemove())
    else:
        pdf_file = f'{filename}.pdf'
        ps_file = f'{filename}.ps'
        file.download(pdf_file)

        logger.info(f"User {update.message.from_user.first_name} print a {pdf_file}.")

        from subprocess import call
        call(['pdf2ps', pdf_file])
        # update.message.reply_text(f"duplex '{ps_file}' | lpr -P {printers[user_data['printer']]}")
        p1 = subprocess.Popen(["/usr/local/bin/duplex", ps_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["lpr", "-P", printers[user_data['printer']]], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        p2.communicate()
        update.message.reply_text(f"Success")

    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Acción cancelada',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(config["BOT_KEY"])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("papel", papel))

    print_handler = ConversationHandler(
        entry_points=[CommandHandler('print', print)],

        states={
            PRINTER: [RegexHandler('^(Toqui|Salita)$', printer, pass_user_data=True)],
            DOC: [MessageHandler(Filters.document, doc, pass_user_data=True)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(print_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
