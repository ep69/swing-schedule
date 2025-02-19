#!/usr/bin/env python3

import sys
import csv
import argparse
import pprint
import regex

from ortools.sat.python import cp_model

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

def stop():
    print(f"STOP ... Execution halted for debugging purposes")
    sys.exit(100)

class Input:
    def init(self, teachers_csv, penalties={}, students_csv=None, extra_courses=[], excluded_teachers=[]):
        self.init_constants()
        self.init_form(teachers_csv, students_csv, extra_courses, excluded_teachers)
        self.init_teachers()
        self.init_rest()
        self.init_penalties(penalties)

    def init_form(self, teachers_csv, students_csv=None, extra_courses=[], excluded_teachers=[]):
        self.init_teachers_form(teachers_csv, extra_courses, excluded_teachers)
        if students_csv is not None:
            self.init_students_form(students_csv)
        info(pprint.pformat(self.input_data))

    courses_extra = {}

    def add_extra_course(self, course, typ, teachers):
        debug(f"add_extra_course: {course} type {typ} teachers {', '.join(teachers)}")
        if typ not in ("open", "solo", "regular"):
            error(f"add_extra_course: unknown type {typ}")
        self.courses_extra[course] = {}
        self.courses_extra[course]["type"] = typ
        self.courses_extra[course]["teachers"] = teachers

    def init_constants(self):
        #self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]
        self.days = ["Mon", "Tue", "Wed", "Thu"]
        self.Days = {}
        for i, D in enumerate(self.days):
            self.Days[D] = i

        #self.times = ["17:30-18:40", "18:50-20:00", "20:10-21:20"]
        self.times = ["17:30", "18:50", "20:10"]

        self.slots = [ d + " " + t for d in self.days for t in self.times ]

        self.rooms = [
            #"big",
            #"small",
            "k3",
            "k4",
        ]
        self.Rooms = {}
        for i, R in enumerate(self.rooms):
            self.Rooms[R] = i

        self.venues = ["koliste"]
        self.Venues = {}
        for i, V in enumerate(self.venues):
            self.Venues[V] = i

        self.rooms_venues = {
            "k3": "koliste",
            "k4": "koliste",
            }

        self.courses_open = [
            "Shag/Balboa Open Training",
            "Lindy/Charleston Open Training",
            #"Teachers Training", # TODO
            "Rhythm Pilots /1",
            "Rhythm Pilots /2",
            #"Blues/Slow Open Training",
            ]
        self.courses_solo = [
            "Solo Int",
            ]
        self.courses_regular = [
            "LH Newbies /1",
            "LH Newbies /2",
            #"LH Newbies /3",

            "LH Beg /BottomsUp",
            "LH Beg /SureThing",
            "LH Beg /New",

            "LH Beg/Int /JiveAtFive",
            "LH Beg/Int /Sandu",

            "LH Int /SmoothOne",
            "LH Int /Perdido",
            #"LH Int /BasieBeat",
            "LH Int /6weeks",

            "LH Int/Adv",

            "LH Adv",

            #"Airsteps 1",

            "Collegiate Shag Beg",
            "Collegiate Shag Beg/Int",
            "Collegiate Shag Int",

            #"Balboa Beg",
            "Balboa Beg/Int",
            "Balboa Int",

            #"Blues Beg",
            "Blues Int",
            "Blues Solo",
            ]
        self.COURSES_IGNORE = [
            "Solo Beg",
            "Slow Balboa (2nd half)",
            "Saint Louis Shag Beg",
            "Saint Louis Shag Beg/Int",
            "Saint Louis Shag Int",

            "Zumba s Tomem",
        ]
        for C, d in self.courses_extra.items():
            debug(f"init_constants: extra course {C}")
            typ = d["type"]
            teachers = d["teachers"]
            if typ == "open":
                self.courses_open.append(C)
            elif typ == "solo":
                self.courses_solo.append(C)
            elif typ == regular:
                self.courses_regular.append(C)
            else:
                error(f"init_constants: unknown extra course {C} type {typ}")
        self.courses_open = list(set(self.courses_open)-set(self.COURSES_IGNORE))
        debug(f"init_constants: courses_open: {', '.join(self.courses_open)}")
        self.courses_solo = list(set(self.courses_solo)-set(self.COURSES_IGNORE))
        debug(f"init_constants: courses_solo: {', '.join(self.courses_solo)}")
        self.courses_regular = list(set(self.courses_regular)-set(self.COURSES_IGNORE))
        debug(f"init_constants: courses_regular: {', '.join(self.courses_regular)}")
        self.courses = self.courses_regular + self.courses_solo + self.courses_open
        debug(f"init_constants: courses: {', '.join(self.courses)}")
        self.Courses = {}
        for (i, c) in enumerate(self.courses):
            self.Courses[c] = i

    def init_teachers(self):
        debug("Initializing teachers")
        debug(f"Active teachers: {self.teachers}")
        self.teachers_lead = [T for T in self.teachers if self.input_data[T]["role"] == "lead"]
        debug(f"Leaders: {self.teachers_lead}")
        self.teachers_lead_primary = [T for T in self.teachers if self.input_data[T]["role"] in ("lead", "both/lead")]
        debug(f"Primary leaders: {self.teachers_lead_primary}")
        self.teachers_follow = [T for T in self.teachers if self.input_data[T]["role"] == "follow"]
        debug(f"Follows: {self.teachers_follow}")
        self.teachers_follow_primary = [T for T in self.teachers if self.input_data[T]["role"] in ("follow", "both/follow")]
        debug(f"Primary follows: {self.teachers_follow_primary}")
        self.teachers_both = [T for T in self.teachers if self.input_data[T]["role"].startswith("both/")]
        debug(f"Both: {self.teachers_both}")
        assert(set(self.teachers) >= set(self.teachers_lead + self.teachers_follow + self.teachers_both))
        assert(len(set(self.teachers_lead) & set(self.teachers_follow)) == 0)
        assert(len(set(self.teachers_lead) & set(self.teachers_both)) == 0)
        assert(len(set(self.teachers_both) & set(self.teachers_follow)) == 0)

        self.Teachers = {}
        for (i, t) in enumerate(self.teachers):
            self.Teachers[t] = i

        # caring only about teachers for now
        self.people = self.teachers # FIXME


    def translate_teacher_name(self, name):
        result = name.strip()
        result = result.replace(" ", "-")
        debug(f"Translated '{name}' to '{result}'")
        return result

    def is_course_type(self, Cspecn, Cgen):
        # ugly hack for theme courses
        if (Cspecn.startswith("Balboa - theme course") and Cgen.startswith("Balboa Int")) \
                or (Cspecn.startswith("Collegiate Shag - theme course") and Cgen.startswith("Collegiate Shag Int")) \
                or (Cspecn.startswith("Blues - theme course") and Cgen.startswith("Blues Int")) \
                or (Cspecn.startswith("Blues Solo") and Cgen.startswith("Blues Int")) \
                or False:
            return True

        courses_with_subprefix = [
            "LH Beg",
            "LH Int",
            "Collegiate Shag Beg",
            "Collegiate Shag Int",
            "Balboa Beg",
            "Saint Louis Shag Beg",
        ]
        Cspec = regex.sub(" /[A-Za-z0-9-]+$", "", Cspecn)
        result = None
        if Cspec.endswith("English"):
            result = Cgen == Cspec
        elif Cgen in courses_with_subprefix:
            result = Cgen == Cspec
        else:
            result = Cspec.startswith(Cgen)
        #debug(f"is_course_type: '{Cspecn}' '{Cspec}' '{Cgen}' {result}")
        return result

    def check_course(self, course):
        for Cspec in self.courses:
            if self.is_course_type(Cspec, course):
                #debug(f"check_course: course preference {course} maps, e.g to {Cspec}")
                return True
        warn(f"check_course: unknown course: '{course}'") # TODO
        return False

    def read_teachers_input(self, infile=None, extra_courses=[], excluded_teachers=[]):
        debug(f"read_teachers_input: Excluded teachers: {', '.join(excluded_teachers)}")
        if infile:
            debug(f"Opening {infile}")
            f = open(infile, mode="r")
        else: # use stdin
            f = sys.stdin

        result = {}
        self.teachers= []
        input_courses = [] # courses
        n = 0

        reader = csv.DictReader(f)
        for row in reader:
            n += 1
            if n == 1:
                # check courses when handling the first row
                columns = list(row.keys())
                for col in columns:
                    debug(f"Column: {col}")
                    if col.startswith("What courses would you like to teach in your primary role?"):
                        course = col.split("[")[1].split("]")[0]
                        if course in self.COURSES_IGNORE:
                            continue
                        if self.check_course(course):
                            input_courses.append(course)
                for C in extra_courses:
                    if C not in input_courses:
                        input_courses.append(C)
                debug(f"Input courses (F): {sorted(input_courses)}")
                debug(f"Input courses (C): {sorted(self.courses)}")
                # does not make sense (general vs. specific course names)
                #debug(f"Input courses (diff): {set(self.courses)-set(input_courses)-set(self.COURSES_IGNORE)}")
            # handle the input data
            debug("")
            who = row["Who are you?"]
            if who.startswith("IGNORE") or not any(row.values()): # explicitly ignored row or empty row
                debug(f"read_teachers_input: skipping row {row}")
                continue
            if who in excluded_teachers:
                info(f"Skipping teacher {who}")
                continue
            name = self.translate_teacher_name(who)
            debug(f"Reading: name {name}")
            if name in result:
                warn(f"Re-reading answers for {name}")
                del result[name]
