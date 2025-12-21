from immanuel import charts

s = charts.Subject('2000-01-01 12:00:00', 32.71, -117.15)
n = charts.Natal(s)

print("Testing natal chart attributes:")
print()

attrs_to_test = [
    ('shape', 'natal.shape'),
    ('moon_phase', 'natal.moon_phase'),
    ('diurnal', 'natal.diurnal'),
    ('house_system', 'natal.house_system'),
]

for attr_name, access_path in attrs_to_test:
    try:
        value = getattr(n, attr_name)
        print(f"PASS {access_path}: {value}")
        print(f"  Type: {type(value)}")

        # If it's moon_phase, try to access .formatted
        if attr_name == 'moon_phase':
            if hasattr(value, 'formatted'):
                print(f"  {access_path}.formatted: {value.formatted}")
            else:
                print(f"  FAIL NO 'formatted' attribute!")
                print(f"  Available attributes: {[x for x in dir(value) if not x.startswith('_')]}")
        print()
    except AttributeError as e:
        print(f"FAIL {access_path}: AttributeError - {e}")
        print()
    except Exception as e:
        print(f"FAIL {access_path}: {type(e).__name__} - {e}")
        print()

# Now try the full get_chart_summary logic
print("=" * 60)
print("Testing full get_chart_summary logic:")
print("=" * 60)

try:
    sun = n.objects.get(4000001)
    moon = n.objects.get(4000002)
    asc = n.objects.get(3000001)

    result = {
        "sun_sign": sun.sign.name if sun else "Unknown",
        "moon_sign": moon.sign.name if moon else "Unknown",
        "rising_sign": asc.sign.name if asc else "Unknown",
        "chart_shape": n.shape,
        "moon_phase": n.moon_phase.formatted,
        "diurnal": n.diurnal,
        "house_system": n.house_system
    }

    print("PASS SUCCESS!")
    print("Result:", result)
except Exception as e:
    print(f"FAIL FAILED: {type(e).__name__} - {e}")
    import traceback
    traceback.print_exc()
