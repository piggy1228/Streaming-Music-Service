#!/usr/bin/env python

import ao
import mad
import readline
import socket
import struct
import sys
import threading
from time import sleep
import socket
import base64

READ_BUFFER = 4096


downloaded = {}
playing = [False]

# The Mad audio library we're using expects to be given a file object, but
# we're not dealing with files, we're reading audio data over the network.  We
# use this object to trick it.  All it really wants from the file object is the
# read() method, so we create this wrapper with a read() method for it to
# call, and it won't know the difference.
# NOTE: You probably don't need to modify this class.
class mywrapper(object):
    def __init__(self):
        self.mf = None
        self.data = ""

    # When it asks to read a specific size, give it that many bytes, and
    # update our remaining data.
    def read(self, size):
        result = self.data[:size]
        self.data = self.data[size:]
        return result


# Receive messages.  If they're responses to info/list, print
# the results for the user to see.  If they contain song data, the
# data needs to be added to the wrapper object.  Be sure to protect
# the wrapper with synchronization, since the other thread is using
# it too!
def recv_thread_func(wrap, cond_filled, sock,download_dir):
    response = None


    while True:
        # TODO
        data = sock.recv(READ_BUFFER)
        #print "client receiving:",data\
        if "+OK " in data:
            wrap.data = ''
            wrap.mf = mad.MadFile(wrap)
            idx = data.find("+OK ")
            data = data[idx:]
        if "+NO " in data:
            idx = data.find("+NO ")
            data = data[idx:]



        if data[4:8] in ["list","play","erro"]:

            response = data[4:8]

            if response != "play":
                data = data[9:]
            else:
                i = 9
                id = ""
                while data[i].isdigit():
                    id += data[i]
                    i+=1

                current_play = ""
                while data[i] != "\r" and data[i+1] !="\n":
                    current_play += data[i]

                    i+=1
                print "current playing:",current_play
                playing[0] = True


        if response == "list":
            print data[:-3]


        if response == "play":
            #print "play:",current_play
            cond_filled.acquire()
            wrap.data += data
            cond_filled.notify()
            cond_filled.release()
        if response == 'erro':
            if data[:3] == "out":
                print "Oops!song number/name is not in the list, try again!"
            if data[:3] == "Unk":
                print "Oops! Unkown error!"
        if data[-4:] == "\r\n\r\n":
            #download the whole song
            if response == "play":
                download_mp3(current_play,wrap.data,download_dir)
                downloaded[id] = current_play
                #print "current downloaded:",downloaded
            response = None









# If there is song data stored in the wrapper object, play it!
# Otherwise, wait until there is.  Be sure to protect your accesses
# to the wrapper with synchronization, since the other thread is
# using it too!
def play_thread_func(wrap, cond_filled, dev):
    while True:
        """
        TODO
        example usage of dev and wrap (see mp3-example.py for a full example):

        """
        cond_filled.acquire()
        while not wrap.data:
            #response = None
            #buf = None
            #continue
            cond_filled.wait()
        #print "p ",playing
        if playing[0]:

            buf = wrap.mf.read()
            if buf is None:  # eof
                break

            dev.play(buffer(buf), len(buf))

        cond_filled.release()

def download_mp3(song_name,music,download_dir):
    #music_64_decode = base64.b64decode(music_64_encode)
    #print "song name is:",song_name,"dir:",download_dir
    music_result= open(download_dir+"/"+song_name, 'wb') # create a writable mp3 and write the decoding result
    music_result.write(music)
    print "finish downloading "+song_name
    #execfile("mp3-example.py music_result")


def sendRequest(sock,request):
    sock.sendall(request)
    #print "sending",request


def main():
    if len(sys.argv) < 4:
        print 'Usage: %s <download directory> <server name/ip> <server port>' % sys.argv[0]
        sys.exit(1)

    #get the download path from client to store downloaded songs
    download_dir = str(sys.argv[1])

    # Create a pseudo-file wrapper, condition variable, and socket.  These will
    # be passed to the thread we're about to create.
    wrap = mywrapper()
    wrap.mf = mad.MadFile(wrap)

    # Create a condition variable to synchronize the receiver and player threads.
    # In python, this implicitly creates a mutex lock too.
    # See: https://docs.python.org/2/library/threading.html#condition-objects
    cond_filled = threading.Condition()

    # Create a TCP socket and try connecting to the server.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((sys.argv[2], int(sys.argv[3])))



    # Create a thread whose job is to receive messages from the server.
    recv_thread = threading.Thread(
        target=recv_thread_func,
        args=(wrap, cond_filled, sock,download_dir)
    )
    recv_thread.daemon = True
    recv_thread.start()

    # Create a thread whose job is to play audio file data.
    dev = ao.AudioDevice('pulse')
    play_thread = threading.Thread(
        target=play_thread_func,
        args=(wrap, cond_filled, dev)
    )
    play_thread.daemon = True
    play_thread.start()



    # Enter our never-ending user I/O loop.  Because we imported the readline
    # module above, raw_input gives us nice shell-like behavior (up-arrow to
    # go backwards, etc.).
    while True:
        line = raw_input('>> ')


        if ' ' in line:
            cmd, args = line.split(' ', 1)
        else:
            cmd = line

        # TODO: Send messages to the server when the user types things.
        if cmd in ['l', 'list']:
            print 'The user asked for list.'
            sendRequest(sock,cmd)


        elif cmd in ['p', 'play']:
            if ' ' not in line:
                print "Enter song id or song name!"
                continue


            print 'The user asked to play:', args


            #wrap.mp = None
            #if the music is already downloaded locally
            '''
            if args in downloaded:
                f = open(download_dir+"/"+downloaded[args], 'r')
                data = f.read()
                f.close()

                # Hand off the data to the wrapper object and use it to create a new MAD
                # library decoder.  For your client, you will be appending chunks of data
                # to the end of wrap.data in your receiver thread while the player thread
                # is removing and playing data from the front of it.
                wrap.data = data
            '''

            if playing[0]:
                playing[0] = False
                cond_filled.acquire()

                wrap.data = ''
                wrap.mf = mad.MadFile(wrap)
                cond_filled.notify()
                cond_filled.release()


                sendRequest(sock,"stop")


            sendRequest(sock,cmd+" "+args)



        elif cmd in ['s', 'stop']:
            if not playing[0]:
                print "No song is playing!"
                continue
            playing[0] = False
            print 'The user asked for stop.'
            cond_filled.acquire()

            wrap.data = ''
            wrap.mf = mad.MadFile(wrap)
            cond_filled.notify()
            cond_filled.release()


            sendRequest(sock,cmd)


        elif cmd in ['quit', 'q', 'exit']:
            sendRequest(sock,cmd)
            sock.close()
            sys.exit(0)
        else:
            print "Try again, wrong command"

if __name__ == '__main__':
    main()
