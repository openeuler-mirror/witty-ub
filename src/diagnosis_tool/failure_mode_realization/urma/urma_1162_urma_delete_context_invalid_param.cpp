#include "urma_1162_urma_delete_context_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1162UrmaDeleteContextInvalidParam> g_urma("urma_1162");

bool Urma1162UrmaDeleteContextInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1162UrmaDeleteContextInvalidParam::GetName() const
{
    return "urma_delete_context 参数非法";
}

std::string Urma1162UrmaDeleteContextInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev == NULL || ctx->dev->ops == NULL || "
           "ctx->dev->ops->delete_context == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1162UrmaDeleteContextInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1162UrmaDeleteContextInvalidParam::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma1162UrmaDeleteContextInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1162UrmaDeleteContextInvalidParam::GetId() const
{
    return "urma_1162";
}
} // namespace diag
