import rules


@rules.predicate
def owns_book_record(user, obj):
    if obj.library.user == user:
        return True
    return False


rules.add_perm("collections.can_delete_book", owns_book_record)
