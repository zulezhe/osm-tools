"""OSM 标签字段字典 - 常用标签的中文解释

数据来源: OSM Wiki (https://wiki.openstreetmap.org/wiki/Map_features)
"""

# 格式: key → { label: 中文标签名, desc: 详细解释, values: 常见值列表 }
TAG_DICTIONARY: dict[str, dict[str, str | list[str]]] = {
    # ── 基本信息 ──
    "name": {"label": "名称", "desc": "地物的名称，通常是当地语言的名称", "values": []},
    "name:en": {"label": "英文名称", "desc": "地物的英文名称", "values": []},
    "name:zh": {"label": "中文名称", "desc": "地物的中文名称", "values": []},
    "alt_name": {"label": "别名", "desc": "地物的替代名称", "values": []},
    "old_name": {"label": "旧名称", "desc": "地物的历史名称", "values": []},
    "official_name": {"label": "官方名称", "desc": "地物的官方正式名称", "values": []},
    "description": {"label": "描述", "desc": "对地物的文字描述", "values": []},
    "note": {"label": "备注", "desc": "给其他制图者的备注信息", "values": []},

    # ── 道路交通 ──
    "highway": {
        "label": "道路类型",
        "desc": "道路的分类和属性",
        "values": ["motorway", "trunk", "primary", "secondary", "tertiary", "residential",
                    "unclassified", "service", "motorway_link", "trunk_link", "primary_link",
                    "secondary_link", "tertiary_link", "living_street", "pedestrian", "track",
                    "bus_guideway", "escape", "raceway", "proposed", "construction", "footway",
                    "bridleway", "steps", "corridor", "path", "cycleway"],
    },
    "surface": {
        "label": "路面类型",
        "desc": "道路或区域的表面材质",
        "values": ["paved", "unpaved", "asphalt", "concrete", "sett", "cobblestone",
                    "gravel", "dirt", "ground", "sand", "grass", "paving_stones"],
    },
    "lanes": {"label": "车道数", "desc": "道路的车道数量", "values": ["1", "2", "3", "4"]},
    "maxspeed": {"label": "最高速度", "desc": "法定最高限速 (km/h 或 mph)", "values": ["20", "30", "40", "50", "60", "80", "100", "120", "130"]},
    "oneway": {"label": "单行道", "desc": "是否为单向通行道路", "values": ["yes", "no", "-1"]},
    "junction": {"label": "路口类型", "desc": "交叉口的类型", "values": ["roundabout", "circular", "jughandle"]},
    "traffic_signals": {"label": "交通信号灯", "desc": "交通信号灯类型", "values": ["signal", "stop", "yield"]},

    # ── 建筑 ──
    "building": {
        "label": "建筑物",
        "desc": "建筑物的类型或存在标记",
        "values": ["yes", "residential", "commercial", "industrial", "retail", "office",
                    "apartments", "house", "detached", "semi-detached", "terrace", "hotel",
                    "school", "university", "hospital", "church", "mosque", "temple",
                    "warehouse", "factory", "greenhouse", "roof", "garage", "garages",
                    "service", "civic", "government", "public", "barn", "farm_auxiliary",
                    "allotment_house", "boathouse", "bridge", "bunker", "castle", "cabin",
                    "carport", "cathedral", "chapel", "collapsed", "construction",
                    "container", "dormitory", "fire_station", "grandstand", "guardhouse",
                    "hangar", "hospital", "kindergarten", "kiosk", "library", "manufacture",
                    "military", "monastery", "mortuary", "museum", "office", "parking",
                    "pavilion", "power", "prison", "proposed", "ruins", "school", "semidetached_house",
                    "service", "shed", "silo", "slurry_tank", "stable", "stadium", "static_caravan",
                    "sty", "supermarket", "synagogue", "tank", "temple", "terrace", "tower",
                    "train_station", "transformer_tower", "transportation", "trullo", "university",
                    "utility", "warehouse"],
    },
    "building:levels": {"label": "建筑层数", "desc": "建筑物在地上的楼层数", "values": ["1", "2", "3", "4", "5", "6"]},
    "building:material": {"label": "建筑材料", "desc": "建筑物的主要结构材料", "values": ["brick", "concrete", "glass", "steel", "wood", "stone"]},
    "roof:shape": {"label": "屋顶形状", "desc": "建筑物的屋顶形状类型", "values": ["flat", "gabled", "hipped", "skillion", "dome", "pyramidal"]},

    # ── 土地利用 ──
    "landuse": {
        "label": "土地利用",
        "desc": "土地的主要用途分类",
        "values": ["residential", "commercial", "industrial", "retail", "farmland", "farmyard",
                    "forest", "meadow", "grass", "orchard", "vineyard", "basin", "brownfield",
                    "cemetery", "construction", "greenfield", "greenhouse_horticulture",
                    "landfill", "military", "plant_nursery", "quarry", "railway", "recreation_ground",
                    "religious", "reservoir", "village_green", "allotments", "salt_pond"],
    },
    "natural": {
        "label": "自然地物",
        "desc": "自然地理要素类型",
        "values": ["wood", "tree", "water", "wetland", "grassland", "scrub", "heath",
                    "moor", "bare_rock", "scree", "shingle", "sand", "mud", "beach",
                    "coastline", "cliff", "bay", "spring", "glacier", "volcano", "reef", "cave_entrance"],
    },

    # ── 水系 ──
    "waterway": {
        "label": "水系类型",
        "desc": "水体或水道类型",
        "values": ["river", "stream", "canal", "drain", "ditch", "riverbank", "waterfall", "rapid"],
    },
    "water": {
        "label": "水体类型",
        "desc": "水体的分类",
        "values": ["lake", "pond", "reservoir", "basin", "lagoon", "oxbow", "lock", "wastewater"],
    },

    # ── 设施 ──
    "amenity": {
        "label": "公共设施",
        "desc": "各种公共设施和服务的分类",
        "values": ["restaurant", "cafe", "bar", "fast_food", "pub", "food_court", "school",
                    "university", "college", "kindergarten", "library", "hospital", "clinic",
                    "pharmacy", "doctors", "dentist", "veterinary", "bank", "atm", "bureau_de_change",
                    "post_office", "courthouse", "townhall", "police", "fire_station", "prison",
                    "place_of_worship", "parking", "fuel", "charging_station", "bus_station",
                    "ferry_terminal", "marketplace", "toilets", "drinking_water", "shower",
                    "bench", "waste_basket", "recycling", "waste_disposal", "kindergarten",
                    "community_centre", "theatre", "cinema", "arts_centre", "nightclub",
                    "gambling", "stripclub", "brothel", "swimming_pool", "fitness_centre",
                    "sports_centre", "ice_rink", "stadium"],
    },
    "shop": {
        "label": "商店类型",
        "desc": "零售商店的类型",
        "values": ["supermarket", "convenience", "bakery", "butcher", "clothes", "shoes",
                    "electronics", "hardware", "furniture", "mobile_phone", "optician",
                    "books", "gift", "jewelry", "kiosk", "mall", "department_store"],
    },
    "office": {"label": "办公类型", "desc": "办公室的类型", "values": ["government", "insurance", "lawyer", "estate_agent", "it"]},
    "craft": {"label": "手工艺", "desc": "手工艺作坊类型", "values": ["bakery", "brewery", "carpenter", "electrician", "plumber", "shoemaker"]},
    "tourism": {
        "label": "旅游设施",
        "desc": "旅游景点和旅游相关设施",
        "values": ["hotel", "motel", "hostel", "guest_house", "camp_site", "caravan_site",
                    "attraction", "viewpoint", "information", "museum", "picnic_site", "artwork",
                    "gallery", "yes"],
    },
    "leisure": {
        "label": "休闲设施",
        "desc": "休闲娱乐设施类型",
        "values": ["park", "garden", "playground", "sports_centre", "swimming_pool", "fitness_centre",
                    "stadium", "pitch", "track", "golf_course", "marina", "slipway", "fishing",
                    "nature_reserve", "common", "dog_park", "ice_rink"],
    },

    # ── 铁路 ──
    "railway": {
        "label": "铁路类型",
        "desc": "铁路线路和设施的类型",
        "values": ["rail", "subway", "light_rail", "tram", "monorail", "narrow_gauge",
                    "station", "halt", "platform", "level_crossing", "crossing", "signal",
                    "switch", "buffer_stop", "derail", "razed", "construction", "proposed",
                    "disused", "abandoned", "miniature", "funicular"],
    },

    # ── 航空 ──
    "aeroway": {
        "label": "航空设施",
        "desc": "航空相关设施",
        "values": ["aerodrome", "runway", "taxiway", "apron", "gate", "terminal", "helipad",
                    "navigationaid", "windsock", "beacon"],
    },

    # ── 边界与行政 ──
    "boundary": {
        "label": "边界类型",
        "desc": "行政或自然边界的类型",
        "values": ["administrative", "national_park", "protected_area", "maritime",
                    "political", "postal_code", "lot", "marker"],
    },
    "admin_level": {
        "label": "行政级别",
        "desc": "行政区域的级别 (1=国家级, 2=省级, ..., 10=村级)",
        "values": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    },

    # ── 电力与通信 ──
    "power": {
        "label": "电力设施",
        "desc": "电力系统设施的类型",
        "values": ["line", "cable", "substation", "transformer", "generator", "tower", "pole",
                    "portal", "switch", "busbar", "catenary_mast", "insulator", "terminal",
                    "plant", "sub_station"],
    },
    "telecom": {"label": "通信设施", "desc": "通信相关设施", "values": ["data_center", "exchange", "connection_point", "cabinet"]},

    # ── 地形与地质 ──
    "geological": {"label": "地质类型", "desc": "地质分类", "values": []},
    "ele": {"label": "海拔", "desc": "地物的海拔高度 (米)", "values": []},
    "height": {"label": "高度", "desc": "建筑物或结构的高度 (米)", "values": []},
    "width": {"label": "宽度", "desc": "道路、河流等的宽度 (米)", "values": []},
    "length": {"label": "长度", "desc": "地物的长度 (米)", "values": []},
    "area": {"label": "面积", "desc": "地物的面积", "values": []},
    "depth": {"label": "深度", "desc": "水体或坑洞的深度 (米)", "values": []},

    # ── 地址 ──
    "addr:housenumber": {"label": "门牌号", "desc": "街道地址中的门牌号", "values": []},
    "addr:street": {"label": "街道名称", "desc": "地址中的街道名称", "values": []},
    "addr:city": {"label": "城市", "desc": "地址中的城市名称", "values": []},
    "addr:postcode": {"label": "邮政编码", "desc": "地址中的邮政编码", "values": []},
    "addr:country": {"label": "国家代码", "desc": "ISO 3166-1 国家代码", "values": []},
    "addr:province": {"label": "省份", "desc": "地址中的省份名称", "values": []},
    "addr:suburb": {"label": "区/镇", "desc": "地址中的区或镇", "values": []},
    "addr:place": {"label": "地名", "desc": "较小范围的地名标记", "values": []},

    # ── POI 分类 ──
    "place": {
        "label": "地名类型",
        "desc": "居民点或地理区域的类型",
        "values": ["city", "town", "village", "hamlet", "suburb", "neighbourhood", "quarter",
                    "isolated_dwelling", "locality", "island", "islet", "farm", "country",
                    "state", "region", "county", "municipality"],
    },
    "population": {"label": "人口", "desc": "居民点的人口数", "values": []},
    "capital": {"label": "首都/省会", "desc": "是否为首都或省会城市", "values": ["yes", "2", "3", "4", "5", "6"]},

    # ── 历史与文化 ──
    "historic": {
        "label": "历史遗迹",
        "desc": "具有历史价值的地点或建筑",
        "values": ["castle", "monument", "memorial", "ruins", "archaeological_site", "battlefield",
                    "fort", "manor", "palace", "stone", "wayside_cross", "wayside_shrine", "wreck",
                    "heritage", "city_gate", "farmstead", "building"],
    },
    "heritage": {"label": "遗产等级", "desc": "文化遗产保护级别", "values": ["1", "2", "3", "4"]},
    "cuisine": {"label": "菜系", "desc": "餐厅提供的菜系类型", "values": ["regional", "chinese", "pizza", "burger", "sushi", "indian", "thai", "mexican"]},

    # ── 交通相关 ──
    "public_transport": {
        "label": "公共交通",
        "desc": "公共交通站点或设施类型",
        "values": ["station", "stop_position", "platform", "stop_area"],
    },
    "bus": {"label": "公交", "desc": "公交线路标记", "values": ["yes", "no"]},
    "route": {"label": "路线类型", "desc": "交通路线的类型", "values": ["bus", "train", "subway", "tram", "ferry", "bicycle", "hiking", "road"]},

    # ── 限制与访问 ──
    "access": {
        "label": "通行权限",
        "desc": "地物的访问权限",
        "values": ["yes", "private", "permissive", "customers", "delivery", "destination", "no"],
    },
    "fee": {"label": "是否收费", "desc": "是否需要付费才能使用", "values": ["yes", "no"]},
    "wheelchair": {"label": "无障碍通行", "desc": "轮椅是否可以通行", "values": ["yes", "no", "limited"]},
    "opening_hours": {"label": "营业时间", "desc": "设施的开放时间", "values": []},
    "operator": {"label": "运营方", "desc": "设施的管理或运营机构", "values": []},

    # ── 其他 ──
    "source": {"label": "数据来源", "desc": "数据的来源或采集方式", "values": []},
    "ref": {"label": "参考编号", "desc": "官方参考编号或代码", "values": []},
    "layer": {"label": "图层", "desc": "垂直层叠顺序，用于区分立交桥等", "values": ["-5", "-4", "-3", "-2", "-1", "0", "1", "2", "3", "4", "5"]},
    "start_date": {"label": "建成日期", "desc": "建筑物或设施的建成日期", "values": []},
    "wikidata": {"label": "维基数据", "desc": "关联的 Wikidata 实体 ID", "values": []},
    "wikipedia": {"label": "维基百科", "desc": "关联的维基百科文章", "values": []},
    "website": {"label": "网站", "desc": "官方网站或相关网页", "values": []},
    "phone": {"label": "电话", "desc": "联系电话", "values": []},
    "email": {"label": "邮箱", "desc": "联系邮箱", "values": []},
    "internet_access": {"label": "网络接入", "desc": "网络接入类型", "values": ["wlan", "wired", "yes", "no"]},
    "brand": {"label": "品牌", "desc": "连锁店或品牌名称", "values": []},
}


def get_tag_info(key: str) -> dict:
    """获取标签信息，未知标签返回默认值"""
    if key in TAG_DICTIONARY:
        return TAG_DICTIONARY[key]
    return {"label": key, "desc": "未知标签", "values": []}


def search_tags(query: str) -> list[dict]:
    """搜索标签，支持中英文关键词"""
    query = query.lower().strip()
    results = []
    for key, info in TAG_DICTIONARY.items():
        if query in key or query in info["label"].lower() or query in info["desc"].lower():
            results.append({"key": key, **info})
    return results
