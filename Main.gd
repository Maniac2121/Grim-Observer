extends Node3D

const FACTIONS = ["Ultramarines", "Cadian Imperial Guard", "Chaos Daemons", "Black Legion"]
const HEROES = ["Marneus Calgar", "Ursula Creed", "Skarbrand", "Abaddon the Despoiler"]
const COLORS = [Color("285ec2"), Color("71805a"), Color("b32c35"), Color("242735")]
const TEAM_COLORS = [Color("6bc9ff"), Color("ff655d"), Color("e4be62"), Color("b195ef")]
const MAPS = ["CADIA • Câmpul cenușii", "MACRAGGE • Citadela", "WARP • Riftul de obsidian"]
var world: Node3D
var camera: Camera3D
var canvas: CanvasLayer
var menu: Control
var hud: Control
var stats: Label
var feed: Label
var title: Label
var battle_config_path = "user://battle.cfg"
var pause_button: Button
var cinematic_button: Button
var slots: Array = []
var fighters: Array = []
var dead_bodies: Array = []
var effects: Array = []
var materials: Dictionary = {}
var team_select: OptionButton
var map_select: OptionButton
var hero_toggle: CheckBox
var blood_toggle: CheckBox
var active = false
var paused = false
var cinematic = false
var elapsed = 0.0
var speed = 1.0
var yaw = 0.6
var pitch = 0.65
var distance = 45.0
var focus = Vector3.ZERO
var selected = -1
var cinematic_clock = 0.0
var cinematic_shot = 0
var hud_clock = 0.0
var touches: Dictionary = {}
var event_lines: Array[String] = []
var rng = RandomNumberGenerator.new()
var map_id = 0
var testing = false
var test_stage = 0
var test_frames = 0
var kills = 0
var blocks = 0
var counters = 0
var shots = 0
var battle_over = false

func _ready():
	rng.seed = 40102026
	testing = "--smoke" in OS.get_cmdline_user_args() or "--stress" in OS.get_cmdline_user_args()
	build_world()
	build_ui()
	show_menu()
	if testing:
		for row in slots:
			row["count"].value = 20 if "--stress" in OS.get_cmdline_user_args() else 3
		if "--stress" in OS.get_cmdline_user_args():
			team_select.selected = 2
			test_stage = 2
		start_battle()
		print("SMOKE_STARTED units=", fighters.size())

func mat(color: Color, glow = false) -> StandardMaterial3D:
	var key = str(color) + str(glow)
	if materials.has(key): return materials[key]
	var m = StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.72
	if glow:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = 2.0
	materials[key] = m
	return m

func box(parent: Node3D, pos: Vector3, size: Vector3, color: Color, glow = false) -> MeshInstance3D:
	var n = MeshInstance3D.new()
	var mesh = BoxMesh.new()
	mesh.size = size
	n.mesh = mesh
	n.material_override = mat(color, glow)
	parent.add_child(n)
	n.position = pos
	return n

func orb(parent: Node3D, pos: Vector3, radius: float, color: Color) -> MeshInstance3D:
	var n = MeshInstance3D.new()
	var mesh = SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2
	mesh.radial_segments = 8
	mesh.rings = 4
	n.mesh = mesh
	n.material_override = mat(color)
	parent.add_child(n)
	n.position = pos
	return n

func build_world():
	world = Node3D.new()
	add_child(world)
	var env = WorldEnvironment.new()
	var settings = Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("151c2b")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("9caec9")
	settings.ambient_light_energy = 0.65
	settings.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = settings
	add_child(env)
	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -30, 0)
	sun.light_color = Color("ffdfbb")
	sun.light_energy = 1.4
	sun.shadow_enabled = true
	add_child(sun)
	camera = Camera3D.new()
	camera.far = 300
	camera.fov = 55
	add_child(camera)
	camera.current = true
	update_camera(0)

