#!/usr/bin/env python

import os
from socket import *
import struct
import sys
from threading import Lock, Thread
#import eyed3
import base64


QUEUE_LENGTH = 10
SEND_BUFFER = 4096

clients = {}
# per-client struct
class Client:
    def __init__(self,conn = None):
        self.lock = Lock()
        self.conn = conn
        self.id = -1
        self.responses = False #flag for client when
        self.data = None



# TODO: Thread that sends music and lists to the client.  All send() calls
# should be contained in this function.  Control signals from client_read could
# be passed to this thread through the associated Client object.  Make sure you
# use locks or similar synchronization tools to ensure that the two threads play
# nice with one another!
def client_write(client,songlist,encode_dic):


    while True:
        if client.responses:


            #length = len(client.data)/SEND_BUFFER
            while client.data and client.responses:
                #client.lock.acquire()
                send = client.data[:SEND_BUFFER]
                client.data = client.data[SEND_BUFFER:]
                client.conn.sendall(send)
                #print "server sending:",send

                #client.lock.release()


            #send the end of message
            client.lock.acquire()
            end = "\r\n\r\n"
            #print "sending end..."
            client.conn.sendall(end)
            client.lock.release()


            client.data = None
            client.responses = False




# TODO: Thread that receives commands from the client.  All recv() calls should
# be contained in this function.
def client_read(client,songlist,encode_dic):

    while True:
        data = client.conn.recv(SEND_BUFFER)


        data = data.split(" ")
        cmd = data[0]
        #print "receiving,",cmd

        #deal with data
        if cmd in ['quit', 'q', 'exit']:
            print "client "+str(clients[client]) +" quitting..."
            client.conn.close()
            return
        elif cmd in ['l', 'list']:
            client.lock.acquire()
            client.data = "+OK list\r\n"
            for i,s in enumerate(songlist):
                client.data += str(i)+": "+s+"\r\n"
            client.responses = True
            client.lock.release()


        elif cmd in ['p', 'play']:
            client.lock.acquire()
            client.responses = False
            client.data = ""
            client.lock.release()
            #client.lock.acquire()

            if data[1][0].isdigit():
                id = int(data[1])
                if id >=len(songlist):
                    client.data ="+NO erro out\r\n"
                else:

                    #print "song:"+songlist[id]
                    client.data ="+OK play "+str(id)+str(songlist[id])+"\r\n"
                    #print "client data",client.data
                    client.data += encode_dic[songlist[id]]
            else:
                songs= data[1:]
                songName = " ".join(songs)
                if songName+".mp3" in songlist or songName in songlist:
                    if songName not in songlist:
                        songName +='.mp3'
                    id = songlist.index(songName)
                    client.data ="+OK play "+str(id)+str(songlist[id])+"\r\n"
                    client.data += encode_dic[songlist[id]]
                else:
                    client.data ="+NO erro out\r\n"



            client.responses = True
            #client.lock.release()

        elif cmd in ['s', 'stop']:
            client.lock.acquire()
            client.responses = False
            #client.data = "+OK stop"
            client.data = ""
            client.lock.release()
        else:
            client.lock.acquire()
            client.data ="+NO erro Unk\r\n"
            client.responses = True
            client.lock.release()







def encode_mp3(song_name):
    f = open(song_name, 'r')
    data = f.read()
    f.close()
    return data

    '''
    with open(song_name, 'r') as music:
        #music_64_encode = base64.b64encode(music.read())
        music_64_encode = music.read()
    return music_64_encode
    '''

def get_mp3s(musicdir):
    print("Reading music files...")
    songs = []
    songlist = []
    encode_dic = {}


    for filename in os.listdir(musicdir):
        if not filename.endswith(".mp3"):
            continue

        # TODO: Store song metadata for future use.  You may also want to build
        # the song list once and send to any clients that need it.
        #audiofile = eyed3.load(musicdir+"/"+filename)
        #print("metadata",audiofile.tag.artist)
        songs.append(filename)
        songlist.append(filename)
        music_encode = encode_mp3(musicdir+"/"+filename)
        encode_dic[filename] = music_encode #song name with all the encoded data stored in

    print("Found {0} song(s)!".format(len(songs)))
    return songs,songlist,encode_dic

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python server.py [port] [musicdir]")
    if not os.path.isdir(sys.argv[2]):
        sys.exit("Directory '{0}' does not exist".format(sys.argv[2]))

    port = int(sys.argv[1])

    songs, songlist,encode_dic = get_mp3s(sys.argv[2])
    threads = []


    # TODO: create a socket and accept incoming connections
    s = socket(AF_INET, SOCK_STREAM)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind(('localhost', port))
    s.listen(10)

    while True:
        conn, addr = s.accept()

        client = Client(conn)
        num = len(clients)
        clients[client] = num
        t = Thread(target=client_read, args=(client,songlist,encode_dic,))
        threads.append(t)
        t.start()


        t = Thread(target=client_write, args=(client,songlist,encode_dic,))
        threads.append(t)
        t.start()


    s.close()


if __name__ == "__main__":
    main()
