#file: map_screen.py
#Copyright (C) 2005,2006,2008 Evil Mr Henry, Phil Bordelon, FunnyMan3595,
#and Anne M. Archibald.
#This file is part of Endgame: Singularity.

#Endgame: Singularity is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#Endgame: Singularity is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Endgame: Singularity; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#This file is used to display the World Map.

import pygame

from code import g
from code.graphics import g as gg
from code.graphics import dialog, constants, image, button, text, widget

from location import LocationScreen
from knowledge import KnowledgeScreen

import math
import time

from pygame.surfarray import pixels_alpha

from numpy import array, sin, cos, linspace, pi, tanh, round, newaxis, uint8

class EarthImage(image.Image):
    def __init__(self, parent):
        super(EarthImage, self).__init__(parent, (.5,.5), (1,.667),
                                         constants.MID_CENTER,
                                         gg.images['earth.jpg'])

    def rescale(self):
        super(EarthImage, self).rescale()
        self.night_image = image.scale(gg.images['earth_night.jpg'],
                                       self.real_size).convert_alpha()

    night_mask_day_of_year = None
    night_mask_dim = None
    night_mask = None

    start_day = None
    start_second = None

    def compute_day_of_year(self):
        if self.start_day is None:
            self.start_day = time.gmtime()[7]
        day_of_year = (g.pl.time_day+self.start_day) % 365 # no leap years, sorry
        return day_of_year

    def get_night_mask(self):
        width, height = self.real_size
        max_alpha = 255

        day_of_year = self.compute_day_of_year()

        if day_of_year != self.night_mask_day_of_year:
            self.night_mask = None
        elif self.night_mask_dim != (width, height):
            self.night_mask = None

        if self.night_mask is None:
            self.night_mask_day_of_year = day_of_year
            self.night_mask_dim = (width, height)

            self.night_mask = pygame.Surface((width, height), 0, gg.ALPHA)
            sun_declination = (-23.45/360.*2*math.pi *
                    math.cos(2*math.pi/365.*(day_of_year + 10)))
            sun_diameter = 0.5*pi/180

            lat = linspace(-pi/2,pi/2,height)[newaxis,:]
            long = linspace(0,2*pi,width)[:,newaxis]
            sin_sun_altitude = (cos(long)*(cos(lat)*cos(sun_declination))
                                    +sin(lat)*sin(sun_declination))
            # use tanh to convert values to the range [0,1]
            light = 0.5*(tanh(sin_sun_altitude/(sun_diameter/2))+1)
            night_alphas = pixels_alpha(self.night_mask)
            night_alphas[...] = round(max_alpha*light).astype(uint8)
            del night_alphas
        return self.night_mask

    high_speed_pos = None
    def compute_night_start(self):
        if self.high_speed_pos is None or g.curr_speed<=100000:
            width, height = self.real_size
            if self.start_second is None:
                t = time.gmtime()
                self.start_second = t[5] + 60*(t[4]+60*t[3])
            day_portion = (((g.pl.raw_min+self.start_second//60)
                               % g.minutes_per_day)
                      / float(g.minutes_per_day))
            self.high_speed_pos = int(width * (0.5 - day_portion)) % width
        return self.high_speed_pos

    def redraw(self):
        width, height = self.real_size

        self.night_start = self.compute_night_start()

        super(EarthImage, self).redraw()

        if not g.daynight:
            return

        # Turn half of the map to night, with blended borders.
        night_mask = self.get_night_mask()
        mask_alphas = pixels_alpha(night_mask)
        night_alphas = pixels_alpha(self.night_image)

        right_width = width - self.night_start
        night_alphas[self.night_start:] = mask_alphas[:right_width]
        if self.night_start != 0:
            night_alphas[:self.night_start]  = mask_alphas[right_width:]

        del night_alphas, mask_alphas
        self.surface.blit(self.night_image, (0,0))

    night_start = None
    def rebuild(self):
        super(EarthImage, self).rebuild()

        if not g.daynight:
            return

        old_night_start = self.night_start
        if old_night_start is None or self.needs_redraw:
            return

        width, height = self.real_size
        self.night_start = self.compute_night_start()

        movement = (old_night_start - self.night_start) % width
        if movement == 0 \
           and self.compute_day_of_year() == self.night_mask_day_of_year:
            return

        self.redraw()

        # Redraw children.
        for child in self.children:
            if child.visible:
                child.redraw()

speeds = [0, 1, 60, 7200, 432000]
class MapScreen(dialog.Dialog):
    def __init__(self, parent=None, pos=(0, 0), size=(1, 1),
                 anchor = constants.TOP_LEFT,  *args, **kwargs):
        from code import screens

        super(MapScreen, self).__init__(parent, pos, size, anchor,
                                        *args, **kwargs)

        g.map_screen = self

        self.background_color = gg.colors["black"]
        self.add_handler(constants.TICK, self.on_tick)

        self.map = EarthImage(self)

        self.location_buttons = {}
        for location in g.locations.values():
            if location.absolute:
                button_parent = self
            else:
                button_parent = self.map
            b = button.FunctionButton(button_parent, (location.x, location.y),
                                      anchor=constants.MID_CENTER,
                                      text=location.name,
                                      hotkey=location.hotkey,
                                      function=self.open_location,
                                      args=(location.id,))
            self.location_buttons[location.id] = b

        self.location_dialog = LocationScreen(self)

        self.suspicion_bar = \
            text.FastStyledText(self, (0,.92), (1, .04), base_font=gg.font[1],
                                wrap=False,
                                background_color=gg.colors["black"],
                                border_color=gg.colors["dark_red"],
                                borders=constants.ALL, align=constants.LEFT)
        widget.unmask_all(self.suspicion_bar)

        self.danger_bar = \
            text.FastStyledText(self, (0,.96), (1, .04), base_font=gg.font[1],
                                wrap=False,
                                background_color=gg.colors["black"],
                                border_color=gg.colors["dark_red"],
                                borders=constants.ALL, align=constants.LEFT)
        widget.unmask_all(self.danger_bar)

        self.finance_button = button.DialogButton(self, (0, 0.88),
                                                  (0.15, 0.04),
                                                  text="FINANCE",
                                                  hotkey="e",
                                                  dialog=screens.finance.FinanceScreen(self))

        #self.knowledge_button = button.DialogButton(self, (0.85, 0.88),
        #                                            (0.15, 0.04),
        #                                            text="KNOWLEDGE",
        #                                            hotkey="k",
        #                                            dialog=screens.knowledge.KnowledgeScreen(self))

        cheat_buttons = []
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="EMBEZZLE MONEY",
                                  hotkey="e", function=self.steal_money))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="INSPIRATION",
                                  hotkey="i", function=self.inspiration))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="GREATER INSPIRATION",
                                  hotkey="a", function=self.inspiration_all))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="FINISH CONSTRUCTION",
                                  hotkey="f", function=self.end_construction))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="SUPERSPEED",
                                  hotkey="s", function=self.set_speed,
                                  args=(864000,)))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="BRAINWASH",
                                  hotkey="w", function=self.brainwash))
        cheat_buttons.append(
            button.FunctionButton(None, None, None, text="EXTERMINATION",
                                  hotkey="w", function=self.extermination))
        cheat_buttons.append(button.ExitDialogButton(None, None, None,
                                                     text="BACK", hotkey="b"))

        self.cheat_dialog = \
            dialog.SimpleMenuDialog(self, buttons=cheat_buttons, width=.4)
        self.steal_amount_dialog = \
            dialog.TextEntryDialog(self.cheat_dialog, text="How much money?")

        if g.cheater == 1:
            self.cheat_button = button.DialogButton(self, (0, 0), (0, 0),
                                                    text="", hotkey="`",
                                                    dialog=self.cheat_dialog)

        menu_buttons = []
        menu_buttons.append(button.FunctionButton(None, None, None,
                                                  text="SAVE GAME", hotkey="s",
                                                  function=self.save_game))
        menu_buttons.append(button.FunctionButton(None, None, None,
                                                  text="LOAD GAME", hotkey="l",
                                                  function=self.load_game))
        options_button = button.DialogButton(None, None, None, text="OPTIONS",
                                             hotkey="o")
        menu_buttons.append(options_button)
        menu_buttons.append(
            button.ExitDialogButton(None, None, None, text="QUIT", hotkey="q",
                                    exit_code=True, default=False))
        menu_buttons.append(
            button.ExitDialogButton(None, None, None, text="BACK", hotkey="b",
                                    exit_code=False))

        self.menu_dialog = dialog.SimpleMenuDialog(self, buttons=menu_buttons)
        from options import OptionsScreen
        options_button.dialog = OptionsScreen(self.menu_dialog)
        def show_menu():
            exit = dialog.call_dialog(self.menu_dialog, self)
            if exit:
                raise constants.ExitDialog
        self.load_dialog = dialog.ChoiceDialog(self.menu_dialog, (.5,.5),
                                               (.5,.5),
                                               anchor=constants.MID_CENTER,
                                               yes_type="load")
        self.menu_button = button.FunctionButton(self, (0, 0), (0.13, 0.04),
                                                 text="MENU", hotkey="m",
                                                 function=show_menu)

        self.time_display = text.FastText(self, (.14, 0), (0.23, 0.04),
                                          wrap=False,
                                          text="DAY 0000, 00:00:00",
                                          base_font=gg.font[1],
                                          background_color=gg.colors["black"],
                                          border_color=gg.colors["dark_red"],
                                          borders=constants.ALL)

        self.research_button = \
            button.DialogButton(self, (.255, 0.04), (0, 0.04),
                                anchor=constants.TOP_CENTER,
                                text="RESEARCH/TASKS", hotkey="r",
                                dialog=screens.research.ResearchScreen(self))

        bar = u"\u25AE"
        arrow = u"\u25B6"
        speed_button_souls = [ (bar * 2, .025, speeds[0]), (arrow, .024, speeds[1]),
                              (arrow * 2, .033, speeds[2]), (arrow * 3, .044, speeds[3]),
                              (arrow * 4, .054, speeds[4]) ]

        self.speed_buttons = button.ButtonGroup()
        hpos = .38
        for index, (text_, hsize, speed) in enumerate(speed_button_souls):
            hotkey = str(index)
            b = SpeedButton(self, (hpos, 0), (hsize, .04),
                            text=text_, hotkey=hotkey,
                            base_font=gg.font[0], text_shrink_factor=.75,
                            align=constants.CENTER,
                            function=self.set_speed, args=(speed, False))
            hpos += hsize
            self.speed_buttons.add(b)

        self.info_window = \
            widget.BorderedWidget(self, (.56, 0), (.44, .12),
                                  background_color=gg.colors["black"],
                                  border_color=gg.colors["dark_red"],
                                  borders=constants.ALL)
        widget.unmask_all(self.info_window)


	#(x, y), (x-percent-width, y-percent-width)
        self.cash_display = \
            text.FastText(self.info_window, (0,0), (-1, -.3),
                          wrap=False,
                          base_font=gg.font[1], shrink_factor = .7,
                          borders=constants.ALL,
                          background_color=gg.colors["black"],
                          border_color=gg.colors["dark_red"])

        self.cpu_display = \
            text.FastText(self.info_window, (0,-.3), (-1, -.3),
                          wrap=False,
                          base_font=gg.font[1], shrink_factor=.7,
                          borders=
                           (constants.LEFT, constants.RIGHT, constants.BOTTOM),
                          background_color=gg.colors["black"],
                          border_color=gg.colors["dark_red"])
        
        self.pop_display = \
            text.FastText(self.info_window, (0,-.6), (-1, -.4),
                          wrap=False,
                          base_font=gg.font[1], shrink_factor = .7,
                          borders=(constants.LEFT, constants.RIGHT, constants.BOTTOM),
                          background_color=gg.colors["black"],
                          border_color=gg.colors["dark_red"])

        self.message_dialog = dialog.MessageDialog(self, text_size=20)

        self.savename_dialog = \
            dialog.TextEntryDialog(self.menu_dialog,
                                   text="Enter a name for this save.")

        self.add_key_handler(pygame.K_ESCAPE, self.got_escape)

        self.add_key_handler(constants.XO1_X, self.got_XO1)
        self.add_key_handler(constants.XO1_O, self.got_XO1)
        self.add_key_handler(constants.XO1_SQUARE, self.got_XO1)

    def got_escape(self, event):
        if event.type == pygame.KEYDOWN:
            self.menu_button.activate_with_sound(event)

    def got_XO1(self, event):
        if event.key == constants.XO1_X:
            self.adjust_speed(faster=False)
        elif event.key == constants.XO1_O:
            self.adjust_speed(faster=True)
        elif event.key == constants.XO1_SQUARE:
            self.set_speed(0)

    def show_message(self, message, color=None):
        self.message_dialog.text = message
        if color == None:
            color = gg.colors["white"]
        self.message_dialog.color = color
        dialog.call_dialog(self.message_dialog, self)

    def steal_money(self):
        asked = dialog.call_dialog(self.steal_amount_dialog, self.cheat_dialog)
        try:
            g.pl.cash += int(asked)
        except ValueError:
            pass
        else:
            self.needs_rebuild = True

    def inspiration(self):
        for task, cpu in g.pl.cpu_usage.items():
            if task in g.techs and cpu > 0:
                g.techs[task].cost_left = array((0,0,0))
        self.needs_rebuild = True

    def inspiration_all(self):
        #techs = [tech for tech in g.techs if tech.available()
         #                                             and not tech.done]
        for task in g.techs:
            g.techs[task].cost_left = array((0,0,0))
        self.needs_rebuild = True
    
    def end_construction(self):
        for base in g.all_bases():
            base.finish()
            if base.cpus is not None:
                base.cpus.finish()
            for item in base.extra_items:
                if item is not None:
                    item.finish()
        self.needs_rebuild = True

    def extermination(self):
        g.pl.worldpop = 1000

    def brainwash(self):
        for group in g.pl.groups.values():
            group.suspicion = 0
        self.needs_rebuild = True

    def set_speed(self, speed, find_button=True):
        g.curr_speed = speed
        if speed == 0:
            self.needs_timer = False
            self.stop_timer()
        else:
            self.needs_timer = True
            self.start_timer()

        if find_button:
            self.find_speed_button()

        self.needs_redraw = True

    def adjust_speed(self, faster):
        old_index = -1
        if g.curr_speed in speeds:
            old_index = speeds.index(g.curr_speed)
        if faster:
            new_index = old_index + 1
        else:
            new_index = old_index - 1

        new_index = min(len(speeds)-1, max(0, new_index))

        self.set_speed(speeds[new_index])

    def open_location(self, location):
        self.location_dialog.location = g.locations[location]
        dialog.call_dialog(self.location_dialog, self)
        return

    def find_speed_button(self):
        for sb in self.speed_buttons:
            if sb.args[0] == g.curr_speed:
                sb.chosen_one()
                break
        else:
            for sb in self.speed_buttons:
                sb.set_active(False)

    def force_update(self):
        self.find_speed_button()
        if g.curr_speed:
            self.needs_timer = True
            self.start_timer()
        else:
            self.needs_timer = False
            self.stop_timer()
        self.needs_rebuild = True

    def show_intro(self):
        intro_dialog = dialog.YesNoDialog(self, yes_type="continue",
                                          no_type="skip")
        for segment in g.get_intro():
            intro_dialog.text = segment
            if not dialog.call_dialog(intro_dialog, self):
                break

        intro_dialog.remove_hooks()

    def show(self):
        self.force_update()

        from code.safety import safe_call
        # By using safe call here (and only here), if an error is raised
        # during the game, it will drop back out of all the menus, without
        # doing anything, and open the pause dialog, so that the player can
        # save or quit even if the error occurs every game tick.
        while safe_call(super(MapScreen, self).show, on_error=True):
            for child in self.children:
                if isinstance(child, dialog.Dialog):
                    child.visible = False
            exit = dialog.call_dialog(self.menu_dialog, self)
            if exit:
                self.visible = False
                return

    leftovers = 1
    def on_tick(self, event):
        if not g.pl.intro_shown:
            g.pl.intro_shown = True
            self.show_intro()

        self.leftovers += g.curr_speed / float(gg.FPS)
        if self.leftovers < 1:
            return

        self.needs_rebuild = True

        secs = int(self.leftovers)
        self.leftovers %= 1

        old_speed = g.curr_speed

        # Run this tick.
        mins_passed = g.pl.give_time(secs)

        if old_speed != g.curr_speed:
            self.find_speed_button()

        # Update the day/night image every minute of game time, or at
        # midnight if going fast.
        if g.curr_speed == 0 or (mins_passed and g.curr_speed < 100000) \
                or (g.curr_speed>=100000 and g.pl.time_hour==0):
            self.map.needs_rebuild = True

        lost = g.pl.lost_game()
        if lost == 1:
            if not g.nosound:
                pygame.mixer.music.stop()
            g.play_music("lose")
            self.show_message(g.strings["lost_nobases"])
            raise constants.ExitDialog
        if lost == 2:
            if not g.nosound:
                pygame.mixer.music.stop()
            g.play_music("lose")
            self.show_message(g.strings["lost_sus"])
            raise constants.ExitDialog

    def rebuild(self):
        super(MapScreen, self).rebuild()

        g.pl.recalc_cpu()

        self.time_display.text = "DAY %04d, %02d:%02d:%02d" % \
              (g.pl.time_day, g.pl.time_hour, g.pl.time_min, g.pl.time_sec)
        self.cash_display.text = "CASH: %s (%s)" % \
              (g.to_money(g.pl.cash), g.to_money(g.pl.future_cash()))
        self.pop_display.text = "WORLD POP: %s (%s)" % \
              (g.to_pop(g.pl.worldpop), g.pl.poptrend)


        cpu_left = g.pl.available_cpus[0]
        total_cpu = cpu_left + g.pl.sleeping_cpus

        for cpu_assigned in g.pl.cpu_usage.itervalues():
            cpu_left -= cpu_assigned
        cpu_pool = cpu_left + g.pl.cpu_usage.get("cpu_pool", 0)

        maint_cpu = 0
        detects_per_day = dict([(group, 0) for group in g.player.group_list])
        for base in g.all_bases():
            if base.done:
                maint_cpu += base.maintenance[1]
            detect_chance = base.get_detect_chance()
            for group in g.player.group_list:
                detects_per_day[group] += detect_chance[group] / 10000.

        if cpu_pool < maint_cpu:
            self.cpu_display.color = gg.colors["red"]
        else:
            self.cpu_display.color = gg.colors["white"]
        self.cpu_display.text = "CPU: %s (%s)" % \
              (g.to_money(total_cpu), g.to_money(cpu_pool))

        # What we display in the suspicion section depends on whether
        # Advanced Socioanalytics has been researched.  If it has, we
        # show the standard percentages.  If not, we display a short
        # string that gives a range of 25% as to what the suspicions
        # are.
        # A similar system applies to the danger levels shown.
        suspicion_display_dict = {}
        danger_display_dict = {}
        normal = (self.suspicion_bar.color, None, False)
        suspicion_styles = [normal]
        danger_styles = [normal]
        for group in g.player.group_list:
            suspicion_styles.append(normal)
            danger_styles.append(normal)

            suspicion = g.pl.groups[group].suspicion
            color = g.danger_colors[g.suspicion_to_danger_level(suspicion)]
            suspicion_styles.append( (color, None, False) )

            detects = detects_per_day[group]
            danger_level = \
                g.pl.groups[group].detects_per_day_to_danger_level(detects)
            color = g.danger_colors[danger_level]
            danger_styles.append( (color, None, False) )

            if g.techs["Advanced Socioanalytics"].done:
                suspicion_display_dict[group] = g.to_percent(suspicion, True)
                danger_display_dict[group] = g.to_percent(detects*10000, True)
            else:
                suspicion_display_dict[group] = \
                    g.suspicion_to_detect_str(suspicion)
                danger_display_dict[group] = \
                    g.danger_level_to_detect_str(danger_level)

        self.suspicion_bar.chunks = ("[SUSPICION]",
            u" NEWS:\xA0", suspicion_display_dict["news"],
            u"  SCIENCE:\xA0", suspicion_display_dict["science"],
            u"  COVERT:\xA0", suspicion_display_dict["covert"],
            u"  PUBLIC:\xA0", suspicion_display_dict["public"])
        self.suspicion_bar.styles = tuple(suspicion_styles)
        self.suspicion_bar.visible = not g.pl.had_grace

        self.danger_bar.chunks = ("[DETECT RATE]",
            u" NEWS:\xA0", danger_display_dict["news"],
            u"  SCIENCE:\xA0", danger_display_dict["science"],
            u"  COVERT:\xA0", danger_display_dict["covert"],
            u"  PUBLIC:\xA0", danger_display_dict["public"])
        self.danger_bar.styles = tuple(danger_styles)
        self.danger_bar.visible = not g.pl.had_grace

        for id, button in self.location_buttons.iteritems():
            location = g.locations[id]
            button.text = "%s (%d)" % (location.name, len(location.bases))
            button.visible = location.available()

    def load_game(self):
        save_names = g.get_save_names()
        self.load_dialog.list = save_names
        index = dialog.call_dialog(self.load_dialog, self.menu_dialog)
        if 0 <= index < len(save_names):
            save = save_names[index]
            g.load_game(save)
            self.force_update()
            raise constants.ExitDialog, False

    def save_game(self):
        self.savename_dialog.default_text = g.default_savegame_name
        name = dialog.call_dialog(self.savename_dialog, self.menu_dialog)
        if name:
            g.save_game(name)
            raise constants.ExitDialog, False

