FROM tparkerusgs/avopytroll:release-1.9.0

WORKDIR /app
WORKDIR avoviirstools

COPY setup.py .
COPY setup.cfg .
COPY avoviirstools avoviirstools
RUN python setup.py install

RUN pip freeze > requirements.txt
COPY supervisord.conf /etc/supervisor/supervisord.conf
CMD ["supervisord"]
