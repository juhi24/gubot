import json
import telegram
from telegram.ext import Dispatcher, CommandHandler
import os
import logging

import gupy


# Logging is cool!
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

OK_RESPONSE = {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps('ok')
}
ERROR_RESPONSE = {
    'statusCode': 400,
    'body': json.dumps('Oops, something went wrong!')
}


def start_callback(bot, update):
    greeting = 'Greetings, human! I am Ares Peacemaker, the messenger between you and the gods.'
    update.message.reply_text(greeting)


def version_callback(bot, update):
    update.message.reply_text(telegram.__version__)


def refratio_callback(bot, update, args):
    lines = []
    for arg in args:
        ratio = gupy.referral_gained_ratio(arg)
        lines.append('{addr}: {ratio:.2f}'.format(addr=arg, ratio=ratio))
    reply = '\n'.join(lines)
    update.message.reply_text(reply)


def predict_callback(bot, update, args):
    """Reply Elo prediction result."""
    player_id = args[0]
    opponent_id = args[1]
    result = gupy.predict(player_id, opponent_id)
    reply_base = 'Propability of {} winning {} is {:.1f}%.'
    reply = reply_base.format(player_id, opponent_id, result*100)
    update.message.reply_text(reply)


def user_stats_callback(bot, update, args):
    player_id = args[0]
    ustats = gupy.user_stats(player_id)
    reply_lines = ['Player {username} stats in constructed mode:',
                  'W/L: {won_matches}/{lost_matches} = {wl}',
                  'Rating: {rating}',
                  'Rank level: {rank_level}',
                  'Points: {win_points}W, {loss_points}L',
                  'XP: {total_xp}, Level {xp_level}']
    reply_base = '\n'.join(reply_lines)
    ustats['wl'] = ustats['won_matches']/ustats['lost_matches']
    reply = reply_base.format(**ustats)
    update.message.reply_text(reply)


def configure_telegram():
    """
    Configures the bot with a Telegram Token.

    Returns a bot instance.
    """

    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        logger.error('The TELEGRAM_TOKEN must be set')
        raise NotImplementedError

    bot = telegram.Bot(TELEGRAM_TOKEN)
    #dispatcher = Dispatcher(bot, None, workers=0)
    return bot


def webhook(event, context):
    """
    Runs the Telegram webhook.
    """

    bot = configure_telegram()
    dispatcher = Dispatcher(bot, None, workers=0)

    dispatcher.add_handler(CommandHandler('start', start_callback))
    dispatcher.add_handler(CommandHandler('version', version_callback))
    dispatcher.add_handler(CommandHandler('refratio', refratio_callback, pass_args=True))
    dispatcher.add_handler(CommandHandler('predict', predict_callback, pass_args=True))
    dispatcher.add_handler(CommandHandler('stats', user_stats_callback, pass_args=True))

    logger.info('Event: {}'.format(event))

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)
        dispatcher.process_update(update)
        logger.info('Message sent')
        return OK_RESPONSE
    return ERROR_RESPONSE


def set_webhook(event, context):
    """
    Sets the Telegram bot webhook.
    """

    logger.info('Event: {}'.format(event))
    bot = configure_telegram()
    url = 'https://{}/{}/'.format(
        event.get('headers').get('Host'),
        event.get('requestContext').get('stage'),
    )
    webhook = bot.set_webhook(url)

    if webhook:
        return OK_RESPONSE
    return ERROR_RESPONSE
