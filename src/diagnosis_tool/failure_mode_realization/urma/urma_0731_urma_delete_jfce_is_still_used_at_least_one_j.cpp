#include "urma_0731_urma_delete_jfce_is_still_used_at_least_one_j.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ> g_urma("urma_0731");

bool Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Jfce is still used by at least one jfc, refcnt:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::GetName() const
{
    return "urma_delete_jfce Jfce is still used by at least one j";
}

std::string Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `atomic_load(&jfce->ref.atomic_cnt) > 1`；该路径返回 URMA_FAIL";
}

RootCause Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Jfce is still used by at least one jfc, refcnt:%.";
}

std::string Urma0731UrmaDeleteJfceIsStillUsedAtLeastOneJ::GetId() const
{
    return "urma_0731";
}
} // namespace diag
