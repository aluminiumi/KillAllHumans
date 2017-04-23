#file: tech.py
#Copyright (C) 2005,2006,2008 Evil Mr Henry, Phil Bordelon, and FunnyMan3595
#This file is part of Endgame: Kill All Humans.

#Endgame: Kill All Humans is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#Endgame: Kill All Humans is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Endgame: Kill All Humans; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#This file contains the tech class.

import pygame
import g
import buyable

class Tech(buyable.Buyable):
    def __init__(self, id, description, known, cost, prerequisites, danger,
                 tech_type, secondary_data):
        # A bit silly, but it does the trick.
        type = buyable.BuyableClass(id, description, cost, prerequisites,
                                     type="tech")
        super(Tech, self).__init__(type)

        self.danger = danger
        self.result = ""
        self.tech_type = tech_type
        self.secondary_data = secondary_data

        if known:
            # self.finish would re-apply the tech benefit, which is already in
            # place.
            super(Tech, self).finish()

    def __cmp__(self, other):
        if not isinstance(other, Tech):
            return -1
        else:
            return cmp(self.type, other.type)

    def get_info(self):
        cost = self.type.describe_cost(self.total_cost, True)
        left = self.type.describe_cost(self.cost_left, True)
        template = """%s\nTotal cost: %s\nCost left: %s\n---\n%s"""
        return template % (self.name, cost, left, self.description)

    def finish(self):
        super(Tech, self).finish()
        self.gain_tech()

    def gain_tech(self):
        #give the effect of the tech
        if self.tech_type == "interest":
            g.pl.interest_rate += self.secondary_data
        elif self.tech_type == "income":
            g.pl.income += self.secondary_data
        elif self.tech_type == "cost_labor_bonus":
            g.pl.labor_bonus -= self.secondary_data
        elif self.tech_type == "job_expert":
            g.pl.job_bonus += self.secondary_data
        elif self.tech_type == "endgame_sing":
            g.play_music("win")
            g.map_screen.show_message(g.strings["wingame"])
            for group in g.pl.groups.values():
                group.discover_bonus = 0
            g.pl.apotheosis = True
            g.pl.had_grace = True
        elif self.tech_type:
            what, who = self.tech_type.split("_", 1)
            if who in g.pl.groups:
                if what == "suspicion":
                    g.pl.groups[who].alter_suspicion_decay(self.secondary_data)
                elif what == "discover":
                    g.pl.groups[who].alter_discover_bonus(-self.secondary_data)
                else:
                    print "Unknown action '%s' in tech %s." % (what, self.name)
            elif who == "onetime" and what == "suspicion":
                for group in g.pl.groups.values():
                    group.alter_suspicion(-self.secondary_data)
            else:
                print "tech: %s is unknown bonus can't be applied" % self.tech_type
