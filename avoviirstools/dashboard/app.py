#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
import dash
import zmq
import threading
import time
import flask

PICKLING_INTERVAL = 5 * 60
external_css = [
    "https://fonts.googleapis.com/css?family=Merriweather:300&display=swap",
    "https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css",
    "https://stackpath.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
]
zmq_context = zmq.Context()


class Flusher(threading.Thread):
    def __init__(self, *args):
        threading.Thread.__init__(self)
        self.flushables = list(args)

    def run(self):
        while True:
            time.sleep(PICKLING_INTERVAL)
            print("flushing")
            for flushable in self.flushables:
                flushable.flush()


flusher = Flusher()

server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=external_css)

from avoviirstools.dashboard.layout import apply_layout

apply_layout()

from avoviirstools.dashboard.data_arrival import DataArrival

data_arrival = DataArrival()
flusher.flushables.append(data_arrival)

from avoviirstools.dashboard.product_generation import ProductGeneration

product_generation = ProductGeneration()
flusher.flushables.append(product_generation)

from avoviirstools.dashboard.volcview_images import VolcviewImages

volcview_images = VolcviewImages()
flusher.flushables.append(volcview_images)

flusher.start()