#            # check that we know the teacher
#            found = False
#            for T,_ in self.TEACHERS:
#                if name == T:
#                    found = True
#                    break
#            if not found:
#                debug(f"Teachers: {self.TEACHERS}")
#                error(f"Unknown teacher {name}")
            d = {}
            d["type"] = "teacher"
            d["ncourses_ideal"] = int(row["How many courses would you ideally like to teach?"])
            d["ncourses_max"] = int(row["How many courses are you able to teach at most?"])
            d["ndays_max"] = int(row["How many days are you able to teach at most?"])
            if d["ndays_max"] == 0 or d["ncourses_max"] == 0:
                # skip
                info(f"Skipping {who} - does not want to teach courses")
                continue
            if row["Are you fine with teaching in English?"] == "Yes":
                d["english"] = True
            else:
                d["english"] = False
            slots = []
            for day in ["Mon", "Tue", "Wed", "Thu"]:
                for time in ["17:30", "18:50", "20:10"]:
                    slots.append(int(row[f"What days and times are convenient for you? [{day} {time}]"][0]))
            d["slots"] = slots
            ICW = { # inconvenience weigths
                "no problemo": 0,
                "slightly": 1,
                "quite": 3,
                "very": 6,
            }
            ICN = { # inconvenience names
                "Teaching undesirable course (\"1 - only if needed\")": "bad_course",
                "Teaching in undesirable time (\"1 - only if needed\")": "bad_time",
                "Not teaching with any preferred person": "no_person",
                "Teaching 2 courses in 2 days": "2c2d",
                "Teaching 3 courses in 1 day": "3c1d",
                "Waiting between courses": "split",
                "Not teaching any \"3 - perfect!\" course": "no_perfect",
                "Teaching 1 more course than desired": "1more",
                "Teaching 2 more courses than desired": "2more",
                "Teaching 1 less course than desired": "1less",
                "Not teaching at all": "not_teaching",
#                "Teaching during Teachers' Training": "tt",
                "Not respecting an explicit wish from the last question": "special",
            }
            ic = {} # inconvenience data
            for ic_name, ic_id in ICN.items():
                val = ICW[row[f"How inconvenient are following situations for you? [{ic_name}]"]]
                ic[ic_id] = val

            # role
            role = row["What is your dancing role?"]
            if role == "Lead only":
                role = "lead"
            elif role == "Follow only":
                role = "follow"
            elif role.startswith("Primarily lead"):
                role = "both/lead"
            elif role.startswith("Primarily follow"):
                role = "both/follow"
            else:
                error(f"Unknown role {role}")
            d["role"] = role

            courses_teach_primary = {}
            for C in input_courses:
                #debug(f"course {C}")
#                if C == "Rhythm Pilots":
#                    pass
#                elif C == "Charleston 2": # TODO
#                    pass
#                else:
                if C.startswith("Airsteps"):
                    C_answer = "Airsteps"
                else:
                    C_answer = C
                answer = row[f"What courses would you like to teach in your primary role? [{C_answer}]"]
                if not answer:
                    warn(f"{name} provided no answer for {C}, defaulting to 0")
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
                courses_teach_primary[C] = answer_num
                #courses_teach_primary[C] = int(row[f"What courses would you like to teach? [{C}]"][0])
            for C, ed in self.courses_extra.items():
                if name in ed["teachers"]:
                    courses_teach_primary[C] = 2
                else:
                    courses_teach_primary[C] = 0
            d["courses_teach_primary"] = courses_teach_primary
            courses_teach_secondary = []
            d["courses_teach_secondary"] = [c.strip() for c in row["What courses would you like to teach in your secondary role?"].split(",") if c]
# FIXME new structure
#            bestpref = row["What preference is the most important for you?"]
#            if bestpref.startswith("Time"):
#                d["bestpref"] = "time"
#            elif bestpref.startswith("Course"):
#                d["bestpref"] = "course"
#            elif bestpref.startswith("People"):
#                d["bestpref"] = "person"
#            elif bestpref.startswith("None"):
#                d["bestpref"] = "none"
#            else:
#                error(f"Unknow best pref: {bestpref}")
#            d["courses_attend"] = [a.strip() for a in row["What courses and trainings would you like to attend?"].split(",") if a]
#            assert("" not in d["courses_attend"])
#            #debug(f"Courses attend before: {d['courses_attend']}")
#            for c in set(d["courses_attend"]):
#                if c in self.COURSES_IGNORE:
#                    debug(f"courses_attend: removing: {c}")
#                    d["courses_attend"].remove(c)
#                else:
#                    debug(f"NOT removing: {c}")
#            #debug(f"Courses attend after: {d['courses_attend']}")
#            if "LH 4" in d["courses_attend"]:
#                d["courses_attend"].remove("LH 4")
#                d["courses_attend"].append("LH 4 - more technical")
#                d["courses_attend"].append("LH 4 - more philosophical")
#            if "Solo" in d["courses_attend"]:
#                d["courses_attend"].remove("Solo")
#                d["courses_attend"].append("Solo - choreography")
#                d["courses_attend"].append("Solo - improvisation")
#            for c in d["courses_attend"]:
#                self.check_course(c)
            teach_together = row["Who would you like to teach with?"]
            d["teach_together"] = [self.translate_teacher_name(name.strip()) for name in teach_together.split(",") if name]
            if name in d["teach_together"]:
                d["teach_together"].remove(name)
            d["teach_not_together"] = [self.translate_teacher_name(name) for name in row["Are there any people you cannot teach with?"].split(",") if name]
            if name in d["teach_not_together"]:
                d["teach_not_together"].remove(name)
            if name not in self.teachers:
                debug(f"Adding {name} to result")
                self.teachers.append(name)
            else:
                warn(f"Teacher {name} already known, probably re-reading")
            def ic_filter(old):
                # TODO
                new = old
                if old["no_perfect"] and 3 not in courses_teach_primary.values():
                    warn(f"ic_filter: {name}: no perfect course, zeroing.")
                    new["no_perfect"] = 0
                return old
            d["ic"] = ic_filter(ic)
            result[name] = d
        debug(f"Number of lines: {n}")
        debug(f"Result: {'|'.join(result)}")
        if len(self.teachers) != len(set(self.teachers)):
            error(f"Unexpected teachers, probably duplicates in {', '.join(sorted(self.teachers))}")
        #self.teachers = list(set(self.teachers))
        debug(f"Active teachers: {self.teachers}")

        if f is not sys.stdin:
            f.close()

        #print(f"Column names: {columns}")
        return result

    def init_teachers_form(self, infile=None, extra_courses=[], excluded_teachers=[]):
        teachers_data = self.read_teachers_input(infile, extra_courses, excluded_teachers)
        debug("TEACHERS' ANSWERS:")
        debug(pprint.pformat(teachers_data))
        self.input_data = teachers_data

    def init_students_form(self, infile):
        debug(f"Reading students' preferences")
        students_data = self.read_students_input(infile)
        debug("STUDENTS' ANSWERS:")
        debug(pprint.pformat(students_data))
        for k in students_data:
            self.input_data[k] = students_data[k]

    def translate_course_cs_en(self, course):
        if course == "Autentický pohyb":
            Cstud = "Authentic Dance"
        else:
            Cstud = course

        result = None
        for C in self.courses:
            if self.is_course_type(C, Cstud):
                #debug(f"student course {course} maps, e.g., to {C}")
                result = Cstud
        #if course in self.courses:
            #result = course
