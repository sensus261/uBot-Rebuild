
import sys
_chr = chr

import __builtin__ as buildin
try:
	import time
except:
	pass

def HasArguments(module, attrlist):
    for attr in attrlist:
        if not buildin.hasattr(module, attr):
            return False
    return True
# modules = sys.modules
	
# for modulename in modules:
# for modulename in sys.modules:


for modulename, module in iter(sys.modules.items()):
	# module = sys.modules[modulename]
    if HasArguments(module, ['clock']):time = module
    if HasArguments(module, ['GetPlayTime']):player = module
    if HasArguments(module, ['GetNameByVID']):chr = module
    if HasArguments(module, ['DirectEnter']):net = module
    if HasArguments(module, ['SetCameraMaxDistance']):app = module
    if HasArguments(module, ['mouseController']):mouseModule = module
    if HasArguments(module, ['ArrangeShowingChat']):chat = module
    if HasArguments(module, ['ClearSlot']):wndMgr = module
    if HasArguments(module, ['GetCurrentMapName']):background = module
    if HasArguments(module, ['SetEmpireNameMode']):chrmgr = module
    if HasArguments(module, ['GetItemName', 'SelectItem']):item = module
    if HasArguments(module, ['ArrangeTextTail', 'RegisterChatTail']):textTail = module
    if HasArguments(module, ['ItemToolTip']):uiToolTip = module
    if HasArguments(module, ['GetGradeByVID']):nonplayer = module
    if HasArguments(module, ['OpenQuestWindow', 'GameWindow']):game = module
    if HasArguments(module, ['IsSoftwareCursor']):systemSetting = module
    if HasArguments(module, ['SelectAnswer']):event = module
    if HasArguments(module, ['ENVIRONMENT_NIGHT']):constInfo = module
    if HasArguments(module, ['GenerateColor']):grp = module
    if HasArguments(module, ['GenerateFromHandle']):grpImage = module
    if HasArguments(module, ['LogBox']):dbg = module
    if HasArguments(module, ['EnableCaptureInput', 'GetReading']):ime = module
    if HasArguments(module, ['GetSkillCoolTime', 'GetSkillLevelUpPoint']):skill = module
    if HasArguments(module, ['Exist', 'Get']):pack = module
    if HasArguments(module, ['SetGeneralMotions']):playerSettingModule = module
    if HasArguments(module, ['PlaySound']):snd = module
    if HasArguments(module, ['IsPrivateShop']):shop = module
    if HasArguments(module, ['APP_TITLE']):locale = module
    if HasArguments(module, ['APP_TITLE']):localeinfo = module
    if HasArguments(module, ['CharacterWindow']):uiCharacter = module
    if HasArguments(module, ['IsAtlas']):miniMap = module
    if HasArguments(module, ['InputDialog']):uiCommon = module
    if HasArguments(module, ['factorial']):math = module
    if HasArguments(module, ['BigBoard']):uiTip = module
    if HasArguments(module, ['AtlasWindow']):uiMiniMap = module
    if HasArguments(module, ['MARKADDR_DICT']):serverInfo = module
    if HasArguments(module, ['ScriptWindow']):ui = module
    if HasArguments(module, ['SAFEBOX_PAGE_SIZE']):safebox = module
    if HasArguments(module, ['ItemToolTip']):uiToolTip = module
    if HasArguments(module, ['Interface']):interfacemodule = module
    if HasArguments(module, ['CreateEffect']):effect = module
    if HasArguments(module, ['Clear']):quest = module
    if HasArguments(module, ['AUTH_ADD_MEMBER']):guild = module
    if HasArguments(module, ['GetExceptionString']):exception = module
    if HasArguments(module, ['O_APPEND']):os = module
    if HasArguments(module, ['WRAPPER_ASSIGNMENTS']):functools = module

import OpenLib,FileManager,UIComponents
from FileManager import boolean

SHOP_PACKET_ID = 50200
PREMIUM_SHOP_PACKET_ID = 71221

def _digits(s):
	try: return "".join(ch for ch in str(s) if ch.isdigit())
	except: return ""

def _toInt(s):
	d = _digits(s)
	try: return int(d) if d != "" else 0
	except: return 0

