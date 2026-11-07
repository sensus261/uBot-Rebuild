# MapGrid -- Python-side map collision grid + A* pathfinder, for maps where eXLib's own pathfinder has no data.
#
# eXLib.FindPath needs OpenBot/Maps/<map>.dat. When that file is missing, the DLL tries to build it from the
# client's attr.atr files, but (a) it only looks under the exact map name (dungeon copies such as
# metin2_map_monkey_dungeon_13 reuse a parent map's terrain) and (b) it caches the failed build until the map
# changes. So on those maps every FindPath returns nothing. This module:
#   1. loads OpenBot/Maps/<map>.dat if present, else BUILDS the grid itself from the client's attr.atr files
#      (read through the client's `pack` module, trying the exact name, then parent-style names), and SAVES
#      the .dat so the DLL can use it on the next visit;
#   2. runs a bounded 8-direction A* on it, smoothed by line of sight, returning world-unit waypoints for
#      Movement.FollowPath.
#
# .dat format (same as the DLL writes): first line "maxX maxY", then maxY rows of maxX chars, '1' = walkable,
# '0' = blocked. One cell = 100 world units (cell = int(world / 100), like eXLib.FindPath).
# attr.atr: 6-byte header (WORD version, width, height) + 256*256 attribute bytes; bit 0x1 = blocked. Pieces
# live in <base>/<XXX><YYY>/attr.atr (3-digit piece indices). Blocked areas are grown by one cell (as the DLL
# does) so paths keep a margin from walls.

import sys
import __builtin__ as buildin
import eXLib


def HasArguments(module, attrlist):
    for attr in attrlist:
        if not buildin.hasattr(module, attr):
            return False
    return True


pack = None
background = None
for _mn, _m in list(sys.modules.items()):
    try:
        if _m is None:
            continue
        if HasArguments(_m, ['Exist', 'Get']):
            pack = _m
        if HasArguments(_m, ['GetCurrentMapName']):
            background = _m
    except:
        pass

ATTR = 256
CELL = 100
MAPS_DIR = eXLib.PATH + 'OpenBot/Maps/'
MAX_EXPANSIONS = 60000   # A* node budget per search (bounds the frame hitch on huge/unreachable searches)
SNAP_RADIUS = 12         # cells to search for a walkable cell when start/goal sits in a blocked one

_grid = {'name': None, 'w': 0, 'h': 0, 'rows': None, 'source': None, 'tried': []}


def _log(msg):
    # write into the Auto-Hunt trace. Look the module up -- never `import AutoHunting`: the live one is
    # registered as OpenBot.Modules.AutoHunting and a plain import would load a second copy (second window).
    for name in ('OpenBot.Modules.AutoHunting', 'AutoHunting'):
        m = sys.modules.get(name)
        if m is not None:
            try:
                m._dbg('[GRID] ' + msg)
            except:
                pass
            return


# ------------------------------------------------------------------ grid loading / building
def _loadDat(name):
    try:
        f = open(MAPS_DIR + name + '.dat', 'rb')
        data = f.read().replace('\r\n', '\n').split('\n')
        f.close()
    except:
        return None
    try:
        hdr = data[0].split()
        w, h = int(hdr[0]), int(hdr[1])
    except:
        return None
    rows = data[1:1 + h]
    if w <= 0 or h <= 0 or len(rows) < h:
        return None
    return w, h, rows


def _exists(path):
    try:
        return bool(pack.Exist(path))
    except:
        return False


def _candidateNames(name):
    # exact name first, then parent-style names: strip trailing _NN (dungeon copies), and the
    # 'monkey_dungeon' <-> 'monkeydungeon' spelling difference seen between map names and data folders
    names = [name]
    n = name
    while True:
        i = n.rfind('_')
        if i <= 0 or not n[i + 1:].isdigit():
            break
        n = n[:i]
        names.append(n)
    for x in list(names):
        y = x.replace('_dungeon', 'dungeon')
        if y != x and y not in names:
            names.append(y)
    return names


