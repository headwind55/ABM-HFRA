"""Agent classes used by the ABM-IRM household simulation."""


class HouseHold:
    """Household agent that stores location, members, type, and residential duration."""

    _next_household_uid = 1

    def __init__(self, mesh_id, hh_id, members, old_hh, income=0, housevalue=0, expenditure=0, saving=0, live_year=0):
        """Create a household agent with the attributes used by the model."""
        self.household_uid = HouseHold._next_household_uid
        HouseHold._next_household_uid += 1
        self.mesh_id = mesh_id
        self.hh_id = hh_id
        self.members = members
        self.exist = True
        self.old_hh = old_hh
        self.agri = False
        self.income = income
        self.housevalue = housevalue
        self.expenditure = expenditure
        self.saving = saving
        self.live_year = live_year
        self.tp = 0.0
        self.tp0 = None
        self.cp = 0.0
        self.sp = 0.0
        self.psy = 0.0
        self.pa = 0.0
        self.sc = 0.0
        self.experienced = 0
        self.tp_initialized = False
        self.tp_t0_year = None
        self.tp_last_update_year = None
        self.tp_start = None
        self.tp_pre_flood = None
        self.tp_post_flood = None
        self.hbm_group = None
        self.p_move_disaster = 0.0
        self.disaster_move = False
        self.disaster_old_mesh = None
        self.disaster_new_mesh = None
        # Annual PIns_01 coverage; insured households have full asset coverage.
        self.insured = False
        self.insurance_expire_year = None
        self.insurance_initialized = False
        self.insurance_efficacy = None
        self.insurance_affordability = None
        self.provider_trust = None
        self.p_insurance = None
        self.insurance_decision = "not_evaluated"
        self.insurance_origin = None

    def __repr__(self):
        """Return a compact representation for debug output and saved household traces."""
        return f'Household(uid={self.household_uid}, mesh={self.mesh_id}, hh_id={self.hh_id}, members={self.members}, elder={self.old_hh}, exist={self.exist}, agriculture={self.agri}, living={self.live_year})'

    def add_member(self, person, max_size=8):
        """Add a person if the household has remaining capacity."""
        if len(self.members) < max_size:
            self.members.append(person)
            return True
        return False

    def get_family_size(self):
        """Return the current number of household members."""
        return len(self.members)

    def household_combine(self, other_self):
        """Merge another household's members into this household."""
        self.members.extend(other_self.members)

    def liveyear_update(self):
        """Increase residential duration by one year."""
        self.live_year = self.live_year + 1


def ensure_household_uid(household):
    """Attach a permanent household UID to household objects created by older code."""
    if not hasattr(household, "household_uid") or household.household_uid is None:
        household.household_uid = HouseHold._next_household_uid
        HouseHold._next_household_uid += 1
    return household.household_uid


def ensure_household_uids(households):
    """Ensure every household in a collection has a permanent UID."""
    for household in households:
        ensure_household_uid(household)
    return households


class FamilyMember:
    """Individual member agent nested inside a household."""

    def __init__(self, age, sex=None, marriage=False, income=0, saving=0, expenditure=0):
        """Create a family-member agent with the attributes used by the model."""
        self.age = age
        self.sex = sex
        self.alive = True
        self.marriage = marriage
        self.income = income
        self.saving = saving
        self.expenditure = expenditure

    def age_one_year(self):
        """Increase member age by one year."""
        self.age = self.age + 1

    def __repr__(self):
        """Return a compact representation for debug output."""
        return f'FamilyMember(age={self.age}, sex={self.sex}, marriage={self.marriage}, )'
