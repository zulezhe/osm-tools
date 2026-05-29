# OSM Data Toolbox - Design Specification

**Date**: 2026-05-07
**Status**: Approved
**Architecture**: Monolithic PySide6 Desktop Application

## Overview

A desktop GUI tool for the complete OSM data lifecycle: download, split, process, convert, and publish as vector tiles. Built with PySide6, using QThread for async operations.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| GUI Framework | PySide6 |
| Package Manager | uv |
| HTTP | requests |
| OSM Data I/O | osmium (python-osmium) |
| Vector I/O | fiona |
| Geometry | shapely |
| Coordinate Transform | pyproj |
| System Monitor | psutil |
| External: Format Convert | GDAL (ogr2ogr) |
| External: OSM Operations | osmium-tool |
| External: Vector Tiles | tippecanoe / planetiler |

## Architecture

Monolithic single-process architecture with modular internal design. All I/O-bound operations run in QThread workers to keep the GUI responsive.

```
PySide6 GUI
├── Panels: Download | Split | Process | Convert | Publish
├── Task Queue & Progress & Log
└── Status Bar

Core Services (QThread workers)
├── Downloader: Geofabrik / Overpass / BBox
├── Splitter: Administrative / Range / Attribute / Type
├── Processor: Compress / Transform / Simplify / Field Delete
├── Converter: PBF / GeoJSON / Shapefile / GeoPackage
└── Publisher: MVT / GeoJSON tiles / MBTiles

Data Layer: osmium / fiona / ogr2ogr / shapely / pyproj
```

## Module 1: Download

### Data Sources

1. **Geofabrik**: Pre-cut regional PBF files with region tree browser (continent > country > state)
2. **Overpass API**: Custom Overpass QL queries with XML/JSON output
3. **OSM API (BBox)**: Direct BBox download from OSM servers

### Multi-threading Strategy

