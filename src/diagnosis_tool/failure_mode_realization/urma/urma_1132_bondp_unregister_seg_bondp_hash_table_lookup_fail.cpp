#include "urma_1132_bondp_unregister_seg_bondp_hash_table_lookup_fail.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1132BondpUnregisterSegBondpHashTableLookupFail> g_urma("urma_1132");

bool Urma1132BondpUnregisterSegBondpHashTableLookupFail::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bondp_hash_table_lookup fail."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1132BondpUnregisterSegBondpHashTableLookupFail::GetName() const
{
    return "bondp_unregister_seg bondp_hash_table_lookup fail.";
}

std::string Urma1132BondpUnregisterSegBondpHashTableLookupFail::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `va_vtseg == NULL`";
}

RootCause Urma1132BondpUnregisterSegBondpHashTableLookupFail::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1132BondpUnregisterSegBondpHashTableLookupFail::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1132BondpUnregisterSegBondpHashTableLookupFail::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bondp_hash_table_lookup fail.";
}

std::string Urma1132BondpUnregisterSegBondpHashTableLookupFail::GetId() const
{
    return "urma_1132";
}
} // namespace diag
