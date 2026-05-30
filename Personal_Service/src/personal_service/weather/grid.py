"""KMA LCC 격자 ↔ 위경도 변환.

기상청이 공개한 동네예보 격자 변환 알고리즘(Lambert Conformal Conic).
파라미터는 KMA 공개 문서(`기상청41_단기예보 조회서비스_오픈API활용가이드`)와
동일하다.

CLI:
    python -m personal_service.weather.grid --to-grid 37.5547 127.1453
    python -m personal_service.weather.grid --to-latlon 62 126
"""

from __future__ import annotations

import argparse
import math

# KMA LCC 파라미터
RE = 6371.00877       # 지구 반경(km)
GRID = 5.0            # 격자 간격(km)
SLAT1 = 30.0          # 표준 위도1
SLAT2 = 60.0          # 표준 위도2
OLON = 126.0          # 기준점 경도
OLAT = 38.0           # 기준점 위도
XO = 43               # 기준점 X
YO = 136              # 기준점 Y

_DEGRAD = math.pi / 180.0


def _projection_constants() -> tuple[float, float, float, float]:
    """LCC 투영 상수 (re, sn, sf, ro). 모듈 import 시 한 번만 계산해도 되지만
    가독성을 위해 함수로 분리."""
    re = RE / GRID
    slat1 = SLAT1 * _DEGRAD
    slat2 = SLAT2 * _DEGRAD
    olon = OLON * _DEGRAD
    olat = OLAT * _DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)
    return re, sn, sf, ro


def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """위도/경도 (도) → KMA 격자 (nx, ny). 반올림은 KMA 공식 코드와 동일하게
    int(x + 1.5)/int(y + 1.5)."""
    re, sn, sf, ro = _projection_constants()
    ra = math.tan(math.pi * 0.25 + lat * _DEGRAD * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * _DEGRAD - OLON * _DEGRAD
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + YO + 0.5)
    return nx, ny


def grid_to_latlon(nx: int, ny: int) -> tuple[float, float]:
    """KMA 격자 (nx, ny) → 위도/경도 (도)."""
    re, sn, sf, ro = _projection_constants()
    xn = nx - XO
    yn = ro - ny + YO
    ra = math.sqrt(xn * xn + yn * yn)
    if sn < 0.0:
        ra = -ra
    alat = (re * sf / ra) ** (1.0 / sn)
    alat = 2.0 * math.atan(alat) - math.pi * 0.5
    if abs(xn) <= 0.0:
        theta = 0.0
    else:
        if abs(yn) <= 0.0:
            theta = math.pi * 0.5
            if xn < 0.0:
                theta = -theta
        else:
            theta = math.atan2(xn, yn)
    alon = theta / sn + OLON * _DEGRAD
    return alat / _DEGRAD, alon / _DEGRAD


def _main() -> int:
    parser = argparse.ArgumentParser(description="KMA LCC 격자 변환")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--to-grid", nargs=2, type=float, metavar=("LAT", "LON"),
                     help="위경도 → nx, ny")
    grp.add_argument("--to-latlon", nargs=2, type=int, metavar=("NX", "NY"),
                     help="nx, ny → 위경도")
    args = parser.parse_args()

    if args.to_grid:
        lat, lon = args.to_grid
        nx, ny = latlon_to_grid(lat, lon)
        print(f"nx={nx} ny={ny}")
    else:
        nx, ny = args.to_latlon
        lat, lon = grid_to_latlon(nx, ny)
        print(f"lat={lat:.4f} lon={lon:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
