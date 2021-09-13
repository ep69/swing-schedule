#!/usr/bin/env python3

import sys
import csv
from ortools.sat.python import cp_model
from pprint import pprint

VERBOSE = False

def set_verbose():
    global VERBOSE
    VERBOSE = True

def debug(m):
    if not VERBOSE:
        return
    print(f"DEBUG: {m}")

def info(m):
    print(f"INFO: {m}")

def warn(m):
    print(f"WARNING: {m}")

def error(m):
    print(f"ERROR: {m}")
    sys.exit(1)

class Input:
    def init(self, infile=None):
        self.init_constants()
        self.init_form(infile)
        self.init_teachers()
        self.init_rest()
        self.init_penalties()

    def init_constants(self):
        #self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]
        self.days = ["Mon", "Tue", "Wed", "Thu"]
        self.Days = {}
        for i, D in enumerate(self.days):
            self.Days[D] = i

        #self.times = ["17:30-18:40", "18:45-19:55", "20:00-21:10"]
        self.times = ["17:30", "18:45", "20:00"]

        self.slots = [ d + " " + t for d in self.days for t in self.times ]

        self.rooms = [
            #"big",
            #"small",
            "k-3",
            "k-4",
        ]
        self.Rooms = {}
        for i, R in enumerate(self.rooms):
            self.Rooms[R] = i

        #self.venues = ["mosilana", "koliste"]
        self.venues = ["koliste"]
        self.Venues = {}
        for i, V in enumerate(self.venues):
            self.Venues[V] = i

        self.rooms_venues = {
            #"small": "mosilana",
            #"big": "mosilana",
            "k-3": "koliste",
            "k-4": "koliste",
            }

        self.courses_open = [
            "Lindy/Charleston Open Training",
            "Blues/Slow Open Training",
            "Balboa Teachers Training",
            "Rhythm Pilots /1",
            "Rhythm Pilots /2",
            ]
        self.courses_solo = [
            "Solo",
            "Teachers Training",
            "Shag/Balboa Open Training",
            ]
        self.courses_regular = [
            "LH 1 - Beginners /1",
            "LH 1 - Beginners /2",
            "LH 1 - Beginners /3",
            "LH 1 - English",
            "LH 2 - Party Moves /1",
            "LH 2 - Party Moves /2",
            "LH 2 - Survival Guide",
            "LH 2.5 - Swingout /1",
            "LH 2.5 - Swingout /2",
            "LH 3 - Musicality",
            "LH 3 - Charleston",
            "LH 3 - Cool Moves and Styling",
            "LH 4 - TODO /1",
            "LH 4 - TODO /2",
            "LH 5",
            "Collegiate Shag 1",
            "Collegiate Shag 2",
            "Balboa Beginners",
            "Balboa Intermediate",
            "Balboa Advanced",
            "Slow Balboa",
            "Airsteps 1",
            "Airsteps 2",
            "Saint Louis Shag 1",
            "Saint Louis Shag 2",
            "Blues 1",
            "Blues 2",
            ]
        self.COURSES_IGNORE = [
            "LH 1 - Beginners /3", #
            #"LH 1 - English",
            #"LH 2.5 - Swingout /2", #
            #"LH 3 - Musicality",
            "LH 4 - TODO /2",
            "LH 5",
            "Solo",
            "Airsteps 1",
            "Airsteps 2",
            "Saint Louis Shag 1",
            "Saint Louis Shag 2",
            "Balboa Advanced",
            "Slow Balboa",
            "Balboa Teachers Training",
            "Blues 2",
        ]
        self.courses_open = list(set(self.courses_open)-set(self.COURSES_IGNORE))
        self.courses_solo = list(set(self.courses_solo)-set(self.COURSES_IGNORE))
        self.courses_regular = list(set(self.courses_regular)-set(self.COURSES_IGNORE))
        self.courses = self.courses_regular + self.courses_solo + self.courses_open
        self.Courses = {}
        for (i, c) in enumerate(self.courses):
            self.Courses[c] = i

    def init_teachers(self):
        debug("Initializing teachers")

        if not hasattr(self, "TEACHERS"): # if not overriden in child class
            debug(f"Initializing TEACHERS database")
            # name, role
            self.TEACHERS = [
                ("LEADER", "lead"),
                ("FOLLOW", "follow"),
                ("Karel-X.", "lead"),
                ("Roman", "lead"),
                ("Bart", "lead"),
                ("Evzen-E.", "lead"),
                ("Krasomil", "lead"),
                ("Vilda", "lead"),
                ("Radek", "lead"),
                ("Karla", "follow"),
                ("Hermiona", "both"),
                ("Eva", "follow"),
                ("Dana", "follow"),
                ("Wendy", "follow"),
                ("Jana", "follow"),
                ("Hanka", "follow"),
                ("Lenka-V.", "follow"),
                ("Lucka", "follow"),
                ("Zora", "follow"),
                ("Martina", "follow"),
                ]
            self.FAKE_TEACHERS = ["LEADER", "FOLLOW"]

        self.teachers = self.teachers_active + self.FAKE_TEACHERS
        debug(f"Active teachers: {self.teachers_active}")
        self.teachers_lead = [t[0] for t in self.TEACHERS if t[1] == "lead" and t[0] in self.teachers]
        debug(f"Leaders: {self.teachers_lead}")
        self.teachers_follow = [t[0] for t in self.TEACHERS if t[1] == "follow" and t[0] in self.teachers]
        debug(f"Follows: {self.teachers_follow}")
        self.teachers_both = [t[0] for t in self.TEACHERS if t[1] == "both" and t[0] in self.teachers]
        debug(f"Both: {self.teachers_both}")
        assert(set(self.teachers) == set(self.teachers_lead + self.teachers_follow + self.teachers_both))
        assert(len(set(self.teachers_lead) & set(self.teachers_follow)) == 0)
        assert(len(set(self.teachers_lead) & set(self.teachers_both)) == 0)
        assert(len(set(self.teachers_both) & set(self.teachers_follow)) == 0)

        self.Teachers = {}
        for (i, t) in enumerate(self.teachers):
            self.Teachers[t] = i

        # caring only about teachers for now
        self.people = self.teachers_active


    def translate_teacher_name(self, name):
        result = name.strip()
        result = result.replace(" ", "-")
        debug(f"Translated '{name}' to '{result}'")
        return result

    def check_course(self, course):
        for c in self.courses:
            if c.startswith(course):
                debug(f"Course {c} starts with {course}")
                return
        error(f"Unknown course: '{course}'")

    def is_course_type(self, Cspec, Cgen):
        if Cspec.startswith("LH 1 - English"):
            return Cgen.startswith("LH 1 - English")
        return Cspec.startswith(Cgen)

    def read_input(self, infile=None):
        if infile:
            info(f"Opening {infile}")
            f = open(infile, mode="r")
        else: # use stdin
            f = sys.stdin

        result = {}
        self.teachers_active = []
        input_courses = [] # courses
        n = 0

        reader = csv.DictReader(f)
        for row in reader:
            n += 1
            if n == 1:
                # check courses when handling the first row
                columns = list(row.keys())
                for col in columns:
                    if col.startswith("What courses would you like to teach?"):
                        course = col.split("[")[1].split("]")[0]
                        if course in self.COURSES_IGNORE:
                            continue
                        self.check_course(course)
                        # problematic: Balboa Beginners 2
                        input_courses.append(course)
                input_courses.append("Rhythm Pilots") # TODO
                info(f"Input courses (F): {sorted(input_courses)}")
                info(f"Input courses (C): {sorted(self.courses)}")
                # does not make sense (general vs. specific course names)
                #info(f"Input courses (diff): {set(self.courses)-set(input_courses)-set(self.COURSES_IGNORE)}")
            # handle the input data
            debug("")
            name = self.translate_teacher_name(row["Who are you?"])
            debug(f"Reading: name {name}")
            d = {}
            d["ncourses_ideal"] = int(row["How many courses would you ideally like to teach?"])
            d["ncourses_max"] = int(row["How many courses are you able to teach at most?"])
            slots = []
            for day in ["Mon", "Tue", "Wed", "Thu"]:
                for time in ["17:30", "18:45", "20:00"]:
                    slots.append(int(row[f"What days and times are convenient for you? [{day} {time}]"][0]))
            d["slots"] = slots
            #d["mosilana"] = row["Are you fine with teaching in Mosilana?"] == "Yes"
            courses_teach = {}
            for c in input_courses:
                #debug(f"course {c}")
                if c == "Rhythm Pilots":
                    pass
                elif c == "Teachers Training" and name == "Kuba-Š.":
                    answer_num = 3
                else:
                    answer = row[f"What courses would you like to teach? [{c}]"]
                    if not answer:
                        warn(f"{name} provided no answer for {c}, defaulting to 0")
                        answer_num = 0
                    elif len(answer) >= 1:
                        first = answer[0]
                        if first in ("0", "1", "2", "3"):
                            answer_num = int(first)
                        else:
                            error(f"Unexpected first char in answer: '{answer}'")
                    else:
                        # should not happen
                        error(f"Unexpected answer: '{answer}'")
                courses_teach[c] = answer_num
                #courses_teach[c] = int(row[f"What courses would you like to teach? [{c}]"][0])
            d["courses_teach"] = courses_teach
            d["courses_attend"] = [a.strip() for a in row["What courses and trainings would you like to attend?"].split(",") if a]
            assert("" not in d["courses_attend"])
            # there won't be Balboa Teachers Training, people would like to train at Shag/Balboa Open Training
            if "Balboa Teachers Training" in d["courses_attend"]:
                # would happen in ignoring logic, but to be sure..
                d["courses_attend"].remove("Balboa Teachers Training")
                if "Shag/Balboa Open Training" not in d["courses_attend"]:
                    d["courses_attend"].append("Shag/Balboa Open Training")
            #debug(f"Courses attend before: {d['courses_attend']}")
            for c in set(d["courses_attend"]):
                if c in self.COURSES_IGNORE:
                    debug(f"courses_attend: removing: {c}")
                    d["courses_attend"].remove(c)
                else:
                    debug(f"NOT removing: {c}")
            #debug(f"Courses attend after: {d['courses_attend']}")
            for c in d["courses_attend"]:
                debug(f"Check course 2: {c}")
                self.check_course(c)
            teach_together = row["Who would you like to teach with?"]
            d["teach_together"] = [self.translate_teacher_name(name.strip()) for name in teach_together.split(",") if name]
            d["teach_not_together"] = [self.translate_teacher_name(name) for name in row["Are there any people you cannot teach with?"].split(",") if name not in ["", "-", "No", "není", "nah", "ne", "no", "None"]]
            debug(f"Adding {name} to result")
            self.teachers_active.append(name)
            result[name] = d
        debug(f"Number of lines: {n}")
        debug(f"Result: {'|'.join(result)}")
        debug(f"Active teachers: {set(self.teachers_active)}")

        if f is not sys.stdin:
            f.close()

        #print(f"Column names: {columns}")
        return result

    def init_form(self, infile=None):
        self.input_data = self.read_input(infile)
        pprint(self.input_data)

    # SPECIFIC HARD CONSTRAINTS
    def init_rest(self):
        # HARD teacher T can teach maximum N courses
        self.t_util_max = {}
        # teacher T wants to teach N courses
        self.t_util_ideal = {}
        # HARD teacher T1 must not teach a course with teacher T2
        self.tt_not_together = []
        # SOFT teacher T wants to teach a course with teachers Ts
        self.tt_together = {}
        # HARD teacher T cannot do anything in slots Ss
        self.ts_pref = {}
        # teacher T preference about teaching course C (HARD if 0)
        self.tc_pref = {}
        # course C can be taught only by Ts
        self.ct_possible = {}
        for C in self.courses:
            if C not in self.courses_open:
                self.ct_possible[C] = list(set(self.teachers_active))
        # course C must not take place in room R
        # TODO improve - some of these actualy fake course-venues constraints
        self.cr_not = {}
        # course C must take place in room R
        # PJ in Mosilana
        self.cr_strict = {}
        # teacher T must teach courses Cs
        self.tc_strict = {}
        # course Cx that must open
        self.courses_must_open = []
        # course Cx must happen on different day and at different time than Cy (and Cz)
        self.courses_different = []
        # course Cx must happen on different day than Cy (and Cz)
        self.courses_diffday = []
        # course C1, C2, (C3) should happen
        #  * on the same day
        #  * in different times
        #  * following each other
        #  * in the same venue
        self.courses_same = []

        # translate input data to variables understood by the rest of the script
        self.teachers_active = []
        for T in self.input_data:
            debug(f"Teacher {T}")
            data = self.input_data[T]
            self.t_util_max[T] = data["ncourses_max"]
            if self.t_util_max[T] > 0:
                self.teachers_active.append(T)
                self.t_util_ideal[T] = data["ncourses_ideal"]
                courses_teach = data["courses_teach"]
                courses_pref = {}
                for (Cgen, v) in courses_teach.items():
                    for Cspec in self.courses_regular + self.courses_solo:
                        #if Cspec.startswith(Cgen):
                        if self.is_course_type(Cspec, Cgen):
                            courses_pref[Cspec] = v
                            debug(f"courses_pref[{Cspec}] = {v}")
                            if v == 0:
                                # HARD preference
                                if T in self.ct_possible[Cspec]:
                                    self.ct_possible[Cspec].remove(T)
                                    assert(T not in self.ct_possible[Cspec])
                            elif v <= 3:
                                pass
                            else:
                                error(f"Unexpected course preference value: teacher {T} course {Cgen} value {v}")
                self.tc_pref[T] = courses_pref
                for d in data["teach_not_together"]:
                    if d in self.input_data:
                        self.tt_not_together.append((T, d))
                    else:
                        warn(f"Unknown teacher {d} (tt_not_together), ignoring")
                l = []
                for d in data["teach_together"]:
                    if d in self.input_data:
                        l.append(d)
                    else:
                        warn(f"Unknown teacher {d} (tt_together), ignoring")
                self.tt_together[T] = l
            self.ts_pref[T] = data["slots"]
            assert(len(self.ts_pref[T]) == len(self.slots))
            # attendance done directly through input_data

    def init_penalties(self):
        # "name" -> coeff
        self.PENALTIES = {
            # workload
            "utilization": 25, # squared
            # placement
            "days": 75,
            "occupied_days": 25, # squared
            "split": 50,
            # slots
            "slotpref_bad": 80,
            "slotpref_slight": 20,
            # courses
            "coursepref_bad": 80,
            "coursepref_slight": 20,
            "attend_free": 50,
            # person-related
            "teach_together": 25,
            # serious penalties
            "faketeachers": 1000000,
            "everybody_teach": 1000,
            # other
            "mosilana": 0,
            # TODO teaching multiple times with the same person?
        }