#        elif course == "LH 4 - techničtější":
#            result = "LH 4"
#        elif course == "LH 4 - filozofičtější":
#            result = "LH 4"
#        elif course == "Solo - improvizace":
#            result = "Solo"
#        elif course == "Solo - choreografie":
#            result = "Solo"
        if Cstud in self.COURSES_IGNORE:
            result = Cstud
        if not result:
            result = "IGNORE"
            warn(f"Unknown student course '{course}'")
        return result

    def read_students_input(self, csv_file):
        debug(f"Opening students CSV: {csv_file}")
        f = open(csv_file, mode="r")
        reader = csv.DictReader(f)

        n = 0
        result = {}
        for row in reader:
            n += 1
            if n == 1:
                # check courses when handling the first row
                debug("First row")
            # handle the input data
            name = f"stud{n}"
            debug(f"Reading student: {name}")
            d = {}
            d["type"] = "student"
            provided_id = row["Kdo jsi, pokud to chceš říct?"]
            if provided_id:
                d["provided_id"] = provided_id
            if provided_id == "IGNORE":
                continue
            slots = []
            for day in ("Pondělí", "Úterý", "Středa", "Čtvrtek"):
                daycell = row[f"Jaké dny a časy ti absolutně NEvyhovují? [{day}]"]
                for time in ("17:30 - 18:40", "18:50 - 20:00", "20:10 - 21:20"):
                    if time in daycell:
                        slots.append(0)
                    else:
                        slots.append(2)
            debug(f"Slots: {''.join(str(s) for s in slots)}")
            d["slots"] = slots

            answer = row[f"V jaké roli si zapisuješ kurzy?"]
            if answer in ("Lead", "Follow"):
                d["role"] = answer.lower()
            else:
                warn(f"Ignoring non-standard role '{answer}'")
                continue

            answer = row[f"Jaké kurzy si chceš zapsat?"]
            courses_attend = [c.strip() for c in answer.split(",") if c]
            debug(f"Chosen courses: '{','.join(courses_attend)}'")
            if not courses_attend:
                warn(f"No prefered courses for student {name}, ignoring the student")
                continue
                #courses_attend = []
            if len(courses_attend) > 3:
                warn(f"Student {name} wants more than 3 courses")
            courses_attend = [self.translate_course_cs_en(Ccs) for Ccs in courses_attend]
            courses_attend = [C for C in courses_attend if C != "IGNORE"]
            d["courses_attend"] = []
            for C in courses_attend:
                if C in self.COURSES_IGNORE:
                    debug(f"read_students_input: ignoring course explicitly {C}")
                elif not self.check_course(C):
                    debug(f"read_students_input: ignoring course implicitly {C}")
                else:
                    d["courses_attend"].append(C)
            debug(f"read_students_input: courses_attend: {d['courses_attend']}")
            result[name] = d

        debug(f"Student CSV rows: {n}")

        return result

    # SPECIFIC HARD CONSTRAINTS
    def init_rest(self):
        # HARD teacher T can teach maximum N courses
        self.t_util_max = {}
        # teacher T wants to teach N courses
        self.t_util_ideal = {}
        # HARD teacher T can teach maximum N days
        self.t_days_max = {}
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
        self.ct_possible_lead = {}
        self.ct_possible_follow = {}
        #assert(set(self.teachers) == set(self.teachers_active))
        for C in self.courses:
            if C not in self.courses_open:
                self.ct_possible[C] = list(set(self.teachers))
            if C in self.courses_regular:
                # we will start with primary people and add sceondary later
                self.ct_possible_lead[C] = list(self.teachers_lead_primary)
                self.ct_possible_follow[C] = list(self.teachers_follow_primary)
            #else:
                #self.ct_possible_lead[C] = []
                #self.ct_possible_follow[C] = []
        # course C must not take place in room R
        # TODO improve - some of these actualy fake course-venues constraints
        self.cr_not = {}
        # course C must take place in room R
        # PJ in Mosilana
        self.cr_strict = {}
        # course Cx that must open
        self.courses_must_open = []
        # course Cx that must not open
        self.courses_not_open = []
        # strict C -> slot mapping
        self.courses_slots_strict = {}
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

        #self.custom_penalties = []

        # translate input data to variables understood by the rest of the script
        for T in set(self.teachers):
            debug(f"Person {T}")
            data = self.input_data[T]
            if data["type"] != "teacher":
                error(f"Bad person type? {T}")
                continue
            self.t_util_max[T] = data["ncourses_max"]
            self.t_days_max[T] = data["ndays_max"]
            if self.t_util_max[T] == 0 or self.t_days_max[T] == 0:
                # could be warning, it is probably legit to just say 0 max_courses/madays
                # but if it happens, logic should be moved to CSV parsing
                error(f"Removing (probably too late) the inactive teacher: {T}")
                self.teachers.remove(T)
            else:
                self.t_util_ideal[T] = data["ncourses_ideal"]
                courses_teach_primary = data["courses_teach_primary"]
                courses_pref = {}
                for (Cgen, v) in courses_teach_primary.items():
                    #debug(f"Cgen: {Cgen}")
                    for Cspec in self.courses_regular + self.courses_solo:
                        #debug(f"Cspec 1: {Cspec}")
                        if self.is_course_type(Cspec, Cgen):
                            #debug(f"Cspec 2: {Cspec}")
                            courses_pref[Cspec] = v
                            debug(f"courses_pref[{Cspec}] = {v}")
                            if v == 0:
                                #debug(f"Cspec 3: {Cspec}")
                                # HARD preference
                                if Cspec in self.courses_regular:
                                    if T in self.teachers_lead_primary:
                                        if T in self.ct_possible_lead[Cspec]:
                                            self.ct_possible_lead[Cspec].remove(T)
                                            #self.ct_possible_lead[Cspec] = list(set(self.ct_possible_lead[Cspec]) - set([T]))
                                            assert(T not in self.ct_possible_lead[Cspec])
                                    elif T in self.teachers_follow_primary:
                                        if T in self.ct_possible_follow[Cspec]:
                                            self.ct_possible_follow[Cspec].remove(T)
                                            #self.ct_possible_follow[Cspec] = list(set(self.ct_possible_follow[Cspec]) - set([T]))
                                            assert(T not in self.ct_possible_follow[Cspec])
                                    else:
                                        error(f"No primary role for teacher {T}")
                                elif Cspec in self.courses_solo:
                                    if T in self.ct_possible[Cspec]:
                                        self.ct_possible[Cspec].remove(T)
                                        assert(T not in self.ct_possible[Cspec])
                                else:
                                    error(f"Course {Cspec} is neither regular nor solo")
                            elif v <= 3:
                                pass
                            else:
                                error(f"Unexpected primary course preference value: teacher {T} course {Cgen} value {v}")
                for Cgen in data["courses_teach_secondary"]:
                    for Cspec in self.courses_regular: # does not make sense for solo courses
                        if self.is_course_type(Cspec, Cgen):
                                if T in self.teachers_lead_primary:
                                    if T not in self.ct_possible_follow[Cspec]:
                                        debug(f"Appending to {Cspec}: follow {T}")
                                        self.ct_possible_follow[Cspec].append(T)
                                        assert(T in self.ct_possible_follow[Cspec])
                                elif T in self.teachers_follow_primary:
                                    if T not in self.ct_possible_lead[Cspec]:
                                        debug(f"Appending to {Cspec}: lead {T}")
                                        self.ct_possible_lead[Cspec].append(T)
                                        assert(T in self.ct_possible_lead[Cspec])
                                else:
                                    error(f"No primary role for teacher {T}")
                self.tc_pref[T] = courses_pref
                for d in data["teach_not_together"]:
                    if d in self.input_data:
                        self.tt_not_together.append((T, d))
                    else:
                        info(f"Inactive teacher {d} (tt_not_together), ignoring")
                l = []
                for d in data["teach_together"]:
                    if d in self.input_data:
                        l.append(d)
                    else:
                        info(f"Inactive teacher {d} (tt_together), ignoring")
                self.tt_together[T] = l
            self.ts_pref[T] = data["slots"]
            assert(len(self.ts_pref[T]) == len(self.slots))
        debug("CT_POSSIBLE:")
        for C in self.courses_regular + self.courses_solo:
            debug(f"ct_possible {C}: {', '.join(self.ct_possible[C])}")
            if C in self.courses_regular:
                debug(f"ct_possible_lead {C}: {', '.join(self.ct_possible_lead[C])}")
                debug(f"ct_possible_follow {C}: {', '.join(self.ct_possible_follow[C])}")
            # attendance done directly through input_data

    def init_penalties(self, penalties):
        # "name" -> coeff
        self.PENALTIES = {
#            # workload
#            "utilization": 25, # squared
#            # placement
#            "teach_days": 75,
#            "teach_three": 75,
#            "occupied_days": 25, # squared
#            "split": 50,
#            # slots
#            "slotpref_bad": 80,
#            "slotpref_slight": 20,
#            # courses
#            "coursepref_bad": 80,
#            "coursepref_slight": 20,
#            "attend_free": 50,
#            # person-related
#            "teach_together": 25,
#            # overall schedule
            "courses_closed": 1, #50, # FIXME
#            # serious penalties
#            "everybody_teach": 50,
            # students
            "student": 24, # absolutely unhappy student
            "nice": 50,
            "custom": 400,
            "heavy": 1000000,
            "very_heavy": 100000000,
            "teacher": 1000,
        }
        #self.BOOSTER = 2

        # user input penalties
        for k, v in penalties.items():
            if k not in self.PENALTIES:
                error(f"Unknown penalty {k}")
            else:
                self.PENALTIES[k] = v