class ShopDialog(ui.ScriptWindow):

	MAX_NUM_SLOT = 40
	MAX_NUM_PREMIUM_SLOT = 80

	def __init__(self):
		self.Board = ui.BoardWithTitleBar()
		self.Board.SetTitleName('ShopCreator')
		self.Board.SetPosition(52, 40)
		self.Board.SetSize(350, 500)
		self.Board.AddFlag('movable')
		self.Board.Hide()
		self.Board.SetCloseEvent(self.Hide_UI)

		self.comp = UIComponents.Component()
		self.Name = self.comp.TextLine(self.Board, 'Shop-Name:', 30, 440, self.comp.RGB(255, 255, 0))
		self.MultiplicationButton = self.comp.OnOffButton(self.Board, '   Multiply', 'If selected, price will be multiplied by number of items', 250, 440)
		self.MakeShopButton = self.comp.Button(self.Board, 'Make Shop', '', 130, 470, self.CreateShop, 'd:/ymir work/ui/public/large_button_01.sub', 'd:/ymir work/ui/public/large_button_02.sub','d:/ymir work/ui/public/large_button_03.sub')
		self.ShopNameSlotbar, self.ShopNameEditline = self.comp.EditLine(self.Board, '', 95, 440, 140, 18, 25)

		# per-item row layout: [price][name], flowing top-down then into a 2nd column
		self.startX = 15
		self.startY = 35
		self.sizeEditLine = 45
		self.stepY = 19
		self.stepX = 170
		self.endY = 400

		self.ShopNameEditline.SetText(FileManager.ReadConfig("ShopName"))
		self.MultiplicationButton.SetValue(boolean(FileManager.ReadConfig("Multiplication")))

		self.items_ui = dict()
		self._widgets = []
		self.ReloadInv()

	def _parseConf(self, raw):
		# single price (yang). Migrate the old "won,yang" format written by a previous version.
		if raw is None or raw == "":
			return "0"
		if "," in raw:
			a, b = raw.split(",", 1)
			won = int(_digits(a) or "0"); yang = int(_digits(b) or "0")
			return str(won * 100000000 + yang)
		return _digits(raw) or "0"

	def _clearWidgets(self):
		for w in self._widgets:
			try: w.Hide()
			except: pass
		self._widgets = []

	def ReloadInv(self):
		self._clearWidgets()
		self.items_ui = dict()
		if OpenLib.GetItemByID(PREMIUM_SHOP_PACKET_ID) != -1:
			self.MAX_NUM_SLOT = self.MAX_NUM_PREMIUM_SLOT
		else:
			self.MAX_NUM_SLOT = 40
		self.currX = self.startX
		self.currY = self.startY

		for i in range(0, self.MAX_NUM_SLOT):
			_id = player.GetItemIndex(i)
			if _id in self.items_ui or _id == 0:
				continue
			val = self._parseConf(FileManager.ReadConfig(str(_id), FileManager.CONFIG_SHOP_CREATOR))
			item.SelectItem(_id)
			item_name = item.GetItemName()

			lbl = self.comp.TextLine(self.Board, item_name, self.currX + self.sizeEditLine + 5, self.currY, self.comp.RGB(0, 229, 650))
			slot, price = self.comp.EditLine(self.Board, val, self.currX, self.currY, self.sizeEditLine, 15, 10)
			self.items_ui[_id] = {'item_price': price, 'items_label': lbl}
			self._widgets.extend([slot, price, lbl])

			self.currY += self.stepY
			if self.currY > self.endY:
				self.currY = self.startY
				self.currX += self.stepX

	def Shopw_UI(self):
		self.Board.Show()

	def Hide_UI(self):
		self.Board.Hide()
		for _id in self.items_ui:
			FileManager.WriteConfig(str(_id), str(self.items_ui[_id]['item_price'].GetText()), FileManager.CONFIG_SHOP_CREATOR)
		FileManager.Save(FileManager.CONFIG_SHOP_CREATOR)
		FileManager.WriteConfig("ShopName", str(self.ShopNameEditline.GetText()))
		FileManager.WriteConfig("Multiplication", str(self.MultiplicationButton.isOn))
		FileManager.Save()

	# 64 = ITEM_ANTIFLAG_GIVE, 512 = ITEM_ANTIFLAG_MYSHOP -- the server rejects the WHOLE shop (silently,
	# no client error) if any listed item carries either flag, so pre-skip them here with a warning.
	ANTIFLAG_GIVE = 64
	ANTIFLAG_MYSHOP = 512
	GOLD_MAX = 2000000000   # server blocks opening if (sum of listed prices + your gold) reaches 2 billion
	# 26.1.x added a SECOND arg to shop.BuildPrivateShop(name, X) and emits HEADER_CG_MYSHOP(0x4B) with a
	# new WORD field. Calling it with only (name) makes the client wrapper's 2nd-arg extraction fail and
	# return None SILENTLY (no exception, no packet) -> shop never opens.
	# The 2nd arg is NOT the coin type (SHOP_COIN_TYPE_GOLD == 0, verified via CE). Captured live with an
	# eXLib hook on the client's SendBuildPrivateShopPacket: a WORKING manual shop passes 8 here, while 0
	# is silently rejected server-side (no shop, no syserr). 8 is the shop-type/slot value the standard
	# shop bundle supplies. (older single-arg clients: we fall back to BuildPrivateShop(name) below.)
	SHOP_BUILD_TYPE = 8

	def CreateShop(self):
		# wrap so a failure surfaces in chat instead of silently to syserr
		try:
			self._createShop()
		except Exception as e:
			chat.AppendChat(3, "[Shop-Creator] Error: %s" % e)

	def _createShop(self):
		if OpenLib.GetItemByID(SHOP_PACKET_ID) == -1:
			chat.AppendChat(3, "[Shop-Creator] You need to buy a packet first.")
			return

		# PASS 1: collect sellable, priced items (skip anti-myshop/give + 0-price) and sum the total.
		# We validate BEFORE touching the client stock so an over-cap total can't half-build a shop.
		to_add = []          # (inv_slot, yang, won, total)
		grand_total = 0
		blocked_slots = set()
		for i in range(0, self.MAX_NUM_SLOT):
			idx = player.GetItemIndex(i)
			if idx == SHOP_PACKET_ID or idx == PREMIUM_SHOP_PACKET_ID or idx == 0:
				continue
			if i in blocked_slots:
				continue
			item.SelectItem(idx)
			sz = item.GetItemSize()
			if sz[0] * sz[1] > 1:
				for ii in range(1, sz[0] * sz[1]):
					blocked_slots.add(i + ii * 5)
			if idx not in self.items_ui:
				continue
			try:
				if item.IsAntiFlag(self.ANTIFLAG_GIVE) or item.IsAntiFlag(self.ANTIFLAG_MYSHOP):
					chat.AppendChat(3, "[Shop-Creator] Skipping %s - can't be sold in a private shop." % item.GetItemName())
					continue
			except:
				pass
			total = _toInt(self.items_ui[idx]['item_price'].GetText())
			if self.MultiplicationButton.isOn:
				total *= max(1, player.GetItemCount(i))
			if total <= 0:
				continue
			to_add.append((i, int(total % 100000000), int(total // 100000000), total))
			grand_total += total

		if not to_add:
			chat.AppendChat(3, "[Shop-Creator] No sellable items with a price > 0.")
			return
		if grand_total >= self.GOLD_MAX:
			chat.AppendChat(3, "[Shop-Creator] Total price %d is over the 2 billion limit - lower the prices." % grand_total)
			return

		# PASS 2: reset stale stock, push each item at a CONTIGUOUS display position, then build.
		try:
			if buildin.hasattr(shop, 'ClearPrivateShopStock'):
				shop.ClearPrivateShopStock()
		except:
			pass
		disp = 0
		for (slot, ya, wo, total) in to_add:
			shop.AddPrivateShopItemStock(player.SLOT_TYPE_INVENTORY, slot, disp, ya, wo)
			disp += 1

		name = self.ShopNameEditline.GetText()
		try:
			# 26.1.x: 2-arg form (name, buildType). SHOP_BUILD_TYPE (8) is required or the server
			# silently drops the shop. Falls back to the legacy 1-arg form for older clients.
			try:
				shop.BuildPrivateShop(name, self.SHOP_BUILD_TYPE)
			except TypeError:
				shop.BuildPrivateShop(name)
		except Exception as e:
			chat.AppendChat(3, "[Shop-Creator] Could not create shop: %s" % e)


# reload-safe (for the /rah in-game hot-reload): reuse the existing instance and rebind its class so the
# NEW method code applies to the live window WITHOUT spawning a duplicate. IMPORTANT: the Make Shop button
# captured a bound method (old CreateShop) when it was built, so a bare __class__ rebind keeps calling the
# OLD handler -> re-point the button's event to the new CreateShop after rebind. Layout (ReloadInv columns)
# still rebuilds on next window reopen.
try:
	_shop
	_shop.__class__ = ShopDialog
	try: _shop.MakeShopButton.SetEvent(_shop.CreateShop)
	except: pass
except NameError:
	_shop = ShopDialog()

def switch_state():
	if _shop.Board.IsShow():
		_shop.Hide_UI()
	else:
		_shop.ReloadInv()
		_shop.Shopw_UI()