func terrain():
	var ground_colors = [Color("45433e"), Color("444f5c"), Color("302736")]
	box(world, Vector3(0,-0.3,0), Vector3(110,0.6,110), ground_colors[map_id])
	var ground = StaticBody3D.new()
	var shape = CollisionShape3D.new()
	var mesh = BoxShape3D.new()
	mesh.size = Vector3(110,0.6,110)
	shape.shape = mesh
	ground.add_child(shape)
	ground.position.y = -0.3
	world.add_child(ground)
	for i in range(75):
		var p = Vector3(rng.randf_range(-49,49),0,rng.randf_range(-49,49))
		# Keep the battle area free of impassable decorative geometry.
		if abs(p.x) < 28 and abs(p.z) < 28: continue
		if map_id == 1:
			box(world, p + Vector3(0,3,0), Vector3(2,6,2), Color("6e7580"))
			box(world, p + Vector3(0,6.1,0), Vector3(3,0.4,3), Color("a3a197"))
		elif map_id == 2:
			var rock = box(world, p + Vector3(0,2,0), Vector3(1,5,1), Color("693965"))
			rock.rotation.z = rng.randf_range(-0.5,0.5)
			box(world, p + Vector3(0,0.02,0), Vector3(4,0.03,0.3), Color("e34b98"), true)
		else:
			box(world, p + Vector3(0,0.7,0), Vector3(3,1.4,1.2), Color("68645a"))
	for z in [-27,27]:
		for x in range(-24,25,8):
			box(world, Vector3(x,0.025,z), Vector3(3,0.05,0.15), Color("a88b55"))

func style(bg: Color, border: Color, radius = 12) -> StyleBoxFlat:
	var s = StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(1)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 12
	s.content_margin_bottom = 12
	return s

func text_label(text: String, size = 22, color = Color("e6eaf3")) -> Label:
	var l = Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

func button(text: String, callable: Callable) -> Button:
	var b = Button.new()
	b.text = text
	b.custom_minimum_size.y = 54
	b.pressed.connect(callable)
	return b