class Result:
    pass


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
        # course C is taught by teacher T as a leader
        self.tc_lead = {}
        for c in range(len(I.courses)):
            for t in range(len(I.teachers)):
                self.tc_lead[(t,c)] = model.NewBoolVar("")
        # course C is taught by teacher T as a follow
        self.tc_follow = {}
        for c in range(len(I.courses)):
            for t in range(len(I.teachers)):
                self.tc_follow[(t,c)] = model.NewBoolVar("")
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
        for p in range(len(I.teachers)): # TODO people vs. teachers
            for c in range(len(I.courses)):
                self.ac[(p,c)] = model.NewBoolVar("")
        # person P teaches or attends course C
        self.pc = {}
        for p in range(len(I.teachers)): # TODO people vs. teachers
            for c in range(len(I.courses)):
                self.pc[(p,c)] = model.NewBoolVar("")
        # person P attends or teaches course C in slot S
        self.psc = {}
        for p in range(len(I.teachers)): # TODO people vs. teachers
            for s in range(len(I.slots)):
                for c in range(len(I.courses)):
                    self.psc[(p,s,c)] = model.NewBoolVar("")
        # person P attends or teaches in slot S
        self.ps = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers
                self.ps[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # person P occupied according to slot preferences in slot S
        self.ps_occupied = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers
                self.ps_occupied[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # person P not available (teaches or bad slot preferences) in slot S
        self.ps_na = {}
        for s in range(len(I.slots)):
            for p in range(len(I.teachers)): # TODO people vs. teachers
                self.ps_na[(p,s)] = model.NewBoolVar("PS:p%is%i" % (p,s))
        # teacher T teaches on day D
        self.td = {}
        for d in range(len(I.days)):
            for t in range(len(I.teachers)):
                self.td[(t,d)] = model.NewBoolVar("TD:t%id%i" % (t,d))
        # person P is occupied (teaches or attends courses) on day D
        self.pd = {}
        for d in range(len(I.days)):
            for p in range(len(I.teachers)): # TODO people vs. teachers
                self.pd[(p,d)] = model.NewBoolVar("")
        # course C takes place in slot S
        self.cs = []
        for c in range(len(I.courses)):
            self.cs.append(model.NewIntVar(-1, len(I.slots)-1, ""))
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
                # we use -1 as a value for non-active (c_active) courses
                model.Add(self.cs[c] != s).OnlyEnforceIf(hit.Not())
                for t in range(len(I.teachers)):
                    model.AddBoolAnd([hit, self.tc[(t,c)]]).OnlyEnforceIf(self.tsc[(t,s,c)])
                    model.AddBoolOr([hit.Not(), self.tc[(t,c)].Not()]).OnlyEnforceIf(self.tsc[(t,s,c)].Not())
        for c in range(len(I.courses)):
            C = I.courses[c]
            if C in I.courses_regular:
                # regular course => one lead, one follow
                model.Add(sum(self.tc_lead[(t,c)] for t in range(len(I.teachers))) == 1).OnlyEnforceIf(self.c_active[c])
                model.Add(sum(self.tc_follow[(t,c)] for t in range(len(I.teachers))) == 1).OnlyEnforceIf(self.c_active[c])
                for t in range(len(I.teachers)):
                    # TODO why XOr does not work?
                    #model.AddBoolXOr([self.tc_lead[(t,c)], self.tc_follow[(t,c)]]).OnlyEnforceIf(self.tc[(t,c)])
                    model.AddBoolOr([self.tc_lead[(t,c)], self.tc_follow[(t,c)]]).OnlyEnforceIf(self.tc[(t,c)])
                    model.AddBoolAnd([self.tc_lead[(t,c)].Not(), self.tc_follow[(t,c)].Not()]).OnlyEnforceIf(self.tc[(t,c)].Not())
            else:
                # non-regular course => no roles
                model.Add(sum(self.tc_lead[(t,c)] for t in range(len(I.teachers))) == 0)
                model.Add(sum(self.tc_follow[(t,c)] for t in range(len(I.teachers))) == 0)
        # inferring TS info
        for s in range(len(I.slots)):
            for t in range(len(I.teachers)):
                model.Add(sum(self.tsc[(t,s,c)] for c in range(len(I.courses))) == 1).OnlyEnforceIf(self.ts[(t,s)])
                model.Add(sum(self.tsc[(t,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ts[(t,s)].Not())
#        # construct AC info (person P attends course C)
#        for P in I.people:
#            p = I.Teachers[P]
#            if P in I.input_data:
#                courses_attend = I.input_data[P]["courses_attend"]
#            else:
#                courses_attend = []
#                error(f"unexpected - no attendance info for person {P}")
#            for c in range(len(I.courses)):
#                if [x for x in courses_attend if I.is_course_type(I.courses[c], x)]: # TODO course types
#                    model.Add(self.ac[(p,c)] == 1)
#                else:
#                    model.Add(self.ac[(p,c)] == 0)
#        # construct PC info (person P attends or teaches course C)
#        for P in I.people:
#            p = I.Teachers[P]
#            for c in range(len(I.courses)):
#                model.AddBoolOr([self.tc[(p,c)], self.ac[(p,c)]]).OnlyEnforceIf(self.pc[(p,c)])
#                model.AddBoolAnd([self.tc[(p,c)].Not(), self.ac[(p,c)].Not()]).OnlyEnforceIf(self.pc[(p,c)].Not())
#        # inferring PSC info - person P attends or teaches course C in slot S
#        for s in range(len(I.slots)):
#            for c in range(len(I.courses)):
#                hit = model.NewBoolVar("") # course C is at slot S
#                model.Add(self.cs[c] == s).OnlyEnforceIf(hit)
#                model.Add(self.cs[c] != s).OnlyEnforceIf(hit.Not())
#                for P in I.people:
#                    p = I.Teachers[P]
#                    model.AddBoolAnd([hit, self.pc[(p,c)]]).OnlyEnforceIf(self.psc[(p,s,c)])
#                    model.AddBoolOr([hit.Not(), self.pc[(p,c)].Not()]).OnlyEnforceIf(self.psc[(p,s,c)].Not())
#        # inferring PS info - person P teaches or attends at slot S
#        # * teaching
#        # * attending course
#        for s in range(len(I.slots)):
#            for P in I.people:
#                p = I.Teachers[P] # only teachers are people for now
##                teach_or_learn = model.NewBoolVar("")
##                occupied_elsewhere = model.NewBoolVar("")
#                model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) >= 1).OnlyEnforceIf(self.ps[(p,s)])
#                model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ps[(p,s)].Not())
##                model.Add(I.ts_pref[P][s] <= occ_thres).OnlyEnforceIf(occupied_elsewhere)
##                model.Add(I.ts_pref[P][s] > occ_thres).OnlyEnforceIf(occupied_elsewhere.Not())
##                model.AddBoolOr([teach_or_learn, occupied_elsewhere]).OnlyEnforceIf(self.ps[(p,s)])
##                model.AddBoolAnd([teach_or_learn.Not(), occupied_elsewhere.Not()]).OnlyEnforceIf(self.ps[(p,s)].Not())
#                #model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 1).OnlyEnforceIf(self.ps[(p,s)])
#                #model.Add(sum(self.psc[(p,s,c)] for c in range(len(I.courses))) == 0).OnlyEnforceIf(self.ps[(p,s)].Not())
        # inferring TD info
        for d in range(len(I.days)):
            for t in range(len(I.teachers)):
                model.Add(sum(self.ts[(t,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) >= 1).OnlyEnforceIf(self.td[(t,d)])
                model.Add(sum(self.ts[(t,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) == 0).OnlyEnforceIf(self.td[(t,d)].Not())
#        # inferring PD info
#        for d in range(len(I.days)):
#            for P in I.people:
#                p = I.Teachers[P] # only teachers are people for now
#                model.Add(sum(self.ps[(p,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) >= 1).OnlyEnforceIf(self.pd[(p,d)])
#                model.Add(sum(self.ps[(p,s)] for s in range(d*len(I.times), (d+1)*len(I.times))) == 0).OnlyEnforceIf(self.pd[(p,d)].Not())
#
        # when do we consider person occupied according to slot preferences
        occ_thres = 0
        for s in range(len(I.slots)):
            for P in I.people:
                # FIXME
                p = I.Teachers[P] # only teachers are people for now
                model.Add(I.ts_pref[P][s] <= occ_thres).OnlyEnforceIf(self.ps_occupied[(p,s)])
                model.Add(I.ts_pref[P][s] > occ_thres).OnlyEnforceIf(self.ps_occupied[(p,s)].Not())

        for s in range(len(I.slots)):
            for P in I.people:
                p = I.Teachers[P] # only teachers are people for now
                model.AddBoolOr([self.ts[(p,s)], self.ps_occupied[(p,s)]]).OnlyEnforceIf(self.ps_na[(p,s)])
                model.AddBoolAnd([self.ts[(p,s)].Not(), self.ps_occupied[(p,s)].Not()]).OnlyEnforceIf(self.ps_na[(p,s)].Not())
#
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

        # prevent teachers from teaching two courses at the same time
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

        self.penalties = {} # penalties data (model variables)
        self.penalties["heavy"] = {}
        self.penalties["very_heavy"] = {}
        self.penalties["custom"] = {}
        self.penalties["nice"] = {}

        for T in I.teachers:
            debug(f"Teacher max: {T} {I.t_util_max.get(T,-1)}")
            # unspecified teachers teach no courses
            self.add_heavy(f"{T}-ncourses", sum(self.tc[(I.Teachers[T],c)] for c in range(len(I.courses))) <= I.t_util_max.get(T, 0))
            self.add_heavy(f"{T}-ndays", sum(self.td[(I.Teachers[T],d)] for d in range(len(I.days))) <= I.t_days_max.get(T, 0))

        info(f"Courses that must open: {', '.join(I.courses_must_open)}")
        for C in I.courses_must_open:
            self.add_heavy(f"mustopen-{C}", self.c_active[I.Courses[C]] == 1)

        for C in I.courses_not_open:
            self.add_heavy(f"notopen-{C}", self.c_active[I.Courses[C]] == 0)

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
        for (C, Ts) in I.ct_possible_lead.items():
            c = I.Courses[C]
            teachers_can = []
            for T in Ts:
                t = I.Teachers[T]
                teachers_can.append(t)
            teachers_not = teachers_all - set(teachers_can)
            # no other teacher can teach C
            model.Add(sum(self.tc_lead[(t,c)] for t in teachers_not) == 0)
        for (C, Ts) in I.ct_possible_follow.items():
            c = I.Courses[C]
            teachers_can = []
            for T in Ts:
                t = I.Teachers[T]
                teachers_can.append(t)
            teachers_not = teachers_all - set(teachers_can)
            # no other teacher can teach C
            model.Add(sum(self.tc_follow[(t,c)] for t in teachers_not) == 0)

        for T1, T2 in set(I.tt_not_together):
            for c in range(len(I.courses)):
                #model.Add(sum(self.tc[(t,c)] for t in [I.Teachers[T1], I.Teachers[T2]]) < 2)
                self.add_heavy(f"tt_not/{T1}+{T2}/{I.courses[c]}".replace(" ", "-"), sum(self.tc[(t,c)] for t in [I.Teachers[T1], I.Teachers[T2]]) < 2)

        # TODO: this should be loosened, also wrt. attending
        # teacher T does not teach in two venues in the same day
        for t in range(len(I.teachers)):
            for d in range(len(I.days)):
                model.Add(sum(self.tdv[(t,d,v)] for v in range(len(I.venues))) <= 1)

        # teachers HARD slot preferences
        for T in I.teachers:
            if T in I.ts_pref: # TODO what about people without preferences?
                for s, v in enumerate(I.ts_pref[T]):
                    if v == 0:
                        model.Add(self.ts[(I.Teachers[T], s)] == 0)
            else:
                warn(f"No slot preferences for teacher {T}")

        # strict course -> slot mapping
        debug(f"I.courses_slots_strict: {I.courses_slots_strict}")
        for C, s in I.courses_slots_strict.items():
            self.add_heavy(f"cs-strict-{C}", self.cs[I.Courses[C]] == s)

        # same courses should not happen in same days and also not in same times
        # it should probably not be a strict limitation, but it is much easier to write
        # TODO could be turned into heavy penalty, but probably later in the process (after init_penalties)
        debug(f"courses_different")
        for Cs in I.courses_different:
            debug(f"courses_different: Cs: {Cs}")
            daylist = [] # days
            timelist = [] # times
            courselist = []
            #assert(2 <= len(Cs) <= min(len(I.days), len(I.times)))
            assert(2 <= len(Cs))
            if len(Cs) > 3:
                error(f"courses_different does not work for more than 3 courses, to be fixed")
            for C in Cs:
                c = I.Courses[C]
                debug(f"courses_different: C: {C} ({c})")
                day = model.NewIntVar(-1, len(I.days)-1, "")
                time = model.NewIntVar(-1, len(I.times)-1, "")
                model.AddDivisionEquality(day, self.cs[c], len(I.times))
                model.AddModuloEquality(time, self.cs[c], len(I.times))
                debug(f"courses_different: courselist: {courselist}")
                for i in range(len(courselist)):
                    co = courselist[i]
                    debug(f"courses_different: co: {co} ({I.courses[co]})")
                    D = daylist[i]
                    T = timelist[i]
                    model.Add(day != D).OnlyEnforceIf([self.c_active[c], self.c_active[co]])
                    model.Add(time != T).OnlyEnforceIf([self.c_active[c], self.c_active[co]])
                courselist.append(c)
                daylist.append(day)
                timelist.append(time)
            debug("")
            #old version of these constraints
            #model.AddAllDifferent(daylist)
            #model.AddAllDifferent(timelist)
        #stop()

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

        self.custom_penalties = {}
        #self.heavy_penalties = {}


    def init_penalties(self):
        debug(f"Model: init_penalties")
        I = self.I
        M = self
        model = self.model

        # OPTIMIZATION

        self.wish = {}
        for T in I.Teachers:
            self.wish[T] = model.NewBoolVar("")

        penalties_analysis = {} # deeper analysis functions for penalties # TODO remove

        for (name, coeff) in I.PENALTIES.items():
            if coeff == 0:
                warn(f"Penalties: skipping '{name}'")
                continue
            if name == "teacher":
                self.penalties["teacher"] = {}
                total_teacher = coeff

                for T in I.Teachers:
                    t = I.Teachers[T]
                    self.penalties["teacher"][T] = {}

                    # precompute real penalty weigths
                    ic = I.input_data[T]["ic"]
                    total_ic = sum(ic.values())
                    if total_ic == 0:
                        # this is the case when a person does not mind anything
                        total_ic = 1
                    icw = {} # weigths
                    for k, v in ic.items():
                        icw[k] = total_teacher * v // total_ic
                        debug(f"teacher {T} pen. {k}: {ic[k]} -> {icw[k]}")

                    # utilization

                    # utilization - general
                    util_ideal = I.t_util_ideal[T]
                    MAX_DIFF = 10 # set according to preferences form
                    util_diff = model.NewIntVar(-MAX_DIFF, MAX_DIFF, "")
                    model.Add(util_diff == M.teach_num[t] - util_ideal)

                    # utilization - 1more
                    util_diff_pos = model.NewIntVar(0, MAX_DIFF, "")
                    model.AddMaxEquality(util_diff_pos, [0, util_diff])
                    more1_max = icw["1more"]
                    more1 = model.NewIntVar(0, more1_max, "")
                    zero1 = model.NewBoolVar("")
                    model.Add(util_diff_pos <= 0).OnlyEnforceIf(zero1)
                    model.Add(util_diff_pos >= 1).OnlyEnforceIf(zero1.Not())
                    model.Add(more1 == 0).OnlyEnforceIf(zero1)
                    model.Add(more1 == more1_max).OnlyEnforceIf(zero1.Not())
                    self.penalties["teacher"][T]["1more"] = more1
                    # utilization - 2more
                    more2_max = icw["2more"] * MAX_DIFF
                    more2 = model.NewIntVar(0, more2_max, "")
                    zero2 = model.NewBoolVar("")
                    model.Add(util_diff_pos <= 1).OnlyEnforceIf(zero2)
                    model.Add(util_diff_pos >= 2).OnlyEnforceIf(zero2.Not())
                    model.Add(more2 == 0).OnlyEnforceIf(zero2)
                    model.Add(more2 == util_diff_pos * icw["2more"]).OnlyEnforceIf(zero2.Not())
                    self.penalties["teacher"][T]["2more"] = more2

                    # utilization - definitely not more than 2 extra courses
                    M.add_heavy(f"3more-{T}", util_diff_pos <= 2)

                    # utilization - 1 less
                    util_diff_neg_neg = model.NewIntVar(-MAX_DIFF, 0, "")
                    util_diff_neg = model.NewIntVar(0, MAX_DIFF, "")
                    model.AddMinEquality(util_diff_neg_neg, [0, util_diff])
                    model.AddAbsEquality(util_diff_neg, util_diff_neg_neg)
                    less1 = model.NewIntVar(0, icw["1less"] * MAX_DIFF, "")
                    model.Add(less1 == util_diff_neg * icw["1less"])
                    self.penalties["teacher"][T]["1less"] = less1

                    # utilization - definitely not less than 1 desired course
                    M.add_heavy(f"2less-{T}", util_diff_neg <= 1)

                    # 3c1d - three courses in one day
                    p31 = model.NewIntVar(0, len(I.days) * icw["3c1d"], "")
                    days_three_list = []
                    for d in range(len(I.days)):
                        # day is full (teacher teaches in all three slots)
                        day_three = model.NewBoolVar("")
                        model.Add(sum(M.ts[(t,s)] for s in [d*3+i for i in (0,1,2)]) == 3).OnlyEnforceIf(day_three)
                        model.Add(sum(M.ts[(t,s)] for s in [d*3+i for i in (0,1,2)]) < 3).OnlyEnforceIf(day_three.Not())
                        days_three_list.append(day_three)
                    model.Add(p31 == sum(days_three_list) * icw["3c1d"])
                    self.penalties["teacher"][T]["3c1d"] = p31

                    # 2c2d - courses in more days than needed
                    teaches_days = model.NewIntVar(0, len(I.days), "TD:%i" % t)
                    model.Add(teaches_days == sum(M.td[(t,d)] for d in range(len(I.days))))
                    teaches_minus_1 = model.NewIntVar(0, len(I.slots), "Tm1:%i" % t)
                    teaches_some = model.NewBoolVar("Ts:%i" % t)
                    model.Add(M.teach_num[t] >= 1).OnlyEnforceIf(teaches_some)
                    model.Add(M.teach_num[t] == 0).OnlyEnforceIf(teaches_some.Not())
                    model.Add(teaches_minus_1 == M.teach_num[t] - 1).OnlyEnforceIf(teaches_some)
                    model.Add(teaches_minus_1 == 0).OnlyEnforceIf(teaches_some.Not())
                    should_teach_days_minus_1 = model.NewIntVar(0, len(I.days), "TDs:%i" % t)
                    model.AddDivisionEquality(should_teach_days_minus_1, teaches_minus_1, len(I.times)) # -1 to compensate rounding down
                    days_extra = model.NewIntVar(0, len(I.days), "Tdd:%i" % t)
                    model.Add(days_extra == teaches_days - should_teach_days_minus_1 - 1).OnlyEnforceIf(teaches_some) # -1 to compensate rounding down
                    model.Add(days_extra == 0).OnlyEnforceIf(teaches_some.Not())
                    p22 = model.NewIntVar(0, icw["2c2d"] * len(I.days), "")
                    model.Add(p22 == icw["2c2d"] * days_extra)
                    self.penalties["teacher"][T]["2c2d"] = p22

                    self.add_heavy(f"2extradays-{T}", days_extra < 2)

                    # not_teaching
                    p_not_teaching = model.NewIntVar(0, icw["not_teaching"], "")
                    model.Add(p_not_teaching == teaches_some.Not() * icw["not_teaching"])
                    self.penalties["teacher"][T]["not_teaching"] = p_not_teaching

                    # teaching or not being available during Teachers Training
                    if "Teachers Training" in I.Courses and "tt" in icw:
                        tt_map = []
                        c = I.Courses["Teachers Training"]
                        for s in range(len(I.slots)):
                            hit = model.NewBoolVar("")
                            model.Add(M.cs[c] == s).OnlyEnforceIf(hit)
                            model.Add(M.cs[c] != s).OnlyEnforceIf(hit.Not())
                            tt_map.append(hit)

                        w = icw["tt"]
                        l = []
                        for s in range(len(I.slots)):
                            hit = model.NewBoolVar("")
                            model.AddBoolAnd([tt_map[s], M.ps_na[(t,s)]]).OnlyEnforceIf(hit)
                            model.AddBoolOr([tt_map[s].Not(), M.ps_na[(t,s)].Not()]).OnlyEnforceIf(hit.Not())
                            l.append(hit)
                        teaches_tt = model.NewBoolVar("")
                        c = I.Courses["Teachers Training"]
                        model.Add(M.tc[(t,c)] == 1).OnlyEnforceIf(teaches_tt)
                        model.Add(M.tc[(t,c)] == 0).OnlyEnforceIf(teaches_tt.Not())
                        teaches_tt_time = model.NewBoolVar("")
                        model.Add(teaches_tt_time == sum(l)).OnlyEnforceIf(teaches_tt.Not())
                        model.Add(teaches_tt_time == 0).OnlyEnforceIf(teaches_tt)
                        p_tt = model.NewIntVar(0, w, "")
                        model.Add(p_tt == teaches_tt_time * w)
                        self.penalties["teacher"][T]["tt"] = p_tt

                    # split
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
                    p_split = model.NewIntVar(0, icw["split"] * len(I.days), "")
                    model.Add(p_split == icw["split"] * days_split)
                    self.penalties["teacher"][T]["split"] = p_split

                    # bad_time
                    prefs = I.ts_pref[T]
                    slots_bad = [s for s in range(len(I.slots)) if prefs[s] == 1]
                    p_slot_bad = model.NewIntVar(0, icw["bad_time"] * 10, "")
                    model.Add(p_slot_bad == icw["bad_time"] * sum(M.ts[(t,s)] for s in slots_bad))
                    self.penalties["teacher"][T]["bad_time"] = p_slot_bad

                    # bad_course
                    # teacher T strongly prefers some courses over others
                    courses_bad = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 1]
                    p_course_bad = model.NewIntVar(0, icw["bad_course"] * 10, "")
                    debug(f"courses_bad {T}: {courses_bad}")
                    model.Add(p_course_bad == icw["bad_course"] * sum(M.tc[(I.Teachers[T],I.Courses[C])] for C in courses_bad))
                    self.penalties["teacher"][T]["bad_course"] = p_course_bad

                    # no_perfect
                    courses_perfect = [C for C in I.courses_regular+I.courses_solo if I.tc_pref[T].get(C, -1) == 3]
                    p_no_perfect = model.NewIntVar(0, icw["no_perfect"], "")
                    debug(f"courses_perfect {T}: {courses_perfect}")
                    teaches_perfect = model.NewIntVar(0, 10, "")
                    model.Add(teaches_perfect == sum(M.tc[(I.Teachers[T],I.Courses[C])] for C in courses_perfect))
                    zero = model.NewBoolVar("")
                    model.Add(teaches_perfect == 0).OnlyEnforceIf(zero)
                    model.Add(teaches_perfect >= 1).OnlyEnforceIf(zero.Not())
                    model.Add(p_no_perfect == icw["no_perfect"] * zero)
                    self.penalties["teacher"][T]["no_perfect"] = p_no_perfect

                    # no_person
                    debug(f"teach_together: {T} + {I.tt_together[T]}")
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
                    if not I.tt_together[T]:
                        debug(f"teach_together: no preference => no penalty for {T}") # TODO
                    p_no_person = model.NewIntVar(0, icw["no_person"], "")
                    model.Add(p_no_person == icw["no_person"] * nobody)
                    self.penalties["teacher"][T]["no_person"] = p_no_person

                    # special
                    if icw["special"]:
                        debug(f"Special wish for {T}")
                        p_special = model.NewIntVar(0, icw["special"], "")
                        model.Add(p_special == icw["special"] * self.wish[T])
                        self.penalties["teacher"][T]["special"] = p_special

            elif name == "courses_closed": # penalty if too little courses are opened
                penalties_courses_closed = []
                total_courseslots = 4 * 3 * 2 # days, times, rooms
                n_active = model.NewIntVar(0, total_courseslots, "")
                n_closed = model.NewIntVar(0, total_courseslots, "")
                model.Add(n_closed == total_courseslots - sum(M.c_active))
                #w = I.PENALTIES["courses_closed"]
                #p_closed = model.NewIntVar(0, total_courseslots * w, "")
                self.penalties["courses_closed"] = n_closed

            elif name == "student": # penalty if student cannot attend desired course
                self.penalties["student"] = {}
                total_student = coeff

                penalties_stud_bad = []
                for S, val in I.input_data.items():
                    if val["type"] != "student":
                        debug(f"stud_bad: skipping {S}, not a student")
                        continue
                    debug(f"stud_bad: student {S}")
                    if not val["courses_attend"]:
                        warn(f"stud_bad: skipping {S}, no courses_attend")
                        continue
                    if "provided_id" in val:
                        debug(f"stud_bad: provided_id '{val['provided_id']}'")
                    else:
                        debug(f"stud_bad: no id provided")
                    debug(f"courses_attend: {val['courses_attend']}")
                    course_weigth = 100 // len(val["courses_attend"])

                    courses_bad = []
                    penalties_student = {}
                    for C in val["courses_attend"]:
                        Cs = [Cspec for Cspec in I.courses if I.is_course_type(Cspec, C)]
                        if not Cs:
                            error(f"stud_bad: no specific course found for {C}")
                            continue
                        slots_available = [s for s in range(len(I.slots)) if val["slots"][s] != 0]
                        course_cannot = model.NewBoolVar("")
                        model.Add(sum(M.src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) == 0).OnlyEnforceIf(course_cannot)
                        model.Add(sum(M.src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) >= 1).OnlyEnforceIf(course_cannot.Not())
                        p_stud_course = model.NewIntVar(0, course_weigth, "")
                        model.Add(p_stud_course == course_cannot * course_weigth)
                        penalties_student[C] = p_stud_course

                    if len(penalties_student) == 0:
                        error(f"No student penalties for {S}")
                    self.penalties["student"][S] = penalties_student

#                penalties[name] = penalties_stud_bad
#                def analysis(R):
#                    src = R.src
#                    tc = R.tc
#                    result = []
#                    total_bad = 0
##                    total_open = 0
#                    total_ok = 0
#                    courses_bad_stats = {}
#                    courses_ok_stats = {}
#                    for S, val in I.input_data.items():
#                        if val["type"] != "student":
#                            debug(f"analysis stud_bad: skipping {S}, not a student")
#                            continue
#                        debug(f"analysis stud_bad: student {S}")
#                        who = f"{S}"
#                        if "provided_id" in val:
#                            who += f"({val['provided_id']})"
#                            debug(f"analysis stud_bad: provided_id '{val['provided_id']}'")
#                        else:
#                            debug(f"analysis stud_bad: no id provided")
#                        courses_bad = []
##                        courses_na_open = []
#                        courses_ok = []
#                        slots_available = [s for s in range(len(I.slots)) if val["slots"][s] != 0]
#                        debug(f"analysis stud_bad: slots_available: {slots_available}")
#                        for C in val["courses_attend"]:
#                            Cs = [Cspec for Cspec in I.courses if I.is_course_type(Cspec, C)]
#                            if not Cs:
#                                warn(f"analysis stud_bad: no specific course found for {C}")
#                                continue
#                            debug(f"analysis stud_bad: specific courses: {', '.join(Cs)}")
#                            if sum(src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) == 0:
#                                courses_bad.append(C)
#                                total_bad += 1
#                                if C in courses_bad_stats:
#                                    courses_bad_stats[C] += 1
#                                else:
#                                    courses_bad_stats[C] = 1
#
##                                if any([CCC in I.courses_must_open for CCC in Cs]):
##                                    # FIXME: this looks like a bad attempt to get active courses, use c_active
##                                    courses_na_open.append(C)
##                                    total_open += 1
#                            else:
#                                courses_ok.append(C)
#                                total_ok += 1
#                                if C in courses_ok_stats:
#                                    courses_ok_stats[C] += 1
#                                else:
#                                    courses_ok_stats[C] = 1
##                        if courses_na_open:
#                        if courses_bad:
#                            debug(f"analysis stud_bad: courses_bad: {who}: {', '.join(courses_bad)}")
##                            debug(f"analysis stud_bad: courses_na_open: {who}: {', '.join(courses_na_open)}")
##                            result.append(f"{who} [{', '.join(courses_na_open)}]")
#                            result.append(f"{who} [{', '.join(courses_bad)}]")
#                        if courses_ok:
#                            debug(f"analysis stud_bad: courses OK: {who}: {', '.join(courses_ok)}")
#                    debug(f"Students missed:\n{pprint.pformat(result)}")
#                    courses_bad_stats_view = sorted( ((v,k) for k,v in courses_bad_stats.items()), reverse=True)
#                    result = [f"{k} ({v})" for v,k in courses_bad_stats_view] # FIXME
#                    debug(f"Students missed statistics:\n{pprint.pformat(courses_bad_stats_view)}")
#                    courses_ok_stats_view = sorted( ((v,k) for k,v in courses_ok_stats.items()), reverse=True)
#                    debug(f"Students ok statistics:\n{pprint.pformat(courses_ok_stats_view)}")
##                    debug(f"analysis stud_bad: total missed: {total_bad}, open missed: {total_open}, total OK: {total_ok}")
#                    debug(f"analysis stud_bad: total missed: {total_bad}, total OK: {total_ok}")
#                    return result
#                penalties_analysis[name] = analysis

        #self.penalties = penalties
        self.penalties_analysis = penalties_analysis

        debug(f"Model: penalties initialized")

    # finalize penalties
    def final_penalties(self):
        I = self.I
        model = self.model

        penalties_values = []
        for (top, d) in self.penalties.items():
            if top == "teacher":
                for T, dict_penalties in d.items():
                    penalties_values.append(sum(dict_penalties.values()))
            elif top == "student":
                penalties_students = []
                for S, dict_penalties in d.items():
                    penalties_students.append(sum(dict_penalties.values()))
                penalty_students_weighted = model.NewIntVar(0, len(d) * I.PENALTIES["student"] * 100, "")
                model.Add(penalty_students_weighted == sum(penalties_students) * I.PENALTIES["student"])
                #penalty_students_weighted = sum(penalties_students) * I.PENALTIES["student"]
                penalty_students_adjusted = model.NewIntVar(0, len(d) * I.PENALTIES["student"], "")
                model.AddDivisionEquality(penalty_students_adjusted, penalty_students_weighted, 100)
                penalties_values.append(penalty_students_adjusted)
            elif top == "courses_closed":
                penalties_values.append(d * I.PENALTIES["courses_closed"])
            elif top == "heavy":
                penalties_values.append(sum(d.values()) * I.PENALTIES["heavy"])
            elif top == "very_heavy":
                penalties_values.append(sum(d.values()) * I.PENALTIES["very_heavy"])
            elif top == "custom":
                penalties_values.append(sum(d.values()) * I.PENALTIES["custom"])
            elif top == "nice":
                penalties_values.append(sum(d.values()) * I.PENALTIES["nice"])
            else:
                error(f"Unknown penalty domain: {top}")

        model.Minimize(sum(penalties_values))

        debug(f"Model: penalties finalized")

    def print_stats(self):
        print(self.model.ModelStats())

    def add_very_heavy(self, name, *args):
        self.add_rule("very_heavy", name, *args)

    def add_heavy(self, name, *args):
        self.add_rule("heavy", name, *args)

    def add_custom(self, name, *args):
        self.add_rule("custom", name, *args)

    def add_nice(self, name, *args):
        self.add_rule("nice", name, *args)

    def add_rule(self, typ, name, *args):
        model = self.model

        #debug(f"Adding rule type '{typ}' name '{name}' args '{args}'")
        debug(f"Adding rule type '{typ}' name '{name}'")
        debug(f"Current penalties of type '{typ}': {self.penalties[typ]}")
        if not name:
            # TODO probably not possible..
            name = f"{typ}-{len(self.penalties[typ])}"

        if name in self.penalties[typ]:
            error(f"Type {typ} penalty {name} already exists")
            p = self.penalties[typ][name]
        else:
            #debug(f"Type {typ} penalty {name} does not exist yet")
            p = model.NewBoolVar(f"{typ}-{name}")
            self.penalties[typ][name] = p

        model.Add(*args).OnlyEnforceIf(p.Not())

    def add_wish(self, T, *args):
        model = self.model

        p = self.wish[T]

        model.Add(*args).OnlyEnforceIf(p.Not())


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
            R = Result()
            self.count += 1
            R.src = {}
            for s in range(len(I.slots)):
                for r in range(len(I.rooms)):
                    for c in range(len(I.courses)):
                            R.src[(s,r,c)] = self.Value(M.src[(s,r,c)])
            debug(pprint.pformat(R))
            R.tc = {}
            R.tc_lead = {}
            R.tc_follow = {}
            for t in range(len(I.teachers)):
                for c in range(len(I.courses)):
                    R.tc[(t,c)] = self.Value(M.tc[(t,c)])
                    R.tc_lead[(t,c)] = self.Value(M.tc_lead[(t,c)])
                    R.tc_follow[(t,c)] = self.Value(M.tc_follow[(t,c)])
            for P in I.people:
                p = I.Teachers[P] # FIXME
                teach_courses = [I.courses[c] for c in range(len(I.courses)) if self.Value(M.tc[(p,c)])]
                ta_courses = [I.courses[c] for c in range(len(I.courses)) if self.Value(M.pc[(p,c)])]
                attend_courses = list(set(ta_courses) - set(teach_courses))
                #debug(f"PSPD: {P} teaches {', '.join(teach_courses)}")
                #debug(f"PSPD: {P} attends {', '.join(attend_courses)}")
                #debug(f"PSPD: {P} teaches or attends {', '.join(ta_courses)}")
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
                #debug(f"PSPD: As {As}")
                #debug(f"PSPD: ps {ps}")
                #debug(f"ps/pd analysis: {P :<9} os {os} ts {ts} as {As} ps {ps} na {na} num {self.Value(M.occupied_num[p])} days {days}")
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
            debug(f"Courses openness and indices")
            R.c_active = []
            R.cs = []
            for c in range(len(I.courses)):
                R.c_active.append(self.Value(M.c_active[c]))
                debug(f"{I.courses[c]: <30}: {self.Value(M.c_active[c])} {self.Value(M.cs[c])}")
                R.cs.append(self.Value(M.cs[c]))
            R.penalties = M.penalties
#            R.penalties = {}
#            # FIXME how to access penalties?
#            for (name, l) in M.penalties.items():
#                v = sum([self.Value(p) for p in l])
#                coeff = I.PENALTIES[name]
#                R.penalties[name] = (coeff, v)
#            R.custom_penalties = {}
#            for name, v in M.custom_penalties.items():
#                R.custom_penalties[name] = self.Value(v)
#            R.heavy_penalties = {}
#            for name, v in M.heavy_penalties.items():
#                R.heavy_penalties[name] = self.Value(v)
            print(f"No: {self.count}")
            print(f"Wall time: {self.WallTime()}")
            #print(f"Branches: {self.NumBranches()}")
            #print(f"Conflicts: {self.NumConflicts()}")
            def print_solution(R, penalties_analysis, objective=None, utilization=True):
                src = R.src
                tc = R.tc
                tc_lead = R.tc_lead
                tc_follow = R.tc_follow
                penalties = R.penalties
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
                                    #t_lead = "UNKNOWN"
                                    #t_follow = "UNKNOWN"
                                    for t in range(len(I.teachers)):
                                        if tc_lead[(t,c)]:
                                            t_lead = t
                                        if tc_follow[(t,c)]:
                                            t_follow = t
                                    Ts.append(I.teachers[t_lead])
                                    Ts.append(I.teachers[t_follow])
                                #if len(Ts) == 2 and (Ts[0] in I.teachers_follow or Ts[1] in I.teachers_lead):
                                    #Ts[0], Ts[1] = Ts[1], Ts[0]
                                if len(Ts) == 2:
                                    Ts_print = f"{Ts[0] :<10}+ {Ts[1]}"
                                else:
                                    Ts_print = f"{Ts[0]}"
                                #print(f"{I.slots[s]: <11}{I.rooms[r]: <5}{'+'.join(Ts): <19}{I.courses[c]}")
                                print(f"  {I.slots[s]: <11}{I.rooms[r]: <4}{Ts_print: <21}{I.courses[c]}")
                if penalties:
                    print("PENALTIES:")
                    total = 0

                    n_heavy = 0
                    l = []
                    w = I.PENALTIES["heavy"]
                    for (name, v) in penalties["heavy"].items():
                        y = self.Value(v) # TODO
                        if y != 0:
                            n_heavy += y
                            l.append(name)
                    if not l:
                        l.append("none")
                    total_heavy = n_heavy * w
                    print(f"Heavy ({n_heavy}*{w}={total_heavy}): {', '.join(l)}")
                    total += total_heavy

                    n_very_heavy = 0
                    l = []
                    w = I.PENALTIES["very_heavy"]
                    for (name, v) in penalties["very_heavy"].items():
                        y = self.Value(v) # TODO
                        if y != 0:
                            n_very_heavy += y
                            l.append(name)
                    if not l:
                        l.append("none")
                    total_very_heavy = n_very_heavy * w
                    print(f"VERY Heavy ({n_very_heavy}*{w}={total_very_heavy}): {', '.join(l)}")
                    total += total_very_heavy

                    total_teachers = 0
                    print("Teachers:")
                    teachers_happy = []
                    # FIXME
                    for T, d in penalties["teacher"].items():
                        l = []
                        s = 0
                        for p, v in d.items():
                            y = self.Value(v) # TODO have all values in R?
                            if y > 0:
                                total_teachers += y
                                l.append((p,y))
                                s += y
                        if s:
                            details = ", ".join([f"{x[0]}:{x[1]}" for x in l])
                            print(f" * {T}: {s} // {details}")
                        else:
                            debug(f" * {T} is happy")
                            teachers_happy.append(T)
                    print(f" Happy teachers: ({len(teachers_happy)}) {', '.join(teachers_happy)}")
                    print(f"Teachers total: {total_teachers}")
                    total += total_teachers

                    n_closed = self.Value(penalties["courses_closed"])
                    w = I.PENALTIES["courses_closed"]
                    total_closed = n_closed * w
                    print(f"Closed courses: {n_closed}*{w}={total_closed}")
                    total += total_closed

                    n_custom = 0
                    l = []
                    w = I.PENALTIES["custom"]
                    for (name, v) in penalties["custom"].items():
                        y = self.Value(v) # TODO
                        if y != 0:
                            n_custom += y
                            l.append(name)
                    if not l:
                        l.append("none")
                    total_custom = n_custom * w
                    print(f"Custom ({n_custom}*{w}={total_custom}): {', '.join(l)}")
                    total += total_custom

                    n_nice = 0
                    l = []
                    w = I.PENALTIES["nice"]
                    for (name, v) in penalties["nice"].items():
                        y = self.Value(v) # TODO
                        if y != 0:
                            n_nice += y
                            l.append(name)
                    if not l:
                        l.append("none")
                    total_nice = n_nice * w
                    print(f"Nice: ({n_nice}*{w}={total_nice}): {', '.join(l)}")
                    total += total_nice

                    print("Students:")
                    total_students = 0
                    happiness_sum = 0
                    happiness_count = 0
                    students_hh = {} # Happiness Histogram
                    for S, d in penalties["student"].items():
                        l = []
                        s = 0
                        courses_wanted = 0
                        courses_bad = 0
                        for p, v in d.items():
                            courses_wanted += 1
                            y = self.Value(v) # TODO have all values in R?
                            if y > 0:
                                courses_bad += 1
                                total_students += y
                                l.append((p,y))
                                s += y
                        courses_good = courses_wanted - courses_bad
                        happiness = int(courses_good / courses_wanted * 100)
                        hh_item = students_hh.get(happiness, [])
                        hh_item.append(S)
                        students_hh[happiness] = hh_item
                        happiness_sum += happiness
                        happiness_count += 1

                    for v in sorted(students_hh.keys()):
                        print(f" * {v:>3}%: {len(students_hh[v]):>3} ({' '.join(students_hh[v])})")
                    total_students = total_students * I.PENALTIES["student"] // 100
                    if happiness_count:
                        print(f"Students total: {total_students} ({happiness_sum//happiness_count}%)")
                    total += total_students

                if utilization:
                    print("UTILIZATION:")
                    tn = {}
                    #for t in range(len(I.teachers)):
                        #tn[I.teachers[t]] = sum(tc[t,c] for c in range(len(I.courses)))
                    for T in I.teachers:
                        tn[T] = sum(tc[I.Teachers[T],c] for c in range(len(I.courses)))
                    for v in sorted(set(tn.values())):
                        print(f"{v}: {', '.join(t for t in tn if tn[t] == v)}")
                print(f"TOTAL: {total}")

                if objective and objective != total:
                    warn(f"Mismatch of objective value: objective {objective} vs. total {total}") # FIXME

            debug(pprint.pformat(R))
            print_solution(R, M.penalties_analysis, objective=self.ObjectiveValue())
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


# The worst argument parser in the history of argument parsers, maybe ever.
def parse(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Debug output")
    parser.add_argument("-s", "--students", action="store", dest="students", help="Students' preferences CSV")
    parser.add_argument("-t", "--teachers", action="store", dest="teachers", help="Teachers' preferences CSV")
    parser.add_argument("-p", "--penalty", action="append", dest="penalties", help="Penalty value 'name:X'")
    parser.add_argument("-e", "--exclude-teacher", action="append", default=[], dest="excluded_teachers", help="Ignore teacher")
    args = parser.parse_args()

    if args.verbose:
        set_verbose()

    penalties = {}
    if args.penalties:
        for x in args.penalties:
            name, value = x.split(":")
            penalties[name] = int(value)

    return (args.teachers, args.students, penalties, args.excluded_teachers)

def main():
    teach_csv, stud_csv, penalties, excluded_teachers = parse()

    # all input information
    input = Input()
    input.init(teach_csv, students_csv=stud_csv, penalties=penalties, excluded_teachers=excluded_teachers)

    # model construction
    model = Model()
    model.init(input)
    model.init_penalties()

    # run the solver
    model.solve()

if __name__ == "__main__":
    main()

# TODO
    # "not teaching during TT" should also look at person's availability in time preferences