class Model:
    def init(self, I):
        self.I = I
        M = self

        model = cp_model.CpModel()
        self.model = model

        # course C takes place in slot S in room R
        self.src = {}
        for s in range(len(I.slots)):
            for r in range(len(I.rooms)):
                for c in range(len(I.courses)):
                    self.src[(s,r,c)] = model.NewBoolVar("CSR:s%ir%ic%i" % (s,r,c))
        # course C is taught by teacher T
        self.tc = {}
        for c in range(len(I.courses)):
            for t in range(len(I.teachers)):
                self.tc[(t,c)] = model.NewBoolVar("CT:t%ic%i" % (t,c))
        # teacher T teaches in slot S course C
        self.tsc = {}
        for s in range(len(I.slots)):
            for t in range(len(I.teachers)):
                for c in range(len(I.courses)):
                    self.tsc[(t,s,c)] = model.NewBoolVar("TS:t%is%ic%i" % (t,s,c))
        # teacher T teaches in slot S
        self.ts = {}
        for s in range(len(I.slots)):
            for t in range(len(I.teachers)):
                self.ts[(t,s)] = model.NewBoolVar("TS:t%is%i" % (t,s))
        # person P attends course C
        self.ac = {}
        for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
            for c in range(len(I.courses)):
                self.ac[(p,c)] = model.NewBoolVar("")
        # person P teaches or attends course C
        self.pc = {}
        for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
            for c in range(len(I.courses)):
                self.pc[(p,c)] = model.NewBoolVar("")
        # person P attends or teaches course C in slot S
        self.psc = {}
        for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
            for s in range(len(I.slots)):
                for c in range(len(I.courses)):
                    self.psc[(p,s,c)] = model.NewBoolVar("")
        # person P attends or teaches in slot S
        self.ps = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
                self.ps[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # person P occupied according to slot preferences in slot S
        self.ps_occupied = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
                self.ps_occupied[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # person P not available (teaches or bad slot preferences) in slot S
        self.ps_na = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
                self.ps_na[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # teacher T teaches on day D
        self.td = {}
        for d in range(len(I.days)):
            for t in range(len(I.teachers)):
                self.td[(t,d)] = model.NewBoolVar("TD:t%id%i" % (t,d))
        # person P is occupied (teaches or attends courses) on day D
        self.pd = {}
        for d in range(len(I.days)):
            for p in range(len(I.teachers)): # TODO people vs. teachers vs. teachers_active
                self.pd[(p,d)] = model.NewBoolVar("")
        # course C takes place in slot S
        self.cs = []
        for c in range(len(I.courses)):
            self.cs.append(model.NewIntVar(0, len(I.slots)-1, ""))
        # room R is in venue V
        self.rv = []
        for r in range(len(I.rooms)):
            self.rv.append(model.NewIntVar(0, len(I.venues)-1, ""))
            model.Add(self.rv[r] == I.Venues[I.rooms_venues[I.rooms[r]]])
        # teacher T teaches in slot S course C in venue V
        self.tscv = {}
        for t in range(len(I.teachers)):
            for s in range(len(I.slots)):
                for c in range(len(I.courses)):
                    for v in range(len(I.venues)):
                        self.tscv[(t,s,c,v)] = model.NewBoolVar("")
        # course C is active
        self.c_active = []
        for c in range(len(I.courses)):
            self.c_active.append(model.NewBoolVar(""))

        # teacher T teaches in venue V on day D
        # TODO do it wrt. attending courses - cannot teach in Koliste, attend in Mosilana, and teach again in Koliste
        self.tdv = {}
        for t in range(len(I.teachers)):
            for d in range(len(I.days)):
                for v in range(len(I.venues)):
                    self.tdv[(t,d,v)] = model.NewBoolVar("")

        # teacher T teaches course C in slot S iff course C takes place at slot S and is taught by teacher T
        # inferring CTS info
        for s in range(len(I.slots)):
            for c in range(len(I.courses)):
                hit = model.NewBoolVar("") # course C is at slot S
                model.Add(sum(self.src[(s,r,c)] for r in range(len(I.rooms))) == 1).OnlyEnforceIf(hit)
                model.Add(sum(self.src[(s,r,c)] for r in range(len(I.rooms))) == 0).OnlyEnforceIf(hit.Not())
                model.Add(self.cs[c] == s).OnlyEnforceIf(hit)
                # TODO when course is not active, we cannot require this
                #model.Add(self.cs[c] != s).OnlyEnforceIf(hit.Not())
                for t in range(len(I.teachers)):
                    model.AddBoolAnd([hit, self.tc[(t,c)]]).OnlyEnforceIf(self.tsc[(t,s,c)])
                    model.AddBoolOr([hit.Not(), self.tc[(t,c)].Not()]).OnlyEnforceIf(self.tsc[(t,s,c)].Not())
        # inferring TS info
        for s in range(len(I.slots)):
            for t in range(len(I.teachers)):
                model.Add(sum(self.tsc[(t,s,c)] for c in range(len(I.courses))) == 1).OnlyEnforceIf(self.ts[(t,s)])
                model.Add(sum(self.tsc[(t,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ts[(t,s)].Not())
        # construct AC info (person P attends course C)
        for P in I.people:
            p = I.Teachers[P]
            if P in I.input_data:
                courses_attend = I.input_data[P]["courses_attend"]
            else:
                courses_attend = []
                error(f"unexpected - no attendance info for person {P}")
            for c in range(len(I.courses)):
                if [x for x in courses_attend if I.courses[c].startswith(x)]:
                    model.Add(self.ac[(p,c)] == 1)
                else:
                    model.Add(self.ac[(p,c)] == 0)
        # construct PC info (person P attends or teaches course C)
        for P in I.people:
            p = I.Teachers[P]
            for c in range(len(I.courses)):
                model.AddBoolOr([self.tc[(p,c)], self.ac[(p,c)]]).OnlyEnforceIf(self.pc[(p,c)])
                model.AddBoolAnd([self.tc[(p,c)].Not(), self.ac[(p,c)].Not()]).OnlyEnforceIf(self.pc[(p,c)].Not())
        # inferring PSC info - person P attends or teaches course C in slot S
        for s in range(len(I.slots)):
            for c in range(len(I.courses)):
                hit = model.NewBoolVar("") # course C is at slot S
                model.Add(self.cs[c] == s).OnlyEnforceIf(hit)
                model.Add(self.cs[c] != s).OnlyEnforceIf(hit.Not())
                for P in I.people:
                    p = I.Teachers[P]
                    model.AddBoolAnd([hit, self.pc[(p,c)]]).OnlyEnforceIf(self.psc[(p,s,c)])
                    model.AddBoolOr([hit.Not(), self.pc[(p,c)].Not()]).OnlyEnforceIf(self.psc[(p,s,c)].Not())
        # inferring PS info - person P teaches or attends at slot S
        # * teaching
        # * attending course
        for s in range(len(I.slots)):
            for P in I.people:
                p = I.Teachers[P] # only teachers are people for now
#                teach_or_learn = model.NewBoolVar("")
#                occupied_elsewhere = model.NewBoolVar("")
                model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) >= 1).OnlyEnforceIf(self.ps[(p,s)])
                model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ps[(p,s)].Not())
#                model.Add(I.ts_pref[P][s] <= occ_thres).OnlyEnforceIf(occupied_elsewhere)
#                model.Add(I.ts_pref[P][s] > occ_thres).OnlyEnforceIf(occupied_elsewhere.Not())
#                model.AddBoolOr([teach_or_learn, occupied_elsewhere]).OnlyEnforceIf(self.ps[(p,s)])
#                model.AddBoolAnd([teach_or_learn.Not(), occupied_elsewhere.Not()]).OnlyEnforceIf(self.ps[(p,s)].Not())
                #model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 1).OnlyEnforceIf(self.ps[(p,s)])
                #model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ps[(p,s)].Not())
        # inferring TD info
        for d in range(len(I.days)):
            for t in range(len(I.teachers)):
                model.Add(sum(self.ts[(t,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) >= 1).OnlyEnforceIf(self.td[(t,d)])
                model.Add(sum(self.ts[(t,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) == 0).OnlyEnforceIf(self.td[(t,d)].Not())
        # inferring PD info
        for d in range(len(I.days)):
            for P in I.people:
                p = I.Teachers[P] # only teachers are people for now
                model.Add(sum(self.ps[(p,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) >= 1).OnlyEnforceIf(self.pd[(p,d)])
                model.Add(sum(self.ps[(p,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) == 0).OnlyEnforceIf(self.pd[(p,d)].Not())

        # when do we consider person occupied according to slot preferences
        occ_thres = 0
        for s in range(len(I.slots)):
            for P in I.people:
                p = I.Teachers[P] # only teachers are people for now
                model.Add(I.ts_pref[P][s] <= occ_thres).OnlyEnforceIf(self.ps_occupied[(p,s)])
                model.Add(I.ts_pref[P][s] > occ_thres).OnlyEnforceIf(self.ps_occupied[(p,s)].Not())

        for s in range(len(I.slots)):
            for P in I.people:
                p = I.Teachers[P] # only teachers are people for now
                model.AddBoolOr([self.ts[(p,s)], self.ps_occupied[(p,s)]]).OnlyEnforceIf(self.ps_na[(p,s)])
                model.AddBoolAnd([self.ts[(p,s)].Not(), self.ps_occupied[(p,s)].Not()]).OnlyEnforceIf(self.ps_na[(p,s)].Not())

        # inferring TDV info
        for s in range(len(I.slots)):
            for c in range(len(I.courses)):
                for v in range(len(I.venues)):
                    hit = model.NewBoolVar("") # course C is at slot S in venue V
                    model.Add(sum(self.src[(s,r,c)] for r in range(len(I.rooms)) if I.rooms_venues[I.rooms[r]] == I.venues[v]) == 1).OnlyEnforceIf(hit)
                    model.Add(sum(self.src[(s,r,c)] for r in range(len(I.rooms)) if I.rooms_venues[I.rooms[r]] == I.venues[v]) == 0).OnlyEnforceIf(hit.Not())
                    for t in range(len(I.teachers)):
                        model.AddBoolAnd([hit, self.tc[(t,c)]]).OnlyEnforceIf(self.tscv[(t,s,c,v)])
                        model.AddBoolOr([hit.Not(), self.tc[(t,c)].Not()]).OnlyEnforceIf(self.tscv[(t,s,c,v)].Not())
        for t in range(len(I.teachers)):
            for d in range(len(I.days)):
                for v in range(len(I.venues)):
                    model.Add(sum(self.tscv[(t,s,c,v)] for s in range(d*len(I.times),(d+1)*len(I.times)) for c in range(len(I.courses))) >= 1).OnlyEnforceIf(self.tdv[(t,d,v)])
                    model.Add(sum(self.tscv[(t,s,c,v)] for s in range(d*len(I.times),(d+1)*len(I.times)) for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.tdv[(t,d,v)].Not())
        # inferring CV info
        self.cv = []
        for c in range(len(I.courses)):
            self.cv.append(model.NewIntVar(0, len(I.venues)-1, ""))
            for v in range(len(I.venues)):
                hit = model.NewBoolVar("")
                model.Add(sum(self.src[(s,r,c)] for s in range(len(I.slots)) for r in range(len(I.rooms)) if I.rooms_venues[I.rooms[r]] == I.venues[v]) >= 1).OnlyEnforceIf(hit)
                model.Add(sum(self.src[(s,r,c)] for s in range(len(I.slots)) for r in range(len(I.rooms)) if I.rooms_venues[I.rooms[r]] == I.venues[v]) == 0).OnlyEnforceIf(hit.Not())
                model.Add(self.cv[c] == v).OnlyEnforceIf(hit)
                # TODO when course is not active, we cannot require this
                #model.Add(self.cv[c] != v).OnlyEnforceIf(hit.Not())

        # number of lessons teacher T teaches
        self.teach_num = {}
        for t in range(len(I.teachers)):
            self.teach_num[t] = model.NewIntVar(0, len(I.slots), "Tteach_num:%i" % t)
            model.Add(self.teach_num[t] == sum(self.tc[(t,c)] for c in range(len(I.courses))))
        # does teacher T teach at least one course?
        self.does_not_teach = []
        for t in range(len(I.teachers)):
            hit = model.NewBoolVar("")
            model.Add(self.teach_num[t] == 0).OnlyEnforceIf(hit)
            model.Add(self.teach_num[t] > 0).OnlyEnforceIf(hit.Not())
            self.does_not_teach.append(hit)
        # number of slots person P occupies (teaches or attends)
        self.occupied_num = {}
        for P in I.people:
            p = I.Teachers[P]
            self.occupied_num[p] = model.NewIntVar(0, len(I.slots), "")
            model.Add(self.occupied_num[p] == sum(self.ps[(p,s)] for s in range(len(I.slots))))

        # prevent teachers from teaching in two rooms in the same time
        for t in range(len(I.teachers)):
            for s in range(len(I.slots)):
                model.Add(sum(self.tsc[(t,s,c)] for c in range(len(I.courses))) <= 1)

        # one course takes place at one time in one room
        for c in range(len(I.courses)):
            # TODO this is probably the crucial spot to solve courses discrepancy
            if I.courses[c] not in I.COURSES_IGNORE:
                debug(f"Not ignoring one-place-time constraing for {I.courses[c]}")
                model.Add(sum(self.src[(s,r,c)] for s in range(len(I.slots)) for r in range(len(I.rooms))) == 1).OnlyEnforceIf(self.c_active[c])
                model.Add(sum(self.src[(s,r,c)] for s in range(len(I.slots)) for r in range(len(I.rooms))) == 0).OnlyEnforceIf(self.c_active[c].Not())
            else:
                # assert that I.courses contains only non-ignored courses
                error(f"Ignoring one-place-time constraing for {I.courses[c]}")

        # at one time in one room, there is maximum one course
        for s in range(len(I.slots)):
            for r in range(len(I.rooms)):
                model.Add(sum(self.src[(s,r,c)] for c in range(len(I.courses))) <= 1)

        # every regular course is taught by two teachers and solo course by one teacher
        for c in range(len(I.courses)):
            if I.courses[c] in I.COURSES_IGNORE:
                # assert that I.courses contains only non-ignored courses
                error(f"Course {I.courses[c]} should be ignored")
            elif I.courses[c] in I.courses_regular:
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers if T in I.teachers_lead) <= 1)
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers if T in I.teachers_follow) <= 1)
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers) == 2).OnlyEnforceIf(self.c_active[c])
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers) == 0).OnlyEnforceIf(self.c_active[c].Not())
            elif I.courses[c] in I.courses_solo:
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers) == 1).OnlyEnforceIf(self.c_active[c])
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers) == 0).OnlyEnforceIf(self.c_active[c].Not())
            elif I.courses[c] in I.courses_open:
                model.Add(sum(self.tc[(I.Teachers[T],c)] for T in I.teachers) == 0)
            else:
                assert(False)

        # SPECIFIC CONSTRAINTS

        # TODO remove, testing only
        #model.Add(self.c_active[I.Courses["Balboa Beginners"]] == 0)
        model.Add(self.c_active[I.Courses["Collegiate Shag 1"]] == 0)

        for C in I.courses_must_open:
            model.Add(self.c_active[I.Courses[C]] == 1)

        # unspecified teachers teach no courses
        for T in I.teachers:
            if T not in I.FAKE_TEACHERS:
                debug(f"Teacher max: {T} {I.t_util_max.get(T,-1)}")
                model.Add(sum(self.tc[(I.Teachers[T],c)] for c in range(len(I.courses))) <= I.t_util_max.get(T, 0))

