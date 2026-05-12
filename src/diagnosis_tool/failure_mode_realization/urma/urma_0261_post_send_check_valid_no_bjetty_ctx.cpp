#include "urma_0261_post_send_check_valid_no_bjetty_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0261PostSendCheckValidNoBjettyCtx> g_urma("urma_0261");

bool Urma0261PostSendCheckValidNoBjettyCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"No bjetty_ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0261PostSendCheckValidNoBjettyCtx::GetName() const
{
    return "post_send_check_valid No bjetty_ctx";
}

std::string Urma0261PostSendCheckValidNoBjettyCtx::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bjetty_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0261PostSendCheckValidNoBjettyCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0261PostSendCheckValidNoBjettyCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0261PostSendCheckValidNoBjettyCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：No bjetty_ctx";
}

std::string Urma0261PostSendCheckValidNoBjettyCtx::GetId() const
{
    return "urma_0261";
}
} // namespace diag