def _findBase(name):
    tried = []
    for nm in _candidateNames(name):
        for pre in ('', 'd:/ymir work/map/', 'map/'):
            for sep in ('/', '\\'):
                base = pre + nm + sep
                tried.append(base)
                if _exists(base + '000000' + sep + 'attr.atr'):
                    return base, sep, tried
    return None, None, tried


def _build(name):
    if pack is None:
        return None, ['client pack module not found']
    base, sep, tried = _findBase(name)
    if base is None:
        return None, tried
    pieces = {}
    nx = 0
    ny = 0
    while _exists(base + '%03d000' % nx + sep + 'attr.atr'):
        y = 0
        while True:
            path = base + '%03d%03d' % (nx, y) + sep + 'attr.atr'
            if not _exists(path):
                break
            try:
                pieces[(nx, y)] = pack.Get(path)
            except:
                pass
            y += 1
        ny = max(ny, y)
        nx += 1
    if not pieces:
        return None, tried
    w, h = nx * ATTR, ny * ATTR
    full = (1 << w) - 1
    pieceMask = (1 << ATTR) - 1
    blocked = [full] * h   # rows as bitmasks (bit x = column x); missing pieces stay blocked
    tbl = ''.join([('1' if (i & 1) else '0') for i in range(256)])   # attr byte -> '1' if blocked
    for (px, py), data in pieces.items():
        if len(data) < 6 + ATTR * ATTR:
            continue
        shift = px * ATTR
        clear = ~(pieceMask << shift)
        for r in range(ATTR):
            seg = data[6 + r * ATTR: 6 + (r + 1) * ATTR].translate(tbl)
            m = int(seg[::-1], 2)
            row = py * ATTR + r
            blocked[row] = (blocked[row] & clear) | (m << shift)
    # grow blocked areas by one cell (8-neighbourhood), out-of-map counts as blocked -- same as the DLL
    rows = []
    edge = (1 << (w - 1)) | 1
    for r in range(h):
        up = blocked[r - 1] if r > 0 else full
        dn = blocked[r + 1] if r < h - 1 else full
        b = up | blocked[r] | dn
        d = (b | (b << 1) | (b >> 1) | edge) & full
        s = bin(d)[2:].zfill(w)[::-1]          # '1' = blocked, column 0 first
        rows.append(s.replace('1', 'x').replace('0', '1').replace('x', '0'))
    _log('built %s from %s (%dx%d pieces, %dx%d cells)' % (name, base, nx, ny, w, h))
    try:
        f = open(MAPS_DIR + name + '.dat', 'w')
        f.write('%d %d\n' % (w, h))
        f.write('\n'.join(rows))
        f.write('\n')
        f.close()
        _log('saved %s.dat (the DLL uses it after the next map load)' % name)
    except Exception as e:
        _log('could not save %s.dat: %s' % (name, e))
    return (w, h, rows), tried


def Ensure(name=None):
    """Load (or build) the grid for the current map. Returns True when a grid is available."""
    if name is None:
        try:
            name = background.GetCurrentMapName()
        except:
            return False
    if not name:
        return False
    if _grid['name'] == name:
        return _grid['rows'] is not None
    _grid['name'] = name
    _grid['rows'] = None
    _grid['tried'] = []
    g = _loadDat(name)
    src = 'dat'
    if g is None:
        g, tried = _build(name)
        _grid['tried'] = tried
        src = 'client'
        if g is None:
            _log('no grid for %s (tried %d paths, e.g. %s)' % (name, len(tried), ', '.join(tried[:4])))
            return False
    _grid['w'], _grid['h'], _grid['rows'] = g
    _grid['source'] = src
    return True


def Source():
    return _grid['source'] if _grid['rows'] is not None else None