func build_ui():
	canvas = CanvasLayer.new()
	add_child(canvas)
	var theme = Theme.new()
	theme.default_font_size = 21
	theme.set_stylebox("normal", "Button", style(Color("1a273b"),Color("354864")))
	theme.set_stylebox("hover", "Button", style(Color("29405b"),Color("d5b471")))
	theme.set_stylebox("pressed", "Button", style(Color("40516b"),Color("e8bd65")))
	theme.set_stylebox("normal", "OptionButton", style(Color("182538"),Color("3c4a60")))
	menu = PanelContainer.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.add_theme_stylebox_override("panel",style(Color("0b111e"),Color("19263b"),0))
	menu.theme = theme
	canvas.add_child(menu)
	var scroll = ScrollContainer.new()
	menu.add_child(scroll)
	var column = VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation",18)
	scroll.add_child(column)
	column.add_child(text_label("G R I M   O B S E R V E R",44,Color("e9c987")))
	column.add_child(text_label("WARHAMMER 40,000  /  FAN PROTOTYPE  /  OBSERVER ONLY",18,Color("8b9cb6")))
	column.add_child(text_label("Configurează frontul. Urmărește fiecare duel.",25))
	var settings_row = HBoxContainer.new()
	settings_row.add_theme_constant_override("separation",16)
	column.add_child(settings_row)
	map_select = OptionButton.new()
	for name in MAPS: map_select.add_item(name)
	map_select.custom_minimum_size = Vector2(460,54)
	settings_row.add_child(map_select)
	team_select = OptionButton.new()
	for count in [2,3,4]: team_select.add_item(str(count)+" echipe", count)
	settings_row.add_child(team_select)
	team_select.item_selected.connect(func(_i): update_team_rows())
	hero_toggle = CheckBox.new()
	hero_toggle.text = "Eroi din lore"
	hero_toggle.button_pressed = true
	settings_row.add_child(hero_toggle)
	blood_toggle = CheckBox.new()
	blood_toggle.text = "Sânge"
	blood_toggle.button_pressed = true
	settings_row.add_child(blood_toggle)
	column.add_child(text_label("COALIȚII  /  0–40 soldați per facțiune și echipă • maximum 320 în total",18,Color("8b9cb6")))
	for team in range(4):
		var panel = PanelContainer.new()
		panel.add_theme_stylebox_override("panel",style(Color("111c2d"), TEAM_COLORS[team].darkened(0.6)))
		column.add_child(panel)
		var v = VBoxContainer.new()
		panel.add_child(v)
		v.add_child(text_label("ECHIPA " + str(team+1),23,TEAM_COLORS[team]))
		var row = HBoxContainer.new()
		row.add_theme_constant_override("separation",20)
		v.add_child(row)
		for f in range(4):
			var cell = VBoxContainer.new()
			cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(cell)
			cell.add_child(text_label(FACTIONS[f],19))
			var count = SpinBox.new()
			count.min_value = 0
			count.max_value = 40
			count.step = 1
			count.custom_minimum_size = Vector2(210,48)
			count.value = 0
			if team == 0 and f < 2: count.value = 12
			if team == 1 and f == 2: count.value = 24
			if team > 1 and f == team: count.value = 12
			cell.add_child(count)
			slots.append({"team":team,"faction":f,"count":count,"panel":panel})
	var launch = button("ÎNCEPE BĂTĂLIA   →",start_battle)
	launch.add_theme_color_override("font_color",Color("f3d294"))
	column.add_child(launch)
	title = text_label("Trage: orbită • două degete: zoom • mod cinematic: urmărire automată\nModele și animații procedurale. Prototip neoficial, fără afiliere cu Games Workshop.",18,Color("8b9cb6"))
	column.add_child(title)
	hud = Control.new()
	hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.theme = theme
	canvas.add_child(hud)
	var top = VBoxContainer.new()
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 24
	top.offset_top = 18
	top.offset_right = -24
	hud.add_child(top)
	stats = text_label("",22)
	top.add_child(stats)
	feed = text_label("",17,Color("d6ba83"))
	top.add_child(feed)
	var bar = HBoxContainer.new()
	bar.add_theme_constant_override("separation",10)
	bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bar.offset_left = 20
	bar.offset_right = -20
	bar.offset_top = -80
	bar.offset_bottom = -20
	hud.add_child(bar)
	bar.add_child(button("← Configurare",show_menu))
	pause_button = button("Ⅱ Pauză",toggle_pause)
	bar.add_child(pause_button)
	var speeds = OptionButton.new()
	for s in [0.25,0.5,1.0,2.0,4.0]: speeds.add_item(str(s)+"×")
	speeds.selected = 2
	speeds.item_selected.connect(func(i): speed = [0.25,0.5,1.0,2.0,4.0][i])
	bar.add_child(speeds)
	cinematic_button = button("Cinematic: OFF",toggle_cinematic)
	bar.add_child(cinematic_button)
	bar.add_child(button("Următorul erou",next_hero))
	bar.add_child(button("−",func(): distance = minf(85,distance+5)))
	bar.add_child(button("+",func(): distance = maxf(5,distance-5)))
	bar.add_child(button("Vedere generală",func(): selected = -1; cinematic = false; distance = 45; pitch = 0.65; focus = Vector3.ZERO; cinematic_button.text = "Cinematic: OFF"))
	load_config()
	update_team_rows()

func save_config():
	var config = ConfigFile.new()
	config.set_value("battle","map",map_select.selected)
	config.set_value("battle","teams",team_select.selected)
	config.set_value("battle","heroes",hero_toggle.button_pressed)
	config.set_value("battle","blood",blood_toggle.button_pressed)
	for i in range(slots.size()): config.set_value("units",str(i),slots[i]["count"].value)
	if not testing: config.save(battle_config_path)

func load_config():
	if testing: return
	var config = ConfigFile.new()
	if config.load(battle_config_path) != OK: return
	map_select.selected = clampi(config.get_value("battle","map",0),0,2)
	team_select.selected = clampi(config.get_value("battle","teams",0),0,2)
	hero_toggle.button_pressed = config.get_value("battle","heroes",true)
	blood_toggle.button_pressed = config.get_value("battle","blood",true)
	for i in range(slots.size()): slots[i]["count"].value = clampf(config.get_value("units",str(i),0),0,40)

func update_team_rows():
	for row in slots: row["panel"].visible = row["team"] < team_select.get_selected_id()

func show_menu():
	active = false
	Engine.time_scale = 1
	menu.show()
	hud.hide()