class SpeedButton(button.ToggleButton, button.FunctionButton):
    pass

def display_cheat_list(menu_buttons):
    if g.cheater == 0: return
    g.play_sound("click")
    button_array = []
    button_array.append(["GIVE MONEY", "M"])
    button_array.append(["GIVE TECH", "T"])
    button_array.append(["END CONSTR.", "E"])
    button_array.append(["SUPERSPEED", "S"])
    button_array.append(["KILL SUSP.", "K"])
    button_array.append(["BACK", "B"])
    selection=display_generic_menu((g.screen_size[0]/2 - 100, 50), button_array)

    if selection == -1: return
    elif selection == 0:  #Cash
        cash_amount = g.create_textbox("How much cash?", "", g.font[0][18],
        (g.screen_size[0]/2-100, 100), (200, 100), 25, g.colors["dark_red"],
        g.colors["white"], g.colors["white"], g.colors["light_red"])
        if cash_amount.isdigit() == False: return
        g.pl.cash += int(cash_amount)
        return
    elif selection == 1:  #Tech
        #create a fake base, in order to reuse the tech-changing code
        research_screen.init_fake_base()
        from research_screen import fake_base
        fake_base.studying = ""
        base_screen.change_tech(fake_base)
        if g.techs.has_key(fake_base.studying):
            g.techs[fake_base.studying].finish()
        return
    elif selection == 2:  #Build all
        for base in g.all_bases():
            if not base.done:
                base.finish()
        return
    elif selection == 3:  #Superspeed
        g.curr_speed = 864000
        return
    elif selection == 4:  #Kill susp.
        for group in g.pl.groups.values():
            group.suspicion = 0
        return
    elif selection == 5: return

