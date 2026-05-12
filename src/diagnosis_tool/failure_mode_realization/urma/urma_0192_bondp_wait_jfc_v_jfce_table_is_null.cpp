#include "urma_0192_bondp_wait_jfc_v_jfce_table_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0192BondpWaitJfcVJfceTableIsNull> g_urma("urma_0192");

bool Urma0192BondpWaitJfcVJfceTableIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"v_jfce_table is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0192BondpWaitJfcVJfceTableIsNull::GetName() const
{
    return "bondp_wait_jfc v_jfce_table is NULL.";
}

std::string Urma0192BondpWaitJfcVJfceTableIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `v_jfce_table == NULL`；该路径返回 -1";
}

RootCause Urma0192BondpWaitJfcVJfceTableIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0192BondpWaitJfcVJfceTableIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0192BondpWaitJfcVJfceTableIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：v_jfce_table is NULL.";
}

std::string Urma0192BondpWaitJfcVJfceTableIsNull::GetId() const
{
    return "urma_0192";
}
} // namespace diag