func toggle_pause():
	paused = not paused
	pause_button.text = "▶ Continuă" if paused else "Ⅱ Pauză"

func toggle_cinematic():
	cinematic = not cinematic
	cinematic_button.text = "Cinematic: ON" if cinematic else "Cinematic: OFF"
	if cinematic:
		next_hero()
		distance = 10
		pitch = 0.28
		cinematic_clock = 0

func next_hero():
	if fighters.is_empty(): return
	for offset in range(1,fighters.size()+1):
		var index = (selected+offset)%fighters.size()
		if fighters[index]["hp"] > 0 and fighters[index]["hero"]:
			selected = index
			return
	for index in range(fighters.size()):
		if fighters[index]["hp"] > 0:
			selected = index
			return
	selected = -1

func start_battle():
	var totals = [0,0,0,0]
	var total = 0
	for row in slots:
		if row["team"] < team_select.get_selected_id():
			totals[row["team"]] += int(row["count"].value)
			total += int(row["count"].value)
	var populated = 0
	for n in totals:
		if n > 0: populated += 1
	if populated < 2 or total > 320:
		title.text = "Configurează cel puțin două echipe cu soldați. Limita totală este 320."
		return
	save_config()
	for child in world.get_children():
		world.remove_child(child)
		child.queue_free()
	fighters.clear()
	dead_bodies.clear()
	effects.clear()
	event_lines.clear()
	elapsed = 0
	kills = 0
	blocks = 0
	counters = 0
	shots = 0
	battle_over = false
	map_id = map_select.selected
	terrain()
	var team_offsets = [0,0,0,0]
	for row in slots:
		var team = row["team"]
		if team >= team_select.get_selected_id(): continue
		for i in range(int(row["count"].value)):
			var offset = team_offsets[team]
			var angle = TAU * team / team_select.get_selected_id()
			var p = Vector3(cos(angle),0,sin(angle))*19
			p += Vector3(-sin(angle),0,cos(angle)) * (float(offset%10)-4.5)*1.3
			p += Vector3(cos(angle),0,sin(angle))*floorf(offset/10.0)*1.5
			spawn_fighter(team,row["faction"],p,i == 0 and hero_toggle.button_pressed)
			team_offsets[team] += 1
	active = true
	paused = false
	cinematic = false
	selected = -1
	focus = Vector3.ZERO
	distance = 45
	pitch = 0.65
	pause_button.text = "Ⅱ Pauză"
	cinematic_button.text = "Cinematic: OFF"
	menu.hide()
	hud.show()
	log_event("Contact pe " + MAPS[map_id] + ". Lupta începe.")

