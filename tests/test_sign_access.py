from immanuel import charts
from immanuel.const import chart as chart_const

s = charts.Subject('2000-01-01 12:00:00', 32.71, -117.15)
n = charts.Natal(s)

# Get the objects
sun = n.objects.get(chart_const.SUN)
moon = n.objects.get(chart_const.MOON)
asc = n.objects.get(chart_const.ASC)

print("Sun object:", sun)
print("Sun type:", type(sun))
print("Sun has 'sign' attr:", hasattr(sun, 'sign'))
print()

if sun:
    print("Sun.sign:", sun.sign)
    print("Sun.sign type:", type(sun.sign))
    print("Sun.sign has 'name' attr:", hasattr(sun.sign, 'name'))
    if hasattr(sun.sign, 'name'):
        print("Sun.sign.name:", sun.sign.name)
    print()

print("Moon object:", moon)
if moon:
    print("Moon.sign:", moon.sign if hasattr(moon, 'sign') else "NO SIGN ATTR")
    if hasattr(moon, 'sign') and hasattr(moon.sign, 'name'):
        print("Moon.sign.name:", moon.sign.name)
    print()

print("Ascendant object:", asc)
if asc:
    print("Asc.sign:", asc.sign if hasattr(asc, 'sign') else "NO SIGN ATTR")
    if hasattr(asc, 'sign') and hasattr(asc.sign, 'name'):
        print("Asc.sign.name:", asc.sign.name)
    print()

# Now test the exact code from get_chart_summary
result = {
    "sun_sign": sun.sign.name if sun else "Unknown",
    "moon_sign": moon.sign.name if moon else "Unknown",
    "rising_sign": asc.sign.name if asc else "Unknown",
}
print("Result:", result)
