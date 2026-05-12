#include "urma_1056_bondp_post_send_wr_no_store_bondp_supports_at_most.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost> g_urma("urma_1056");

bool Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Bondp supports at most % wr_list."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::GetName() const
{
    return "bondp_post_send_wr_no_store Bondp supports at most % wr_list.";
}

std::string Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `index >= BONDP_MAX_WR_LIST_NUM - 1`；该路径返回 URMA_EINVAL";
}

RootCause Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Bondp supports at most % wr_list.";
}

std::string Urma1056BondpPostSendWrNoStoreBondpSupportsAtMost::GetId() const
{
    return "urma_1056";
}
} // namespace diag