# ------------------------------------------------------------------ pathfinding
def _walkable(x, y):
    if x < 0 or y < 0 or x >= _grid['w'] or y >= _grid['h']:
        return False
    r = _grid['rows'][y]
    return x < len(r) and r[x] == '1'


def _snap(x, y):
    if _walkable(x, y):
        return (x, y)
    for rad in range(1, SNAP_RADIUS + 1):
        for dx in range(-rad, rad + 1):
            for dy in (-rad, rad):
                if _walkable(x + dx, y + dy):
                    return (x + dx, y + dy)
        for dy in range(-rad + 1, rad):
            for dx in (-rad, rad):
                if _walkable(x + dx, y + dy):
                    return (x + dx, y + dy)
    return None


def _push(heap, item):
    heap.append(item)
    i = len(heap) - 1
    while i > 0:
        p = (i - 1) >> 1
        if heap[p][0] <= item[0]:
            break
        heap[i] = heap[p]
        i = p
    heap[i] = item


def _pop(heap):
    last = heap.pop()
    if not heap:
        return last
    top = heap[0]
    n = len(heap)
    i = 0
    while True:
        c = 2 * i + 1
        if c >= n:
            break
        if c + 1 < n and heap[c + 1][0] < heap[c][0]:
            c += 1
        if heap[c][0] >= last[0]:
            break
        heap[i] = heap[c]
        i = c
    heap[i] = last
    return top


_DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


def _astar(s, g):
    gx, gy = g

    def hfun(x, y):
        dx = abs(x - gx)
        dy = abs(y - gy)
        return (dx + dy) + (0.4142 * min(dx, dy))

    rows = _grid['rows']
    w, h = _grid['w'], _grid['h']
    openh = []
    _push(openh, (hfun(s[0], s[1]), 0.0, s))
    gcost = {s: 0.0}
    parent = {s: None}
    closed = set()
    n = 0
    while openh:
        f, gc, cur = _pop(openh)
        if cur in closed:
            continue
        if cur == g:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            path.reverse()
            return path
        closed.add(cur)
        n += 1
        if n > MAX_EXPANSIONS:
            return None
        cx, cy = cur
        for dx, dy, c in _DIRS:
            nx, ny = cx + dx, cy + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h or rows[ny][nx] != '1':
                continue
            if dx and dy and (rows[cy][nx] != '1' or rows[ny][cx] != '1'):
                continue   # no corner cutting through a wall
            nb = (nx, ny)
            if nb in closed:
                continue
            ng = gc + c
            if ng < gcost.get(nb, 1e18):
                gcost[nb] = ng
                parent[nb] = cur
                _push(openh, (ng + hfun(nx, ny), ng, nb))
    return None


def _lineClear(a, b):
    # every cell on the straight segment a->b is walkable (Bresenham; also checks both cells at diagonal steps)
    x0, y0 = a
    x1, y1 = b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        if not _walkable(x, y):
            return False
        if x == x1 and y == y1:
            return True
        e2 = 2 * err
        if e2 > -dy and e2 < dx:
            if not (_walkable(x + sx, y) and _walkable(x, y + sy)):
                return False
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def _smooth(path):
    if len(path) <= 2:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not _lineClear(path[i], path[j]):
            j -= 1
        out.append(path[j])
        i = j
    return out


def FindPath(x0, y0, x1, y1):
    """World coords in, world-coord waypoints out (start excluded). [] = no path / no grid."""
    if not Ensure():
        return []
    s = _snap(int(x0) // CELL, int(y0) // CELL)
    g = _snap(int(x1) // CELL, int(y1) // CELL)
    if s is None or g is None:
        return []
    if s == g:
        return [(g[0] * CELL + CELL // 2, g[1] * CELL + CELL // 2)]
    path = _astar(s, g)
    if not path:
        return []
    pts = _smooth(path)[1:]
    return [(px * CELL + CELL // 2, py * CELL + CELL // 2) for px, py in pts]
