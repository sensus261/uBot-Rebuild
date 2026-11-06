import sys
_chr = chr

import __builtin__ as buildin

def HasArguments(module, attrlist):
    for attr in attrlist:
        if not buildin.hasattr(module, attr):
            return False
    return True

for modulename, module in iter(sys.modules.items()):
    if HasArguments(module, ['GetPlayTime']):player = module
    if HasArguments(module, ['GetNameByVID']):chr = module
    if HasArguments(module, ['ArrangeShowingChat']):chat = module
    if HasArguments(module, ['ScriptWindow']):ui = module
    if HasArguments(module, ['SetCameraMaxDistance']):app = module
    if HasArguments(module, ['GetItemName', 'SelectItem']):item = module

import eXLib
import FileManager, UIComponents, Movement, OpenLib, Data
from FileManager import boolean
from BotBase import BotBase

# Auto pickup (PRD-auto-pickup.md). Walks to the closest eligible ground item (the DLL applies the filter,
# range, items-first and blocked-path rules) and collects it with eXLib.SendPickupItem(vid), which calls the
# client's own SendItemPickUpPacket leaf (verified in game, Phase 0). No teleporting.
#
# Two ways to run it:
#   standalone  - SetEnabled(True) -> BotBase.Frame() ticks _step() every 0.2s
#   hunt mode   - AutoHunting calls TickForHunt() between fights; it runs _step() and returns True while busy

# Accent/case/spacing-insensitive item-name search that does NOT depend on any codec: the client's embedded python
# lacks the codec modules (str.decode / unicodedata fail), and names come in the client's own encoding. So work on raw
# characters: a run of non-ASCII chars is ONE accented letter ('~'), which may stand for a/i/s/t (Romanian
# a-breve, a-circ, i-circ, s-comma/cedilla, t-comma/cedilla); everything that isn't a letter/digit is ignored.
_ACCENTABLE = 'aist'

def _hayTokens(text):
    out = []
    prevNonAscii = False
    for ch in text:
        if ord(ch) > 127:
            if not prevNonAscii:
                out.append('~')
            prevNonAscii = True
        else:
            prevNonAscii = False
            if ch.isalnum():
                out.append(ch.lower())
    return out

def _needleTokens(text):
    """List of sets of haystack tokens each needle position accepts."""
    out = []
    prevNonAscii = False
    for ch in text:
        if ord(ch) > 127:
            if not prevNonAscii:
                out.append(set(list(_ACCENTABLE) + ['~']))
            prevNonAscii = True
        else:
            prevNonAscii = False
            if ch.isalnum():
                c = ch.lower()
                out.append(set([c, '~']) if c in _ACCENTABLE else set([c]))
    return out

def _nameMatches(needle, name):
    """True when the needle (from _needleTokens) occurs in the name. A '~' in the name is either one accented letter
    or stray spacing (e.g. a non-breaking space), so it may also be skipped."""
    if not needle:
        return False
    hay = _hayTokens(name)
    n, h = len(needle), len(hay)
    memo = {}
    def m(ni, hi):
        if ni == n:
            return True
        if hi == h:
            return False
        key = (ni, hi)
        if key in memo:
            return memo[key]
        if hay[hi] == '~':
            r = ('~' in needle[ni] and m(ni + 1, hi + 1)) or m(ni, hi + 1)
        else:
            r = (hay[hi] in needle[ni]) and m(ni + 1, hi + 1)
        memo[key] = r
        return r
    for start in range(h):
        if m(0, start):
            return True
    return False

PICKUP_DEBUG = False

PICK_DIST = 100.0        # world units: distance to the item at which SendPickupItem is sent (75 verified in game)
APPROACH_TIMEOUT = 20.0  # s: give up walking to one item
NO_PROGRESS_TIMEOUT = 5.0  # s: give up when the distance to the item hasn't shrunk by PROGRESS_MIN
PROGRESS_MIN = 40.0
MAX_PICK_TRIES = 3       # SendPickupItem attempts on the same vid before blacklisting it
BLACKLIST_TIME = 15.0    # s an unreachable/stuck item is ignored
COOLDOWN_MAX = 0.5       # s cap so a high saved PickupSpeed doesn't make looting crawl
COOLDOWN_MIN = 0.3       # s between a pick attempt and the next target look-up (floor for pickUpSpeed)

