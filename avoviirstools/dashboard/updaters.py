#!/usr/bin/env python

# -*- coding: utf-8 -*-
import zmq
from datetime import datetime
import threading
from posttroll.message import Message
import os
import os.path
import numpy as np
import pandas as pd


UPDATE_PUBLISHER = "tcp://viirscollector:19191"
SDR_PUBLISHER = "tcp://viirscollector:29092"
PICKLE_DIR = "/viirs/pickle"
UPDATE_PICKLE = os.path.join(PICKLE_DIR, "task_queue.pickle")
SDR_PICKLE = os.path.join(PICKLE_DIR, "sdr.pickle")


class SdrSubscriber(threading.Thread):
    def __init__(self, context):
        threading.Thread.__init__(self)
        self.socket = context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "pytroll://AVO/viirs/sdr")
        self.socket.connect(SDR_PUBLISHER)
        self.lock = threading.Lock()
        self.initalize()

    def initalize(self):
        if os.path.exists(SDR_PICKLE):
            print("loading {}".format(SDR_PICKLE))
            self.datafiles = pd.read_pickle(SDR_PICKLE)
        else:
            print("Can't find {}".format(SDR_PICKLE))
            self.datafiles = pd.Series()

    @property
    def sdrs(self):
        return self.datafiles

    def flush(self):
        last_week = pd.to_datetime("now") - pd.Timedelta("7 days")
        with self.lock:
            self.datafiles.truncate(before=last_week)
            copy = self.datafiles.copy(deep=True)

        copy.to_pickle(os.path.join(SDR_PICKLE))

    def run(self):
        print("starting SDR subscriber loop")
        while True:
            msg_bytes = self.socket.recv()
            print("GOT SDR: {}".format(msg_bytes))
            npnow = pd.to_datetime("now")
            message = Message.decode(msg_bytes)
            filename = os.path.basename(message.data["uri"])
            file_time = datetime.strptime(filename[-69:-51], "_d%Y%m%d_t%H%M%S")
            npthen = pd.to_datetime(file_time)
            latency = (npnow - npthen) / pd.Timedelta("1 s")
            with self.lock:
                self.datafiles[npnow] = latency


class UpdateSubscriber(threading.Thread):
    def __init__(self, context):
        threading.Thread.__init__(self)
        self.socket = context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.socket.connect(UPDATE_PUBLISHER)
        self.lock = threading.Lock()
        self.initialize()

    def initialize(self):
        if os.path.exists(UPDATE_PICKLE):
            print("loading {}".format(UPDATE_PICKLE))
            self.waiting_tasks = pd.read_pickle(UPDATE_PICKLE)
        else:
            self.waiting_tasks = pd.Series()
            print("Can't find {}".format(UPDATE_PICKLE))

    @property
    def updates(self):
        return self.waiting_tasks

    def flush(self):
        lastweek = pd.to_datetime("now") - pd.Timedelta("7 days")
        with self.lock:
            self.waiting_tasks.truncate(before=lastweek)
            self.waiting_tasks = self.waiting_tasks.resample("1min").apply( "max")
            copy = self.waiting_tasks.copy()

        copy.to_pickle(os.path.join(UPDATE_PICKLE))

    def run(self):
        while True:
            message = self.socket.recv_json()
            npnow = pd.to_datetime("now")
            with self.lock:
                self.waiting_tasks.at[npnow] = message["queue length"]