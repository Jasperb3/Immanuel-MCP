from immanuel import charts
from immanuel.const import chart as chart_const

s = charts.Subject('2000-01-01 12:00:00', 32.71, -117.15)
n = charts.Natal(s)

print("Type of n.objects:", type(n.objects))
print("Has 'get' method:", hasattr(n.objects, 'get'))
print("Has 'items' method:", hasattr(n.objects, 'items'))
print()

# Try to access Sun
print("Trying to get Sun with chart_const.SUN:", chart_const.SUN)
sun = n.objects.get(chart_const.SUN)
print("Result:", sun)
print()

# List all available keys/attributes
if hasattr(n.objects, 'keys'):
    print("Keys in n.objects:", list(n.objects.keys())[:10])
if hasattr(n.objects, '__dict__'):
    print("Object attributes:", list(n.objects.__dict__.keys())[:10])
