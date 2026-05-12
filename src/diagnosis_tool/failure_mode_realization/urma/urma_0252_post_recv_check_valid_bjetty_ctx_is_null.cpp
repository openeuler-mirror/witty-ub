#include "urma_0252_post_recv_check_valid_bjetty_ctx_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0252PostRecvCheckValidBjettyCtxIsNull> g_urma("urma_0252");

bool Urma0252PostRecvCheckValidBjettyCtxIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bjetty_ctx is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0252PostRecvCheckValidBjettyCtxIsNull::GetName() const
{
    return "post_recv_check_valid bjetty_ctx is NULL";
}

std::string Urma0252PostRecvCheckValidBjettyCtxIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bjetty_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0252PostRecvCheckValidBjettyCtxIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0252PostRecvCheckValidBjettyCtxIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0252PostRecvCheckValidBjettyCtxIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bjetty_ctx is NULL";
}

std::string Urma0252PostRecvCheckValidBjettyCtxIsNull::GetId() const
{
    return "urma_0252";
}
} // namespace diag
