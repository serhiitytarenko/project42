import argparse
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pathlib

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

DT_FORMAT = '%a, %d %b %Y %H:%M:%S %z'
REPORT_DIR = pathlib.Path(__file__).parent.absolute() / 'report'


def get_last_comment(comments):
    if not comments:
        return {}
    _comments = []
    for comment in comments.findall('.//comment'):
        _comment = comment.attrib
        _comment['text'] = comment.text
        _comment['created'] = datetime.strptime(_comment['created'],
                                                DT_FORMAT)
        _comments.append(_comment)
    _comments.sort(key=lambda _item: _item['created'])
    return _comments[-1]


def get_delta_time(created, closed):
    _created = datetime.strptime(created, DT_FORMAT)
    _closed = datetime.strptime(closed, DT_FORMAT)
    return _closed - _created


def get_ticket(ticket):
    _ticket = {
        'id': ticket.find('.//key').text,
        'title': ticket.find('.//title').text,
        'type': ticket.find('.//type').text,
        'priority': ticket.find('.//priority').text,
        'status': ticket.find('.//status').text,
        'created': ticket.find('.//created').text,
        'updated': ticket.find('.//updated').text,
    }
    return _ticket


def parse_data(filename):
    urgent_priorities = ['Blocker', 'Critical', 'Major']
    opened_tickets = {}
    closed_bugs = {}
    urgent_tickets = []
    tree = ET.parse(filename)
    root = tree.getroot()
    for item in root.findall('.//item'):
        ticket = get_ticket(item)
        if ticket['status'] == 'Open':
            opened_tickets[
                ticket.get('type')] = opened_tickets.setdefault(
                ticket.get('type'), 0) + 1
        if ticket.get('type') == 'Bug' and ticket['status'] == 'Closed':
            closed_bugs.setdefault(ticket.get('priority'), []).append(
                get_delta_time(ticket['created'], ticket['updated'])
            )
        if ticket.get('priority') in urgent_priorities:
            ticket['last_comment'] = get_last_comment(
                item.find('.//comments'))
            urgent_tickets.append(ticket)
    return opened_tickets, closed_bugs, urgent_tickets


def open_tickets_chart(opened_tickets, report_dir):
    plt.figure(figsize=(12, 7))
    data = list(opened_tickets.values())
    ticket_types = list(opened_tickets.keys())
    plt.bar(ticket_types, data)
    for i in range(len(ticket_types)):
        plt.text(i, data[i] + 0.25, data[i], ha='center')
    plt.title("Open tickets by type")
    plt.xlabel("Tickets")
    plt.ylabel("Amount")
    plt.savefig(report_dir / 'open_tickets_chart.png')


def mean_time_closed_bugs_chart(closed_bugs, report_dir):
    _bugs = {}
    for priority, list_time_delta in closed_bugs.items():
        average = sum(list_time_delta,
                      timedelta()) / len(list_time_delta)
        _bugs[priority] = average

    data = list(_bugs.values())
    priorities = list(_bugs.keys())
    zero = datetime.now()
    time2 = [t + zero for t in data]
    zero = mdates.date2num(zero)
    time = [t - zero for t in mdates.date2num(time2)]

    def dt2str(dt):
        d, seconds = dt.days, dt.seconds
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f'{d} days, {h} hr, {m} min, {s} sec'

    f = plt.figure(figsize=(15, 10))
    ax = f.add_subplot()
    ax.bar(priorities, time)
    plt.bar(priorities, time)
    for i in range(len(priorities)):
        plt.text(i, time[i] + 0.05, dt2str(data[i]), ha='center')
    plt.title("Meantime closed bugs by types")
    plt.xlabel("Bugs")
    plt.ylabel("Time")
    plt.savefig(report_dir / 'closed_bugs_chart.png')


def urgent_bugs_report(urgent_tickets, report_dir):
    with open(report_dir / 'urgent_bugs.csv', mode='w') as fp:
        wr = csv.writer(fp, delimiter=',', quotechar='"',
                        quoting=csv.QUOTE_MINIMAL)
        for ticket in urgent_tickets:

            lc_text = ticket.get('last_comment', {}).get('text', '')
            lc_created = ticket.get('last_comment', {}).get('created')
            if lc_created:
                lc_created = lc_created.strftime(DT_FORMAT)
            row = [ticket['id'], ticket['priority'], ticket['updated'],
                   lc_text, lc_created]
            wr.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="input_filename",
                        required=True)
    parser.add_argument('-o', '--output', dest="output",
                        type=lambda output: pathlib.Path(output),
                        default=REPORT_DIR)
    args = parser.parse_args()
    xml_file = args.input_filename
    report_dir = args.output
    report_dir.mkdir(parents=True, exist_ok=True)
    opened_tickets, closed_bugs, urgent_tickets = parse_data(xml_file)
    open_tickets_chart(opened_tickets, report_dir)
    mean_time_closed_bugs_chart(closed_bugs, report_dir)
    urgent_bugs_report(urgent_tickets, report_dir)
    print('Done.')