func spawn_fighter(team: int, faction: int, p: Vector3, hero: bool):
	var root = Node3D.new()
	world.add_child(root)
	root.position = p
	var armor = COLORS[faction]
	var gold = Color("cda65d")
	var dark = Color("161c25")
	var size = 1.22 if hero else 1.0
	if faction == 2: size *= 1.18
	root.scale = Vector3.ONE*size
	box(root,Vector3(0,1.18,0),Vector3(0.65,0.65,0.42),armor)
	box(root,Vector3(0,0.78,0),Vector3(0.48,0.22,0.35),dark)
	box(root,Vector3(0,1.26,-0.235),Vector3(0.34,0.10,0.04),gold)
	box(root,Vector3(0,1.31,-0.26),Vector3(0.08,0.25,0.04),gold)
	box(root,Vector3(0,1.77,0),Vector3(0.36,0.4,0.36),armor)
	box(root,Vector3(0,1.82,-0.19),Vector3(0.28,0.05,0.035),Color("ff473e") if faction != 1 else Color("8be3af"),true)
	box(root,Vector3(0,1.68,-0.21),Vector3(0.19,0.1,0.09),dark)
	var limbs = []
	for side in [-1,1]:
		var leg = Node3D.new()
		root.add_child(leg)
		leg.position = Vector3(side*0.2,0.78,0)
		box(leg,Vector3(0,-0.3,0),Vector3(0.28,0.56,0.3),armor)
		box(leg,Vector3(0,-0.63,-0.09),Vector3(0.31,0.2,0.46),dark)
		box(leg,Vector3(0,-0.3,-0.17),Vector3(0.24,0.19,0.09),gold if hero else armor.lightened(0.15))
		limbs.append(leg)
		var arm = Node3D.new()
		root.add_child(arm)
		arm.position = Vector3(side*0.47,1.48,0)
		box(arm,Vector3.ZERO,Vector3(0.4,0.33,0.48),gold if hero else armor.lightened(0.15))
		box(arm,Vector3(0,-0.28,0),Vector3(0.24,0.4,0.24),armor)
		box(arm,Vector3(0,-0.5,0),Vector3(0.27,0.18,0.27),dark)
		limbs.append(arm)
		if side == 1:
			if hero and faction == 0:
				box(arm,Vector3(0,-0.43,-0.18),Vector3(0.45,0.4,0.5),gold)
				box(arm,Vector3(0,-0.35,-0.5),Vector3(0.22,0.13,0.32),dark)
			elif faction == 2:
				box(arm,Vector3(0,-0.45,-0.5),Vector3(0.09,0.09,1.2),dark)
				box(arm,Vector3(0,-0.45,-1),Vector3(0.12,0.65,0.35),gold)
			elif hero and faction == 3:
				box(arm,Vector3(0,-0.45,-0.7),Vector3(0.13,0.09,1.5),Color("a769cb"),true)
				box(arm,Vector3(0,-0.45,-0.25),Vector3(0.45,0.1,0.1),gold)
			elif faction == 1:
				box(arm,Vector3(0,-0.5,-0.4),Vector3(0.12,0.15,1.0),dark)
				box(arm,Vector3(0,-0.48,-0.91),Vector3(0.07,0.07,0.12),Color("94b39b"))
			else:
				box(arm,Vector3(0,-0.48,-0.36),Vector3(0.16,0.15,0.75),dark)
				box(arm,Vector3(0,-0.45,-0.8),Vector3(0.14,0.14,0.4),gold if faction == 2 else Color("8e9cab"))
				for tooth in range(5):
					box(arm,Vector3(0,-0.35,-0.6-tooth*0.1),Vector3(0.16,0.08,0.05),Color("d6d9dc"))
		else:
			box(arm,Vector3(0,-0.4,-0.18),Vector3(0.32,0.44,0.13),armor.darkened(0.2))
			if hero and faction == 3:
				for claw in range(3): box(arm,Vector3(-0.12+claw*0.12,-0.5,-0.45),Vector3(0.05,0.06,0.5),gold)
	if faction != 1:
		box(root,Vector3(0,1.24,0.33),Vector3(0.5,0.5,0.3),dark)
		for side in [-1,1]:
			orb(root,Vector3(side*0.29,1.5,0.33),0.16,armor)
	if faction >= 2:
		for side in [-1,1]:
			var horn = box(root,Vector3(side*0.23,2.03,0),Vector3(0.08,0.45,0.1),gold)
			horn.rotation.z = side*-0.4
	if hero:
		box(root,Vector3(0,0.9,0.35),Vector3(0.62,1.2,0.07),Color("80303d"))
	var ring = MeshInstance3D.new()
	var torus = TorusMesh.new()
	torus.inner_radius = 0.42
	torus.outer_radius = 0.47
	torus.rings = 12
	torus.ring_segments = 6
	ring.mesh = torus
	ring.material_override = mat(TEAM_COLORS[team],true)
	root.add_child(ring)
	ring.position.y = 0.035
	var unit_name = HEROES[faction] if hero else FACTIONS[faction]+" #"+str(fighters.size()+1)
	if hero:
		var label = Label3D.new()
		label.text = unit_name + " · E"+str(team+1)
		label.font_size = 32
		label.pixel_size = 0.009
		label.position.y = 2.6
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.modulate = TEAM_COLORS[team]
		root.add_child(label)
	fighters.append({"node":root,"team":team,"faction":faction,"hero":hero,"name":unit_name,"hp":240.0 if hero else 90.0,"limbs":limbs,"target":-1,"think":rng.randf(),"cooldown":rng.randf(),"anim":0.0,"state":"idle","phase":rng.randf()*TAU,"counter":false})

