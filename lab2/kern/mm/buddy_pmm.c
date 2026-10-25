#include <buddy_pmm.h>
#include <stdio.h>

/* Order k contains blocks of 2^k pages. Alignment is relative to DRAM_BASE.
 * Requests round UP to a power of two; free_pages(base,n) uses the original n.
 * This allocator is for the single-hart teaching kernel (no locking). */
#define MAX_ORDER 18
static list_entry_t lists[MAX_ORDER + 1];
static size_t free_count;

static unsigned order_for(size_t n) {
    unsigned k = 0;
    while (((size_t)1 << k) < n && k < MAX_ORDER) k++;
    return k;
}
static void insert(struct Page *p, unsigned k) {
    p->property = (size_t)1 << k;
    SetPageProperty(p);
    list_add(&lists[k], &p->page_link);
}
static void remove_block(struct Page *p) {
    list_del(&p->page_link);
    ClearPageProperty(p);
}
static void buddy_init(void) {
    for (unsigned k = 0; k <= MAX_ORDER; k++) list_init(&lists[k]);
    free_count = 0;
}
static void buddy_init_memmap(struct Page *base, size_t n) {
    assert(n > 0);
    for (struct Page *p = base; p < base + n; p++) {
        assert(PageReserved(p));
        p->flags = 0;
        p->property = 0;
        set_page_ref(p, 0);
    }
    free_count += n;
    while (n) {
        size_t idx = base - pages;
        unsigned k = MAX_ORDER;
        while (((size_t)1 << k) > n || (idx & (((size_t)1 << k) - 1))) k--;
        insert(base, k);
        base += (size_t)1 << k;
        n -= (size_t)1 << k;
    }
}
static struct Page *buddy_alloc_pages(size_t n) {
    assert(n > 0);
    if (n > ((size_t)1 << MAX_ORDER)) return NULL;
    unsigned want = order_for(n), k = want;
    while (k <= MAX_ORDER && list_empty(&lists[k])) k++;
    if (k > MAX_ORDER) return NULL;
    struct Page *p = le2page(list_next(&lists[k]), page_link);
    remove_block(p);
    while (k > want) {
        k--;
        insert(p + ((size_t)1 << k), k);
    }
    p->property = (size_t)1 << want;
    free_count -= p->property;
    return p;
}
static void buddy_free_pages(struct Page *base, size_t n) {
    assert(n > 0 && n <= ((size_t)1 << MAX_ORDER));
    unsigned k = order_for(n);
    size_t amount = (size_t)1 << k;
    assert(base >= pages && base + amount <= pages + npage - nbase);
    assert(!PageProperty(base) && base->property == amount);
    for (struct Page *p = base; p < base + amount; p++) {
        assert(!PageReserved(p) && !PageProperty(p));
        p->flags = 0;
        p->property = 0;
        set_page_ref(p, 0);
    }
    free_count += amount;
    while (k < MAX_ORDER) {
        size_t idx = base - pages;
        size_t other_idx = idx ^ ((size_t)1 << k);
        if (other_idx >= npage - nbase) break;
        struct Page *other = pages + other_idx;
        if (!PageProperty(other) || other->property != ((size_t)1 << k)) break;
        remove_block(other);
        other->property = 0;
        if (other < base) base = other;
        k++;
    }
    insert(base, k);
}
static size_t buddy_nr_free_pages(void) { return free_count; }
static void buddy_check(void) {
    size_t before = free_count;
    struct Page *a = buddy_alloc_pages(3), *b = buddy_alloc_pages(5);
    assert(a && b && a != b);
    assert(a->property == 4 && b->property == 8);
    assert(((a - pages) & 3) == 0 && ((b - pages) & 7) == 0);
    assert(free_count == before - 12);
    buddy_free_pages(a, 3);
    buddy_free_pages(b, 5);
    assert(free_count == before);
    assert(buddy_alloc_pages(before + 1) == NULL);
    /* Exhaust RAM one page at a time; use allocated descriptors as a list. */
    list_entry_t allocated;
    list_init(&allocated);
    size_t count = 0;
    while ((a = buddy_alloc_pages(1)) != NULL) {
        list_add(&allocated, &a->page_link);
        count++;
    }
    assert(count == before && free_count == 0);
    while (!list_empty(&allocated)) {
        a = le2page(list_next(&allocated), page_link);
        list_del(&a->page_link);
        buddy_free_pages(a, 1);
    }
    assert(free_count == before);
    size_t sum = 0;
    for (unsigned k = 0; k <= MAX_ORDER; k++) {
        list_entry_t *le;
        for (le = list_next(&lists[k]); le != &lists[k]; le = list_next(le)) {
            a = le2page(le, page_link);
            assert(PageProperty(a) && a->property == ((size_t)1 << k));
            size_t idx = a - pages;
            assert((idx & (a->property - 1)) == 0);
            size_t bi = idx ^ a->property;
            if (k < MAX_ORDER && bi < npage - nbase) {
                struct Page *other = pages + bi;
                assert(!PageProperty(other) || other->property != a->property);
            }
            sum += a->property;
        }
    }
    assert(sum == before);
    cprintf("buddy_check() succeeded! (rounding/alignment/exhaustion/coalescing)\n");
}
const struct pmm_manager buddy_pmm_manager = {
    .name = "buddy_pmm_manager", .init = buddy_init,
    .init_memmap = buddy_init_memmap, .alloc_pages = buddy_alloc_pages,
    .free_pages = buddy_free_pages, .nr_free_pages = buddy_nr_free_pages,
    .check = buddy_check,
};
