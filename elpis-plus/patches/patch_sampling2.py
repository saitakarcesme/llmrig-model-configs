"""elpis-plus 0001 (part 2): sampled / stop-string jobs never take the admitted greedy path; check exactly that."""
import sys
p = sys.argv[1]; s = open(p).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)
sub('''        if (
            self.verified_acceptance
            and self.gen.greedy_verify_rounds - verified_before != spec_rounds
        ):''', '''        # elpis-plus: a non-greedy job (sampled or with stop strings) is ineligible for the admitted greedy
        # path, so it must commit zero greedy (and zero tree) rounds; a greedy job must commit all of them
        greedy_job = pending.options.is_greedy_identity()
        if (
            self.verified_acceptance
            and self.gen.greedy_verify_rounds - verified_before
            != (spec_rounds if greedy_job else 0)
        ):''')
sub('''        if tree_rounds != (spec_rounds if self.tree_rounds_expected else 0):''',
    '''        if tree_rounds != (spec_rounds if self.tree_rounds_expected and greedy_job else 0):''')
open(p, "w").write(s); print("patched")
