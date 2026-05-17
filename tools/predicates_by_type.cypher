// tools/predicates_by_type.cypher
//
// Single source of truth for "non-empty value" predicates per primitive
// type. Phase C adapter verifiers (`tools/verify_adapter_*.py`) reference
// these predicates via `tools/predicates.py.substitute(query)`; inline
// predicates in verifier scripts are forbidden by RESEED_PLAN C.5.
//
// Format (parsed by tools/predicates.py):
//
//     $pred_<type>(<placeholder>) := <cypher boolean expression>
//
// `<type>` is one of: string, int, float, bool, list.
// `<placeholder>` is a single identifier that the loader replaces with
// the caller-supplied expression at substitution time.

$pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ""

$pred_int(x)    := x IS NOT NULL

$pred_float(x)  := x IS NOT NULL AND NOT (x <> x) AND x < (1.0/0.0) AND x > -(1.0/0.0)

$pred_bool(x)   := x IS NOT NULL

$pred_list(x)   := x IS NOT NULL AND size(x) > 0