func log_event(message: String):
	event_lines.push_front(message)
	if event_lines.size() > 3: event_lines.pop_back()
	feed.text = "\n".join(event_lines)

func _process(delta):
	if not active: return
	update_camera(delta / maxf(Engine.time_scale, 0.001))
	if testing:
		test_frames += 1
		if test_frames == 10:
			toggle_pause()
			assert(paused)
			toggle_pause()
			toggle_cinematic()
			assert(cinematic and selected >= 0)
		if test_frames > 2400 or battle_over:
			print("SMOKE_RESULT map=",map_id," units=",fighters.size()," kills=",kills," blocks=",blocks," counters=",counters," shots=",shots," ended=",battle_over)
			assert(kills > 0)
			test_stage += 1
			if test_stage == 3:
				print("SMOKE_PASS")
				get_tree().quit()
			else:
				map_select.selected = test_stage
				team_select.selected = test_stage
				start_battle()
				test_frames = 0
	if paused or battle_over: return
	var dt = minf(delta,0.2)
	if testing: dt = 0.1
	elapsed += dt
	for index in range(fighters.size()):
		var f = fighters[index]
		if f["hp"] <= 0: continue
		f["think"] -= dt
		f["cooldown"] -= dt
		f["anim"] = maxf(0,f["anim"]-dt)
		if f["think"] <= 0 or f["target"] < 0 or fighters[f["target"]]["hp"] <= 0:
			f["think"] = 0.4+rng.randf()*0.25
			f["target"] = nearest_enemy(index)
		if f["target"] < 0: continue
		var enemy = fighters[f["target"]]
		var n = f["node"] as Node3D
		var difference = enemy["node"].position - n.position
		var separation = difference.length()
		if separation > 0.01:
			n.rotation.y = lerp_angle(n.rotation.y, atan2(-difference.x,-difference.z),minf(1,dt*9))
		var attack_range = 12.0 if f["faction"] == 1 else 1.65
		var moving = separation > attack_range
		if moving:
			var direction = difference.normalized()
			# Gentle lateral offsets prevent every soldier sharing the same position.
			var lateral = Vector3(-direction.z,0,direction.x)*sin(index*2.4)*0.18
			n.position += (direction+lateral)*dt*(2.5 if f["faction"] == 2 else 2.0)
			f["phase"] += dt*9
		elif f["cooldown"] <= 0:
			attack(index,f["target"],separation)
		var limbs = f["limbs"]
		limbs[0].rotation.x = sin(f["phase"])*0.5 if moving else 0
		limbs[2].rotation.x = -sin(f["phase"])*0.5 if moving else 0
		if f["anim"] > 0:
			if f["state"] == "block":
				limbs[1].rotation.x = -1.5
				limbs[3].rotation.x = -0.7
			else:
				limbs[3].rotation.x = -1.1 + sin(f["anim"]*12)*1.1
				limbs[1].rotation.x = -0.4
		else:
			limbs[1].rotation.x = 0.2*sin(f["phase"]) if moving else -0.25
			limbs[3].rotation.x = -0.2*sin(f["phase"]) if moving else -0.35
	for i in range(effects.size()-1,-1,-1):
		var e = effects[i]
		e["ttl"] -= dt
		if e["ttl"] <= 0:
			e["node"].queue_free()
			effects.remove_at(i)
		else:
			e["node"].position += e["velocity"]*dt
			if e["gravity"]: e["velocity"].y -= 9.8*dt
	hud_clock -= dt
	if hud_clock <= 0:
		hud_clock = 0.3
		update_stats()

func nearest_enemy(index: int) -> int:
	var result = -1
	var closest = INF
	var f = fighters[index]
	for j in range(fighters.size()):
		var enemy = fighters[j]
		if enemy["hp"] <= 0 or enemy["team"] == f["team"]: continue
		var d = f["node"].position.distance_squared_to(enemy["node"].position)
		if d < closest:
			closest = d
			result = j
	return result