#        # community teachers that must teach
#        for T in ["Zuzka", "Vojta-N.", "Míša-L.", "Kuba-B."]:
#            if I.t_util_max.get(T, 0) >= 1:
#                model.Add(sum(self.tc[(I.Teachers[T],c)] for c in range(len(I.courses))) >= 1)
#            else:
#                warn(f"community teacher {T} should teach, but has no utilization preferences")

        if I.tc_strict:
            debug("strict assignments present")
            strict_assignments = []
            for (T, Cs) in I.tc_strict.items():
                t = I.Teachers[T]
                for C in Cs:
                    c = I.Courses[C]
                    #strict_assignments.append(self.tc[(t,c)])
                    model.Add(self.tc[(t,c)] == 1).OnlyEnforceIf(self.c_active[c])
            #model.AddBoolAnd(strict_assignments)

        teachers_all = set(range(len(I.teachers)))
        for (C, Ts) in I.ct_possible.items():
            c = I.Courses[C]
            teachers_can = []
            for T in Ts:
                t = I.Teachers[T]
                teachers_can.append(t)
            teachers_not = teachers_all - set(teachers_can)
            # no other teacher can teach C
            model.Add(sum(self.tc[(t,c)] for t in teachers_not) == 0)

        for T1, T2 in I.tt_not_together:
            for c in range(len(I.courses)):
                model.Add(sum(self.tc[(t,c)] for t in [I.Teachers[T1], I.Teachers[T2]]) < 2)

        # TODO: this should be loosened, also wrt. attending
        # teacher T does not teach in two venues in the same day
        for t in range(len(I.teachers)):
            for d in range(len(I.days)):
                model.Add(sum(self.tdv[(t,d,v)] for v in range(len(I.venues))) <= 1)

        # strict courses schedule
        # nothing else happens in parallel with Teachers Training
        #model.Add(sum(self.src[(11,r,c)] for r in range(len(I.rooms)) for c in range(len(I.courses))) == 1)
        # Shag/Balboa open is AFTER Collegiate Shag 2 (combined with courses_same
        #model.Add(self.cs[I.Courses["Collegiate Shag 2"]]+1 == self.cs[I.Courses["Shag/Balboa Open Training"]])
        # PJ training must happen on Tuesday and Thursday
        model.Add(self.cs[I.Courses["Rhythm Pilots /1"]] == 10)
        model.Add(self.cs[I.Courses["Rhythm Pilots /2"]] == 11)
        model.AddAllowedAssignments([self.cs[I.Courses["Blues/Slow Open Training"]]], [[x] for x in [1, 2, 4, 5, 7, 8, 10, 11]])
        # Blues Open should not start at 17:30
        model.AddAllowedAssignments([self.cs[I.Courses["Blues/Slow Open Training"]]], [[x] for x in [1, 2, 4, 5, 7, 8, 10, 11]])
        # Teachers Training in the evening in case it's longer and on Monday or Wednesday (due to Rhythm Pilots)
        model.Add(self.cs[I.Courses["Teachers Training"]] == 8)
        model.Add(self.cs[I.Courses["Blues 1"]] == 8)
        #model.AddAllowedAssignments([self.cs[I.Courses["Teachers Training"]]], [[x] for x in [2, 8]])
        #model.AddAllowedAssignments([self.cs[I.Courses["Teachers Training"]]], [[x] for x in [2, 5, 8, 11]])

        # teachers HARD slot preferences
        for T in I.teachers:
            if T in I.ts_pref: # TODO what about people without preferences?
                for s, v in enumerate(I.ts_pref[T]):
                    if v == 0:
                        model.Add(self.ts[(I.Teachers[T], s)] == 0)
            else:
                if T not in I.FAKE_TEACHERS:
                    warn(f"No slot preferences for teacher {T}")

        # same courses should not happen in same days and also not in same times
        # it should probably not be a strict limitation, but it is much easier to write
        for Cs in I.courses_different:
            daylist = [] # days
            timelist = [] # times
            assert(2 <= len(Cs) <= min(len(I.days), len(I.times)))
            for C in Cs:
                day = model.NewIntVar(0, len(I.days)-1, "")
                time = model.NewIntVar(0, len(I.times)-1, "")
                model.AddDivisionEquality(day, self.cs[I.Courses[C]], len(I.times))
                model.AddModuloEquality(time, self.cs[I.Courses[C]], len(I.times))
                daylist.append(day)
                timelist.append(time)
            model.AddAllDifferent(daylist)
            model.AddAllDifferent(timelist)

        # courses that should not happen in same days
        for Cs in I.courses_diffday:
            daylist = [] # days
            assert(2 <= len(Cs) <= len(I.days))
            for C in Cs:
                day = model.NewIntVar(0, len(I.days)-1, "")
                model.AddDivisionEquality(day, self.cs[I.Courses[C]], len(I.times))
                #model.AddModuloEquality(time, self.cs[I.Courses[C]], len(I.times))
                daylist.append(day)
            model.AddAllDifferent(daylist)

        # courses that should follow each other in the same day in the same venue
        for Cs in I.courses_same:
            daylist = [] # days
            timelist = [] # times
            venuelist = [] # venues
            assert(2 <= len(Cs) <= len(I.times))
            for C in Cs:
                day = model.NewIntVar(0, len(I.days)-1, "")
                time = model.NewIntVar(0, len(I.times)-1, "")
                venue = model.NewIntVar(0, len(I.venues)-1, "")
                model.AddDivisionEquality(day, self.cs[I.Courses[C]], len(I.times))
                model.AddModuloEquality(time, self.cs[I.Courses[C]], len(I.times))
                model.Add(venue == self.cv[I.Courses[C]])
                daylist.append(day)
                timelist.append(time)
                venuelist.append(venue)
            model.AddAllowedAssignments(daylist, [[d] * len(Cs) for d in range(len(I.days))])
            model.AddAllowedAssignments(venuelist, [[v] * len(Cs) for v in range(len(I.venues))])
            if len(Cs) == len(I.times):
                # filling whole day
                model.AddAllDifferent(timelist)
            elif len(Cs) == len(I.times) - 1:
                # filling 2 out of three slots
                assert(len(Cs) == 2)
                model.AddAllowedAssignments(timelist, [ [0,1], [1,0], [1,2], [2,1] ])
            else:
                # should not happen
                assert(False)

        for (C, R) in I.cr_not.items():
            model.Add(sum(self.src[(s,I.Rooms[R],I.Courses[C])] for s in range(len(I.slots))) == 0)

        for (C, R) in I.cr_strict.items():
            c = I.Courses[C]
            model.Add(sum(self.src[(s,I.Rooms[R],c)] for s in range(len(I.slots))) == 1).OnlyEnforceIf(self.c_active[c])
            model.Add(sum(self.src[(s,I.Rooms[R],c)] for s in range(len(I.slots))) == 0).OnlyEnforceIf(self.c_active[c].Not())


        # OPTIMIZATION

        penalties = {} # penalties data (model variables)
        penalties_analysis = {} # deeper analysis functions for penalties

        for (name, coeff) in I.PENALTIES.items():
            if coeff == 0:
                info(f"Penalties: skipping '{name}'")
                continue
            if name == "utilization":
                # teaching should be as close to preferences as possible
                penalties_utilization = []
                for T in I.t_util_ideal:
                    t = I.Teachers[T]
                    util_ideal = I.t_util_ideal[T]
                    MAX_DIFF = 10 # set according to preferences form
                    min_diff = -MAX_DIFF
                    max_diff = MAX_DIFF
                    util_diff = model.NewIntVar(min_diff, max_diff, "")
                    model.Add(util_diff == M.teach_num[t] - util_ideal)
                    util_diff_abs = model.NewIntVar(0, abs(MAX_DIFF), "")
                    model.AddAbsEquality(util_diff_abs, util_diff)
                    util_diff_abs_sq = model.NewIntVar(0, abs(MAX_DIFF)**2, "")
                    model.AddMultiplicationEquality(util_diff_abs_sq, [util_diff_abs, util_diff_abs])
                    penalties_utilization.append(util_diff_abs_sq)
                penalties[name] = penalties_utilization
                def analysis(src, tc):
                    result = []
                    for T in I.teachers:
                        if T in I.t_util_ideal:
                            t = I.Teachers[T]
                            util_ideal = I.t_util_ideal[T]
                            util_real = sum(tc[(t,c)] for c in range(len(I.courses)))
                            if util_real != util_ideal:
                                debug(f"analysis utilization - {T} wanted {util_ideal}, teaches {util_real}")
                                result.append(f"{T}/{util_real}r-{util_ideal}i")
                    return result
                penalties_analysis[name] = analysis
            elif name == "days":
                # nobody should come more days then necessary
                penalties_days = []
                for t in range(len(I.teachers)):
                    teaches_days = model.NewIntVar(0, len(I.days), "TD:%i" % t)
                    model.Add(teaches_days == sum(M.td[(t,d)] for d in range(len(I.days))))
                    teaches_minus_1 = model.NewIntVar(0, len(I.days), "Tm1:%i" % t)
                    teaches_some = model.NewBoolVar("Ts:%i" % t)
                    model.Add(M.teach_num[t] >= 1).OnlyEnforceIf(teaches_some)
                    model.Add(M.teach_num[t] == 0).OnlyEnforceIf(teaches_some.Not())
                    model.Add(teaches_minus_1 == M.teach_num[t] - 1).OnlyEnforceIf(teaches_some)
                    model.Add(teaches_minus_1 == 0).OnlyEnforceIf(teaches_some.Not())
                    should_teach_days = model.NewIntVar(0, len(I.days), "TDs:%i" % t)
                    model.AddDivisionEquality(should_teach_days, teaches_minus_1, len(I.times)) # -1 to compensate rounding down
                    days_extra = model.NewIntVar(0, len(I.days), "Tdd:%i" % t)
                    model.Add(days_extra == teaches_days - should_teach_days - 1).OnlyEnforceIf(teaches_some) # -1 to compensate rounding down
                    model.Add(days_extra == 0).OnlyEnforceIf(teaches_some.Not())
                    days_extra_sq = model.NewIntVar(0, len(I.days)**2, "Tdds:%i" % t)
                    model.AddMultiplicationEquality(days_extra_sq, [days_extra, days_extra])
                    penalties_days.append(days_extra_sq)
                penalties[name] = penalties_days
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        cs = []
                        for c in range(len(I.courses)):
                            if tc[(t,c)]:
                                cs.append(c)
                        n_courses = sum(tc[(t,c)] for c in range(len(I.courses)))
                        assert(len(cs) == n_courses)
                        n_days = 0
                        for d in range(len(I.days)):
                            if sum(src[(s,r,c)] for s in range(d*len(I.times), (d+1)*len(I.times)) for r in range(len(I.rooms)) for c in cs):
                                n_days += 1
                        if n_days*len(I.times) - n_courses >= len(I.times):
                            result.append(f"{I.teachers[t]} {n_courses}c/{n_days}d")
                    return result
                penalties_analysis[name] = analysis
            elif name == "occupied_days":
                # nobody should come more days then necessary - including attending courses
                penalties_occupied_days = []
                for P in I.people:
                    p = I.Teachers[P]
                    occupied_days = model.NewIntVar(0, len(I.days), "")
                    model.Add(occupied_days == sum(M.pd[(p,d)] for d in range(len(I.days))))
                    occupied_some = model.NewBoolVar("")
                    model.Add(M.occupied_num[p] >= 1).OnlyEnforceIf(occupied_some)
                    model.Add(M.occupied_num[p] == 0).OnlyEnforceIf(occupied_some.Not())
                    occupied_minus_1 = model.NewIntVar(0, len(I.days), "")
                    model.Add(occupied_minus_1 == M.occupied_num[p] - 1).OnlyEnforceIf(occupied_some)
                    model.Add(occupied_minus_1 == 0).OnlyEnforceIf(occupied_some.Not())
                    should_occupy_days = model.NewIntVar(0, len(I.days), "")
                    model.AddDivisionEquality(should_occupy_days, occupied_minus_1, len(I.times)) # -1 to compensate rounding down
                    occupied_days_extra = model.NewIntVar(0, len(I.days), "")
                    model.Add(occupied_days_extra == occupied_days - should_occupy_days - 1).OnlyEnforceIf(occupied_some) # -1 to compensate rounding down
                    model.Add(occupied_days_extra == 0).OnlyEnforceIf(occupied_some.Not())
                    occupied_days_extra_sq = model.NewIntVar(0, len(I.days)**2, "")
                    model.AddMultiplicationEquality(occupied_days_extra_sq, [occupied_days_extra, occupied_days_extra])
                    penalties_occupied_days.append(occupied_days_extra_sq)
                penalties[name] = penalties_occupied_days
                def analysis(src, tc):
                    result = []
                    for P in I.people:
                        p = I.Teachers[P]
                        occupied_courses = []
                        for c in range(len(I.courses)):
                            if tc[(p,c)] or (P in I.input_data and [x for x in I.input_data[P]["courses_attend"] if I.courses[c].startswith(x)]):
                                occupied_courses.append(c)
                        n_courses = len(occupied_courses)
                        n_days = 0
                        for d in range(len(I.days)):
                            if sum(src[(s,r,c)] for s in range(d*len(I.times), (d+1)*len(I.times)) for r in range(len(I.rooms)) for c in occupied_courses):
                                n_days += 1
                        if n_days*len(I.times) - n_courses >= len(I.times):
                            result.append(f"{P} {n_courses}c/{n_days}d")
                            #debug(f"Person {P} occupied_courses: {', '.join([I.courses[c] for c in occupied_courses])}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "split":
                # teacher should not wait between lessons
                penalties_split = []
                for t in range(len(I.teachers)):
                    days_split = model.NewIntVar(0, len(I.days), "TDsplit:%i" % t)
                    tsplits = []
                    for d in range(len(I.days)):
                        # tsplit == True iff teacher t teaches just the first and the last course in day d
                        tsubsplits = []
                        for i in range(len(I.times)):
                            tsubsplit = model.NewBoolVar("tsubsplit:t%id%ii%i" % (t,d,i))
                            model.Add(sum(M.ts[(t,s)] for s in [d*len(I.times)+i]) == 1).OnlyEnforceIf(tsubsplit)
                            model.Add(sum(M.ts[(t,s)] for s in [d*len(I.times)+i]) == 0).OnlyEnforceIf(tsubsplit.Not())
                            tsubsplits.append(tsubsplit)
                        tsplit = model.NewBoolVar("tsplit:t%id%i" % (t,d))
                        model.AddBoolAnd([tsubsplits[0], tsubsplits[1].Not(), tsubsplits[2]]).OnlyEnforceIf(tsplit)
                        model.AddBoolOr([tsubsplits[0].Not(), tsubsplits[1], tsubsplits[2].Not()]).OnlyEnforceIf(tsplit.Not())
                        tsplits.append(tsplit)
                    model.Add(days_split == sum(tsplits))
                    penalties_split.append(days_split)
                penalties[name] = penalties_split
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        cs = []
                        for c in range(len(I.courses)):
                            if tc[(t,c)]:
                                cs.append(c)
                        n = 0
                        for d in range(len(I.days)):
                            if (
                                    sum(src[(d*len(I.times),r,c)]  for r in range(len(I.rooms)) for c in cs) >= 1
                                    and sum(src[(d*len(I.times)+1,r,c)]  for r in range(len(I.rooms)) for c in cs) == 0
                                    and sum(src[(d*len(I.times)+2,r,c)]  for r in range(len(I.rooms)) for c in cs) >= 1
                                    ):
                                n += 1
                        if n > 0:
                            result.append(f"{I.teachers[t]}/{n}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "slotpref_bad":
                # slots preferences
                penalties_slotpref_bad = []
                for T in I.teachers:
                    if T in I.ts_pref:
                        prefs = I.ts_pref[T]
                        if set([1,2]) <= set(prefs) or set([1,3]) <= set(prefs):
                            # teacher T strongly prefers some slots over others
                            slots_bad = [s for s in range(len(I.slots)) if prefs[s] == 1]
                            penalties_slotpref_bad.append(sum(M.ts[(I.Teachers[T],s)] for s in slots_bad))
                penalties[name] = penalties_slotpref_bad
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        T = I.teachers[t]
                        cs = []
                        for c in range(len(I.courses)):
                            if tc[(t,c)]:
                                cs.append(c)
                        bad_slots = []
                        n = 0
                        if T in I.ts_pref:
                            prefs = I.ts_pref[T]
                            if set([1,2]) <= set(prefs) or set([1,3]) <= set(prefs):
                                for s in range(len(I.slots)):
                                    if I.ts_pref[T][s] == 1:
                                        if sum(src[(s,r,c)] for r in range(len(I.rooms)) for c in cs) >= 1:
                                            bad_slots.append(s)
                                            n += 1
                        if bad_slots:
                            debug(f"analysis slotpref_bad - teacher {T} courses {cs} bad_slots {bad_slots}")
                            result.append(f"{T}/{n}-{','.join([str(s) for s in bad_slots])}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "slotpref_slight":
                # slots preferences
                penalties_slotpref_slight = []
                for T in I.teachers:
                    if T in I.ts_pref:
                        prefs = I.ts_pref[T]
                        if set([2,3]) <= set(prefs):
                            # teacher T slightly prefers some slots over others
                            slots_bad = [s for s in range(len(I.slots)) if prefs[s] == 2]
                            penalties_slotpref_slight.append(sum(M.ts[(I.Teachers[T],s)] for s in slots_bad))
                penalties[name] = penalties_slotpref_slight
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        T = I.teachers[t]
                        cs = []
                        for c in range(len(I.courses)):
                            if tc[(t,c)]:
                                cs.append(c)
                        bad_slots = []
                        n = 0
                        if T in I.ts_pref:
                            prefs = I.ts_pref[T]
                            if set([2,3]) <= set(prefs):
                                for s in range(len(I.slots)):
                                    if I.ts_pref[T][s] == 2:
                                        if sum(src[(s,r,c)] for r in range(len(I.rooms)) for c in cs) >= 1:
                                            bad_slots.append(s)
                                            n += 1
                        if bad_slots:
                            debug(f"analysis slotpref_slight - teacher {T} courses {cs} bad_slots {bad_slots}")
                            result.append(f"{T}/{n}-{','.join([str(s) for s in bad_slots])}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "coursepref_bad":
                # slots preferences
                penalties_coursepref = []
                for T in I.teachers:
                    if T in I.tc_pref:
                        spv = set(I.tc_pref[T].values())
                        if set([1,2]) <= spv or set([1,3]) <= spv:
                            # teacher T strongly prefers some courses over others
                            courses_bad = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 1]
                            debug(f"courses_bad {T}: {courses_bad}")
                            penalties_coursepref.append(sum(M.tc[(I.Teachers[T],I.Courses[C])] for C in courses_bad))
                penalties[name] = penalties_coursepref
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        T = I.teachers[t]
                        courses_bad = []
                        if T in I.tc_pref:
                            spv = set(I.tc_pref[T].values())
                            if set([1,2]) <= spv or set([1,3]) <= spv:
                                # teacher T strongly prefers some courses over others
                                courses_bad = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 1 and tc[(t,I.Courses[C])]]
                        if courses_bad:
                            debug(f"analysis coursepref_bad - teacher {T} courses {courses_bad}")
                            result.append(f"{T}/{len(courses_bad)}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "coursepref_slight":
                # slots preferences
                penalties_coursepref = []
                for T in I.teachers:
                    if T in I.tc_pref:
                        if set([2,3]) <= set(I.tc_pref[T].values()):
                            # teacher T strongly prefers some courses over others
                            courses_bad = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 2]
                            penalties_coursepref.append(sum(M.tc[(I.Teachers[T],I.Courses[C])] for C in courses_bad))
                penalties[name] = penalties_coursepref
                def analysis(src, tc):
                    result = []
                    for t in range(len(I.teachers)):
                        T = I.teachers[t]
                        courses_bad = []
                        if T in I.tc_pref:
                            if set([2,3]) <= set(I.tc_pref[T].values()):
                                # teacher T strongly prefers some courses over others
                                courses_bad = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 2 and tc[(t,I.Courses[C])]]
                        if courses_bad:
                            debug(f"analysis coursepref_slight teacher {T} courses {courses_bad}")
                            result.append(f"{T}/{len(courses_bad)}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "faketeachers":
                penalties_faketeachers = []
                # fake teachers
                for T in I.FAKE_TEACHERS:
                    if T in I.teachers:
                        penalties_faketeachers.append(sum(M.tc[(I.Teachers[T],c)] for c in range(len(I.courses))))
                penalties[name] = penalties_faketeachers
            elif name == "everybody_teach":
                penalties_everybody_teach = []
                # fake teachers
                for T in I.teachers_active:
                    if T in I.teachers:
                        penalties_everybody_teach.append(M.does_not_teach[I.Teachers[T]])
                    else:
                        warn(f"Active teacher {T} not among considered teachers!")
                penalties[name] = penalties_everybody_teach
            elif name == "mosilana": # penalty for not using koliste
                util_koliste = model.NewIntVar(0, 2*len(I.slots), "") # utilization of Koliste
                model.Add(util_koliste == sum(M.src[(s,r,c)] for s in range(len(I.slots)) for r in range(len(I.rooms)) if I.rooms_venues[I.rooms[r]] == "koliste" for c in range(len(I.courses))))
                free_koliste = model.NewIntVar(0, 2*len(I.slots), "") # free slots in Koliste
                model.Add(free_koliste == 2*len(I.slots)-util_koliste-1) # -1 for Teachers Training
                penalties[name] = [free_koliste]
            elif name == "attend_free": # penalty if interested in attending cannot attend (they teach something else in the same time)
                # courses that some teachers would like to attend
                courses_attend = [I.input_data[T]["courses_attend"] for T in I.input_data]
                courses_attend = [item for sl in courses_attend for item in sl if item != ""] # flatten sublists
                courses_attend = list(set(courses_attend)) # unique course names
                debug(f"attend_free: courses_attend {courses_attend}")
                penalties_attend_free = []
                for C in courses_attend:
                    teachers_attend = []
                    for T in I.input_data:
                        if C in I.input_data[T]["courses_attend"]:
                            teachers_attend.append(T)
                    debug(f"attend_free: course {C}: {', '.join(teachers_attend)}")
                    #t = I.Teachers[T]
                    for s in range(len(I.slots)):
                        hit = model.NewBoolVar("")
                        model.Add(M.cs[I.Courses[C]] == s).OnlyEnforceIf(hit)
                        model.Add(M.cs[I.Courses[C]] != s).OnlyEnforceIf(hit.Not())
                        penalty_slot = model.NewIntVar(0, len(teachers_attend), "") # penalty for the slot
                        model.Add(penalty_slot == sum(M.ps_na[(I.Teachers[T],s)] for T in teachers_attend)).OnlyEnforceIf(hit)
                        model.Add(penalty_slot == 0).OnlyEnforceIf(hit.Not())
                        penalties_attend_free.append(penalty_slot)
                penalties[name] = penalties_attend_free
            elif name == "teach_together": # penalty if interested in teaching with Ts but teaches with noone
                penalties_teach_together = []
                # teachers with teach_together preferences
                for T in I.tt_together:
                    debug(f"teach_together: {T} + {I.tt_together[T]}")
                    t = I.Teachers[T]
                    success_list = []
                    for c in range(len(I.courses)):
                        hit_self = model.NewBoolVar("")
                        hit_other = model.NewBoolVar("")
                        success = model.NewBoolVar("")
                        model.Add(M.tc[(t,c)] == 1).OnlyEnforceIf(hit_self)
                        model.Add(M.tc[(t,c)] == 0).OnlyEnforceIf(hit_self.Not())
                        model.Add(sum(M.tc[(I.Teachers[To],c)] for To in I.tt_together[T]) >= 1).OnlyEnforceIf(hit_other)
                        model.Add(sum(M.tc[(I.Teachers[To],c)] for To in I.tt_together[T]) == 0).OnlyEnforceIf(hit_other.Not())
                        model.AddBoolAnd([hit_self, hit_other]).OnlyEnforceIf(success)
                        model.AddBoolOr([hit_self.Not(), hit_other.Not()]).OnlyEnforceIf(success.Not())
                        success_list.append(success)
                    nobody = model.NewBoolVar("")
                    model.Add(sum(success_list) == 0).OnlyEnforceIf(nobody)
                    model.Add(sum(success_list) >= 1).OnlyEnforceIf(nobody.Not())
                    penalties_teach_together.append(nobody)
                penalties[name] = penalties_teach_together
                def analysis(src, tc):
                    result = []
                    for T in I.tt_together:
                        t = I.Teachers[T]
                        teachers_prefered = [I.Teachers[To] for To in I.tt_together[T]]
                        teach_courses = [c for c in range(len(I.courses)) if tc[(t,c)]]
                        success_courses = []
                        for c in teach_courses:
                            if sum(tc[to,c] for to in teachers_prefered) >= 1:
                                success_courses.append(c)
                        #success_courses = [c for c in teach_courses for to in teachers_prefered if sum([(to,c)]) >= 1]
                        #debug(f"analysis teach_together: teacher {T} prefers {', '.join([I.teachers[x] for x in teachers_prefered])}; teaches {', '.join([I.courses[x] for x in teach_courses])}; success in: {[I.courses[x] for x in success_courses]}")
                        debug(f"analysis teach_together: teacher {T} prefers {', '.join([I.teachers[x] for x in teachers_prefered])}; success in: {[I.courses[x] for x in success_courses]}")
                        if not success_courses:
                            result.append(f"{T}")
                    return result
                penalties_analysis[name] = analysis

        self.penalties = penalties
        self.penalties_analysis = penalties_analysis
        penalties_values = []
        for (name, l) in penalties.items():
            penalties_values.append(I.PENALTIES[name] * sum(l))

        model.Minimize(sum(penalties_values))

    def print_stats(self):
        print(self.model.ModelStats())

    # INNER CLASS
    class ContinuousSolutionPrinter(cp_model.CpSolverSolutionCallback):
        def __init__(self, M, I):
            self.count = 0
            self.M = M
            self.I = I
            cp_model.CpSolverSolutionCallback.__init__(self)

        def OnSolutionCallback(self):
            I = self.I
            M = self.M
            self.count += 1
            result_src = {}
            for s in range(len(I.slots)):
                for r in range(len(I.rooms)):
                    for c in range(len(I.courses)):
                            result_src[(s,r,c)] = self.Value(M.src[(s,r,c)])
            result_tc = {}
            for t in range(len(I.teachers)):
                for c in range(len(I.courses)):
                    result_tc[(t,c)] = self.Value(M.tc[(t,c)])
            for P in I.people:
                p = I.Teachers[P]
                teach_courses = [I.courses[c] for c in range(len(I.courses)) if self.Value(M.tc[(p,c)])]
                ta_courses = [I.courses[c] for c in range(len(I.courses)) if self.Value(M.pc[(p,c)])]
                attend_courses = list(set(ta_courses) - set(teach_courses))
                debug(f"PSPD: {P} teaches {', '.join(teach_courses)}")
                debug(f"PSPD: {P} attends {', '.join(attend_courses)}")
                debug(f"PSPD: {P} teaches or attends {', '.join(ta_courses)}")
                na = "".join(["1" if self.Value(M.ps_na[(p,s)]) else "0" for s in range(len(I.slots))])
                ps = "".join(["1" if self.Value(M.ps[(p,s)]) else "0" for s in range(len(I.slots))])
                ts = "".join(["1" if self.Value(M.ts[(p,s)]) else "0" for s in range(len(I.slots))])
                os = "".join(["1" if self.Value(M.ps_occupied[(p,s)]) else "0" for s in range(len(I.slots))])
                #for s in range(len(slots)):
                    #debug(f"sum(self.Value(M.cs[(I.Courses[C],s)]) for C in attend_courses)")
                As = "".join(["1" if any([self.Value(M.cs[(I.Courses[C])]) == s for C in attend_courses]) else "0" for s in range(len(I.slots))])
                days = "".join(["1" if self.Value(M.pd[(p,d)]) else "0" for d in range(len(I.days))])
                debug(f"PSPD: na {na}")
                debug(f"PSPD: os {os}")
                debug(f"PSPD: ts {ts}")
                debug(f"PSPD: As {As}")
                debug(f"PSPD: ps {ps}")
                debug(f"ps/pd analysis: {P :<9} os {os} ts {ts} as {As} ps {ps} na {na} num {self.Value(M.occupied_num[p])} days {days}")
#                m += " slots "
#                for s in range(len(I.slots)):
#                    if self.Value(M.ps[(p,s)]):
#                        m += "1"
#                    else:
#                        m += "0"
#                m += " num "
#                m += f"{self.Value(M.occupied_num[p])}"
#                m += " days "
#                for d in range(len(I.days)):
#                    if self.Value(M.pd[(p,d)]):
#                        m += "1"
#                    else:
#                        m += "0"
#                debug(m)
            result_penalties = {}
            # FIXME how to access penalties?
            for (name, l) in M.penalties.items():
                v = sum([self.Value(p) for p in l])
                coeff = I.PENALTIES[name]
                result_penalties[name] = (coeff, v)
            print(f"No: {self.count}")
            print(f"Wall time: {self.WallTime()}")
            #print(f"Branches: {self.NumBranches()}")
            #print(f"Conflicts: {self.NumConflicts()}")
            def print_solution(src, tc, penalties, penalties_analysis, objective=None, utilization=True):
                if objective:
                    print(f"Objective value: {objective}")
                for s in range(len(I.slots)):
                    for r in range(len(I.rooms)):
                        for c in range(len(I.courses)):
                            if src[(s,r,c)]:
                                Ts = []
                                if I.courses[c] in I.courses_open:
                                    Ts.append("OPEN")
                                elif I.courses[c] in I.courses_solo:
                                    for t in range(len(I.teachers)):
                                        #if solver.Value(tc[(t,c)]):
                                        if tc[(t,c)]:
                                            Ts.append(I.teachers[t])
                                            break
                                elif I.courses[c] in I.courses_regular:
                                    for t in range(len(I.teachers)):
                                        if tc[(t,c)]:
                                            Ts.append(I.teachers[t])
                                if len(Ts) == 2 and (Ts[0] in I.teachers_follow or Ts[1] in I.teachers_lead):
                                    Ts[0], Ts[1] = Ts[1], Ts[0]
                                if len(Ts) == 2:
                                    Ts_print = f"{Ts[0] :<9}+ {Ts[1]}"
                                else:
                                    Ts_print = f"{Ts[0]}"
                                #print(f"{I.slots[s]: <11}{I.rooms[r]: <5}{'+'.join(Ts): <19}{I.courses[c]}")
                                print(f"{I.slots[s]: <11}{I.rooms[r]: <5}{Ts_print: <21}{I.courses[c]}")
                if penalties:
                    print("Penalties:")
                    total = 0
                    for (name, t) in penalties.items():
                        coeff, v = t
                        total += coeff * v
                        if v == 0 or name not in penalties_analysis:
                            print(f"{name}: {v} * {coeff} = {v*coeff}")
                        else:
                            print(f"{name}: {v} * {coeff} = {v*coeff} ({', '.join(penalties_analysis[name](src, tc))})")
                if utilization:
                    debug("UTILIZATION:")
                    tn = {}
                    #for t in range(len(I.teachers)):
                        #tn[I.teachers[t]] = sum(tc[t,c] for c in range(len(I.courses)))
                    for T in I.teachers_active:
                        tn[T] = sum(tc[I.Teachers[T],c] for c in range(len(I.courses)))
                    for v in sorted(set(tn.values())):
                        print(f"{v}: {', '.join(t for t in tn if tn[t] == v)}")
                print(f"TOTAL: {total}")

            print_solution(result_src, result_tc, result_penalties, M.penalties_analysis, self.ObjectiveValue())
            print()

    def solve(self):
        self.print_stats()
        print()

        solver = cp_model.CpSolver()
        #solver.parameters.max_time_in_seconds = 20.0
        status = solver.SolveWithSolutionCallback(self.model, self.ContinuousSolutionPrinter(self, self.I))
        statusname = solver.StatusName(status)
        print(f"Solving finished in {solver.WallTime()} seconds with status {status} - {statusname}")
        if statusname not in ["FEASIBLE", "OPTIMAL"]:
            error(f"Solution NOT found - status {statusname}")

        print()
        print(f"Teachers' utilization:")
        for n in range(len(self.I.slots)):
            Ts = []
            for T in self.I.teachers_active:
                if solver.Value(self.teach_num[self.I.Teachers[T]]) == n:
                    Ts.append(T)
            if Ts:
                print(f"{n}: {' '.join(Ts)}")


def parse(argv=None):
    if argv is None:
        argv = sys.argv
    debug(f"argv: {argv}")

    if len(argv) > 2:
        error(f"Too many arguments: {argv}")
    elif len(argv) == 2:
        return argv[1]
    else:
        return None

def main():
    #set_verbose()

    infile = parse()

    # all input information
    input = Input()
    input.init(infile)

    # model construction
    model = Model()
    model.init(input)

    # run the solver
    model.solve()

if __name__ == "__main__":
    main()