- Geofabrik: Single-threaded with resume support (server doesn't support range requests for all files)
- Overpass: Shard large queries into multiple sub-requests, executed in parallel
- BBox: Single-threaded (OSM API rate limits)

### Resume / Checkpoint

- Uses HTTP `Range` header for partial downloads
- `.download_meta` file stores: URL, file size, downloaded bytes, ETag, timestamp
- On resume: verify existing file integrity (size + optional MD5)
- Supports pause / resume / cancel per download

### Download Manager

- Priority queue for downloads
- Each download runs in independent QThread
- Signals: progress %, speed (MB/s), remaining time
- Pause / resume / cancel controls

## Module 2: Data Splitting

### Split Strategies

| Strategy | Method | Input | Output |
|----------|--------|-------|--------|
| Administrative | Spatial clip with admin boundaries | OSM data + admin boundaries | Multiple files per region |
| Vector Range | Spatial clip with user-defined polygon | OSM data + boundary | Clipped file |
| Attribute | Filter by OSM tag key-value pairs | OSM data + filter conditions | Filtered file |
| Type | Split by OSM element type | OSM data | Multiple files by type |

### Administrative Splitting

- Built-in China administrative boundaries (province/city/district) from DataV.GeoAtlas
- Tree selector for region choice
- Supports custom boundary upload (GeoJSON / Shapefile / GeoPackage)
- Spatial clipping via `osmium-tool extract` for performance

### Attribute Splitting

- Tag browser showing all tags and value distributions in loaded data
- AND/OR combinatorial filter conditions
- Preset filters: buildings, roads, water, green areas, POI

### Type Splitting

- Split by `node` / `way` / `relation`
- Further categorize by tag groups: `highway=*`, `building=*`, `natural=*`, `landuse=*`

### Range Splitting

- Draw rectangle / polygon on built-in map
- Input latitude/longitude coordinates
- Upload boundary file

## Module 3: Data Processing

### Processing Pipeline

Multiple processing steps can be chained into a pipeline and executed in sequence.

### 3.1 Compression

- GeoJSON → Gzip (`.geojson.gz`)
- Shapefile → ZIP (`.shp.zip`)
- Configurable compression level

### 3.2 Coordinate Transform

- Based on `pyproj`
- Preset transforms: WGS84 → GCJ-02, WGS84 → BD-09, WGS84 → EPSG:3857
- Custom EPSG code support
- Batch transform all features

### 3.3 Point Simplification (three algorithms, user-selectable)

| Algorithm | Parameter | Characteristic |
|-----------|-----------|----------------|
| Douglas-Peucker | Tolerance (meters or degrees) | Shape-preserving, moderate speed |
| Visvalingam-Whyatt | Minimum area threshold | Better for curves |
| Fixed Interval | Distance in meters | Fast but may lose detail |

- Real-time preview on small sample
- Display point count before/after and compression ratio

### 3.4 Field Deletion

- List all tag fields with statistics (non-null count, unique value count)
- Checkbox bulk selection for fields to delete
- Preset cleanup: remove `source`, `created_by`, `note` metadata fields
- Preview affected fields before execution

## Module 4: Format Conversion

### Conversion Matrix (all directions supported)

| From \ To | GeoJSON | Shapefile | GeoPackage | PBF |
|-----------|---------|-----------|------------|-----|
| **GeoJSON** | - | ogr2ogr | ogr2ogr | osmium |
| **Shapefile** | ogr2ogr | - | ogr2ogr | osmium |
| **GeoPackage** | ogr2ogr | ogr2ogr | - | osmium |
| **PBF** | osmium | osmium | osmium | - |

- Core: `ogr2ogr` (GDAL CLI) and `osmium-tool`
- Encoding selection for Shapefile (default UTF-8)
- Real-time conversion progress
- Streaming for large files (avoid memory overflow)

## Module 5: Vector Tile Publishing

### Tile Generation Tools

| Tool | Output | Characteristic |
|------|--------|----------------|
| tippecanoe | MVT + MBTiles | Mature, feature-rich, requires installation |
| planetiler | MVT + MBTiles | Extremely fast, requires Java |

### Configuration

- Zoom level range (minzoom / maxzoom)
- Tile size: 256x256 or 512x512
- Layer grouping: by OSM tags
- Attribute filtering: which tags to include in tiles
- Simplification: auto-simplify per zoom level

### Output Formats

1. **MVT Directory**: `{z}/{x}/{y}.pbf` — direct use with MapLibre/Mapbox
2. **MBTiles**: SQLite package, single file for distribution
3. **GeoJSON Tiles**: `{z}/{x}/{y}.geojson` — debugging

### Preview

- Built-in map preview after tile generation (Qt WebEngine + MapLibre GL JS)
- Verify tile rendering before publishing

## GUI Design

### Main Window Layout

```
┌──────────────────────────────────────────────────┐
│  Menu: File | Settings | Help                     │
├──────────────────────────────────────────────────┤
│  Toolbar: [Download][Split][Process][Convert]     │
│           [Publish]  [Task Queue]                 │
├──────────┬───────────────────────────────────────┤
│          │                                       │
│  Side    │         Workspace                     │
│  Panel   │   (switches per active tool)          │
│          │                                       │
│  · Region│   ┌───────────────────────────────┐   │
│    tree  │   │  Current tool's operation UI   │   │
│  · Files │   └───────────────────────────────┘   │
│  · History│                                      │
│          ├───────────────────────────────────────┤
│          │  Log / Progress Panel                 │
│          │  [████████░░░░] 65%  12.3MB/s        │
├──────────┴───────────────────────────────────────┤
│  Status: Ready | Tasks: 3 | Memory: 245MB        │
└──────────────────────────────────────────────────┘
```

## Project Structure

```
osm-download/
├── pyproject.toml
├── src/
│   └── osm_tool/
│       ├── __init__.py
│       ├── main.py
│       ├── app.py
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── widgets/
│       │   ├── panels/
│       │   │   ├── download_panel.py
│       │   │   ├── split_panel.py
│       │   │   ├── process_panel.py
│       │   │   ├── convert_panel.py
│       │   │   └── publish_panel.py
│       │   └── dialogs/
│       ├── core/
│       │   ├── __init__.py
│       │   ├── downloader/
│       │   │   ├── base.py
│       │   │   ├── geofabrik.py
│       │   │   ├── overpass.py
│       │   │   └── bbox.py
│       │   ├── splitter/
│       │   ├── processor/
│       │   ├── converter/
│       │   └── publisher/
│       ├── workers/
│       ├── models/
│       ├── utils/
│       └── resources/
└── tests/
```

## External Dependencies

The application checks for these external tools at startup and prompts the user to install any that are missing:

- **GDAL** (`ogr2ogr`): Required for format conversion
- **osmium-tool**: Required for high-performance OSM data operations
- **tippecanoe**: Required for vector tile generation (optional, planetiler is alternative)

## Error Handling

- All worker threads catch exceptions and emit error signals to the GUI
- User-visible error messages with suggested actions
- Log file with full stack traces for debugging
- External tool detection with clear installation instructions

## Future Considerations (out of scope)

- Plugin architecture for third-party extensions
- Multi-user / server mode
- Custom Python scripting for advanced processing
