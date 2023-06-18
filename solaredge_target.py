#!/usr/bin/env python3

import solaredge

import http.server
import time
import socket
import urllib.request
import configparser
import datetime
import time
import json


class Solar:
    def __init__(self, apikey):
        self.api = solaredge.Solaredge(apikey)

        sites = []
        info = self.api.get_list()
        for p in info["sites"]["site"]:
            sites.append(p["id"])
        self.sites = sites
        self.cache = {"valid_until": 0}

    def pull(self):
        if time.time() < self.cache["valid_until"]:
            return self.cache["data"]

        data = {}
        for site in self.sites:
            to_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            from_time = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            d = self.api.get_power_details(site, from_time, to_time)
            data[site] = {}

            for meter in d["powerDetails"]["meters"]:
                data[site][meter["type"]] = meter["values"]

        self.cache["data"] = data
        self.cache["valid_until"] = time.time() + 300
        return data


def get_solar():
    config = configparser.ConfigParser()
    config.read("solaredge.conf")
    apikey = config["solaredge"]["apikey"]
    return Solar(apikey)


def get_metrics_class(solar):
    class returnclass(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            data = solar.pull()
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4")
            self.end_headers()

            self.wfile.write(
                bytes(
                    "# HELP solar_production The reported solar production\n", "utf-8"
                )
                + bytes("# TYPE solar_production gauge\n", "utf-8")
            )

            for site in data:
                for meter in data[site]:
                    data[site][meter].sort(key=lambda x: x["date"])

                    for measurement in data[site][meter]:
                        ts = datetime.datetime.strptime(
                            measurement["date"], "%Y-%m-%d %H:%M:%S"
                        ).timestamp()

                        v = 0
                        if "value" in measurement:
                            v = measurement["value"]

                        self.wfile.write(
                            bytes(
                                f'solar_production{{site="{site}", meter="{meter}"}} {v} {ts}\n',
                                "utf-8",
                            )
                        )

                    if len(data[site][meter]):
                        measurement = data[site][meter][-1]
                        v = 0
                        if "value" in measurement:
                            v = measurement["value"]

                        self.wfile.write(
                            bytes(
                                f'solar_production{{site="{site}", meter="{meter}"}} {v}\n',
                                "utf-8",
                            )
                        )

    return returnclass


if __name__ == "__main__":
    solar = get_solar()
    web = http.server.HTTPServer(("", 8081), get_metrics_class(solar))
    web.serve_forever()
