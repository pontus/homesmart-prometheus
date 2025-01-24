#!/usr/bin/env python3

import zeroconf
import prometheus_client

import time
import socket
import urllib.request
import time
import json


class P1Meter:
    def __init__(self, host):
        self.host = socket.inet_ntoa(host)

    def pull(self):
        url = f"http://{self.host}/api/v1/data"

        with urllib.request.urlopen(url) as data:
            if data.status == 200:
                j = json.loads(data.read())
                # j['timestamp'] = time.time()
                return j


class Meters(zeroconf.ServiceListener):
    meters = {}
    metrics = {}

    def __init__(self):
        metrics = self.metrics

        metrics["wifi_strength"] = prometheus_client.metrics.Gauge(
            "wifi_strength", "Strength of wifi for meter", ["unique_id"]
        )
        metrics["total_power_import_kwh"] = prometheus_client.metrics.Gauge(
            "total_power_import_kwh", "Total amount of bought power", ["unique_id"]
        )
        metrics["total_power_import_t1_kwh"] = prometheus_client.metrics.Gauge(
            "total_power_import_t1_kwh", "Total amount of bought power", ["unique_id"]
        )
        metrics["total_power_export_kwh"] = prometheus_client.metrics.Gauge(
            "total_power_export_kwh", "Total amount of sold power", ["unique_id"]
        )
        metrics["total_power_export_t1_kwh"] = prometheus_client.metrics.Gauge(
            "total_power_export_t1_kwh", "Total amount of sold power", ["unique_id"]
        )
        metrics["active_power_w"] = prometheus_client.metrics.Gauge(
            "active_power_w", "Current power import", ["unique_id"]
        )
        metrics["active_power_l1_w"] = prometheus_client.metrics.Gauge(
            "active_power_l1_w", "Current power import L1", ["unique_id"]
        )
        metrics["active_power_l2_w"] = prometheus_client.metrics.Gauge(
            "active_power_l2_w", "Current power import L2", ["unique_id"]
        )
        metrics["active_power_l3_w"] = prometheus_client.metrics.Gauge(
            "active_power_l3_w", "Current power import L3", ["unique_id"]
        )
        metrics["active_voltage_l1_v"] = prometheus_client.metrics.Gauge(
            "active_voltage_l1_v", "Current voltage import L1", ["unique_id"]
        )
        metrics["active_voltage_l2_v"] = prometheus_client.metrics.Gauge(
            "active_voltage_l2_v", "Current voltage import L2", ["unique_id"]
        )
        metrics["active_voltage_l3_v"] = prometheus_client.metrics.Gauge(
            "active_voltage_l3_v", "Current voltage import L3", ["unique_id"]
        )
        metrics["active_current_a"] = prometheus_client.metrics.Gauge(
            "active_current_a", "Current current import", ["unique_id"]
        )
        metrics["active_current_l1_a"] = prometheus_client.metrics.Gauge(
            "active_current_l1_a", "Current current import L1", ["unique_id"]
        )
        metrics["active_current_l2_a"] = prometheus_client.metrics.Gauge(
            "active_current_l2_a", "Current current import L2", ["unique_id"]
        )
        metrics["active_current_l3_a"] = prometheus_client.metrics.Gauge(
            "active_current_l3_w", "Current current import L3", ["unique_id"]
        )

    def async_update_service(
        self, zc: zeroconf.Zeroconf, type_: str, name: str
    ) -> None:
        info = zc.get_service_info(type_, name)
        self.meters[name] = P1Meter(info.addresses[0])
        print(f"Service {name} updated")

    def remove_service(self, zc: zeroconf.Zeroconf, type_: str, name: str) -> None:
        del self.meters[name]
        print(f"Service {name} removed")

    def add_service(self, zc: zeroconf.Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        self.meters[name] = P1Meter(info.addresses[0])

    def refresh_all_meters(self):
        for k, v in self.meters.items():
            data = v.pull()

            id = data["unique_id"]

            for k in ["unique_id", "wifi_ssid", "meter_model", "external"]:
                if k in data:
                    del data[k]

            for p in data:
                self.metrics[p].labels(unique_id=id).set(data[p])


def serve():
    zc = zeroconf.Zeroconf()
    listener = Meters()
    browser = zeroconf.ServiceBrowser(zc, "_hwenergy._tcp.local.", listener)
    prometheus_client.start_http_server(8000)

    while True:
        time.sleep(5)
        listener.refresh_all_meters()
    zc.close()


if __name__ == "__main__":
    serve()
