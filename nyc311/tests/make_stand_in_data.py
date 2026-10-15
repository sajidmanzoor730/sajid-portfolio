#!/usr/bin/env python3
"""TEST STAND-IN ONLY. Generates fake rows with the same columns as the real 311 extract so the
pipeline can be dry-run without internet. These numbers mean NOTHING and must never be published.

    python3 tests/make_stand_in_data.py            # writes data/nyc311_raw.csv (overwrites a real download!)
"""
import csv, random, datetime as dt
random.seed(3)
cols = ["unique_key","created_date","closed_date","agency","agency_name","complaint_type","descriptor",
        "location_type","status","borough","incident_zip","incident_address","open_data_channel_type","resolution_description","latitude","longitude"]
types = {"NYPD": ["Noise - Residential", "Illegal Parking", "Blocked Driveway"], "HPD": ["HEAT/HOT WATER", "PLUMBING"],
         "DSNY": ["Missed Collection", "Dirty Conditions"], "DOT": ["Street Condition", "Traffic Signal Condition"]}
boros = ["BROOKLYN", "QUEENS", "MANHATTAN", "BRONX", "STATEN ISLAND", "Unspecified"]
rows = []
start = dt.datetime(2025, 3, 1)
for i in range(30000):
    ag = random.choice(list(types)); c = start + dt.timedelta(seconds=random.randint(0, 31*86400-1))
    closed = random.random() < 0.85
    cl = c + dt.timedelta(hours=random.expovariate(1/40)) if closed else None
    if cl and random.random() < 0.01: cl = c - dt.timedelta(hours=5)
    z = str(random.randint(10001, 11697)); z = z if random.random() > .02 else "N/A"
    lat, lon = (round(random.uniform(40.55, 40.9), 6), round(random.uniform(-74.2, -73.75), 6))
    if random.random() < .005: lat, lon = 0.0, 0.0
    rows.append([100000+i, c.isoformat(timespec="seconds"), cl.isoformat(timespec="seconds") if cl else "",
                 ag, ag, random.choice(types[ag]), "x", "Street", "Closed" if closed else "Open",
                 random.choice(boros), z, f"{random.randint(1,300)} TEST STREET", random.choice(["PHONE","ONLINE","MOBILE"]), "", lat, lon])
rows += random.sample(rows, 60)  # duplicate keys
with open("data/nyc311_raw.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols); w.writerows(rows)
print("Wrote STAND-IN data/nyc311_raw.csv with", len(rows), "rows (fake)")
