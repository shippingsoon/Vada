#!/usr/bin/env python
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import Skype4Py
import config
import argparse
import time
import random
from json import load
from urllib2 import urlopen
import sys
from threading import Timer

class Vada:
	#Vada's constructor.
	def __init__(self, enable_mpd=False):
		self.chat = {}
		self.users = {}
		self.skype = Skype4Py.Skype()
		self.mode = config.modes['argparse']
		self.trivia = {}
		self.openSkype()
		#If the Music Player Daemon is enabled.
		if enable_mpd:
			from mpd import (MPDClient, CommandError)
			from socket import error as SocketError
			self.client = MPDClient()
			self.mpdConnect(self.client, config.mpd_host)
	#Establish a connection with the Music Player Daemon.
	def mpdConnect(self, client, mpd_host):
		try:
			client.connect(**mpd_host)
		except SocketError:
			print 'Failed to connect to MPD server.'
			sys.exit(1)
		print 'Connected to MPD server'
	#Handles onMessageReceived events.
	def getMessage(self, message, status):
		if status == Skype4Py.cmsReceived:
			self.handleMessage(message)
	#Try to establish a connection with a skype client.
	def attachSkype(self):
		try:
			self.skype.Attach(Wait=True)
		except Skype4Py.SkypeAPIError, e:
			print 'Error: %s\nAre you currently logged into your account? ' % e
		return self.skype.AttachmentStatus == Skype4Py.apiAttachSuccess
	#Opens a Skype client and attempts to establish a connection to it.
	def openSkype(self):
		#If an instance of skype is not running start one.
		if not self.skype.Client.IsRunning:
			self.skype.Client.Start()
		#If we fail to connect, take a nap and try again later.
		while not self.attachSkype():
			time.sleep(1)
		#Try to find a group chat.
		self.chat = self.getGroupChat()
		if not self.chat:
			exit('Could not find a group chat')
		#Here we tell the getMessage() member to handle onMessageStatus events.
		#In other words, when our bot receives a message, getMessage() will be called.
		self.skype.OnMessageStatus = self.getMessage
		#Display Vada's information.
		self.displayInfo()
	#Returns the most recent group chat.
	def getGroupChat(self):
		print "Searching for a group chat..."
		for chat in self.skype.RecentChats:
			if len(chat.Members) > 2:
				print "Found chat: %s" % chat.Name
				return chat
	#Displays Vada's information.
	def displayInfo(self):
		print 'Full Name: %s' % self.skype.CurrentUser.FullName
		print 'Status: %s' % self.skype.CurrentUser.OnlineStatus
	#Returns a daily fortune.
	def getFortune(self, handle, *args):
		#If this user does not have a fortune give them one.
		if not handle in self.users:
			self.users[handle] = {'fortune':random.choice(config.fortunes)}
		return self.users[handle]['fortune']
	#Returns an FML.
	def getFML(self, *args):
		return random.choice(config.fmls)
	#Retrieve a user's status.
	def getStatus(self, handle, *args):
		options = ['TOLD', 'NOT TOLD', random.choice(config.tolds)]
		status = random.choice(options)
		message = "%s's STATUS" % handle
		for option in options:
			message += "\n[%s] %s" % ('x' if status == option else ' ', option)
		return message
	#Returns a quote.
	def getQuote(self, *args):
		return config.quotes[random.randint(0, (len(config.quotes)-1))]
	#Queries openweathermap.org for the current weather.
	def getWeather(self, city = 'Savannah', state = 'Ga', *args):
		city = city.replace(',', '')
		data = urlopen('http://openweathermap.org/data/2.1/find/name?units=imperial&q=%s,%s' % (city, state))
		towns = load(data)
		if towns['count'] > 0:
			town = towns['list'][0]
			return u'The weather for %s, %s:\nTemperatue: %s\N{DEGREE SIGN}\nDetails: %s' % (city.title(), state.title(), town['main']['temp'], town['weather'][0]['description'])
		return "Couldn't determine the weather..."
	#Retrieve this program's version
	def getVersion(self, *args):
		return 'You are running: %s' % config.VERSION
	#Get Vada's source code.
	def getSource(self, *args):
		return 'https://github.com/shippingsoon/Vada'
	#Retrieve useful links.
	def getLink(self, *args):
		return '\n'.join(config.links)
	#Set a reminder.
	def setReminder(self, name = None, minutes = 1, message = None, *args):
		minutes = int(minutes)
		args = ' '.join(args) if args else ''
		if message and name:
			timer = Timer(minutes * 60, self.getReminder, (name, message + ' ' + args))
			response = 'Okay, I will remind %s in %s minute%s when it\'s time' % (name, minutes, 's' if minutes > 1 else '')
			self.sendMessage(response)
			timer.start()
		else:
			self.sendMessage('Silly human')
	#Get a reminder.
	def getReminder(self, name, message):
	    self.chat.SendMessage('%s, someone told me to remind you of this: %s' % (name, message))
	#Send a message to the chat.
	def sendMessage(self, message, *args):
		if self.chat:
			self.chat.SendMessage(message)
	#A custom action for argparse.
	class Action(argparse.Action):
		def __init__(self, option_strings, dest, nargs=None, const=None, default=None, type=None, choices=None, required=False, help=None, metavar=None, parent=None):
			self.parent = parent
			argparse.Action.__init__(self, option_strings=option_strings, dest=dest, nargs=nargs, const=const, default=default, type=type, choices=choices, required=required, help=help, metavar=metavar)
		def __call__(self, parser, namespace, args, option_string=None, parent='who'):
			#Force our default values to be an array.
			self.default = self.default if isinstance(self.default, list) else [self.default]
			#If we did not get any input, set a default value.
			if not args:
				args = self.default
			#Merge the arguments with the default arguments.
			if len(args) < len(self.default):
				args += self.default[len(args):]
			#Encapsulate Vada's methods for easy access.
			#Here we use the (*) operator to unpack our argument list.
			response = {
				's':self.parent.getStatus,
				'fml':self.parent.getFML,
				'source':self.parent.getSource,
				'w':self.parent.getWeather,
				'f':self.parent.getFortune,
				'q':self.parent.getQuote,
				'v':self.parent.getVersion,
				'l':self.parent.getLink,
				't':self.parent.startTrivia,
				'r':self.parent.setReminder
			}.get(self.dest, lambda *x : None)(*args)
			if response:
				self.parent.sendMessage(response)
	#Handle user input.
	def handleMessage(self, message):
		#Get the latest message in the group chat and split it into an array.
		arguments = message.Body.split(' ')
		#The message's sender.
		sender = message.FromDisplayName
		#Process the message with argparse.
		if self.mode == config.modes['argparse']:
			parser = argparse.ArgumentParser(prog='', prefix_chars='.')
			#Set up arguments with common default parameters.
			args = [['.s', '.status'], ['.fml', '.fmylife'], ['.f', '.fortune'], ['.q', '.quote'], ['.v', '.version'], ['.l', '.link'], ['.source', '.code']] 
			for arg in args:
				parser.add_argument(*arg, nargs='*', default=sender, action=self.Action, parent=self, help=argparse.SUPPRESS)
			parser.add_argument('.w', '.weather', nargs='*', default=['Savannah', 'Ga'], action=self.Action, parent=self, help=argparse.SUPPRESS)
			parser.add_argument('.t', '.trivia', nargs='*', default=['misc', '5', '20'], action=self.Action, parent=self, help=argparse.SUPPRESS)
			parser.add_argument('.r', '.remind', nargs='*', default=[sender, '1'], action=self.Action, parent=self, help=argparse.SUPPRESS)
			try:
				parser.parse_args(arguments)
			except SystemExit:
				pass
		elif self.mode == config.modes['trivia']:
			self.handleTrivia(sender, message.Body)
	#Initiate a game of trivia.
	def startTrivia(self, theme = 'misc', max_rounds = 5, hint_rate = 20, *args):
		#Make sure this trivia theme exist.
		if not theme in config.trivias:
			return self.stopTrivia('Unknown trivia theme (%s)' % theme)
		#Switch to trivia mode.
		self.mode = config.modes['trivia']
		self.trivia = {
			'theme':theme,
			'max_rounds':1 if int(max_rounds) <= 0 else int(max_rounds),
			'round':0, 
			'hint_rate':20 if float(hint_rate) <= 0 else float(hint_rate),
			'winner':[],
			'hint_index':0,
			'timer':None
		}
		self.postTrivia()
	#Stop a trivia game.
	def stopTrivia(self, message = None):
		self.mode = config.modes['argparse']
		self.sendMessage(message if message else 'Game over')
	#Post a trivia question.
	def postTrivia(self):
		theme = self.trivia['theme']
		round = self.trivia['round']
		#Cancel any persistent timers from the previous round.
		if self.trivia['timer']:
			self.trivia['timer'].cancel()
		if round < len(config.trivias[theme]) and round < self.trivia['max_rounds']:
			self.sendMessage('Trivia question %s of %s' % ((round + 1), self.trivia['max_rounds']))
			#Post the trivia question.
			self.sendMessage(config.trivias[theme][round][0])
			#This index will be used to mask the answer.
			self.trivia['hint_index'] = len(config.trivias[theme][round][1]) - 1
			#In n seconds, post a hint.
			self.trivia['timer'] = Timer(self.trivia['hint_rate'], self.triviaHint)
			self.trivia['timer'].daemon = True
			self.trivia['timer'].start()
		else:
			#Count the occurrences of a user's name in the winner list to determine the game's winner.
			winner = 'Vada' if not self.trivia['winner'] else max(set(self.trivia['winner']), key=self.trivia['winner'].count)
			return self.stopTrivia('Game Over\nGame winner: %s' % winner)
	#Post a trivia answer.
	def triviaAnswer(self, theme, round):
		return config.trivias[theme][round][1]
	#Checks if a user's answer is valid.
	def handleTrivia(self, sender, message = ''):
		answer = self.triviaAnswer(self.trivia['theme'], self.trivia['round'])
		#Do a case insensitive comparison to see if the user posted the correct answer.
		if (message.lower() == answer.lower()):
			self.sendMessage('Round winner: %s' % sender)
			self.trivia['winner'].append(sender)
			#Advance the round.
			self.trivia['round'] += 1
			self.postTrivia()
	#Post a hint to the answer in the chat.
	def triviaHint(self):
		answer = self.triviaAnswer(self.trivia['theme'], self.trivia['round'])
		index = self.trivia['hint_index']
		if self.trivia['hint_index'] > 0:
			#Mask the answer.
			self.sendMessage('Hint: %s' % answer[-(-index):].rjust(len(answer), "*"))
			self.trivia['hint_index'] -= 1
			#Use recursion to keep the hints rolling.
			self.trivia['timer'] = Timer(self.trivia['hint_rate'], self.triviaHint)
			self.trivia['timer'].start()
		else:
			#If the hint is fully unmasked, declare Vada the winner of the round.
			self.handleTrivia('Vada', answer)
#Handle command line arguments.
argument = argparse.ArgumentParser(description=config.VERSION, prog='vada.py', prefix_chars='-')
argument.add_argument('--mpd', '-mpd', action="store_true", help='Enable MPD (Music Player Daemon)?')
try:
	args = argument.parse_args()
except SystemExit:
	print("Unknown argument")
	sys.exit(2)
#Initiate Vada.
Vada(args.mpd)
while True:
	time.sleep(1)

#Copyright 2014 Shippingsoon - All Rights Reserved
