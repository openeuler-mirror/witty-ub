#include "urma_1152_urma_free_token_id_ref_not_zero.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1152UrmaFreeTokenIdRefNotZero> g_urma("urma_1152");

bool Urma1152UrmaFreeTokenIdRefNotZero::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ref:%, not zero"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1152UrmaFreeTokenIdRefNotZero::GetName() const
{
    return "urma_free_token_id ref:%, not zero";
}

std::string Urma1152UrmaFreeTokenIdRefNotZero::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `atomic_load(&token_id->ref.atomic_cnt) != 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma1152UrmaFreeTokenIdRefNotZero::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1152UrmaFreeTokenIdRefNotZero::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1152UrmaFreeTokenIdRefNotZero::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ref:%, not zero";
}

std::string Urma1152UrmaFreeTokenIdRefNotZero::GetId() const
{
    return "urma_1152";
}
} // namespace diag
