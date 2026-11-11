"""Moving target: every +step_ready Ready rows raise the target by step_target. Prints Ready, the target and whether it rose."""
import datetime, json, os
D = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(D, "target.json")
t = json.load(open(T, encoding="utf-8"))
ready = len([x for x in json.load(open(os.path.join(D, "rows.json"), encoding="utf-8"))["ready"] if not x.get("sent")])  # sent rows leave the count
rose = 0
while ready >= t["base"] + t["step_ready"]:
    t["base"] += t["step_ready"]; t["target"] += t["step_target"]; rose += 1
    t["history"].append([datetime.datetime.now().isoformat(timespec="minutes"), ready, t["target"]])
json.dump(t, open(T, "w", encoding="utf-8"), indent=1)
print("Ready %d, target %d, next raise at %d Ready%s" % (ready, t["target"], t["base"] + t["step_ready"], ", TARGET RAISED x%d" % rose if rose else ""))
if ready >= t["target"]:
    print("target reached")
