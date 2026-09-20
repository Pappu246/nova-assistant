from memory import save_fact, get_fact, forget_fact, list_facts

# Fix the confusion: Sahid is friend, not sister
print("Before:")
print(list_facts())
print()

# Save Sahid as friend (already there), remove sister if it's Sahid
sister = get_fact("sister_name")
if sister and sister.lower() == "sahid":
    result = forget_fact("sister_name")
    print("Removed wrong sister_name:", result)

# Make sure friend_name is Sahid
save_fact("friend_name", "Sahid", "friend")

# Save user identity (Dara)
import identity
result = identity.set_name("Dara", confirmed=True)
print("Identity set:", result)

print()
print("After:")
print(list_facts())
print()
print("Verified name:", identity.get_name())
