#include <abstractions/base>

profile bozly_global_core /app/bozly_armored_core.py {
    /app/bozly_armored_core.py r,
    /app/secure_ledgers/bozly_financial_core.db rwk,
    /app/secure_ledgers/bozly_financial_core.db-wal rwk,
    /app/secure_ledgers/bozly_financial_core.db-shm rwk,

    deny ptrace (readby, tracedby),
    deny signal (receive) peer=*,

    deny /bin/dash x,
    deny /bin/bash x,
}
