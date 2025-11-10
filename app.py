import streamlit as st
import folium
from geopy.distance import geodesic
import openrouteservice
import random
from streamlit_folium import st_folium

# =====================================================
# 🌍 PAGE SETUP
# =====================================================
st.set_page_config(page_title="Dynamic Courier Route Optimizer", layout="wide")

page_bg = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("background.jpg");
    background-size: cover;
    background-attachment: fixed;
}
[data-testid="stHeader"] {background: rgba(0,0,0,0);}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

st.title("🚚 Dynamic Courier Route Optimization")
st.markdown("### Enter your delivery points and get the optimal route with cost & map visualization!")

# =====================================================
# 🚦 HELPER FUNCTIONS
# =====================================================
def geocode_locations(names, ors_key):
    """Use ORS for geocoding only."""
    coords = []
    client = openrouteservice.Client(key=ors_key)
    for name in names:
        try:
            res = client.pelias_search(text=name)
            if res and "features" in res and len(res["features"]) > 0:
                loc = res["features"][0]["geometry"]["coordinates"]
                coords.append((loc[1], loc[0]))
                st.success(f"✅ Found {name}: ({loc[1]:.4f}, {loc[0]:.4f})")
            else:
                st.warning(f"⚠️ Could not find {name}. Added default point.")
                coords.append((0, 0))
        except Exception as e:
            st.error(f"❌ Error geocoding {name}: {e}")
            coords.append((0, 0))
    return coords

def fallback_matrix(coords):
    n = len(coords)
    dist = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist[i][j] = geodesic(coords[i], coords[j]).km
    return dist

def draw_route_map(points, route):
    valid_points = [p for p in points if p != (0, 0)]
    if not valid_points:
        m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
        folium.Marker([20.5937, 78.9629], popup="No valid points found").add_to(m)
        return m

    m = folium.Map(location=valid_points[0], zoom_start=10)
    for i, (lat, lon) in enumerate(points):
        color = "green" if i == 0 else "blue"
        folium.Marker([lat, lon], popup=f"Stop {i}", icon=folium.Icon(color=color)).add_to(m)

    for a, b in zip(route[:-1], route[1:]):
        if points[a] != (0, 0) and points[b] != (0, 0):
            folium.PolyLine([[points[a][0], points[a][1]], [points[b][0], points[b][1]]],
                            color="red", weight=5, opacity=0.7).add_to(m)

    m.fit_bounds(valid_points)
    return m

# =====================================================
# 🧮 INPUT FORM
# =====================================================
with st.form("route_form"):
    ors_key = st.text_input("Enter your OpenRouteService API Key:", type="password")
    loc_input = st.text_area("Enter city/area names (one per line):")
    fuel_price = st.number_input("Fuel Price (₹/L)", value=130.0)
    fuel_eff = st.number_input("Fuel Efficiency (km/L)", value=15.0)
    traffic = st.slider("Traffic Level", 0.0, 1.0, 0.2)
    submitted = st.form_submit_button("Optimize Route")

# =====================================================
# ⚙️ MAIN LOGIC
# =====================================================
if submitted:
    if not ors_key.strip():
        st.error("❌ Please enter a valid ORS API key.")
        st.stop()

    loc_names = [l.strip() for l in loc_input.splitlines() if l.strip()]
    if len(loc_names) < 2:
        st.warning("Please enter at least 2 locations.")
        st.stop()

    with st.spinner("🔍 Geocoding locations..."):
        points = geocode_locations(loc_names, ors_key)

    # Fallback: if all fail, use known sample coordinates (Katraj, Hadapsar)
    if not points or all(p == (0, 0) for p in points):
        st.warning("⚠️ Using fallback coordinates (Pune area).")
        points = [(18.4575, 73.8580), (18.5000, 73.9300)]

    with st.spinner("🧮 Building distance matrix..."):
        dist = fallback_matrix(points)
        n = len(dist)
        for i in range(n):
            for j in range(n):
                dist[i][j] *= (1 + random.uniform(0, traffic))

    # Simple nearest neighbor route
    route = [0]
    visited = set(route)
    while len(route) < n:
        last = route[-1]
        next_city = min((j for j in range(n) if j not in visited),
                        key=lambda j: dist[last][j])
        route.append(next_city)
        visited.add(next_city)
    route.append(0)

    total_km = sum(dist[a][b] for a, b in zip(route[:-1], route[1:]))
    total_cost_val = sum((dist[a][b] / fuel_eff) * fuel_price for a, b in zip(route[:-1], route[1:]))

    st.success("✅ Route optimization complete!")
    st.markdown(f"**Optimized Route:** {' → '.join(loc_names[i] for i in route)}")
    st.metric("Total Distance", f"{total_km:.2f} km")
    st.metric("Estimated Cost", f"₹{total_cost_val:.2f}")

    m = draw_route_map(points, route)
    st_folium(m, width=1000, height=600)
