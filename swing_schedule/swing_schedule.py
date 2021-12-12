#!/usr/bin/env python3

import sys
import csv
import argparse
from ortools.sat.python import cp_model
import pprint

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
    def init(self, teachers_csv, penalties={}, students_csv=None, extra_courses=[]):
        self.init_constants()
        self.init_form(teachers_csv, students_csv, extra_courses)
        self.init_teachers()
        self.init_rest()
        self.init_penalties(penalties)

    def init_form(self, teachers_csv, students_csv=None, extra_courses=[]):
        self.init_teachers_form(teachers_csv, extra_courses)
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

        self.venues = ["koliste"]
        self.Venues = {}
        for i, V in enumerate(self.venues):
            self.Venues[V] = i

        self.rooms_venues = {
            "k-3": "koliste",
            "k-4": "koliste",
            }

        self.courses_open = [
            "Lindy/Charleston Open Training",
            "Blues/Slow Open Training",
            "Teachers Training /2",
            #"Rhythm Pilots /1",
            #"Rhythm Pilots /2",
            ]
        self.courses_solo = [
            "Shag/Balboa Open Training",
            "Solo - choreography",
            "Solo - improvisation",
            #"Authentic Movement",
            "Teachers Training /1",
            ]
        self.courses_regular = [
            "LH 1 - Beginners /1",
            "LH 1 - Beginners /2",
            "LH 1 - Beginners /3",
            "LH 1 - English",
            "LH 2 - Party Moves",
            "LH 2 - Party Moves - English",
            "LH 2 - Survival Guide",
            "LH 2.5 - Swingout /1",
            "LH 2.5 - Swingout /2",
            "LH 3 - Musicality",
            "LH 3 - Charleston",
            "LH 3 - Cool Moves and Styling",
            "LH 4 - more technical",
            "LH 4 - more philosophical",
            "LH 5",
            "Charleston 2",
            "Collegiate Shag 1",
            "Collegiate Shag 1.5",
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
#            "LH 1 - Beginners /3", #
#            #"LH 1 - English",
#            #"LH 2.5 - Swingout /2", #
#            #"LH 3 - Musicality",
#            "LH 5",
#            "Airsteps 1", # FIXME
#            "Airsteps 2", # FIXME
#            "Saint Louis Shag 1",
#            "Saint Louis Shag 2",
#            "Balboa Advanced",
#            "Slow Balboa",
#            "Blues 2",
            "Authentic Movement",
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
        self.people = self.teachers


    def translate_teacher_name(self, name):
        result = name.strip()
        result = result.replace(" ", "-")
        debug(f"Translated '{name}' to '{result}'")
        return result

    def is_course_type(self, Cspec, Cgen):
        if Cspec.endswith("English"):
            #debug(f"is_course_type: {Cspec} {Cgen} {Cgen == Cspec}")
            return Cgen == Cspec
        if Cspec.startswith("Collegiate Shag"):
            return Cgen == Cspec
        #debug(f"is_course_type: {Cspec} {Cgen} {Cspec.startswith(Cgen)}")
        return Cspec.startswith(Cgen)

    def check_course(self, course):
        for Cspec in self.courses:
            if self.is_course_type(Cspec, course):
                debug(f"check_course: course preference {course} maps, e.g to {Cspec}")
                return
        error(f"check_course: unknown course: '{course}'")

    def read_teachers_input(self, infile=None, extra_courses=[]):
        if infile:
            info(f"Opening {infile}")
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
                        self.check_course(course)
                        # problematic: Balboa Beginners 2
                        input_courses.append(course)
                for C in extra_courses:
                    if C not in input_courses:
                        input_courses.append(C)
                info(f"Input courses (F): {sorted(input_courses)}")
                info(f"Input courses (C): {sorted(self.courses)}")
                # does not make sense (general vs. specific course names)
                #info(f"Input courses (diff): {set(self.courses)-set(input_courses)-set(self.COURSES_IGNORE)}")
            # handle the input data
            debug("")
            who = row["Who are you?"]
            if who.startswith("IGNORE"):
                debug(f"read_teachers_input: skipping row {row}")
                continue
            name = self.translate_teacher_name(who)
            debug(f"Reading: name {name}")
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
            slots = []
            for day in ["Mon", "Tue", "Wed", "Thu"]:
                for time in ["17:30", "18:45", "20:00"]:
                    slots.append(int(row[f"What days and times are convenient for you? [{day} {time}]"][0]))
            d["slots"] = slots
            mindays = row["Do you prefer to spend as few days as possible with teaching or not having many courses in one day?"]
            if mindays.startswith("I need to spend as few days as possible with teaching"):
                d["mindays"] = 1
            elif mindays.startswith("I prefer teaching less courses in one day"):
                d["mindays"] = -1
            elif mindays.startswith("I don't mind either"):
                d["mindays"] = 0
            else:
                error("Unknown mindays answer")
            splitok = row["How do you feel about waiting between courses?"]
            if splitok.startswith("I prefer courses following each other"):
                d["splitok"] = -1
            elif splitok.startswith("I like to rest between lessons"):
                d["splitok"] = 1
            elif splitok.startswith("Both are equally fine"):
                d["splitok"] = 0
            else:
                error("Unknown splitok answer")

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
                answer = row[f"What courses would you like to teach in your primary role? [{C}]"]
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
            bestpref = row["What preference is the most important for you?"]
            if bestpref.startswith("Time"):
                d["bestpref"] = "time"
            elif bestpref.startswith("Course"):
                d["bestpref"] = "course"
            elif bestpref.startswith("People"):
                d["bestpref"] = "person"
            else:
                error(f"Unknow best pref: {bestpref}")
            d["courses_attend"] = [a.strip() for a in row["What courses and trainings would you like to attend?"].split(",") if a]
            assert("" not in d["courses_attend"])
            #debug(f"Courses attend before: {d['courses_attend']}")
            for c in set(d["courses_attend"]):
                if c in self.COURSES_IGNORE:
                    debug(f"courses_attend: removing: {c}")
                    d["courses_attend"].remove(c)
                else:
                    debug(f"NOT removing: {c}")
            #debug(f"Courses attend after: {d['courses_attend']}")
            if "LH 4" in d["courses_attend"]:
                d["courses_attend"].remove("LH 4")
                d["courses_attend"].append("LH 4 - more technical")
                d["courses_attend"].append("LH 4 - more philosophical")
            if "Solo" in d["courses_attend"]:
                d["courses_attend"].remove("Solo")
                d["courses_attend"].append("Solo - choreography")
                d["courses_attend"].append("Solo - improvisation")
            for c in d["courses_attend"]:
                self.check_course(c)
            teach_together = row["Who would you like to teach with?"]
            d["teach_together"] = [self.translate_teacher_name(name.strip()) for name in teach_together.split(",") if name]
            if name in d["teach_together"]:
                d["teach_together"].remove(name)
            d["teach_not_together"] = [self.translate_teacher_name(name) for name in row["Are there any people you cannot teach with?"].split(",") if name]
            if name in d["teach_not_together"]:
                d["teach_not_together"].remove(name)
            debug(f"Adding {name} to result")
            self.teachers.append(name)
            result[name] = d
        debug(f"Number of lines: {n}")
        debug(f"Result: {'|'.join(result)}")
        debug(f"Active teachers: {set(self.teachers)}")

        if f is not sys.stdin:
            f.close()

        #print(f"Column names: {columns}")
        return result

    def init_teachers_form(self, infile=None, extra_courses=[]):
        teachers_data = self.read_teachers_input(infile, extra_courses)
        debug("TEACHERS' ANSWERS:")
        debug(pprint.pformat(teachers_data))
        self.input_data = teachers_data

    def init_students_form(self, infile):
        warn(f"Not finished: reading students' preferences")
        students_data = self.read_students_input(infile)
        debug("STUDENTS' ANSWERS:")
        debug(pprint.pformat(students_data))
        for k in students_data:
            self.input_data[k] = students_data[k]

    def translate_course_cs_en(self, course):
        result = None
        if course in self.courses:
            result = course
        elif course == "LH 4 - techničtější":
            result = "LH 4 - more technical"
        elif course == "LH 4 - filozofičtější":
            result = "LH 4 - more philosophical"
        elif course == "Solo - improvizace":
            result = "Solo - improvisation"
        elif course == "Solo - choreografie":
            result = "Solo - choreography"
        elif course == "Autentický pohyb":
            result = "Authentic Movement"
        elif course == "Zumba s Tomem":
            result = "Zumba s Tomem"
        if not result:
            error(f"Unknown student course {course}")
        return result

    def read_students_input(self, csv_file):
        info(f"Opening students CSV: {csv_file}")
        f = open(csv_file, mode="r")
        reader = csv.DictReader(f)

        n = 0
        result = {}
        student_courses = []
        for row in reader:
            n += 1
            if n == 1:
                # check courses when handling the first row
                columns = list(row.keys())
                for col in columns:
                    if col.startswith("Jaké kurzy si chceš zapsat?"):
                        course = col.split("[")[1].split("]")[0]
                        #course = self.translate_course_cs_en(course)
                        #if course in self.COURSES_IGNORE:
                            #warn(f"Student CSV: ignoring course {course}")
                            #continue
                        #self.check_course(course)
                        # problematic: Balboa Beginners 2
                        student_courses.append(course)
                debug(f"Student courses (C): {sorted(student_courses)}")
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
                for time in ("17:30 - 18:40", "18:45 - 19:55", "20:00 - 21:10"):
                    if time in daycell:
                        slots.append(0)
                    else:
                        slots.append(2)
            debug(f"Slots: {''.join(str(s) for s in slots)}")
            d["slots"] = slots
            courses_attend_2 = []
            courses_attend_3 = []
            for c in student_courses:
                #debug(f"course {c}")
                answer = row[f"Jaké kurzy si chceš zapsat? [{c}]"]
                if not answer:
                    debug(f"Student {name} provided no answer for {c}, defaulting to 0")
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
                if answer_num == 3:
                    courses_attend_3.append(c)
                elif answer_num == 2:
                    courses_attend_2.append(c)
#            courses_attend = ["BAD_COURSE"]
            courses_attend = courses_attend_2 + courses_attend_3
#            if len(courses_attend_3):
#                courses_attend = courses_attend_3
#            elif len(courses_attend_2):
#                courses_attend = courses_attend_2
#            else:
            if not courses_attend:
                warn(f"No prefered courses for student {name}")
                #courses_attend = []
            courses_attend = [self.translate_course_cs_en(Ccs) for Ccs in courses_attend]
            d["courses_attend"] = []
            for C in courses_attend:
                if C in self.COURSES_IGNORE:
                    debug(f"read_students_input: ignoring course {C}")
                else:
                    self.check_course(C)
                    d["courses_attend"].append(C)
            debug(f"read_students_input: courses_attend: {d['courses_attend']}")
            result[name] = d

        debug(f"Student CSV rows: {n}")
        debug(f"Student courses: {', '.join(student_courses)}")

        return result

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
        # teacher T must teach courses Cs
        self.tc_strict = {}
        # course Cx that must open
        self.courses_must_open = []
        # course Cx that must not open
        self.courses_not_open = []
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

        self.custom_penalties = []

        # translate input data to variables understood by the rest of the script
        for T in set(self.teachers):
            debug(f"Person {T}")
            data = self.input_data[T]
            if data["type"] != "teacher":
                error(f"Bad person type? {T}")
                continue
            self.t_util_max[T] = data["ncourses_max"]
            if self.t_util_max[T] == 0:
                # could be warning, it is probably legit to just say 0 max_courses
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
                        warn(f"Inactive teacher {d} (tt_not_together), ignoring")
                l = []
                for d in data["teach_together"]:
                    if d in self.input_data:
                        l.append(d)
                    else:
                        warn(f"Inactive teacher {d} (tt_together), ignoring")
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
            # workload
            "utilization": 25, # squared
            # placement
            "teach_days": 75,
            "teach_three": 75,
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
            # overall schedule
            "courses_closed": 150,
            # serious penalties
            "everybody_teach": 50,
            # students
            "stud_bad": 50,
            "custom": 200,
        }
        self.BOOSTER = 2

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
        # construct AC info (person P attends course C)
        for P in I.people:
            p = I.Teachers[P]
            if P in I.input_data:
                courses_attend = I.input_data[P]["courses_attend"]
            else:
                courses_attend = []
                error(f"unexpected - no attendance info for person {P}")
            for c in range(len(I.courses)):
                if [x for x in courses_attend if I.is_course_type(I.courses[c], x)]: # TODO course types
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

        # unspecified teachers teach no courses
        for T in I.teachers:
            debug(f"Teacher max: {T} {I.t_util_max.get(T,-1)}")
            model.Add(sum(self.tc[(I.Teachers[T],c)] for c in range(len(I.courses))) <= I.t_util_max.get(T, 0))

        for C in I.courses_must_open:
            model.Add(self.c_active[I.Courses[C]] == 1)

        for C in I.courses_not_open:
            model.Add(self.c_active[I.Courses[C]] == 0)

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

        for T1, T2 in I.tt_not_together:
            for c in range(len(I.courses)):
                model.Add(sum(self.tc[(t,c)] for t in [I.Teachers[T1], I.Teachers[T2]]) < 2)

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

        # same courses should not happen in same days and also not in same times
        # it should probably not be a strict limitation, but it is much easier to write
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


    def init_penalties(self):
        I = self.I
        M = self
        model = self.model

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
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
            elif name == "teach_three":
                # teaching three courses in one day
                penalties_teachthree = []
                for T in I.teachers:
                    t = I.Teachers[T]
                    mindays = I.input_data[T]["mindays"]
                    if mindays == -1:
                        debug(f"teach_three applies to teacher {T}")
                    elif mindays == 0:
                        info(f"teach_three does not apply to teacher {T}")
                        continue
                    elif mindays == 1:
                        debug(f"teach_three is the opposite of what teacher {T} wants")
                        continue
                    else:
                        error(f"Unknown mindays value: {mindays} for teacher {T}")
                    days_three = model.NewIntVar(0, len(I.days), "")
                    days_three_list = []
                    for d in range(len(I.days)):
                        # day is full (teacher teaches in all three slots)
                        day_three = model.NewBoolVar("")
                        model.Add(sum(M.ts[(t,s)] for s in [d*3+i for i in (0,1,2)]) == 3).OnlyEnforceIf(day_three)
                        model.Add(sum(M.ts[(t,s)] for s in [d*3+i for i in (0,1,2)]) < 3).OnlyEnforceIf(day_three.Not())
                        days_three_list.append(day_three)
                    model.Add(days_three == sum(days_three_list))
                    penalties_teachthree.append(days_three)
                penalties[name] = penalties_teachthree
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    for T in I.teachers:
                        if I.input_data[T]["mindays"] != -1:
                            # only applies to teachers who don't want full days
                            continue
                        t = I.Teachers[T]
                        cs = []
                        for c in range(len(I.courses)):
                            if tc[(t,c)]:
                                cs.append(c)
                        n = 0
                        for d in range(len(I.days)):
                            if (
                                    sum(src[(d*len(I.times),r,c)]  for r in range(len(I.rooms)) for c in cs) >= 1
                                    and sum(src[(d*len(I.times)+1,r,c)]  for r in range(len(I.rooms)) for c in cs) >= 1
                                    and sum(src[(d*len(I.times)+2,r,c)]  for r in range(len(I.rooms)) for c in cs) >= 1
                                    ):
                                n += 1
                        if n > 0:
                            result.append(f"{I.teachers[t]}/{n}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "teach_days":
                # nobody should come more days then necessary
                penalties_teachdays = []
                for T in I.teachers:
                    t = I.Teachers[T]
                    mindays = I.input_data[T]["mindays"]
                    if mindays == 1:
                        debug(f"teach_days applies to teacher {T}")
                    elif mindays == 0:
                        info(f"teach_days does not apply to teacher {T}")
                        continue
                    elif mindays == -1:
                        warn(f"teach_days is the opposite of what teacher {T} wants")
                        continue
                    else:
                        error(f"Unknown mindays value: {mindays} for teacher {T}")
                    # TODO - teaches_days could be useful general variable
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
                    penalties_teachdays.append(days_extra_sq)
                penalties[name] = penalties_teachdays
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    for T in I.teachers:
                        if I.input_data[T]["mindays"] != 1:
                            # only applies to teachers who want as few days as possible
                            continue
                        t = I.Teachers[T]
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
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    for P in I.people:
                        p = I.Teachers[P]
                        occupied_courses = []
                        for c in range(len(I.courses)):
                            if tc[(p,c)] or (P in I.input_data and [Cgen for Cgen in I.input_data[P]["courses_attend"] if I.is_course_type(I.courses[c], Cgen)]):
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
                #for t in range(len(I.teachers)):
                for T in I.teachers:
                    t = I.Teachers[T]
                    splitok = I.input_data[T]["splitok"]
                    if splitok == 1:
                        warn(f"Teacher {T} wants split, not implemented yet")
                        # TODO
                    elif splitok == 0:
                        info(f"Teacher {T} indifferent to split")
                        continue
                    elif splitok == -1:
                        debug(f"Teacher {T} does not like split")
                    else:
                        error(f"Unknown splitok value: {splitok}")
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
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    for T in I.teachers:
                        if I.input_data[T]["splitok"] != -1:
                            # only applies to teachers who don't like split
                            continue
                        t = I.Teachers[T]
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
                            boost = 1
                            if I.input_data[T]["bestpref"] == "time":
                                debug(f"Boosting time preferences for {T}")
                                boost = I.BOOSTER
                            penalties_slotpref_bad.append(boost * sum(M.ts[(I.Teachers[T],s)] for s in slots_bad))
                penalties[name] = penalties_slotpref_bad
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
                            boost = 1
                            if I.input_data[T]["bestpref"] == "course":
                                debug(f"Boosting course preferences for {T}")
                                boost = I.BOOSTER
                            penalties_coursepref.append(boost * sum(M.tc[(I.Teachers[T],I.Courses[C])] for C in courses_bad))
                penalties[name] = penalties_coursepref
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
            elif name == "everybody_teach":
                penalties_everybody_teach = []
                # fake teachers
                for T in I.teachers:
                    penalties_everybody_teach.append(M.does_not_teach[I.Teachers[T]])
                penalties[name] = penalties_everybody_teach
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    for t in range(len(I.teachers)):
                        T = I.teachers[t]
                        courses_bad = []
                        if not [(tf,cf) for (tf,cf) in tc if tc[(tf,cf)] and tf == t]:
                            result.append(f"{T}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "attend_free": # penalty if interested in attending cannot attend (they teach something else in the same time)
                # courses that some teachers would like to attend
                courses_attend = [I.input_data[T]["courses_attend"] for T in I.teachers]
                courses_attend = [item for sl in courses_attend for item in sl if item != ""] # flatten sublists
                courses_attend = set(courses_attend) # unique course names
                debug(f"attend_free: considering courses {', '.join(courses_attend)}")
                # TODO do this better
                if [C for C in courses_attend if C.startswith("LH 4")]:
                    courses_attend -= set(["LH 4"])
                    courses_attend |= set(["LH 4 - more technical", "LH 4 - more philosophical"])
                # TODO do this better
                if [C for C in courses_attend if C.startswith("Teachers Training")]:
                    courses_attend -= set(["Teachers Training"])
                    courses_attend |= set(["Teachers Training /1", "Teachers Training /2"])
                    #error(f"attend_free: courses_attend {courses_attend}")
                debug(f"attend_free: courses_attend {courses_attend}")
                penalties_attend_free = []
                boost = 1
                for C in courses_attend:
                    if C == "Teachers Training /1":
                        boost = I.BOOSTER
                    teachers_attend = []
                    for T in I.teachers:
                        if C in I.input_data[T]["courses_attend"]:
                            teachers_attend.append(T)
                    debug(f"attend_free: course {C}: {', '.join(teachers_attend)}")
                    #t = I.Teachers[T]
                    for s in range(len(I.slots)):
                        hit = model.NewBoolVar("")
                        model.Add(M.cs[I.Courses[C]] == s).OnlyEnforceIf(hit)
                        model.Add(M.cs[I.Courses[C]] != s).OnlyEnforceIf(hit.Not())
                        penalty_slot = model.NewIntVar(0, len(teachers_attend), "") # penalty for the slot
                        # FIXME this does not behave as expected
                        model.Add(penalty_slot == sum(M.ps_na[(I.Teachers[T],s)] for T in teachers_attend)).OnlyEnforceIf(hit)
                        model.Add(penalty_slot == 0).OnlyEnforceIf(hit.Not())
                        penalties_attend_free.append(boost * penalty_slot)
                penalties[name] = penalties_attend_free
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    cs = R.cs
                    result = []
                    courses_attend = [I.input_data[T]["courses_attend"] for T in I.teachers]
                    courses_attend = [item for sl in courses_attend for item in sl if item != ""] # flatten sublists
                    courses_attend = set(courses_attend) # unique course names
                    debug(f"analysis attend_free: considering courses {', '.join(courses_attend)}")
                    # TODO do this better
                    if [C for C in courses_attend if C.startswith("LH 4")]:
                        courses_attend -= set(["LH 4"])
                        courses_attend |= set(["LH 4 - more technical", "LH 4 - more philosophical"])
                    # TODO do this better
                    if [C for C in courses_attend if C.startswith("Teachers Training")]:
                        courses_attend -= set(["Teachers Training"])
                        courses_attend |= set(["Teachers Training /1", "Teachers Training /2"])
                        #error(f"attend_free: courses_attend {courses_attend}")
                    debug(f"analysis attend_free: courses_attend {courses_attend}")
                    for T in I.teachers:
                        t = I.Teachers[T]
                        wanted_input = set(I.input_data[T]["courses_attend"])
                        if "Teachers Training" in wanted_input:
                            wanted_input -= set(["Teachers Training"])
                            wanted_input |= set(["Teachers Training /1", "Teachers Training /2"])
                        if not wanted_input:
                            debug(f"analysis attend_free: {T} did not want anything, skipping")
                            continue
                        possible = []
                        not_possible = []
                        for Cw in sorted(wanted_input):
                            debug(f"analysis attend_free: {T} wanted course {Cw}")
                            Cs = []
                            for Ca in courses_attend:
                                if I.is_course_type(Ca, Cw):
                                    Cs.append(Ca)

                            # FIXME this is not ideal
                            if not Cs:
                                error(f"analysis attend_free: {Cw} does not map to any specific course")
                            else:
                                debug(f"analysis attend_free: {Cw} maps to {Cs}")
                            if len(Cs) != 1:
                                warn(f"weird mapping")
                            C = Cs[0]

                            # TODO extend the logic to cover possibility of satisfying one wanted course with one of more specific courses
                            c = I.Courses[C]
                            if tc[(t,c)]:
                                debug(f"analysis attend_free: {T} is actually teaching {C}")
                                possible.append(C)
                                continue
                            s = cs[I.Courses[C]]
                            if s >= 0 and I.input_data[T]["slots"][s] == 0:
                                debug(f"analysis attend_free: time conflict {T} / {C} / {s}")
                                not_possible.append(C)
                                continue
                            # teaching ocnflicts
                            Cos = [Co for Co in set(I.courses) - set( (C,) ) if tc[(t,I.Courses[Co])] and cs[I.Courses[Co]] == s]
                            if Cos:
                                debug(f"analysis attend_free: teaching conflict {T} / {C} / {Cos}")
                                not_possible.append(C)
                                continue

#                            for Co in set(I.courses) - set( (C,) ):
#                                co = I.Courses[Co]
#                                if tc[(t,co)] and cs[co] == s:
#                                    debug(f"analysis attend_free: teaching conflict {T} / {C} / {Co}")
#                                    not_possible.append(C)
#                                    continue
                            possible.append(C)
                        if possible:
                            debug(f"analysis attend_free: teacher {T} possible: {', '.join(possible)}")
                        if not_possible:
                            debug(f"analysis attend_free: teacher {T} not_possible: {', '.join(not_possible)}")
                            result.append(f"{T}: {', '.join(not_possible)}")
                        else:
                            debug(f"analysis attend_free: {T} 100% happy")
                    return result
                penalties_analysis[name] = analysis
            elif name == "teach_together": # penalty if interested in teaching with Ts but teaches with noone
                # IDEA: make this somehow counted as percent of courses taught with non-liked teachers?
                # e.g., teaching 3 courses with liked and 2 with other would mean 40% penalty
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
                    boost = 1
                    if I.input_data[T]["bestpref"] == "person":
                        debug(f"teach_together: boosting people preferences for {T}")
                        boost = I.BOOSTER
                    if not I.tt_together[T]:
                        debug(f"teach_together: no preference => no penalty for {T}")
                        boost = 0
                    boosted = model.NewIntVar(0, I.BOOSTER, "")
                    model.Add(boosted == boost * nobody)
                    penalties_teach_together.append(boosted)
                penalties[name] = penalties_teach_together
                def analysis(R):
                    src = R.src
                    tc = R.tc
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
            elif name == "courses_closed": # penalty if too little courses are opened
                penalties_courses_closed = []
                total_courseslots = 4 * 3 * 2 # days, times, rooms
                n_active = model.NewIntVar(0, total_courseslots, "")
                n_closed = model.NewIntVar(0, total_courseslots, "")
                model.Add(n_closed == total_courseslots - sum(M.c_active))
                penalties_courses_closed = [n_closed]
                penalties[name] = penalties_courses_closed
            elif name == "stud_bad": # penalty if student cannot attend desired course
                penalties_stud_bad = []
                for S, val in I.input_data.items():
                    if val["type"] != "student":
                        debug(f"stud_bad: skipping {S}, not a student")
                        continue
                    debug(f"stud_bad: student {S}")
                    if "provided_id" in val:
                        debug(f"stud_bad: provided_id '{val['provided_id']}'")
                    else:
                        debug(f"stud_bad: no id provided")
                    courses_bad = []
                    for C in val["courses_attend"]:
                        Cs = [Cspec for Cspec in I.courses if I.is_course_type(Cspec, C)]
                        if not Cs:
                            warn(f"stud_bad: no specific course found for {C}")
                            continue
                        slots_available = [s for s in range(len(I.slots)) if val["slots"][s] != 0]
                        course_cannot = model.NewBoolVar("")
                        model.Add(sum(M.src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) == 0).OnlyEnforceIf(course_cannot)
                        model.Add(sum(M.src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) >= 1).OnlyEnforceIf(course_cannot.Not())
                        courses_bad.append(course_cannot)
                    n_courses_bad = model.NewIntVar(0, len(I.courses), "")
                    model.Add(n_courses_bad == sum(courses_bad))
                    penalties_stud_bad.append(n_courses_bad)
                penalties[name] = penalties_stud_bad
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    result = []
                    total_bad = 0
#                    total_open = 0
                    total_ok = 0
                    courses_bad_stats = {}
                    courses_ok_stats = {}
                    for S, val in I.input_data.items():
                        if val["type"] != "student":
                            debug(f"analysis stud_bad: skipping {S}, not a student")
                            continue
                        debug(f"analysis stud_bad: student {S}")
                        who = f"{S}"
                        if "provided_id" in val:
                            who += f"({val['provided_id']})"
                            debug(f"analysis stud_bad: provided_id '{val['provided_id']}'")
                        else:
                            debug(f"analysis stud_bad: no id provided")
                        courses_bad = []
#                        courses_na_open = []
                        courses_ok = []
                        slots_available = [s for s in range(len(I.slots)) if val["slots"][s] != 0]
                        debug(f"analysis stud_bad: slots_available: {slots_available}")
                        for C in val["courses_attend"]:
                            Cs = [Cspec for Cspec in I.courses if I.is_course_type(Cspec, C)]
                            if not Cs:
                                warn(f"analysis stud_bad: no specific course found for {C}")
                                continue
                            debug(f"analysis stud_bad: specific courses: {', '.join(Cs)}")
                            if sum(src[(s,r,I.Courses[CC])] for s in slots_available for r in range(len(I.rooms)) for CC in Cs) == 0:
                                courses_bad.append(C)
                                total_bad += 1
                                if C in courses_bad_stats:
                                    courses_bad_stats[C] += 1
                                else:
                                    courses_bad_stats[C] = 1

#                                if any([CCC in I.courses_must_open for CCC in Cs]):
#                                    # FIXME: this looks like a bad attempt to get active courses, use c_active
#                                    courses_na_open.append(C)
#                                    total_open += 1
                            else:
                                courses_ok.append(C)
                                total_ok += 1
                                if C in courses_ok_stats:
                                    courses_ok_stats[C] += 1
                                else:
                                    courses_ok_stats[C] = 1
#                        if courses_na_open:
                        if courses_bad:
                            debug(f"analysis stud_bad: courses_bad: {who}: {', '.join(courses_bad)}")
#                            debug(f"analysis stud_bad: courses_na_open: {who}: {', '.join(courses_na_open)}")
#                            result.append(f"{who} [{', '.join(courses_na_open)}]")
                            result.append(f"{who} [{', '.join(courses_bad)}]")
                        if courses_ok:
                            debug(f"analysis stud_bad: courses OK: {who}: {', '.join(courses_ok)}")
                    debug(f"Students missed:\n{pprint.pformat(result)}")
                    courses_bad_stats_view = sorted( ((v,k) for k,v in courses_bad_stats.items()), reverse=True)
                    result = [f"{k} ({v})" for v,k in courses_bad_stats_view] # FIXME
                    info(f"Students missed statistics:\n{pprint.pformat(courses_bad_stats_view)}")
                    courses_ok_stats_view = sorted( ((v,k) for k,v in courses_ok_stats.items()), reverse=True)
                    info(f"Students ok statistics:\n{pprint.pformat(courses_ok_stats_view)}")
#                    info(f"analysis stud_bad: total missed: {total_bad}, open missed: {total_open}, total OK: {total_ok}")
                    info(f"analysis stud_bad: total missed: {total_bad}, total OK: {total_ok}")
                    return result
                penalties_analysis[name] = analysis
            elif name == "custom":
                penalties_custom = self.custom_penalties.values()
                penalties[name] = penalties_custom
                def analysis(R):
                    src = R.src
                    tc = R.tc
                    cp = R.custom_penalties
                    result = []
                    for name, v in cp.items():
                        if v:
                            result.append(name)
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
            debug(f"Courses openness and indices")
            R.c_active = []
            R.cs = []
            for c in range(len(I.courses)):
                R.c_active.append(self.Value(M.c_active[c]))
                debug(f"{I.courses[c]: <30}: {self.Value(M.c_active[c])} {self.Value(M.cs[c])}")
                R.cs.append(self.Value(M.cs[c]))
            R.penalties = {}
            # FIXME how to access penalties?
            for (name, l) in M.penalties.items():
                v = sum([self.Value(p) for p in l])
                coeff = I.PENALTIES[name]
                R.penalties[name] = (coeff, v)
            R.custom_penalties = {}
            for name, v in M.custom_penalties.items():
                R.custom_penalties[name] = self.Value(v)
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
                                    Ts_print = f"{Ts[0] :<9}+ {Ts[1]}"
                                else:
                                    Ts_print = f"{Ts[0]}"
                                #print(f"{I.slots[s]: <11}{I.rooms[r]: <5}{'+'.join(Ts): <19}{I.courses[c]}")
                                print(f"{I.slots[s]: <11}{I.rooms[r]: <5}{Ts_print: <21}{I.courses[c]}")
                if penalties:
                    print("Penalties:")
                    total = 0
                    total_teachers = 0
                    for (name, t) in penalties.items():
                        coeff, v = t
                        total += coeff * v
                        if name not in ("stud_bad",):
                            total_teachers += coeff * v
                        if v == 0 or name not in penalties_analysis:
                            print(f"{name}: {v} * {coeff} = {v*coeff}")
                        else:
                            print(f"{name}: {v} * {coeff} = {v*coeff} ({', '.join(penalties_analysis[name](R))})")
                if utilization:
                    debug("UTILIZATION:")
                    tn = {}
                    #for t in range(len(I.teachers)):
                        #tn[I.teachers[t]] = sum(tc[t,c] for c in range(len(I.courses)))
                    for T in I.teachers:
                        tn[T] = sum(tc[I.Teachers[T],c] for c in range(len(I.courses)))
                    for v in sorted(set(tn.values())):
                        print(f"{v}: {', '.join(t for t in tn if tn[t] == v)}")
                print(f"TOTAL: {total}")
                print(f"TEACHERS: {total_teachers}")

            debug(pprint.pformat(R))
            print_solution(R, M.penalties_analysis, self.ObjectiveValue())
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
            for T in self.I.teachers:
                if solver.Value(self.teach_num[self.I.Teachers[T]]) == n:
                    Ts.append(T)
            if Ts:
                print(f"{n}: {' '.join(Ts)}")


# The worst argument parser in the history of argument parsers, maybe ever.
def parse(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Debug output")
    parser.add_argument("-s", "--students", action="store", dest="students", help="Students' preferences CSV")
    parser.add_argument("-t", "--teachers", action="store", dest="teachers", help="Teachers' preferences CSV")
    parser.add_argument("-p", "--penalty", action="append", dest="penalties", help="Penalty value 'name:X'")
    args = parser.parse_args()

    if args.verbose:
        set_verbose()

    penalties = {}
    if args.penalties:
        for x in args.penalties:
            name, value = x.split(":")
            penalties[name] = int(value)

    return (args.teachers, args.students, penalties)

def main():
    teach_csv, stud_csv, penalties = parse()

    # all input information
    input = Input()
    input.init(teach_csv, students_csv=stud_csv, penalties=penalties)

    # model construction
    model = Model()
    model.init(input)

    # run the solver
    model.solve()

if __name__ == "__main__":
    main()