func attack(attacker: int, defender: int, separation: float):
	var a = fighters[attacker]
	var b = fighters[defender]
	if testing: assert(a["team"] != b["team"], "Friendly-fire target selection")
	a["cooldown"] = rng.randf_range(0.65,1.25)
	a["state"] = "counter" if a["counter"] else "attack"
	a["anim"] = 0.48
	var ranged = a["faction"] == 1 and separation > 2
	var damage = rng.randf_range(14,24)*(1.7 if a["hero"] else 1.0)
	if a["counter"]:
		damage *= 1.5
		counters += 1
		a["counter"] = false
	if ranged:
		shots += 1
		tracer(a["node"].position+Vector3(0,1.3,0),b["node"].position+Vector3(0,1.2,0))
	elif rng.randf() < 0.27:
		blocks += 1
		b["state"] = "block"
		b["anim"] = 0.35
		b["counter"] = true
		b["cooldown"] = 0.22
		burst(b["node"].position+Vector3(0,1.3,0),Color("ffce65"),4)
		return
	b["hp"] -= damage
	if blood_toggle.button_pressed: burst(b["node"].position+Vector3(0,1.2,0),Color("9e1729"),4)
	if a["hero"] and rng.randf() < 0.12:
		explosion(b["node"].position)
	if b["hp"] <= 0:
		kill_unit(defender,(b["node"].position-a["node"].position).normalized())

func tracer(a: Vector3,b: Vector3):
	var length = a.distance_to(b)
	var beam = box(world,(a+b)*0.5,Vector3(0.045,0.045,length),Color("ff674e"),true)
	if length > 0.01: beam.look_at(b)
	effects.append({"node":beam,"ttl":0.08,"velocity":Vector3.ZERO,"gravity":false})

func burst(p: Vector3,color: Color,count: int):
	if effects.size() > 220: return
	for i in range(count):
		var particle = box(world,p,Vector3.ONE*rng.randf_range(0.05,0.12),color)
		effects.append({"node":particle,"ttl":rng.randf_range(0.25,0.65),"velocity":Vector3(rng.randf_range(-2,2),rng.randf_range(1,3),rng.randf_range(-2,2)),"gravity":true})

func explosion(p: Vector3):
	burst(p+Vector3.UP,Color("ff8a35"),14)
	var flash = orb(world,p+Vector3.UP,0.8,Color("ff9f45"))
	flash.material_override = mat(Color("ff8e37"),true)
	effects.append({"node":flash,"ttl":0.16,"velocity":Vector3.ZERO,"gravity":false})

func kill_unit(index: int,direction: Vector3):
	var f = fighters[index]
	f["hp"] = 0
	kills += 1
	var p = f["node"].position
	f["node"].hide()
	if f["hero"]: log_event(f["name"]+" a căzut. Echipa "+str(f["team"]+1)+" pierde un erou.")
	# Six collision bodies connected with pin joints form a small physical ragdoll.
	var corpse = Node3D.new()
	world.add_child(corpse)
	var offsets = [Vector3(0,1.15,0),Vector3(0,1.75,0),Vector3(-0.5,1.15,0),Vector3(0.5,1.15,0),Vector3(-0.2,0.45,0),Vector3(0.2,0.45,0)]
	var sizes = [Vector3(0.62,0.65,0.4),Vector3(0.35,0.35,0.35),Vector3(0.22,0.65,0.22),Vector3(0.22,0.65,0.22),Vector3(0.26,0.7,0.28),Vector3(0.26,0.7,0.28)]
	var bodies: Array = []
	for i in range(6):
		var body = RigidBody3D.new()
		body.collision_layer = 2
		body.collision_mask = 1
		body.mass = 3 if i == 0 else 1
		body.linear_damp = 0.8
		body.angular_damp = 1.0
		var collision = CollisionShape3D.new()
		var shape = BoxShape3D.new()
		shape.size = sizes[i]
		collision.shape = shape
		body.add_child(collision)
		corpse.add_child(body)
		body.position = p+offsets[i]
		box(body,Vector3.ZERO,sizes[i],COLORS[f["faction"]])
		body.apply_central_impulse(direction*3+Vector3.UP*1.5)
		body.apply_torque_impulse(Vector3(1,0,0.5))
		bodies.append(body)
	for i in range(1,6):
		var joint = PinJoint3D.new()
		corpse.add_child(joint)
		joint.global_position = p+(offsets[0]+offsets[i])*0.5
		joint.node_a = joint.get_path_to(bodies[0])
		joint.node_b = joint.get_path_to(bodies[i])
	dead_bodies.append(corpse)
	if dead_bodies.size() > 20:
		dead_bodies.pop_front().queue_free()

