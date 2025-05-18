import gc
from dateutil import parser
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
from icalendar import Calendar, Event
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEnginePage
import argparse
from bs4 import BeautifulSoup, SoupStrainer
import pytz

cal = Calendar()
cal.add("prodid", "-//Andyhub//BPL Events Scraper//EN")
cal.add("version", "2.0")
cal.add("summary", "Brooklyn Public Library events")


class Page(QWebEnginePage):

    def __init__(self, url):
        self.app = QApplication(sys.argv)
        QWebEnginePage.__init__(self)
        self.html = ''
        self.loadFinished.connect(self._on_load_finished)
        self.load(QUrl(url))
        self.app.exec_()

    def _on_load_finished(self):
        self.html = self.toHtml(self.Callable)
        print('Load finished')

    def Callable(self, html_str):
        self.html = html_str
        self.app.quit()


def getTheDiv(html_str, index):
    flex = html_str.find_all("div", class_="flex")[index]
    return flex.find_all("div")[1].text


def makeTime(date, time):
    raw = parser.parse(f"{date.split(', ')[1]} {time} EST")
    return raw.astimezone(pytz.utc)


for i in range(1, 4):
    URL = f"https://discover.bklynlibrary.org/?event=true&event=true&eventage=Adults&eventlocation=Central+Library%7C%7CCentral+Library%2C+Business+%26+Career+Center%7C%7CCentral+Library%2C+Info+Commons%7C%7CCrown+Heights+Library%7C%7CPacific+Library%7C%7CPark+Slope+Library%7C%7CBrooklyn+Heights+Library%7C%7CClinton+Hill+Library%7C%7CLibrary+for+Arts+%26+Culture&pagination={i}"  # noqa: E501
    page = Page(URL)
    results = SoupStrainer("div", attrs={"class": "result-detail-text"})
    soup = BeautifulSoup(page.html, "lxml", parse_only=results)
    resultSoup = list(soup)
    for result in resultSoup:
        title = result.find_all("div", class_="result-title")[0].text
        if len(result.find_all("div", class_="event-canceled-msg")) > 0:
            title = f"CANCELLED: {title}"
        link = result.find_all("a")[0]['href']
        dtl = result.find_all("div", class_="event-date-location-container")[0]
        date = getTheDiv(dtl, 0)
        time = getTheDiv(dtl, 1).split(' to ')
        start_time = makeTime(date, time[0])
        end_time = makeTime(date, time[1])
        location = getTheDiv(dtl, 2)
        summary = result.find("div", class_="web-summary").text
        description = f"{summary}\n\n{link}"

        event = Event()
        event.add('summary', title)
        event.add('dtstart', start_time)
        event.add('dtend', end_time)
        event.add('location', location)
        event.add('description', description)
        cal.add_component(event)

    soup.decompose()
    soup = None
    gc.collect()


class GetHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(code=200)
        self.send_header(keyword='Content-type', value='text/calendar')
        self.end_headers()
        self.wfile.write(cal.to_ical())


argParser = argparse.ArgumentParser()
argParser.add_argument('-p', '--port', type=int, default=8000)
httpd = HTTPServer(('', argParser.parse_args().port), GetHandler)
httpd.serve_forever()
