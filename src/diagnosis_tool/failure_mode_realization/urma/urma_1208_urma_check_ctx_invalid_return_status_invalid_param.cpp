#include "urma_1208_urma_check_ctx_invalid_return_status_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam> g_urma("urma_1208");

bool Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::GetName() const
{
    return "URMA_CHECK_CTX_INVALID_RETURN_STATUS 参数非法";
}

std::string Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 URMA_EINVAL";
}

RootCause Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1208UrmaCheckCtxInvalidReturnStatusInvalidParam::GetId() const
{
    return "urma_1208";
}
} // namespace diag
