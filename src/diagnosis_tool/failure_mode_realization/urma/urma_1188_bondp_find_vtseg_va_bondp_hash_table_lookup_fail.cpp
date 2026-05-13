#include "urma_1188_bondp_find_vtseg_va_bondp_hash_table_lookup_fail.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1188BondpFindVtsegVaBondpHashTableLookupFail> g_urma("urma_1188");

bool Urma1188BondpFindVtsegVaBondpHashTableLookupFail::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bondp_hash_table_lookup fail."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1188BondpFindVtsegVaBondpHashTableLookupFail::GetName() const
{
    return "bondp_find_vtseg_by_va bondp_hash_table_lookup fail.";
}

std::string Urma1188BondpFindVtsegVaBondpHashTableLookupFail::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `node == NULL`；该路径返回 NULL";
}

RootCause Urma1188BondpFindVtsegVaBondpHashTableLookupFail::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1188BondpFindVtsegVaBondpHashTableLookupFail::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1188BondpFindVtsegVaBondpHashTableLookupFail::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bondp_hash_table_lookup fail.";
}

std::string Urma1188BondpFindVtsegVaBondpHashTableLookupFail::GetId() const
{
    return "urma_1188";
}
} // namespace diag
