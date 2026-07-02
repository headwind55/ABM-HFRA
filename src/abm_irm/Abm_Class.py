"""Agent classes used by the ABM-IRM household simulation."""


class HouseHold:
    """Household agent that stores location, members, type, and residential duration."""
    def __init__(self, mesh_id, hh_id, members, old_hh, income=0, housevalue=0, expenditure=0, saving=0, live_year=0):
        """Create a household agent with the attributes used by the model."""
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

    def __repr__(self):
        """Return a compact representation for debug output and saved household traces."""
        return f'Household(mesh={self.mesh_id}, hh_id={self.hh_id}, members={self.members}, elder={self.old_hh}, exist={self.exist}, agriculture={self.agri}, living={self.live_year})'

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