YANG_VNUM = 1            # money: not listed under 'recently seen'
RECENT_MAX = 30          # entries kept in 'recently seen'
RECENT_POLL = 0.5        # s between ground scans

S_IDLE = 0
S_APPROACH = 1
S_COOLDOWN = 2

def _dbg(msg):
    if PICKUP_DEBUG:
        try: chat.AppendChat(3, '[Pickup] ' + str(msg))
        except: pass

def _say(msg):
    try: chat.AppendChat(3, '[uBot] Pickup: ' + str(msg))
    except: pass


class PickupBot(BotBase):

    def __init__(self):
        BotBase.__init__(self, 0.2)
        self.enabled = False
        self.pickUpRange = 290.0
        self.pickUpSpeed = 0.5
        self.excludeInFilter = False
        self.doNotPickupIfPlayerHere = False
        self.pickItemsFirst = False
        self.pickItemsIgnorePath = False
        self.pickFilter = set()
        self._resetRuntime()
        self.LoadConfig()
        self.ApplyConfig()
        self.BuildWindow()

    # ------------------------------------------------------------------ runtime state
    def _resetRuntime(self):
        self.pState = S_IDLE
        self.tVid = 0
        self.tX = 0.0
        self.tY = 0.0
        self.tStart = 0.0
        self.tBestDist = 0.0
        self.tBestTime = 0.0
        self.cooldownUntil = 0.0
        self.blacklist = {}   # vid -> expiry time
        self.pickTries = {}   # vid -> SendPickupItem attempts (survives re-targeting the same item)
        self.pickedCount = 0
        self.recent = []          # [vnum, count, lastSeen] most recent first (items seen on the ground)
        self._seenVids = set()    # ground item vids already counted
        self._recentDirty = False
        self._lastPoll = 0.0

    # ------------------------------------------------------------------ config
    def LoadConfig(self):
        self.enabled = boolean(FileManager.ReadConfig("PickupUse"))
        try: self.pickUpRange = float(FileManager.ReadConfig("PickupRange"))
        except: self.pickUpRange = 290.0
        if self.pickUpRange <= 0:
            self.pickUpRange = 290.0
        try: self.pickUpSpeed = float(FileManager.ReadConfig("PickupSpeed"))
        except: self.pickUpSpeed = 0.5
        self.excludeInFilter = boolean(FileManager.ReadConfig("FilterMode"))
        self.doNotPickupIfPlayerHere = boolean(FileManager.ReadConfig("doNotPickupIfPlayerHere"))
        self.pickItemsFirst = boolean(FileManager.ReadConfig("pickItemsFirst"))
        self.pickItemsIgnorePath = boolean(FileManager.ReadConfig("pickItemsIgnorePath"))
        self.pickFilter = set()
        for i in FileManager.LoadListFile(FileManager.CONFIG_PICKUP_FILTER):
            try: self.pickFilter.add(int(i))
            except: pass

    def SaveConfig(self):
        FileManager.WriteConfig("PickupUse", str(self.enabled))
        FileManager.WriteConfig("PickupRange", str(self.pickUpRange))
        FileManager.WriteConfig("PickupSpeed", str(self.pickUpSpeed))
        FileManager.WriteConfig("FilterMode", str(self.excludeInFilter))
        FileManager.WriteConfig("doNotPickupIfPlayerHere", str(self.doNotPickupIfPlayerHere))
        FileManager.WriteConfig("pickItemsFirst", str(self.pickItemsFirst))
        FileManager.WriteConfig("pickItemsIgnorePath", str(self.pickItemsIgnorePath))
        FileManager.SaveListFile(FileManager.CONFIG_PICKUP_FILTER, self.pickFilter)

    def ApplyConfig(self):
        """Single owner of the eXLib.ItemGrnd* settings: push the current config to the DLL."""
        try:
            if self.pickItemsIgnorePath: eXLib.ItemGrndInBlockedPath()
            else: eXLib.ItemGrndNotInBlockedPath()
            if self.pickItemsFirst: eXLib.ItemGrndItemFirst()
            else: eXLib.ItemGrndNoItemFirst()
            eXLib.ItemGrndSelectRange(float(self.pickUpRange))
            eXLib.ItemGrndFilterClear()
            for i in self.pickFilter:
                eXLib.ItemGrndAddFilter(int(i))
            # excludeInFilter=False means "include mode" (only filtered IDs). An empty include list would pick
            # nothing, so treat it as "pick everything" until the user adds an ID.
            if self.excludeInFilter or not self.pickFilter:
                eXLib.ItemGrndNotOnFilter()
            else:
                eXLib.ItemGrndOnFilter()
        except Exception as e:
            _dbg('ApplyConfig ERR %s' % e)

    # filter helpers (Settings delegates here in Phase 2)
    def AddFilterItem(self, itemId):
        self.pickFilter.add(int(itemId))
        self.ApplyConfig()
        self.SaveConfig()

    def DelFilterItem(self, itemId):
        self.pickFilter.discard(int(itemId))
        self.ApplyConfig()
        self.SaveConfig()

    # ------------------------------------------------------------------ public API
    def SetEnabled(self, val):
        val = bool(val)
        self.enabled = val
        if val:
            if self.State == self.STATE_STOPPED:
                self.Start()
        else:
            if self.State != self.STATE_STOPPED:
                self.Stop()
            self.Abort()
        try:
            if self.btnEnable.IsOn != val:
                if val: self.btnEnable.SetOn()
                else: self.btnEnable.SetOff()
        except: pass
        self.SaveConfig()

    def IsEnabled(self):
        return self.enabled

    def IsBusy(self):
        return self.pState != S_IDLE

    def Abort(self):
        """Drop the current target and stop walking (hunt calls this when a mob engages)."""
        if self.pState == S_APPROACH:
            try: Movement.StopMovement()
            except: pass
        self.pState = S_IDLE
        self.tVid = 0

    def TickForHunt(self):
        """Called by AutoHunting between fights. Returns True while pickup is busy (caller should skip its tick)."""
        try:
            self._step()
        except Exception as e:
            _dbg('TickForHunt ERR %s' % e)
            self.Abort()
        return self.pState != S_IDLE

    # BotBase hook: standalone mode
    def Frame(self):
        try:
            self._step()
        except Exception as e:
            _dbg('Frame ERR %s' % e)
            self.Abort()

    # ------------------------------------------------------------------ state machine
    def _myPos(self):
        # eXLib.GetPixelPosition, never chr.GetPixelPosition (NaN on 26.1.11)
        try:
            x, y, z = eXLib.GetPixelPosition(player.GetMainCharacterIndex())
        except Exception:
            return None
        if x != x or y != y:
            return None
        return x, y

    def _pruneBlacklist(self, now):
        for v in [v for v, t in self.blacklist.items() if t <= now]:
            del self.blacklist[v]
            self.pickTries.pop(v, None)   # fresh attempts after the blacklist expires

    def _giveUp(self, why, now):
        _dbg('blacklist vid=%s (%s)' % (self.tVid, why))
        self.blacklist[self.tVid] = now + BLACKLIST_TIME
        self.Abort()

    def _step(self):
        if OpenLib.GetCurrentPhase() != OpenLib.PHASE_GAME:
            if self.pState != S_IDLE:
                self.Abort()
            return
        now = OpenLib.GetTime()
        self._pruneBlacklist(now)
        pos = self._myPos()
        if pos is None:
            if self.pState != S_IDLE:
                self.Abort()
            return
        px, py = pos

        if self.doNotPickupIfPlayerHere and OpenLib.IsAnyPlayerHere():
            if self.pState != S_IDLE:
                self.Abort()
            return

        if self.pState == S_COOLDOWN:
            if now < self.cooldownUntil:
                return
            self.pState = S_IDLE

        if self.pState == S_IDLE:
            vid, ix, iy = eXLib.GetCloseItemGround(px, py)
            if vid == 0:
                return
            if vid in self.blacklist:
                return   # the DLL only reports the closest item; wait for the blacklist to expire
            if ix != ix or iy != iy:
                return
            self.tVid, self.tX, self.tY = vid, float(ix), float(iy)
            self.tStart = now
            self.tBestDist = OpenLib.dist(px, py, self.tX, self.tY)
            self.tBestTime = now
            self.pState = S_APPROACH
            _dbg('target vid=%s vnum=%s at (%d,%d) dist=%.0f tries=%d' % (vid, eXLib.GetItemGrndID(vid), ix, iy, self.tBestDist, self.pickTries.get(vid, 0)))

        if self.pState == S_APPROACH:
            # item taken by someone else / despawned
            if eXLib.GetItemGrndID(self.tVid) == 0:
                _dbg('vid=%s gone (picked or taken)' % self.tVid)
                self.pickTries.pop(self.tVid, None)
                self.Abort()
                return
            d = OpenLib.dist(px, py, self.tX, self.tY)
            if d <= PICK_DIST:
                Movement.StopMovement()
                tries = self.pickTries.get(self.tVid, 0) + 1
                self.pickTries[self.tVid] = tries
                if tries > MAX_PICK_TRIES:
                    self._giveUp('pick had no effect', now)
                    return
                r = eXLib.SendPickupItem(self.tVid)
                _dbg('SendPickupItem vid=%s ret=%r try=%d' % (self.tVid, r, tries))
                if r == 0 and tries == 1:
                    _say('SendPickupItem returned 0 - eXLib.mix is too old (needs the pickup-leaf build)')
                self.pickedCount += 1
                self.cooldownUntil = now + max(COOLDOWN_MIN, min(self.pickUpSpeed, COOLDOWN_MAX))
                self.pState = S_COOLDOWN
                return
            if d < self.tBestDist - PROGRESS_MIN:
                self.tBestDist = d
                self.tBestTime = now
            if now - self.tStart > APPROACH_TIMEOUT:
                self._giveUp('approach timeout', now)
                return
            if now - self.tBestTime > NO_PROGRESS_TIMEOUT:
                self._giveUp('no progress', now)
                return
            res = Movement.GoToPositionAvoidingObjects(self.tX, self.tY)
            if res == 0 or res is None:
                self._giveUp('no path', now)

    # ------------------------------------------------------------------ recently seen items
    def _ensureRecentState(self):
        # /rah rebinds the class on a LIVE singleton whose __init__ never ran the new code -> add missing attrs lazily
        if not buildin.hasattr(self, 'recent'):
            self.recent = []
            self._seenVids = set()
            self._recentDirty = False
            self._lastPoll = 0.0

    def _pollGround(self):
        """Register every newly dropped item type in self.recent (needs eXLib.GetGroundItems; older DLLs: no-op)."""
        self._ensureRecentState()
        now = OpenLib.GetTime()
        if now < self._lastPoll - 1.0:
            self._lastPoll = 0.0          # app clock jumped back (map reload)
        if now - self._lastPoll < RECENT_POLL:
            return
        self._lastPoll = now
        if OpenLib.GetCurrentPhase() != OpenLib.PHASE_GAME:
            return
        fn = buildin.getattr(eXLib, 'GetGroundItems', None)
        if fn is None:
            return
        try:
            items = fn()
        except Exception as e:
            _dbg('GetGroundItems ERR %s' % e)
            return
        current = set()
        for it in items:
            vid, vnum = it[0], it[1]
            current.add(vid)
            if vid in self._seenVids or vnum == YANG_VNUM or vnum == 0:
                continue
            self._seenVids.add(vid)
            for e in self.recent:
                if e[0] == vnum:
                    e[1] += 1
                    e[2] = now
                    self.recent.remove(e)
                    self.recent.insert(0, e)
                    break
            else:
                self.recent.insert(0, [vnum, 1, now])
                del self.recent[RECENT_MAX:]
            self._recentDirty = True
        # forget vids that left the ground (picked up / expired) so the set doesn't grow forever
        self._seenVids &= current

    def _refreshRecentList(self):
        self._ensureRecentState()
        try:
            self.lstRecent.RemoveAllItems()
            for vnum, count, last in self.recent:
                mark = '*' if vnum in self.pickFilter else ' '
                self.lstRecent.AppendItem(OpenLib.Item('%d  %s  x%d %s' % (vnum, self._itemName(vnum), count, mark)))
        except Exception as e:
            _dbg('refresh recent ERR %s' % e)

    def OnAddRecent(self):
        vnum = self._selectedId(self.lstRecent)
        if vnum is None:
            return
        self.AddFilterItem(vnum)
        self._refreshFilterList()
        self._refreshRecentList()

    def OnClearRecent(self):
        self.recent = []
        # _seenVids is kept on purpose: items still on the ground must not be re-registered
        self._refreshRecentList()

    # ------------------------------------------------------------------ window
    _BTN = ('d:/ymir work/ui/public/Middle_Button_01.sub', 'd:/ymir work/ui/public/Middle_Button_02.sub', 'd:/ymir work/ui/public/Middle_Button_03.sub')
    UI_VER = 4
    SEARCH_MAX = 40

    def BuildWindow(self):
        self._uiBuilt = False   # widget callbacks can fire during construction; ignore them until the end
        self.Board = ui.BoardWithTitleBar()
        self.Board.SetTitleName('Pickup')
        self.Board.SetCloseEvent(self.CloseWindow)
        self.Board.SetSize(545, 392)
        self.Board.SetCenterPosition()
        self.Board.AddFlag("movable")
        c = self.comp = UIComponents.Component()
        white = c.RGB(255, 255, 255)
        yellow = c.RGB(255, 255, 0)
        self._keep = []   # MUST hold refs to TextLines or python GC destroys the widgets (labels vanish)

        def label(text, x, y, color=white):
            self._keep.append(c.TextLine(self.Board, text, x, y, color))

        # ---- left column: on/off, options, sliders, recently seen
        self.btnEnable = c.OnOffButton(self.Board, '', 'Start / stop auto pickup', 15, 34,
            funcState=self.OnEnableToggled,
            OffUpVisual=eXLib.PATH + 'OpenBot/Images/start_0.tga', OffOverVisual=eXLib.PATH + 'OpenBot/Images/start_1.tga', OffDownVisual=eXLib.PATH + 'OpenBot/Images/start_2.tga',
            OnUpVisual=eXLib.PATH + 'OpenBot/Images/stop_0.tga', OnOverVisual=eXLib.PATH + 'OpenBot/Images/stop_1.tga', OnDownVisual=eXLib.PATH + 'OpenBot/Images/stop_2.tga')
        if self.enabled: self.btnEnable.SetOn()
        else: self.btnEnable.SetOff()
        self.lStatus = c.TextLine(self.Board, 'Pickup: off', 66, 50, yellow)

        # icon-only toggles + our own left-aligned labels (the button's built-in label is centered and collides with the icon)
        rows = (
            ('btnExclude', 'Exclude mode', 'Off: pick ONLY the listed items. On: pick everything EXCEPT the listed items.', self.OnExcludeMode, self.excludeInFilter),
            ('btnFirst', 'Items first', 'Pick items before yang', self.OnItemsFirst, self.pickItemsFirst),
            ('btnPath', 'Ignore blocked path', 'Skip items with a wall between you and them', self.OnIgnorePath, self.pickItemsIgnorePath),
            ('btnPlayers', 'Avoid players', 'Do not pick up while another player is nearby', self.OnAvoidPlayers, self.doNotPickupIfPlayerHere),
        )
        y = 90
        for attr, text, tip, func, val in rows:
            setattr(self, attr, c.OnOffButton(self.Board, '', tip, 15, y, funcState=func, defaultValue=int(val)))
            label(text, 40, y + 2)
            y += 23

        label('Range', 15, 190)
        self.sldRange = c.SliderBar(self.Board, min(1.0, self.pickUpRange / 10000.0), self.OnRangeSlide, 62, 190)
        self.lRange = c.TextLine(self.Board, '%d' % self.pickUpRange, 228, 190, white)
        label('Delay', 15, 213)
        self.sldSpeed = c.SliderBar(self.Board, min(1.0, self.pickUpSpeed / 3.0), self.OnSpeedSlide, 62, 213)
        self.lSpeed = c.TextLine(self.Board, '%.1f s' % self.pickUpSpeed, 228, 213, white)

        label('Recently seen items  (* = in filter)', 15, 244, yellow)
        self.lstRecent, self._scrRecent = c.FileListBox(self.Board, 15, 262, 250, 85, 5)
        self.btnAddRecent = c.Button(self.Board, 'To filter', '', 15, 355, self.OnAddRecent, *self._BTN)
        self.btnClearRecent = c.Button(self.Board, 'Clear', '', 105, 355, self.OnClearRecent, *self._BTN)

        # ---- right column: filter list + item search
        label('Filter list', 290, 36, yellow)
        self.lstFilter, self._scrFilter = c.FileListBox(self.Board, 285, 54, 250, 85, 5)
        self.btnRemove = c.Button(self.Board, 'Remove', '', 285, 146, self.OnRemoveItem, *self._BTN)

        label('Search item (name or ID)', 290, 186, yellow)
        self._barSearch, self.editSearch = c.EditLine(self.Board, '', 285, 204, 160, 18, 30)
        self.btnSearch = c.Button(self.Board, 'Search', '', 455, 202, self.OnSearch, *self._BTN)
        self.lstResults, self._scrResults = c.FileListBox(self.Board, 285, 230, 250, 85, 5)
        self.btnAdd = c.Button(self.Board, 'To filter', '', 285, 323, self.OnAddResult, *self._BTN)

        self._uiVer = self.UI_VER
        self._uiBuilt = True
        self._refreshFilterList()
        self._refreshRecentList()

    def _rebuildWindow(self):
        wasShown = False
        try: wasShown = self.Board.IsShow()
        except: pass
        try: self.Board.Hide()
        except: pass
        for a in ('Board', 'comp', '_keep', 'lStatus', 'btnEnable', 'btnExclude', 'btnFirst', 'btnPath', 'btnPlayers',
                  'sldRange', 'lRange', 'sldSpeed', 'lSpeed', 'lstFilter', '_scrFilter', 'btnRemove',
                  '_barSearch', 'editSearch', 'btnSearch', 'lstResults', '_scrResults', 'btnAdd',
                  'lstRecent', '_scrRecent', 'btnAddRecent', 'btnClearRecent'):
            try: setattr(self, a, None)
            except: pass
        self.BuildWindow()
        if wasShown:
            self.Board.Show()

    # ---- widget callbacks (all no-ops until BuildWindow finishes)
    def OnExcludeMode(self, val):
        if not self._uiBuilt: return
        self.excludeInFilter = bool(val); self.ApplyConfig(); self.SaveConfig()

    def OnItemsFirst(self, val):
        if not self._uiBuilt: return
        self.pickItemsFirst = bool(val); self.ApplyConfig(); self.SaveConfig()

    def OnIgnorePath(self, val):
        if not self._uiBuilt: return
        self.pickItemsIgnorePath = bool(val); self.ApplyConfig(); self.SaveConfig()

    def OnAvoidPlayers(self, val):
        if not self._uiBuilt: return
        self.doNotPickupIfPlayerHere = bool(val); self.SaveConfig()

    def OnRangeSlide(self):
        if not self._uiBuilt: return
        self.pickUpRange = max(100.0, round(float(self.sldRange.GetSliderPos()) * 10000.0))
        self.lRange.SetText('%d' % self.pickUpRange)
        self.ApplyConfig()

    def OnSpeedSlide(self):
        if not self._uiBuilt: return
        self.pickUpSpeed = round(float(self.sldSpeed.GetSliderPos()) * 3.0, 1)
        self.lSpeed.SetText('%.1f s' % self.pickUpSpeed)

    @staticmethod
    def _itemName(vnum):
        try:
            item.SelectItem(int(vnum))
            return str(item.GetItemName())
        except Exception:
            return ''

    def _refreshFilterList(self):
        try:
            self.lstFilter.RemoveAllItems()
            for vnum in sorted(self.pickFilter):
                self.lstFilter.AppendItem(OpenLib.Item('%d  %s' % (vnum, self._itemName(vnum))))
        except Exception as e:
            _dbg('refresh filter ERR %s' % e)

    @staticmethod
    def _selectedId(listbox):
        sel = listbox.GetSelectedItem()
        if sel is None:
            return None
        try:
            return int(sel.GetText().strip().split(' ', 1)[0])
        except Exception:
            return None

    def OnRemoveItem(self):
        vnum = self._selectedId(self.lstFilter)
        if vnum is None:
            return
        self.DelFilterItem(vnum)
        self._refreshFilterList()

    def OnAddResult(self):
        vnum = self._selectedId(self.lstResults)
        if vnum is None:
            return
        self.AddFilterItem(vnum)
        self._refreshFilterList()

    def _scanItemList(self, needle):
        """Return (matches, scannedLines) from the client's item_list.txt; raises if the file can't be opened."""
        out = []
        handle = app.OpenTextFile(app.GetLocalePath() + "/item_list.txt")
        count = app.GetTextFileLineCount(handle)
        for i in range(count):
            tok = str(app.GetTextFileLine(handle, i)).split("	")
            if not tok or not tok[0].strip().isdigit():
                continue
            vnum = int(tok[0].strip())
            name = self._itemName(vnum)
            if name and _nameMatches(needle, name):
                out.append((vnum, name))
                if len(out) >= self.SEARCH_MAX:
                    break
        app.CloseTextFile(handle)
        return out, count

    def _scanVnums(self, needle, maxVnum=120000):
        """Fallback when item_list.txt is unavailable: probe vnums directly through the client's item module."""
        out = []
        seen = set()
        for vnum in range(1, maxVnum):
            try:
                ok = item.SelectItem(vnum)
            except Exception:
                continue
            if ok is False or ok == 0:
                continue
            name = self._itemName(vnum)
            if name and _nameMatches(needle, name) and (name, vnum) not in seen:
                seen.add((name, vnum))
                out.append((vnum, name))
                if len(out) >= self.SEARCH_MAX:
                    break
        return out

    def OnSearch(self):
        """Numeric text -> that item id. Otherwise case-insensitive name search (item_list.txt, else probe vnums)."""
        text = str(self.editSearch.GetText()).strip()
        self.lstResults.RemoveAllItems()
        if not text:
            return
        if text.isdigit():
            self.lstResults.AppendItem(OpenLib.Item('%d  %s' % (int(text), self._itemName(int(text)))))
            return
        needle = _needleTokens(text)
        results, how = [], ''
        try:
            results, count = self._scanItemList(needle)
            how = 'item_list.txt (%d lines)' % count
        except Exception as e:
            how = 'item_list.txt unavailable (%s)' % e
        if not results:
            try:
                results = self._scanVnums(needle)
                how += ' -> vnum probe'
            except Exception as e:
                how += ' -> probe failed (%s)' % e
        for vnum, name in results:
            self.lstResults.AppendItem(OpenLib.Item('%d  %s' % (vnum, name)))
        _say('search v5 "%s": %d result(s) via %s' % (text, len(results), how))
        if not results:
            # show exactly what was compared so an encoding problem is visible
            try:
                _say('needle=%d tokens (%r)' % (len(needle), text))
            except Exception as e:
                _say('needle debug ERR %s' % e)

    def OnEnableToggled(self, val):
        # fired by the button; only act when it differs from the current state (avoids re-entry from SetOn/SetOff)
        if bool(val) != self.enabled:
            self.SetEnabled(val)

    def CloseWindow(self):
        self.Board.Hide()
        self.SaveConfig()

    def switch_state(self):
        if self.Board.IsShow():
            self.CloseWindow()
        else:
            # self-heal: rebuild a window that predates the current layout (plain /rah keeps old widgets)
            if getattr(self, '_uiVer', 0) != self.UI_VER:
                try: self._rebuildWindow()
                except Exception as e: _dbg('rebuild ERR %s' % e)
            self.Board.Show()

    def OnUpdate(self):
        BotBase.OnUpdate(self)
        try:
            self._pollGround()
            if self._recentDirty and self.Board.IsShow():
                self._recentDirty = False
                self._refreshRecentList()
        except Exception as e:
            _dbg('OnUpdate ERR %s' % e)
        try:
            if self.Board.IsShow():
                if not self.enabled:
                    txt = 'Pickup: off'
                elif self.pState == S_IDLE:
                    txt = 'Pickup: idle (%d sent)' % self.pickedCount
                elif self.pState == S_APPROACH:
                    txt = 'Pickup: walking to item'
                else:
                    txt = 'Pickup: collecting (%d sent)' % self.pickedCount
                self.lStatus.SetText(txt)
        except: pass


# reload-safe (for /rah): keep the live singleton + its window/state, just rebind the class so new logic
# runs (no second window, no second singleton). First load builds it.
try:
    pickupBot
    pickupBot.__class__ = PickupBot
except NameError:
    pickupBot = PickupBot()
    if pickupBot.enabled:
        pickupBot.Start()

instance = pickupBot


def switch_state():
    pickupBot.switch_state()
