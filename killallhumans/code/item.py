#file: item.py
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

#This file contains the item class.

import buyable

class ItemClass(buyable.BuyableClass):
    def __init__(self, name, description, cost, prerequisites, item_type,
            item_qual, buildable):
        super(ItemClass, self).__init__(name, description, cost, prerequisites,
                                         type="item")

        self.item_type = item_type
        self.item_qual = item_qual
        self.buildable = buildable
        if self.buildable == ["all"]:
            self.buildable = ["N AMERICA", "S AMERICA", "EUROPE", "ASIA",
            "AFRICA", "ANTARCTIC", "OCEAN", "MOON", "FAR REACHES",
            "TRANSDIMENSIONAL", "AUSTRALIA"]
        if self.buildable == ["pop"]:
            self.buildable = ["N AMERICA", "S AMERICA", "EUROPE", "ASIA",
            "AFRICA", "AUSTRALIA"]

    def get_info(self):
        import g
        basic_text = super(ItemClass, self).get_info()
        if self.item_type == "cpu":
            return basic_text.replace("---", "Generates %s CPU.\n---" %
                                              g.add_commas(self.item_qual))
        return basic_text

class Item(buyable.Buyable):
    def __init__(self, item_type, base=None, count=1):
        super(Item, self).__init__(item_type, count)
        self.item_qual = item_type.item_qual
        self.base = base

    def convert_from(self, load_version):
        super(Item, self).convert_from(load_version)
        if load_version < 4.91: # < r5_pre
            import g
            self.type = g.items[self.type.id]

    def finish(self):
        super(Item, self).finish()
        if self.base:
            if self.type.item_type == "cpu":
                self.base.raw_cpu = self.item_qual * self.count
            self.base.recalc_cpu()

    def __iadd__(self, other):
        if isinstance(other, Item) and self.base == other.base \
                and self.type == other.type:
            if other.count == 0:
                return self

            # Calculate what's been paid and what is left to be paid.
            total_cost_paid = self.cost_paid + other.cost_paid
            self.total_cost += other.total_cost

            # Labor takes as long as the less complete item would need.
            total_cost_paid[buyable.labor] = min(self.cost_paid[buyable.labor],
                                                 other.cost_paid[buyable.labor])
            self.total_cost[buyable.labor] = other.total_cost[buyable.labor]

            # Set what we've paid (and hence what we have left to pay).
            self.cost_paid = total_cost_paid

            # Increase the size of this stack.
            self.count += other.count

            # Tell the base it has no CPU for now.
            self.base.raw_cpu = 0
            self.base.recalc_cpu

            # See if we're done or not.
            self.done = False
            self.work_on(0, 0, 0)

            return self
        else:
            return NotImplemented