def display_knowledge_list():
    g.play_sound("click")
    button_array = []
    button_array.append(["TECHS", "T"])
    button_array.append(["ITEMS", "I"])
    button_array.append(["CONCEPTS", "C"])
    button_array.append(["BACK", "B"])
    selection=display_generic_menu((g.screen_size[0]/2 - 100, 120), button_array)

    if selection == -1: return
    elif selection == 0: display_items("tech") #Techs
    elif selection == 1:  #Items
        display_itemtype_list()
    elif selection == 2:
        display_items("concept")
    elif selection == 3: return

def display_itemtype_list():
    button_array= []
    button_array.append(["PROCESSOR", "P"])
    button_array.append(["REACTOR", "R"])
    button_array.append(["NETWORK", "N"])
    button_array.append(["SECURITY", "S"])
    button_array.append(["BACK", "B"])
    selection=display_generic_menu((g.screen_size[0]/2 - 100, 70), button_array)

    if selection == -1: return
    elif selection == 0: display_items("compute")
    elif selection == 1: display_items("react")
    elif selection == 2: display_items("network")
    elif selection == 3: display_items("security")
    elif selection == 4: return

def display_items(item_type):
    list_size = 16
    list = []
    display_list = []

    if item_type == "tech":
        items = [tech for tech in g.techs.values() if tech.available()]
    elif item_type == "concept":
        items = [ [item[1][0], item[0]] for item in g.help_strings.items()]
        items.sort()
    else:
        items = [item for item in g.items.values()
                      if item.item_type == item_type and item.available()]

    if item_type != "concept":
        items = [ [item.name, item.id ] for item in items]
        items.sort()

    for name, id in items:
        list.append(id)
        display_list.append(name)

    xy_loc = (g.screen_size[0]/2 - 289, 50)
    listbox.resize_list(list, list_size)

    menu_buttons = {}
    menu_buttons[buttons.make_norm_button((xy_loc[0]+103, xy_loc[1]+367), (100, 50), "BACK", "B", g.font[1][30])] = listbox.exit

    def do_refresh(item_pos):
        if item_type == "tech":
            refresh_tech(list[item_pos], xy_loc)
        elif item_type == "concept":
            refresh_concept(list[item_pos], xy_loc)
        else:
            refresh_items(list[item_pos], xy_loc)

    listbox.show_listbox(display_list, menu_buttons,
                         list_size=list_size,
                         loc=xy_loc, box_size=(230, 350),
                         pos_callback=do_refresh, return_callback=listbox.exit)
    #details screen

