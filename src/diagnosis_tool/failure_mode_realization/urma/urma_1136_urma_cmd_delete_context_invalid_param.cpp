#include "urma_1136_urma_cmd_delete_context_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1136UrmaCmdDeleteContextInvalidParam> g_urma("urma_1136");

bool Urma1136UrmaCmdDeleteContextInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1136UrmaCmdDeleteContextInvalidParam::GetName() const
{
    return "urma_cmd_delete_context 参数非法";
}

std::string Urma1136UrmaCmdDeleteContextInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0`；该路径返回 -1";
}

RootCause Urma1136UrmaCmdDeleteContextInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1136UrmaCmdDeleteContextInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1136UrmaCmdDeleteContextInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1136UrmaCmdDeleteContextInvalidParam::GetId() const
{
    return "urma_1136";
}
} // namespace diag
