#include "urma_0233_bondp_post_send_wr_no_store_wr_tjetty_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0233BondpPostSendWrNoStoreWrTjettyIsNull> g_urma("urma_0233");

bool Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"WR->tjetty is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::GetName() const
{
    return "bondp_post_send_wr_no_store WR->tjetty is NULL";
}

std::string Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_tjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：WR->tjetty is NULL";
}

std::string Urma0233BondpPostSendWrNoStoreWrTjettyIsNull::GetId() const
{
    return "urma_0233";
}
} // namespace diag