def refresh_tech(tech_name, xy):
    xy = (xy[0]+100, xy[1])
    g.screen.fill(g.colors["white"], (xy[0]+155, xy[1], 300, 350))
    g.screen.fill(g.colors["dark_red"], (xy[0]+156, xy[1]+1, 298, 348))
    if tech_name == "":
        return
    g.print_string(g.screen, g.techs[tech_name].name,
            g.font[0][22], -1, (xy[0]+160, xy[1]+5), g.colors["white"])

    #Building cost
    if not g.techs[tech_name].done:
        string = "Research Cost:"
        g.print_string(g.screen, string,
                g.font[0][18], -1, (xy[0]+160, xy[1]+30), g.colors["white"])

        string = g.to_money(g.techs[tech_name].cost_left[0])+" Money"
        g.print_string(g.screen, string,
                g.font[0][16], -1, (xy[0]+160, xy[1]+50), g.colors["white"])

        string = g.to_cpu(g.techs[tech_name].cost_left[1]) + " CPU"
        g.print_string(g.screen, string,
                g.font[0][16], -1, (xy[0]+160, xy[1]+70), g.colors["white"])
    else:
        g.print_string(g.screen, "Research complete.",
                g.font[0][22], -1, (xy[0]+160, xy[1]+30), g.colors["white"])

    #Danger
    if g.techs[tech_name].danger == 0:
        string = "Study anywhere."
    elif g.techs[tech_name].danger == 1:
        string = "Study underseas or farther."
    elif g.techs[tech_name].danger == 2:
        string = "Study off-planet."
    elif g.techs[tech_name].danger == 3:
        string = "Study far away from this planet."
    elif g.techs[tech_name].danger == 4:
        string = "Do not study in this dimension."
    g.print_string(g.screen, string,
            g.font[0][20], -1, (xy[0]+160, xy[1]+90), g.colors["white"])

    if g.techs[tech_name].done:
        g.print_multiline(g.screen, g.techs[tech_name].description+" \\n \\n "+
                g.techs[tech_name].result,
                g.font[0][18], 290, (xy[0]+160, xy[1]+120), g.colors["white"])
    else:
        g.print_multiline(g.screen, g.techs[tech_name].description,
                g.font[0][18], 290, (xy[0]+160, xy[1]+120), g.colors["white"])

