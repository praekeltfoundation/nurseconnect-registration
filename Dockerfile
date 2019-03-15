FROM praekeltfoundation/django-bootstrap:py3.6

COPY . /app
RUN pip install --no-cache-dir -e . 

ENV DJANGO_SETTINGS_MODULE "nurseconnect_registration.settings"
RUN SECREY_KEY=foo ./manage.py collectstatic --noinput
CMD ["nurseconnect_registration.wsgi:application"]
