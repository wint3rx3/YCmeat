import os
import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import json
import geopandas as gpd
from shapely.geometry import box

st.set_page_config(layout="wide")
st.title("영천시 횡단보도 추출")

# 자동 불러오기: coords가 세션에 없으면 CSV에서 로드
if "coords" not in st.session_state:
    csv_path = "data/횡단보도_좌표.csv"
    if os.path.exists(csv_path):
        df_loaded = pd.read_csv(csv_path)
        if "위도" in df_loaded.columns and "경도" in df_loaded.columns:
            st.session_state.coords = list(zip(df_loaded["위도"], df_loaded["경도"]))
            st.success(f"📥 {len(st.session_state.coords)}개의 좌표를 불러왔습니다.")
        else:
            st.session_state.coords = []
            st.warning("⚠️ '위도', '경도' 컬럼이 없습니다. 빈 좌표로 시작합니다.")
    else:
        st.session_state.coords = []
        st.info("ℹ️ 저장된 좌표 CSV가 없어 빈 좌표로 시작합니다.")

if "last_center" not in st.session_state:
    st.session_state.last_center = [35.9749, 128.9461]

if "new_point" not in st.session_state:
    st.session_state.new_point = None

# GeoJSON 경계 불러오기
with open("data/GEOJSON/yeongcheon_dong_boundary.geojson", encoding="utf-8") as f:
    boundary = json.load(f)

# GeoDataFrame으로 경계 처리
gdf_boundary = gpd.GeoDataFrame.from_features(boundary["features"])
gdf_boundary.set_crs("EPSG:4326", inplace=True)

# 500m 격자 생성
minx, miny, maxx, maxy = gdf_boundary.total_bounds
grid_size = 0.0045  # ≒ 500m 위도 기준
grid_cells = []

x = minx
while x < maxx:
    y = miny
    while y < maxy:
        grid_cells.append(box(x, y, x + grid_size, y + grid_size))
        y += grid_size
    x += grid_size

grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326")
grid_in_yeongcheon = grid[grid.intersects(gdf_boundary.unary_union)]

with st.container():
    m = folium.Map(location=st.session_state.last_center, zoom_start=16)

    # 영천시 경계선 추가
    folium.GeoJson(
        boundary,
        name="영천시 경계",
        style_function=lambda x: {
            "fillColor": "none",
            "color": "red",
            "weight": 2
        }
    ).add_to(m)

    # 500m 격자 추가
    for geom in grid_in_yeongcheon.geometry:
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x: {
                "fillColor": "none",
                "color": "gray",
                "weight": 1,
                "opacity": 0.5
            }
        ).add_to(m)

    # 저장된 마커 표시
    for lat, lon in st.session_state.coords:
        folium.CircleMarker(location=[lat, lon], radius=6, color="blue", fill=True).add_to(m)

    m.add_child(folium.LatLngPopup())

    # 지도 표시
    map_data = st_folium(m, width="100%", height=700, returned_objects=["last_clicked"])

    # 클릭 이벤트 처리
    if map_data and map_data.get("last_clicked") is not None:
        latlon = map_data["last_clicked"]
        st.session_state.last_center = [latlon["lat"], latlon["lng"]]
        st.session_state.new_point = (latlon["lat"], latlon["lng"])

# 클릭 후 버튼 처리
if st.session_state.new_point:
    lat, lon = st.session_state.new_point
    st.success(f"📍 {lat:.6f}, {lon:.6f}")
    if (lat, lon) not in st.session_state.coords:
        if st.button("✅ 이 좌표 저장"):
            st.session_state.coords.append((lat, lon))
            st.session_state.new_point = None
            st.rerun()
    else:
        st.info("🟦 이 좌표는 이미 저장되어 있습니다.")

# 좌표 목록 및 다운로드
if st.session_state.coords:
    st.subheader("📋 저장된 좌표 목록")
    df = pd.DataFrame(st.session_state.coords, columns=["위도", "경도"])
    st.dataframe(df)
    df.to_csv("data/횡단보도_좌표.csv", index=False, encoding="utf-8-sig")
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv_data, "횡단보도_좌표.csv", "text/csv")