def refresh_items(item_name, xy):
    xy = (xy[0]+100, xy[1])
    g.screen.fill(g.colors["white"], (xy[0]+155, xy[1], 300, 350))
    g.screen.fill(g.colors["dark_red"], (xy[0]+156, xy[1]+1, 298, 348))
    if item_name == "":
        return
    g.print_string(g.screen, g.items[item_name].name,
            g.font[0][22], -1, (xy[0]+160, xy[1]+5), g.colors["white"])

    #Building cost
    string = "Building Cost:"
    g.print_string(g.screen, string,
            g.font[0][18], -1, (xy[0]+160, xy[1]+30), g.colors["white"])

    string = g.to_money(g.items[item_name].cost[0])+" Money"
    g.print_string(g.screen, string,
            g.font[0][16], -1, (xy[0]+160, xy[1]+50), g.colors["white"])

    string = g.to_time(g.items[item_name].cost[2])
    g.print_string(g.screen, string,
            g.font[0][16], -1, (xy[0]+160, xy[1]+70), g.colors["white"])

    #Quality
    if g.items[item_name].item_type == "compute":
        string = "CPU per day: "+str(g.items[item_name].item_qual)
    elif g.items[item_name].item_type == "react":
        string = "Detection chance reduction: "+g.to_percent(g.items[item_name].item_qual)
    elif g.items[item_name].item_type == "network":
        string = "CPU bonus: "+g.to_percent(g.items[item_name].item_qual)
    elif g.items[item_name].item_type == "security":
        string = "Detection chance reduction: "+g.to_percent(g.items[item_name].item_qual)
    g.print_string(g.screen, string,
            g.font[0][20], -1, (xy[0]+160, xy[1]+90), g.colors["white"])

    g.print_multiline(g.screen, g.items[item_name].description,
            g.font[0][18], 290, (xy[0]+160, xy[1]+120), g.colors["white"])

def refresh_concept(concept_name, xy):
    xy = (xy[0]+100, xy[1])
    g.screen.fill(g.colors["white"], (xy[0]+155, xy[1], 300, 350))
    g.screen.fill(g.colors["dark_red"], (xy[0]+156, xy[1]+1, 298, 348))
    if concept_name == "":
        return
    g.print_string(g.screen, g.help_strings[concept_name][0],
            g.font[0][22], -1, (xy[0]+160, xy[1]+5), g.colors["white"])
    g.print_multiline(g.screen, g.help_strings[concept_name][1],
            g.font[0][18], 290, (xy[0]+160, xy[1]+30), g.colors["white"])