func update_stats():
	var alive = [0,0,0,0]
	for f in fighters:
		if f["hp"] > 0: alive[f["team"]] += 1
	var segments: Array[String] = []
	var surviving = 0
	var winner = -1
	for i in range(team_select.get_selected_id()):
		segments.append("E"+str(i+1)+": "+str(alive[i]))
		if alive[i] > 0:
			surviving += 1
			winner = i
	stats.text = "OBSERVER  •  %02d:%02d  |  %s  |  Căzuți: %d" % [int(elapsed)/60,int(elapsed)%60,"   /   ".join(segments),kills]
	if selected >= 0 and fighters[selected]["hp"] > 0:
		stats.text += "\n"+fighters[selected]["name"]+" • HP "+str(int(fighters[selected]["hp"]))
	if surviving <= 1 and not battle_over:
		battle_over = true
		log_event("VICTORIE • ECHIPA "+str(winner+1) if winner >= 0 else "Bătălia s-a încheiat fără supraviețuitori.")

func _physics_process(_delta):
	# Global simulation rate also governs ragdoll physics; the camera keeps real-time motion.
	Engine.time_scale = speed if active and not paused and not testing else 1.0
	for corpse in dead_bodies:
		if is_instance_valid(corpse):
			for child in corpse.get_children():
				if child is RigidBody3D:
					child.freeze = paused or not active or battle_over

func update_camera(delta: float):
	if selected >= 0 and selected < fighters.size():
		if fighters[selected]["hp"] > 0:
			focus = focus.lerp(fighters[selected]["node"].position+Vector3.UP, minf(1,delta*3))
		elif cinematic: next_hero()
	if cinematic:
		yaw += delta*0.12
		cinematic_clock += delta
		if cinematic_clock > 9:
			cinematic_clock = 0
			cinematic_shot = (cinematic_shot+1)%3
			next_hero()
		distance = lerpf(distance,[8.0,14.0,25.0][cinematic_shot],minf(1,delta*0.7))
		pitch = lerpf(pitch,[0.2,0.4,0.95][cinematic_shot],minf(1,delta*0.7))
	camera.position = focus + Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
	camera.look_at(focus)

func _unhandled_input(event):
	if not active: return
	if event is InputEventScreenTouch:
		if event.pressed: touches[event.index] = event.position
		else: touches.erase(event.index)
	if event is InputEventScreenDrag:
		if touches.size() >= 2 and touches.has(event.index):
			var keys = touches.keys()
			var other = keys[0] if keys[1] == event.index else keys[1]
			var pan = event.position-touches[event.index]
			if not cinematic:
				selected = -1
				focus += Vector3(-cos(yaw),0,sin(yaw))*pan.x*distance*0.001
				focus += Vector3(sin(yaw),0,cos(yaw))*pan.y*distance*0.001
			var previous = touches[event.index].distance_to(touches[other])
			var current = event.position.distance_to(touches[other])
			distance = clampf(distance-(current-previous)*0.04,5,85)
		else:
			yaw -= event.relative.x*0.006
			pitch = clampf(pitch+event.relative.y*0.004,0.12,1.4)
		touches[event.index] = event.position
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		selected = -1
		focus += Vector3(-cos(yaw),0,sin(yaw))*event.relative.x*distance*0.002
		focus += Vector3(sin(yaw),0,cos(yaw))*event.relative.y*distance*0.002
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		yaw -= event.relative.x*0.006
		pitch = clampf(pitch+event.relative.y*0.004,0.12,1.4)
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP: distance = maxf(5,distance-2)
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN: distance = minf(85,distance+2)
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_SPACE: toggle_pause()
		if event.keycode == KEY_C: toggle_cinematic()
		if event.keycode == KEY_ESCAPE: show_menu()
